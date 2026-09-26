from odoo import api, fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paynow', 'Paynow')], ondelete={'paynow': 'set default'}
    )
    paynow_integration_id = fields.Char(
        string="Paynow Integration ID",
        required_if_provider='paynow',
        groups='base.group_system',
    )
    paynow_integration_key = fields.Char(
        string="Paynow Integration Key",
        required_if_provider='paynow',
        groups='base.group_system',
    )

    def _get_supported_currencies(self):
        res = super()._get_supported_currencies()
        if self.code == 'paynow':
            return self.env['res.currency'].search([('name', 'in', ['USD', 'ZWL', 'ZWG'])])
        return res
