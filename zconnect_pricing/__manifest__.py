# -*- coding: utf-8 -*-
{
    'name': 'Zimbabwe Connect — Pricing Engine',
    'version': '19.0.1.0.0',
    'category': 'Logistics/Zimbabwe Connect',
    'summary': 'Configurable, deterministic logistics pricing engine for quote calculation',
    'description': """
Zimbabwe Connect Pricing Engine
================================
Provides a configurable, deterministic logistics pricing engine for calculating
shipment delivery quotes based on distance, cargo weight, vehicle category, and service zones.

Core Concepts:
- zconnect.pricing.rule: Configurable tariff rules (base fare, per-km, per-kg, minimum fare, effective dates).
- zconnect.pricing.zone: Service area pricing / surcharge zones.
- Immutable Pricing Snapshot: Calculates quote breakdown (base fare, distance charge, weight charge, vehicle charge, zone surcharge, total) to be snapshotted immutably onto future shipment records.

Reuses vehicle categories from zconnect_fleet (fleet.vehicle) and currencies from standard Odoo res.currency.
    """,
    'author': 'Zimbabwe Connect Technical Team',
    'license': 'OPL-1',
    'depends': [
        'zconnect_base',
        'zconnect_fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/pricing_data.xml',
        'views/pricing_zone_views.xml',
        'views/pricing_rule_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
