from odoo import http
from odoo.http import request

class PaynowController(http.Controller):
    _return_url = '/payment/paynow/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paynow_return(self, **data):
        # Handle the return from Paynow gateway
        request.env['payment.transaction'].sudo()._handle_notification_data('paynow', data)
        return request.redirect('/payment/status')
