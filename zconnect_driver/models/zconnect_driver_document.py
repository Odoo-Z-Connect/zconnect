# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
#
# Driver KYC document records. Uses standard Odoo ir.attachment for file storage.
# We do NOT build a separate file storage system or replicate Odoo Documents.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


DOCUMENT_TYPE = [
    ('national_id', 'National ID (Zimbabwe NRC)'),
    ('passport', 'Passport'),
    ('driving_licence', 'Driving Licence'),
    ('vehicle_registration', 'Vehicle Registration'),
    ('vehicle_roadworthy', 'Vehicle Roadworthy Certificate'),
    ('insurance', 'Vehicle Insurance'),
    ('police_clearance', 'Police Clearance Certificate'),
    ('other', 'Other Document'),
]

DOCUMENT_VERIFICATION_STATUS = [
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected / Expired'),
]


class ZconnectDriverDocument(models.Model):
    """
    KYC and compliance document record for a Zimbabwe Connect driver.

    File storage uses standard Odoo ir.attachment via the Binary field
    with attachment=True. No separate file-storage infrastructure is needed.
    """

    _name = 'zconnect.driver.document'
    _description = 'Zimbabwe Connect Driver Document'
    _inherit = ['mail.thread']
    _rec_name = 'display_name_computed'
    _order = 'expiry_date asc, document_type asc'

    # ── Relationships ─────────────────────────────────────────────────────────

    driver_id = fields.Many2one(
        'zconnect.driver',
        string='Driver',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True,
    )

    # ── Document Metadata ─────────────────────────────────────────────────────

    document_type = fields.Selection(
        selection=DOCUMENT_TYPE,
        string='Document Type',
        required=True,
        tracking=True,
    )

    document_number = fields.Char(
        string='Document / Reference Number',
        tracking=True,
        help='ID number, licence number, or other reference printed on the document.',
    )

    issue_date = fields.Date(string='Issue Date', tracking=True)

    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help='Date after which this document is no longer valid. '
             'Documents with a past expiry date are flagged automatically.',
    )

    # ── File Attachment ───────────────────────────────────────────────────────

    attachment = fields.Binary(
        string='Document Scan / Photo',
        attachment=True,
        help='Scanned copy or photograph of the document. '
             'Stored as a standard Odoo attachment.',
    )

    attachment_filename = fields.Char(string='Filename')

    # ── Verification Workflow ─────────────────────────────────────────────────

    verification_status = fields.Selection(
        selection=DOCUMENT_VERIFICATION_STATUS,
        string='Verification Status',
        default='pending',
        required=True,
        tracking=True,
    )

    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        readonly=True,
        tracking=True,
        copy=False,
    )

    verified_at = fields.Datetime(
        string='Verified At',
        readonly=True,
        tracking=True,
        copy=False,
    )

    notes = fields.Text(
        string='Notes',
        help='Reviewer comments or rejection reasons.',
    )

    # ── Computed ─────────────────────────────────────────────────────────────

    display_name_computed = fields.Char(
        compute='_compute_display_name_computed',
        store=True,
        string='Document',
    )

    is_expired = fields.Boolean(
        compute='_compute_is_expired',
        store=False,
        string='Expired',
    )

    @api.depends('document_type', 'document_number')
    def _compute_display_name_computed(self):
        for rec in self:
            type_label = dict(DOCUMENT_TYPE).get(rec.document_type, '')
            num = f' ({rec.document_number})' if rec.document_number else ''
            rec.display_name_computed = f'{type_label}{num}'

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_expired = bool(rec.expiry_date and rec.expiry_date < today)

    # ── Business Actions ──────────────────────────────────────────────────────

    def action_approve(self):
        """Operations manager approves the document."""
        for doc in self:
            if doc.verification_status == 'approved':
                raise UserError(_('Document is already approved.'))
            doc.verification_status = 'approved'
            doc.verified_by = self.env.user
            doc.verified_at = fields.Datetime.now()
            doc.message_post(
                body=_('Document approved by %s.', self.env.user.name),
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        """Operations manager rejects or marks document as expired/invalid."""
        for doc in self:
            doc.verification_status = 'rejected'
            doc.verified_by = self.env.user
            doc.verified_at = fields.Datetime.now()
            doc.message_post(
                body=_('Document rejected/marked invalid by %s.', self.env.user.name),
                subtype_xmlid='mail.mt_note',
            )
