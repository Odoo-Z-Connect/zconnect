{
    'name': 'ZConnect Notifications & Africa\'s Talking SMS',
    'version': '1.0',
    'category': 'Logistics/ZConnect',
    'summary': 'Centralized notifications integrating Africa\'s Talking SMS, native WhatsApp, and Email.',
    'description': """
ZConnect Notifications Center
=============================
This module fulfills the notification requirements for the Zimbabwe Connect logistics platform.

Features:
- **WhatsApp Integration**: Declares dependency on Odoo's native `whatsapp` Enterprise app to enable instant messaging.
- **Africa's Talking SMS**: Intercepts Odoo's native `sms.sms` dispatcher to route all system SMS messages through the Africa's Talking API (Standard for Zimbabwe/Africa) instead of Odoo IAP.
- **Email**: Ties into Odoo's native `mail` system.
    """,
    'author': 'ZConnect Technical Team',
    'depends': ['zconnect_base', 'mail', 'sms', 'whatsapp'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'license': 'OPL-1',
}
