{
    'name': 'ZConnect Dashboard',
    'version': '1.0',
    'summary': 'ZConnect Operations Dashboard',
    'category': 'Operations/ZConnect',
    'author': 'ZConnect',
    'depends': [
        'zconnect_base',
        'zconnect_fleet',
        'zconnect_driver',
        'zconnect_shipment',
        'zconnect_dispatch',
        'zconnect_payment',
        'zconnect_pod',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zconnect_dashboard/static/src/scss/dashboard.scss',
            'zconnect_dashboard/static/src/xml/dashboard.xml',
            'zconnect_dashboard/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
