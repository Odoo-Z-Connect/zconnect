# -*- coding: utf-8 -*-
{
    'name': 'Zimbabwe Connect — Driver Domain',
    'version': '19.0.1.0.0',
    'category': 'Logistics/Zimbabwe Connect',
    'summary': 'Logistics-specific driver operational profiles, KYC documents, and status lifecycle',
    'description': """
Zimbabwe Connect Driver Domain
================================
Creates the operational driver profile domain (zconnect.driver) for Zimbabwe Connect.

Architecture:
    res.partner       → master person/contact identity (name, phone, email, address)
    zconnect.driver   → logistics-specific operational profile (KYC, licence, status, vehicles)
    fleet.vehicle     → master vehicle record (via zconnect_fleet)

This separation ensures no duplicate contact master is created. Identity data
is always read from the linked res.partner record.

Provides:
- zconnect.driver: driver profile, code sequence, verification and availability lifecycle
- zconnect.driver.document: KYC/document records with expiry tracking and verification workflow
    """,
    'author': 'Zimbabwe Connect Technical Team',
    'license': 'OPL-1',
    'depends': [
        'zconnect_base',
        'zconnect_fleet',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/zconnect_driver_views.xml',
        'views/zconnect_driver_document_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
