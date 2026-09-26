# -*- coding: utf-8 -*-
{
    'name': 'Zimbabwe Connect — Fleet Extension',
    'version': '19.0.1.0.0',
    'category': 'Logistics/Zimbabwe Connect',
    'summary': 'Extends Odoo Fleet with logistics capacity, operational status and service area for Zimbabwe Connect',
    'description': """
Zimbabwe Connect Fleet Extension
=================================
Extends the standard Odoo Fleet module (fleet.vehicle) with logistics-specific
attributes required for Zimbabwe Connect dispatch, pricing, and driver workflow.

Adds to fleet.vehicle:
- Logistics operational status (available / assigned / in_service / maintenance / inactive)
- Payload capacity (kg) and cargo volume (m³)
- Service area / base location
- Zimbabwe Connect vehicle category (Motorcycle, Sedan, Pickup, Van, Truck, Interlink)

Does NOT create a duplicate vehicle model. All vehicle master data remains in Odoo Fleet.
    """,
    'author': 'Zimbabwe Connect Technical Team',
    'license': 'OPL-1',
    'depends': [
        'zconnect_base',
        'fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/vehicle_category_data.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
