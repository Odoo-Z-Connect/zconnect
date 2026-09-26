# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
{
    'name': 'Zimbabwe Connect — Base & Logistics Foundation',
    'version': '19.0.1.0.0',
    'category': 'Logistics/Zimbabwe Connect',
    'summary': 'Security groups, partner extensions, sequences, and core logistics foundations for Zimbabwe Connect',
    'description': """
Zimbabwe Connect Base Foundation
================================
Foundational module for the Zimbabwe Connect logistics platform on Odoo 19 Enterprise.

Features:
---------
* Security Roles: Administrator, Manager, Dispatcher, Finance, Driver, Customer.
* Partner Extensions: Seamlessly extends `res.partner` with ZConnect customer flags and automated sequence-driven customer code generation (e.g. CUS-00001).
* Shared Logistics Configurations: Base menu hierarchy and sequences.
    """,
    'author': 'Zimbabwe Connect Technical Team',
    'website': 'https://www.zimbabweconnect.co.zw',
    'license': 'OPL-1',
    'depends': [
        'base',
        'contacts',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'data/sequences.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
