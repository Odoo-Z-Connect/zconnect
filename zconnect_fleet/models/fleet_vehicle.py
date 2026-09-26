# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
#
# WHY: Odoo Fleet (fleet.vehicle) is the master vehicle registry.
# We extend it rather than create a duplicate vehicle model.
# All existing Fleet features (odometer, maintenance, driver assignment,
# contracts) remain intact. We only add Zimbabwe Connect logistics domain
# attributes that have no equivalent in standard Fleet.

from odoo import fields, models


# Selection values as module-level constants for testability and reuse.
ZCONNECT_OPERATIONAL_STATUS = [
    ('available', 'Available'),
    ('assigned', 'Assigned to Delivery'),
    ('in_service', 'In Service / On Trip'),
    ('maintenance', 'Under Maintenance'),
    ('inactive', 'Inactive / Decommissioned'),
]

ZCONNECT_VEHICLE_CATEGORY = [
    ('motorcycle', 'Motorcycle'),
    ('sedan', 'Sedan / Hatchback'),
    ('pickup', 'Pickup / Bakkie'),
    ('van', 'Van / Minibus'),
    ('truck_small', 'Small Truck (up to 3 Ton)'),
    ('truck_medium', 'Medium Truck (3–10 Ton)'),
    ('truck_large', 'Large Truck (10+ Ton)'),
    ('interlink', 'Interlink / Articulated'),
]


class FleetVehicle(models.Model):
    """
    Logistics extension of the standard Odoo fleet.vehicle model.

    Adds Zimbabwe Connect-specific operational and capacity attributes.
    No standard Fleet fields or behaviour is altered.
    """
    _inherit = 'fleet.vehicle'

    # ─── Logistics Classification ──────────────────────────────────────────────

    zconnect_vehicle_category = fields.Selection(
        selection=ZCONNECT_VEHICLE_CATEGORY,
        string='Logistics Category',
        tracking=True,
        help='Zimbabwe Connect logistics classification used for pricing rules '
             'and dispatch eligibility. Separate from the standard Fleet category.',
    )

    zconnect_operational_status = fields.Selection(
        selection=ZCONNECT_OPERATIONAL_STATUS,
        string='Operational Status',
        default='available',
        tracking=True,
        help='Current operational status of this vehicle within Zimbabwe Connect. '
             'Updated automatically when assigned to a shipment.',
    )

    zconnect_service_area = fields.Char(
        string='Service Area / Base',
        help='Primary operating area or home depot for this vehicle '
             '(e.g. "Harare CBD", "Bulawayo", "National"). '
             'Used to pre-filter eligible vehicles for dispatch.',
    )

    # ─── Cargo Capacity ────────────────────────────────────────────────────────

    zconnect_payload_capacity_kg = fields.Float(
        string='Max Payload (kg)',
        digits=(10, 2),
        help='Maximum cargo weight this vehicle can safely carry, in kilograms. '
             'Used by the pricing engine to validate shipment weight eligibility.',
    )

    zconnect_volume_capacity_cbm = fields.Float(
        string='Max Volume (m³)',
        digits=(10, 3),
        help='Maximum cargo volume this vehicle can carry, in cubic metres. '
             'Used for oversized shipment validation.',
    )

    # ─── Logistics Notes ───────────────────────────────────────────────────────

    zconnect_logistics_notes = fields.Text(
        string='Logistics Notes',
        help='Internal operational notes about this vehicle\'s logistics capabilities, '
             'restrictions, or special requirements.',
    )
