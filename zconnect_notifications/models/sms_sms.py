from odoo import models, api
import requests
import logging

_logger = logging.getLogger(__name__)

class SmsSms(models.Model):
    _inherit = 'sms.sms'

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ 
        OVERRIDE: Intercept Odoo's native SMS dispatcher and route through Africa's Talking.
        This ensures all system SMS (2FA, shipment updates, driver alerts) use our local provider.
        """
        username = self.env['ir.config_parameter'].sudo().get_param('zconnect.africastalking_username')
        api_key = self.env['ir.config_parameter'].sudo().get_param('zconnect.africastalking_api_key')

        if not username or not api_key:
            _logger.info("Africa's Talking credentials not set. Falling back to native Odoo IAP SMS.")
            return super()._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)

        # Determine endpoint (Sandbox vs Live)
        if username == 'sandbox':
            url = "https://api.sandbox.africastalking.com/version1/messaging"
        else:
            url = "https://api.africastalking.com/version1/messaging"

        headers = {
            'ApiKey': api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # Process each SMS record in the batch
        for sms in self:
            payload = {
                'username': username,
                'to': sms.number,
                'message': sms.body
            }
            try:
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                if response.status_code == 201:
                    sms.write({'state': 'sent'})
                    _logger.info("Africa's Talking SMS sent successfully to %s", sms.number)
                else:
                    sms.write({'state': 'error'})
                    _logger.error("Africa's Talking SMS failed: %s", response.text)
            except Exception as e:
                sms.write({'state': 'error'})
                _logger.error("Africa's Talking connection error: %s", str(e))
                if raise_exception:
                    raise

        if unlink_sent:
            self.filtered(lambda s: s.state == 'sent').unlink()
        if unlink_failed:
            self.filtered(lambda s: s.state == 'error').unlink()
