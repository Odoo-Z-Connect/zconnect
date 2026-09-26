{
    'name': 'ZConnect Payment & Paynow',
    'version': '1.0',
    'category': 'Operations/Logistics',
    'summary': 'Payment Integration and Paynow Gateway for Zimbabwe Connect',
    'description': """
        Integrates ZConnect shipments with Odoo's native accounting and payment engines.
        - Generates standard Odoo customer invoices.
        - Native Paynow Gateway integration for EcoCash and Visa payments.
        - Synchronizes shipment payment state from native payment.transaction.
    """,
    'author': 'ZConnect',
    'depends': [
        'zconnect_base',
        'zconnect_shipment',
        'account',
        'payment',
        'account_payment'
    ],
    'data': [
        'views/payment_paynow_templates.xml',
        'data/payment_provider_data.xml',
        'views/shipment_payment_views.xml',
        'views/payment_provider_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
