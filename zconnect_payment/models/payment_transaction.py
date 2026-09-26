from odoo import api, models, _
from odoo.exceptions import ValidationError
from werkzeug import urls

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paynow':
            return res

        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, '/payment/paynow/return')
        
        # In a real production environment, we use the Paynow Python SDK here
        # to generate the redirect URL based on integration keys.
        # For this Proof of Concept, we provide the payload for our dummy template.
        paynow_values = {
            'reference': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'return_url': return_url,
            'integration_id': self.provider_id.paynow_integration_id,
        }
        res.update(paynow_values)
        return res

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paynow' or len(tx) == 1:
            return tx
        
        reference = notification_data.get('reference')
        if not reference:
            raise ValidationError("Paynow: No reference found in notification.")
            
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'paynow')])
        if not tx:
            raise ValidationError(f"Paynow: No transaction found for reference {reference}.")
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paynow':
            return
            
        status = notification_data.get('status')
        if status == 'paid':
            self._set_done()
        elif status == 'cancelled':
            self._set_canceled()
        else:
            self._set_pending()
