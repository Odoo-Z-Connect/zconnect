from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Shipment(models.Model):
    _inherit = 'zconnect.shipment'

    pod_id = fields.Many2one('zconnect.pod', string='Proof of Delivery', readonly=True, copy=False)

    def write(self, vals):
        if 'state' in vals:
            for record in self:
                if record.state == 'delivered' and not self.env.context.get('allow_pod_override'):
                    raise UserError(_("A delivered shipment cannot have its state reverted."))
        return super().write(vals)
