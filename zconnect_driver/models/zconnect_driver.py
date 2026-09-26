# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
#
# Architecture decision (ADR-003):
#   res.partner  = master person/contact identity
#   zconnect.driver = logistics-specific operational profile
#
# We read name/phone/email/address from partner_id. We do NOT copy them
# here. This ensures there is one source of truth for contact data.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


# ── Lifecycle constants — defined at module level for testability ────────────

VERIFICATION_STATUS = [
    ('unverified', 'Unverified'),
    ('pending', 'Pending Review'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
]

AVAILABILITY_STATUS = [
    ('offline', 'Offline'),
    ('available', 'Available'),
    ('unavailable', 'Unavailable'),
]

LICENCE_CLASS = [
    ('class_1', 'Class 1 — Heavy Articulated / Interlink'),
    ('class_2', 'Class 2 — Heavy Rigid Truck'),
    ('class_3', 'Class 3 — Light Goods Vehicle'),
    ('class_4', 'Class 4 — Light Motor Vehicle'),
    ('class_5', 'Class 5 — Motorcycle'),
]

# Valid transitions: {current_state: [allowed_target_states]}
_VERIFICATION_TRANSITIONS = {
    'unverified': ['pending'],
    'pending': ['verified', 'rejected'],
    'verified': ['pending'],          # Re-submission allowed (e.g. licence renewal)
    'rejected': ['pending'],          # Re-application allowed
}

_AVAILABILITY_TRANSITIONS = {
    'offline': ['available'],
    'available': ['unavailable', 'offline'],
    'unavailable': ['available', 'offline'],
}


class ZconnectDriver(models.Model):
    """
    Zimbabwe Connect logistics driver operational profile.

    Identity/contact information lives on res.partner (partner_id).
    This model holds only logistics-specific operational attributes:
    KYC status, licence details, availability, and vehicle associations.

    Future shipment assignments will be managed by zconnect.dispatch.assignment,
    NOT by fields on this model.
    """

    _name = 'zconnect.driver'
    _description = 'Zimbabwe Connect Driver Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'driver_code'
    _order = 'driver_code asc'

    # ── Identity link ────────────────────────────────────────────────────────

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact / Person',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='The person this driver profile belongs to. '
             'Name, phone, email, and address are read from this contact. '
             'Do not duplicate those fields here.',
    )

    # Convenience computed fields that expose partner identity without duplication.
    name = fields.Char(related='partner_id.name', string='Driver Name', store=True, readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)

    # ── Identification ──────────────────────────────────────────────────────

    driver_code = fields.Char(
        string='Driver Code',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
        help='Unique, stable driver identifier (e.g. DRV-00001). '
             'Generated automatically from ir.sequence and never regenerated.',
    )

    national_id = fields.Char(
        string='National ID (Zimbabwe)',
        tracking=True,
        help='Zimbabwe National Registration Certificate (NRC) number.',
    )

    # ── Licence ─────────────────────────────────────────────────────────────

    licence_class = fields.Selection(
        selection=LICENCE_CLASS,
        string='Licence Class',
        tracking=True,
        help='Zimbabwe driving licence class. Determines eligible vehicle types.',
    )

    licence_number = fields.Char(
        string='Licence Number',
        tracking=True,
    )

    licence_expiry = fields.Date(
        string='Licence Expiry Date',
        tracking=True,
    )

    # ── Verification / KYC Status ────────────────────────────────────────────

    verification_status = fields.Selection(
        selection=VERIFICATION_STATUS,
        string='Verification Status',
        default='unverified',
        required=True,
        tracking=True,
        help='KYC/document verification lifecycle. '
             'A driver must be verified before they can be dispatched.',
    )

    # ── Availability ─────────────────────────────────────────────────────────

    availability_status = fields.Selection(
        selection=AVAILABILITY_STATUS,
        string='Availability',
        default='offline',
        required=True,
        tracking=True,
        help='Current on-duty availability. '
             'Separate from verification status — a driver can be verified '
             'but currently offline or unavailable.',
    )

    # ── Vehicle Relationships ────────────────────────────────────────────────
    #
    # WHY Many2many: A driver may operate more than one vehicle over time
    # (company vehicle + personal vehicle; different vehicle classes for
    # different job types). primary_vehicle_id is a convenience pointer to
    # the current active vehicle without enforcing a single-vehicle constraint
    # at the domain model level.
    #
    # WHY NOT embedding driver_id on fleet.vehicle: fleet.vehicle already has
    # driver_id (res.partner). We do not want to confuse the Fleet-level
    # "who owns/drives this vehicle" relationship with the ZConnect-level
    # "which vehicles is this logistics driver authorised to operate".
    #
    # The actual per-delivery vehicle assignment will live on
    # zconnect.dispatch.assignment, NOT here.

    vehicle_ids = fields.Many2many(
        'fleet.vehicle',
        'zconnect_driver_vehicle_rel',
        'driver_id',
        'vehicle_id',
        string='Authorised Vehicles',
        help='Fleet vehicles this driver is authorised to operate for Zimbabwe Connect. '
             'This is an authorisation relationship, not a per-shipment assignment.',
    )

    primary_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Primary Vehicle',
        domain="[('id', 'in', vehicle_ids)]",
        help='The vehicle this driver currently uses most often. '
             'Must be one of the authorised vehicles above.',
    )

    # ── Document links ───────────────────────────────────────────────────────

    document_ids = fields.One2many(
        'zconnect.driver.document',
        'driver_id',
        string='KYC Documents',
    )

    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count',
    )

    # ── Computed / Summary ───────────────────────────────────────────────────

    is_licence_expired = fields.Boolean(
        string='Licence Expired',
        compute='_compute_is_licence_expired',
        store=False,
        help='True if the driving licence expiry date is today or in the past.',
    )

    # ── Constraints (Odoo 19 models.Constraint) ──────────────────────────────

    _partner_unique = models.Constraint(
        'UNIQUE(partner_id)',
        'A driver profile already exists for this contact. Each person can have only one driver profile.',
    )

    _driver_code_unique = models.Constraint(
        'UNIQUE(driver_code)',
        'Driver code must be unique across all driver profiles.',
    )

    # ── ORM Overrides ────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        Assign stable driver code from ir.sequence on record creation.
        The code is never regenerated — once set it is immutable.
        """
        for vals in vals_list:
            if vals.get('driver_code', _('New')) == _('New'):
                vals['driver_code'] = (
                    self.env['ir.sequence'].next_by_code('zconnect.driver.code')
                    or _('New')
                )
            # Mark the linked partner as a ZConnect driver for filtering.
            if vals.get('partner_id'):
                self.env['res.partner'].browse(vals['partner_id']).write(
                    {'zconnect_is_driver': True}
                )
        return super().create(vals_list)

    # ── Computed Field Methods ───────────────────────────────────────────────

    @api.depends('document_ids')
    def _compute_document_count(self):
        for driver in self:
            driver.document_count = len(driver.document_ids)

    @api.depends('licence_expiry')
    def _compute_is_licence_expired(self):
        today = fields.Date.today()
        for driver in self:
            driver.is_licence_expired = bool(
                driver.licence_expiry and driver.licence_expiry <= today
            )

    # ── Business Actions / State Transitions ─────────────────────────────────
    #
    # All state changes go through explicit action methods so business rules
    # are enforced uniformly from both the Odoo UI and the future API layer.

    def action_submit_for_verification(self):
        """
        Transition: unverified → pending
        Driver/dispatcher submits KYC documents for review.
        """
        for driver in self:
            self._validate_transition(
                driver.verification_status, 'pending', _VERIFICATION_TRANSITIONS, 'Verification'
            )
            driver.verification_status = 'pending'
            driver.message_post(
                body=_('Driver submitted for KYC verification review.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_verify(self):
        """
        Transition: pending → verified
        Operations manager/admin confirms KYC documents are valid.
        """
        for driver in self:
            self._validate_transition(
                driver.verification_status, 'verified', _VERIFICATION_TRANSITIONS, 'Verification'
            )
            driver.verification_status = 'verified'
            driver.message_post(
                body=_('Driver KYC verification approved. Driver is now eligible for dispatch.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """
        Transition: pending → rejected
        KYC documents fail review or are incomplete.
        """
        for driver in self:
            self._validate_transition(
                driver.verification_status, 'rejected', _VERIFICATION_TRANSITIONS, 'Verification'
            )
            driver.verification_status = 'rejected'
            driver.message_post(
                body=_('Driver KYC verification rejected. Driver must resubmit documentation.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_set_available(self):
        """Availability: → available. Requires verified status."""
        for driver in self:
            if driver.verification_status != 'verified':
                raise UserError(_(
                    'Driver "%s" must be verified before setting availability.',
                    driver.name,
                ))
            self._validate_transition(
                driver.availability_status, 'available', _AVAILABILITY_TRANSITIONS, 'Availability'
            )
            driver.availability_status = 'available'

    def action_set_unavailable(self):
        """Availability: available → unavailable (e.g. driver on break)."""
        for driver in self:
            self._validate_transition(
                driver.availability_status, 'unavailable', _AVAILABILITY_TRANSITIONS, 'Availability'
            )
            driver.availability_status = 'unavailable'

    def action_set_offline(self):
        """Availability: → offline (end of shift)."""
        for driver in self:
            self._validate_transition(
                driver.availability_status, 'offline', _AVAILABILITY_TRANSITIONS, 'Availability'
            )
            driver.availability_status = 'offline'

    # ── Internal Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_transition(current, target, allowed_map, label):
        """
        Raise UserError if transition from current → target is not in the
        allowed transitions map for the given lifecycle label.
        """
        allowed = allowed_map.get(current, [])
        if target not in allowed:
            raise UserError(_(
                '%(label)s transition from "%(current)s" to "%(target)s" is not permitted.',
                label=label,
                current=current,
                target=target,
            ))

    def action_open_documents(self):
        """Smart button: open KYC documents for this driver."""
        self.ensure_one()
        return {
            'name': _('Documents — %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'zconnect.driver.document',
            'view_mode': 'list,form',
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }
