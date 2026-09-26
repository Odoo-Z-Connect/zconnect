# -*- coding: utf-8 -*-
{
    'name': 'ZConnect Portal',
    'version': '1.0',
    'category': 'Logistics',
    'summary': 'Customer and Driver Portal for Zimbabwe Connect',
    'description': 'Exposes ZConnect domain models via Odoo Web Portal.',
    'depends': ['portal', 'website', 'zconnect_base', 'zconnect_shipment', 'zconnect_dispatch', 'zconnect_driver', 'zconnect_fleet', 'zconnect_pricing', 'zconnect_payment', 'zconnect_pod'],
    'data': [
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
