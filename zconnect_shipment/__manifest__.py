# -*- coding: utf-8 -*-
{
    'name': 'Zimbabwe Connect — Shipment Core',
    'version': '19.0.1.0.0',
    'category': 'Logistics/Zimbabwe Connect',
    'summary': 'Central shipment logistics transaction aggregate with lifecycle workflow and immutable pricing snapshot',
    'description': """
Zimbabwe Connect Shipment Core
==============================
Establishes the central logistics aggregate (zconnect.shipment) for Zimbabwe Connect.

Architecture (ADR-005):
- res.partner       → Customer identity
- fleet.vehicle     → Assigned vehicle
- zconnect.pricing  → Quote calculation & immutable financial snapshot
- zconnect.shipment → Central logistics transaction and state machine

Features:
- Unique sequential tracking reference (ZC-SHP-00001)
- Comprehensive route, pickup, and delivery geographic metadata
- Package characteristics, category, weight, and volume
- Quote calculation via zconnect_pricing integration
- Commercial confirmation with immutable pricing snapshot
- 10-state logistics lifecycle state machine with Chatter audit logging
- Customer record-level security isolation
    """,
    'author': 'Zimbabwe Connect Technical Team',
    'license': 'OPL-1',
    'depends': [
        'zconnect_base',
        'zconnect_fleet',
        'zconnect_pricing',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/shipment_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
