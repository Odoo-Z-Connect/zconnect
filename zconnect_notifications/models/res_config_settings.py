from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    zconnect_africastalking_username = fields.Char(
        "Africa's Talking Username",
        config_parameter='zconnect.africastalking_username',
        help="Username for Africa's Talking API (e.g., 'sandbox' or your live username)."
    )
    zconnect_africastalking_api_key = fields.Char(
        "Africa's Talking API Key",
        config_parameter='zconnect.africastalking_api_key',
        help="API Key for Africa's Talking API."
    )
