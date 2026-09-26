from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Shipment(models.Model):
    _inherit = 'zconnect.shipment'

    invoice_id = fields.Many2one(
        'account.move', 
        string='Customer Invoice', 
        readonly=True, 
        copy=False,
        domain="[('move_type', '=', 'out_invoice')]"
    )
    
    payment_transaction_id = fields.Many2one(
        'payment.transaction', 
        string='Payment Transaction', 
        compute='_compute_payment_transaction_id', 
        store=True,
        readonly=True
    )

    @api.depends('invoice_id', 'invoice_id.transaction_ids')
    def _compute_payment_transaction_id(self):
        for record in self:
            if record.invoice_id and record.invoice_id.transaction_ids:
                record.payment_transaction_id = record.invoice_id.transaction_ids[0].id
            else:
                record.payment_transaction_id = False

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self.invoice_id

        if not self.customer_id:
            raise UserError(_("A customer is required to create an invoice."))
        if self.state == 'cancelled':
            raise UserError(_("Cannot create an invoice for a cancelled shipment."))
        if not self.is_pricing_confirmed:
            raise UserError(_("Pricing must be confirmed before creating an invoice."))
        if self.total_amount <= 0:
            raise UserError(_("Shipment total amount must be strictly positive."))

        product = self.env['product.product'].search([('default_code', '=', 'ZCONNECT_DELIVERY')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Zimbabwe Connect Delivery',
                'type': 'service',
                'default_code': 'ZCONNECT_DELIVERY',
                'list_price': 0.0,
            })

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_origin': self.name,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': f'Zimbabwe Connect Delivery \u2014 {self.name}',
                    'product_id': product.id,
                    'quantity': 1.0,
                    'price_unit': self.total_amount,
                })
            ],
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        return invoice

    def action_start_payment(self):
        self.ensure_one()
        if not self.invoice_id:
            self.action_create_invoice()

        if self.invoice_id.state == 'draft':
            self.invoice_id.action_post()

        # Generate a safe link to the portal for this invoice
        # It allows the user to complete payment using Demo Provider (or Paynow later)
        url = self.invoice_id.get_portal_url()
        
        # Adding pay=1 ensures the payment dialog/section opens directly on the portal page
        if '?' in url:
            url += '&pay=1'
        else:
            url += '?pay=1'

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
