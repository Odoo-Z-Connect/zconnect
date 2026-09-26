from odoo import models

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _set_done(self, *args, **kwargs):
        super()._set_done(*args, **kwargs)
        self._sync_zconnect_payment_state('paid')

    def _set_pending(self, *args, **kwargs):
        super()._set_pending(*args, **kwargs)
        self._sync_zconnect_payment_state('pending')

    def _set_canceled(self, *args, **kwargs):
        super()._set_canceled(*args, **kwargs)
        self._sync_zconnect_payment_state('failed')

    def _set_error(self, *args, **kwargs):
        super()._set_error(*args, **kwargs)
        self._sync_zconnect_payment_state('failed')

    def _sync_zconnect_payment_state(self, state):
        for tx in self:
            if tx.invoice_ids:
                shipments = self.env['zconnect.shipment'].search([
                    ('invoice_id', 'in', tx.invoice_ids.ids)
                ])
                for shipment in shipments:
                    # Idempotent state synchronization
                    if shipment.payment_state != state:
                        shipment.payment_state = state
