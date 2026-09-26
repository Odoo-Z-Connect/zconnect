# -*- coding: utf-8 -*-
{
    'name': 'ZConnect API',
    'version': '1.0',
    'category': 'Logistics',
    'summary': 'JSON API for Zimbabwe Connect',
    'description': 'Exposes ZConnect domain models via a controlled JSON API.',
    'depends': ['zconnect_base', 'zconnect_shipment', 'zconnect_dispatch', 'zconnect_driver', 'zconnect_pricing', 'zconnect_pod', 'zconnect_payment'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
