{
    'name': 'Zimbabwe Connect - Proof of Delivery',
    'version': '1.0',
    'category': 'Logistics',
    'summary': 'Proof of Delivery module for Zimbabwe Connect',
    'depends': ['zconnect_base', 'zconnect_fleet', 'zconnect_driver', 'zconnect_shipment', 'zconnect_dispatch'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequences.xml',
        'views/pod_views.xml',
        'views/shipment_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
