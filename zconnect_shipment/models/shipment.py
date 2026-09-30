# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
#
# Architecture Decision (ADR-005):
#   zconnect.shipment is the central logistics transaction aggregate.
#   It coordinates between:
#     - res.partner (Customer master)
#     - fleet.vehicle (Vehicle master)
#     - zconnect.pricing (Quote calculation & immutable snapshot)
#     - (future) zconnect.dispatch (Driver assignment)
#     - (future) payment.transaction (Odoo native payments)
#
# FINANCIAL SNAPSHOT IMMUTABILITY:
#   Quote calculation populates estimated rates in 'draft' or 'quoted' state.
#   When the shipment is commercially confirmed (action_confirm), the pricing
#   snapshot is permanently sealed (is_pricing_confirmed=True). Subsequent
#   modifications to pricing rules in zconnect.pricing.rule NEVER mutate
#   confirmed shipment records.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import requests
from odoo.addons.zconnect_fleet.models.fleet_vehicle import ZCONNECT_VEHICLE_CATEGORY


SHIPMENT_STATE = [
    ('draft', 'Draft Booking'),
    ('quoted', 'Quoted'),
    ('awaiting_payment', 'Awaiting Payment'),
    ('confirmed', 'Confirmed / Ready for Dispatch'),
    ('assigned', 'Driver Assigned'),
    ('en_route_pickup', 'En Route to Pickup'),
    ('picked_up', 'Picked Up'),
    ('in_transit', 'In Transit'),
    ('near_delivery', 'Near Delivery'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('exception', 'Exception / Issue'),
]

PAYMENT_STATE = [
    ('unpaid', 'Unpaid'),
    ('pending', 'Pending Verification'),
    ('paid', 'Paid'),
    ('failed', 'Payment Failed'),
    ('refunded', 'Refunded'),
]

SHIPMENT_CATEGORY = [
    ('document', 'Documents & Envelopes'),
    ('parcel', 'Small Parcel / Box'),
    ('freight', 'Bulk Cargo / Freight'),
    ('perishable', 'Perishable Goods / Food'),
    ('fragile', 'Fragile Goods / Electronics'),
    ('hazardous', 'Hazardous Materials'),
    ('other', 'Other Goods'),
]

# Valid state machine transitions: {current_state: [allowed_target_states]}
_STATE_TRANSITIONS = {
    'draft': ['quoted', 'cancelled'],
    'quoted': ['awaiting_payment', 'draft', 'cancelled'],
    'awaiting_payment': ['confirmed', 'quoted', 'cancelled'],
    'confirmed': ['assigned', 'cancelled', 'exception'],
    'assigned': ['en_route_pickup', 'confirmed', 'cancelled', 'exception'],
    'en_route_pickup': ['picked_up', 'exception', 'cancelled'],
    'picked_up': ['in_transit', 'exception'],
    'in_transit': ['near_delivery', 'exception'],
    'near_delivery': ['delivered', 'exception'],
    'exception': ['in_transit', 'assigned', 'cancelled'],
    'delivered': [],   # Terminal state
    'cancelled': [],   # Terminal state
}


class ZconnectShipment(models.Model):
    """
    Central Shipment Logistics Aggregate for Zimbabwe Connect.

    Coordinates customer booking, routing, package specifications,
    vehicle requirements, pricing calculation, and delivery state lifecycle.
    """
    _name = 'zconnect.shipment'
    _description = 'Zimbabwe Connect Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # ── Reference & Master Identity ──────────────────────────────────────────

    name = fields.Char(
        string='Shipment Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
        help='Unique tracking identifier generated sequentially (e.g. ZC-SHP-00001).',
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        ondelete='restrict',
        help='The ordering customer. Uses standard Odoo res.partner.',
    )

    customer_phone = fields.Char(related='customer_id.phone', string='Customer Phone', readonly=True)
    customer_email = fields.Char(related='customer_id.email', string='Customer Email', readonly=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    # ── Pickup Geographic & Contact Information ──────────────────────────────

    pickup_address = fields.Char(
        string='Pickup Address',
        required=True,
        tracking=True,
        help='Physical pickup location address in Zimbabwe.',
    )

    pickup_contact_name = fields.Char(string='Pickup Contact Person')
    pickup_contact_phone = fields.Char(string='Pickup Contact Phone')

    pickup_latitude = fields.Float(
        string='Pickup Latitude',
        digits=(10, 7),
        help='Pickup GPS latitude coordinate (-90.0 to 90.0).',
    )

    pickup_longitude = fields.Float(
        string='Pickup Longitude',
        digits=(10, 7),
        help='Pickup GPS longitude coordinate (-180.0 to 180.0).',
    )

    # ── Delivery Geographic & Contact Information ────────────────────────────

    delivery_address = fields.Char(
        string='Delivery Address',
        required=True,
        tracking=True,
        help='Destination physical address in Zimbabwe.',
    )

    delivery_contact_name = fields.Char(string='Delivery Contact Person')
    delivery_contact_phone = fields.Char(string='Delivery Contact Phone')

    delivery_latitude = fields.Float(
        string='Delivery Latitude',
        digits=(10, 7),
        help='Delivery GPS latitude coordinate (-90.0 to 90.0).',
    )

    delivery_longitude = fields.Float(
        string='Delivery Longitude',
        digits=(10, 7),
        help='Delivery GPS longitude coordinate (-180.0 to 180.0).',
    )

    # ── Package & Cargo Characteristics ──────────────────────────────────────

    shipment_category = fields.Selection(
        selection=SHIPMENT_CATEGORY,
        string='Cargo Category',
        default='parcel',
        required=True,
        tracking=True,
    )

    description = fields.Text(
        string='Package Description',
        help='Contents description, items list, or declared cargo details.',
    )

    weight_kg = fields.Float(
        string='Cargo Weight (kg)',
        digits=(10, 2),
        default=1.0,
        required=True,
        tracking=True,
        help='Total weight of the package/shipment in kilograms.',
    )

    length_cm = fields.Float(string='Length (cm)', digits=(10, 1), default=0.0)
    width_cm = fields.Float(string='Width (cm)', digits=(10, 1), default=0.0)
    height_cm = fields.Float(string='Height (cm)', digits=(10, 1), default=0.0)

    volume_cbm = fields.Float(
        string='Volume (m³)',
        digits=(10, 4),
        compute='_compute_volume_cbm',
        store=True,
        help='Computed package volume in cubic meters.',
    )

    special_instructions = fields.Text(
        string='Handling Instructions',
        help='Special handling, delivery notes, or access gate instructions.',
    )

    package_image = fields.Binary(
        string='Package Photo / Scan',
        attachment=True,
        help='Photograph or document scan of the parcel before shipment.',
    )

    # ── Vehicle & Fleet Integration ──────────────────────────────────────────

    vehicle_category = fields.Selection(
        selection=ZCONNECT_VEHICLE_CATEGORY,
        string='Required Vehicle Category',
        required=True,
        tracking=True,
        help='Required vehicle type for dispatch and tariff matching. '
             'Reuses category vocabulary from zconnect_fleet.',
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Assigned Fleet Vehicle',
        domain="[('zconnect_vehicle_category', '=', vehicle_category)]",
        tracking=True,
        help='Assigned master vehicle record from standard Odoo Fleet.',
    )

    distance_km = fields.Float(
        string='Trip Distance (km)',
        digits=(10, 2),
        default=5.0,
        required=True,
        tracking=True,
        help='Estimated or simulated trip distance in kilometers.',
    )

    zone_id = fields.Many2one(
        'zconnect.pricing.zone',
        string='Delivery Zone',
        tracking=True,
        help='Optional service zone surcharge to apply from zconnect_pricing.',
    )

    # ── Immutable Pricing Snapshot (ADR-004 / ADR-005) ───────────────────────

    pricing_rule_id = fields.Many2one(
        'zconnect.pricing.rule',
        string='Applied Pricing Rule',
        readonly=True,
        copy=False,
    )

    pricing_calculated_at = fields.Datetime(
        string='Pricing Calculated At',
        readonly=True,
        copy=False,
    )

    base_fare = fields.Monetary(
        string='Base Fare Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    distance_charge = fields.Monetary(
        string='Distance Charge Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    weight_charge = fields.Monetary(
        string='Weight Charge Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    zone_charge = fields.Monetary(
        string='Zone Charge Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    subtotal = fields.Monetary(
        string='Subtotal Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    minimum_fare = fields.Monetary(
        string='Minimum Fare Snapshot',
        currency_field='currency_id',
        readonly=True,
    )

    total_amount = fields.Monetary(
        string='Total Quote Amount',
        currency_field='currency_id',
        readonly=True,
        tracking=True,
        help='The final confirmed financial charge for this delivery.',
    )

    is_pricing_confirmed = fields.Boolean(
        string='Pricing Sealed',
        default=False,
        readonly=True,
        copy=False,
        help='When True, the financial snapshot is permanently sealed and immutable.',
    )

    # ── State Machine & Payment Status ───────────────────────────────────────

    state = fields.Selection(
        selection=SHIPMENT_STATE,
        string='Shipment Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    payment_state = fields.Selection(
        selection=PAYMENT_STATE,
        string='Payment Status',
        default='unpaid',
        required=True,
        tracking=True,
        index=True,
    )

    # ── Lifecycle Timestamps & Auditing ──────────────────────────────────────

    quoted_at = fields.Datetime(string='Quoted At', readonly=True, copy=False)
    confirmed_at = fields.Datetime(string='Confirmed At', readonly=True, copy=False)
    assigned_at = fields.Datetime(string='Assigned At', readonly=True, copy=False)
    en_route_pickup_at = fields.Datetime(string='En Route Pickup At', readonly=True, copy=False)
    picked_up_at = fields.Datetime(string='Picked Up At', readonly=True, copy=False)
    in_transit_at = fields.Datetime(string='In Transit At', readonly=True, copy=False)
    near_delivery_at = fields.Datetime(string='Near Delivery At', readonly=True, copy=False)
    delivered_at = fields.Datetime(string='Delivered At', readonly=True, copy=False)

    cancelled_at = fields.Datetime(string='Cancelled At', readonly=True, copy=False)
    cancelled_by = fields.Many2one('res.users', string='Cancelled By', readonly=True, copy=False)
    cancellation_reason = fields.Text(string='Cancellation Reason', tracking=True)

    exception_at = fields.Datetime(string='Exception At', readonly=True, copy=False)
    exception_reason = fields.Text(string='Exception Reason', tracking=True)

    # ── Constraints & Server-Side Invariants ─────────────────────────────────

    _reference_unique = models.Constraint(
        'UNIQUE(name)',
        'The shipment tracking reference must be unique.',
    )

    @api.depends('length_cm', 'width_cm', 'height_cm')
    def _compute_volume_cbm(self):
        for rec in self:
            if rec.length_cm > 0 and rec.width_cm > 0 and rec.height_cm > 0:
                rec.volume_cbm = round((rec.length_cm * rec.width_cm * rec.height_cm) / 1000000.0, 4)
            else:
                rec.volume_cbm = 0.0

    @api.constrains('weight_kg', 'length_cm', 'width_cm', 'height_cm', 'distance_km')
    def _check_non_negative_metrics(self):
        for rec in self:
            if rec.weight_kg <= 0:
                raise ValidationError(_('Cargo weight must be greater than zero.'))
            if rec.distance_km < 0:
                raise ValidationError(_('Distance cannot be negative.'))
            if rec.length_cm < 0 or rec.width_cm < 0 or rec.height_cm < 0:
                raise ValidationError(_('Package dimensions cannot be negative.'))

    @api.constrains('pickup_latitude', 'pickup_longitude', 'delivery_latitude', 'delivery_longitude')
    def _check_coordinates(self):
        for rec in self:
            for prefix, lat, lon in [
                ('Pickup', rec.pickup_latitude, rec.pickup_longitude),
                ('Delivery', rec.delivery_latitude, rec.delivery_longitude),
            ]:
                if lat and not (-90.0 <= lat <= 90.0):
                    raise ValidationError(_('%(p)s latitude %(v)s is invalid (must be between -90 and 90).', p=prefix, v=lat))
                if lon and not (-180.0 <= lon <= 180.0):
                    raise ValidationError(_('%(p)s longitude %(v)s is invalid (must be between -180 and 180).', p=prefix, v=lon))

    @api.onchange('pickup_latitude', 'pickup_longitude', 'delivery_latitude', 'delivery_longitude')
    def _onchange_coordinates_calc_distance(self):
        for rec in self:
            if rec.pickup_latitude and rec.pickup_longitude and rec.delivery_latitude and rec.delivery_longitude:
                try:
                    api_key = self.env['ir.config_parameter'].sudo().get_param('zconnect.google_maps_api_key', 'AIzaSyCxVvPpOrhUw2O0-PwSfy6BaFIGfiFHBr8')
                    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={rec.pickup_latitude},{rec.pickup_longitude}&destinations={rec.delivery_latitude},{rec.delivery_longitude}&key={api_key}"
                    resp = requests.get(url, timeout=5)
                    data = resp.json()
                    if data.get('status') == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
                        distance_meters = data['rows'][0]['elements'][0]['distance']['value']
                        rec.distance_km = distance_meters / 1000.0
                except Exception as e:
                    pass

    # ── ORM Overrides ────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('zconnect.shipment.ref')
                    or _('New')
                )
            # Ensure partner is flagged as ZConnect customer
            if vals.get('customer_id'):
                customer = self.env['res.partner'].browse(vals['customer_id'])
                if not customer.zconnect_is_customer:
                    customer.sudo().write({'zconnect_is_customer': True})
        return super().create(vals_list)

    def write(self, vals):
        # Guard: Financial snapshot immutability once pricing is confirmed
        protected_financial_fields = [
            'base_fare', 'distance_charge', 'weight_charge', 'zone_charge',
            'subtotal', 'minimum_fare', 'total_amount', 'pricing_rule_id'
        ]
        for rec in self:
            if rec.is_pricing_confirmed and any(f in vals for f in protected_financial_fields):
                # Only internal recalculation actions can overwrite before confirmation
                if not self.env.context.get('allow_financial_override', False):
                    raise UserError(_(
                        'Financial pricing snapshot on confirmed shipment "%s" is sealed and immutable.',
                        rec.name,
                    ))
        return super().write(vals)

    # ── Business Workflow Actions ────────────────────────────────────────────

    def _validate_transition(self, target_state):
        """Helper to enforce state machine transition validity."""
        for rec in self:
            allowed = _STATE_TRANSITIONS.get(rec.state, [])
            if target_state not in allowed:
                raise UserError(_(
                    'Invalid status transition from "%(current)s" to "%(target)s" on shipment %(name)s.',
                    current=dict(SHIPMENT_STATE).get(rec.state, rec.state),
                    target=dict(SHIPMENT_STATE).get(target_state, target_state),
                    name=rec.name,
                ))

    def action_calculate_quote(self):
        """
        Calculate fare quote from zconnect_pricing without confirming the shipment.
        State: draft/quoted -> quoted.
        """
        for shipment in self:
            if shipment.state not in ['draft', 'quoted']:
                raise UserError(_('Quotes can only be calculated in Draft or Quoted status.'))

            if not shipment.pickup_address or not shipment.delivery_address:
                raise UserError(_('Both pickup and delivery addresses are required to calculate a quote.'))
            if not shipment.vehicle_category:
                raise UserError(_('Please select a required vehicle category for quote calculation.'))
            if shipment.distance_km <= 0:
                raise UserError(_('Trip distance must be greater than zero kilometers.'))
            if shipment.weight_kg <= 0:
                raise UserError(_('Cargo weight must be greater than zero kg.'))

            # Retrieve applicable rule from pricing engine
            rule = self.env['zconnect.pricing.rule'].get_applicable_rule(
                vehicle_category=shipment.vehicle_category,
                company_id=shipment.company_id.id,
            )

            # Compute quote breakdown
            quote = rule.compute_quote(
                distance_km=shipment.distance_km,
                weight_kg=shipment.weight_kg,
                zone=shipment.zone_id,
            )

            shipment.write({
                'pricing_rule_id': quote['pricing_rule_id'],
                'pricing_calculated_at': fields.Datetime.now(),
                'base_fare': quote['base_fare'],
                'distance_charge': quote['distance_charge'],
                'weight_charge': quote['weight_charge'],
                'zone_charge': quote['zone_charge'],
                'subtotal': quote['subtotal'],
                'minimum_fare': quote['minimum_fare'],
                'total_amount': quote['total_amount'],
                'state': 'quoted',
                'quoted_at': fields.Datetime.now(),
            })

            currency_sym = shipment.currency_id.symbol or shipment.currency_id.name or '$'
            shipment.message_post(
                body=_(
                    '<b>Fare Quote Calculated:</b> %(total)s%(cur)s<br/>'
                    '• Rule: %(rule)s<br/>'
                    '• Base Fare: %(cur)s%(base).2f | Distance (%(dist).1f km): %(cur)s%(dist_c).2f<br/>'
                    '• Cargo Weight (%(wt).1f kg): %(cur)s%(wt_c).2f | Zone Surcharge: %(cur)s%(zone_c).2f',
                    total=f"{quote['total_amount']:.2f}",
                    cur=currency_sym,
                    rule=quote['pricing_rule_name'],
                    base=quote['base_fare'],
                    dist=quote['distance_km'],
                    dist_c=quote['distance_charge'],
                    wt=quote['weight_kg'],
                    wt_c=quote['weight_charge'],
                    zone_c=quote['zone_charge'],
                ),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_prepare_payment(self):
        """
        Transition: quoted -> awaiting_payment.
        Indicates customer proceeded to checkout/payment step.
        """
        for shipment in self:
            shipment._validate_transition('awaiting_payment')
            if not shipment.total_amount or shipment.total_amount <= 0:
                raise UserError(_('Cannot prepare payment: shipment has not been quoted.'))

            shipment.write({
                'state': 'awaiting_payment',
                'payment_state': 'pending',
            })
            shipment.message_post(
                body=_('Shipment moved to Awaiting Payment. Payment transaction pending.'),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_confirm(self):
        """
        Transition: awaiting_payment (or quoted in manual back-office flow) -> confirmed.
        Seals the pricing snapshot permanently (is_pricing_confirmed=True).
        """
        for shipment in self:
            shipment._validate_transition('confirmed')

            if not shipment.customer_id:
                raise UserError(_('Cannot confirm shipment without a valid customer.'))
            if not shipment.pickup_address or not shipment.delivery_address:
                raise UserError(_('Cannot confirm shipment without pickup and delivery addresses.'))
            if not shipment.total_amount or shipment.total_amount <= 0:
                raise UserError(_('Cannot confirm shipment without a calculated quote amount.'))

            shipment.write({
                'state': 'confirmed',
                'confirmed_at': fields.Datetime.now(),
                'is_pricing_confirmed': True,
            })
            shipment.message_post(
                body=_(
                    '<b>Shipment Commercially Confirmed.</b><br/>'
                    'Financial pricing snapshot permanently sealed at %(cur)s%(total).2f.',
                    cur=shipment.currency_id.symbol or shipment.currency_id.name or '$',
                    total=shipment.total_amount,
                ),
                subtype_xmlid='mail.mt_comment',
            )
        return True

    def action_cancel(self):
        """
        Transition to cancelled state with reason logging.
        """
        for shipment in self:
            if shipment.state == 'delivered':
                raise UserError(_('Delivered shipments cannot be cancelled.'))
            if shipment.state == 'cancelled':
                raise UserError(_('Shipment is already cancelled.'))

            shipment.write({
                'state': 'cancelled',
                'cancelled_at': fields.Datetime.now(),
                'cancelled_by': self.env.user.id,
            })
            reason_text = f" Reason: {shipment.cancellation_reason}" if shipment.cancellation_reason else ""
            shipment.message_post(
                body=_('Shipment cancelled by %s.%s', self.env.user.name, reason_text),
                subtype_xmlid='mail.mt_comment',
            )
        return True

    def action_mark_exception(self):
        """
        Transition to exception state for operational delays or incidents.
        """
        for shipment in self:
            shipment._validate_transition('exception')
            shipment.write({
                'state': 'exception',
                'exception_at': fields.Datetime.now(),
            })
            reason_text = f" Issue: {shipment.exception_reason}" if shipment.exception_reason else ""
            shipment.message_post(
                body=_('Operational Exception flagged by %s.%s', self.env.user.name, reason_text),
                subtype_xmlid='mail.mt_comment',
            )
        return True
