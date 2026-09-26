from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ZconnectPod(models.Model):
    _name = 'zconnect.pod'
    _description = 'Proof of Delivery'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    shipment_id = fields.Many2one('zconnect.shipment', string='Shipment', required=True, readonly=True)
    assignment_id = fields.Many2one('zconnect.dispatch.assignment', string='Dispatch Assignment', required=True, readonly=True)
    driver_id = fields.Many2one('zconnect.driver', string='Driver', related='assignment_id.driver_id', store=True, readonly=True)
    
    recipient_name = fields.Char(string='Recipient Name', required=True, tracking=True)
    recipient_phone = fields.Char(string='Recipient Phone', tracking=True)
    
    delivered_at = fields.Datetime(string='Delivered At', readonly=True)
    delivery_notes = fields.Text(string='Delivery Notes', tracking=True)
    
    photo = fields.Binary(string='Delivery Photo', attachment=True)
    signature = fields.Binary(string='Signature', attachment=True)
    
    latitude = fields.Float(string='Delivery Latitude', digits=(10, 7))
    longitude = fields.Float(string='Delivery Longitude', digits=(10, 7))
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted')
    ], string='Status', default='draft', required=True, tracking=True)
    
    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for record in self:
            if record.latitude or record.longitude:
                if not (-90.0 <= record.latitude <= 90.0):
                    raise ValidationError(_("Latitude must be between -90 and 90."))
                if not (-180.0 <= record.longitude <= 180.0):
                    raise ValidationError(_("Longitude must be between -180 and 180."))
                    
    @api.constrains('state', 'shipment_id')
    def _check_unique_submitted_pod(self):
        for record in self:
            if record.state == 'submitted':
                existing_submitted = self.search_count([
                    ('shipment_id', '=', record.shipment_id.id),
                    ('state', '=', 'submitted'),
                    ('id', '!=', record.id)
                ])
                if existing_submitted > 0:
                    raise ValidationError(_("This shipment already has a submitted Proof of Delivery."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('zconnect.pod.ref') or _('New')
                
        records = super().create(vals_list)
        for record in records:
            record._validate_assignment()
        return records

    def write(self, vals):
        for record in self:
            if record.state == 'submitted' and not self.env.context.get('allow_pod_override'):
                raise UserError(_("Submitted Proof of Delivery cannot be modified."))
        res = super().write(vals)
        if 'assignment_id' in vals or 'shipment_id' in vals:
            for record in self:
                record._validate_assignment()
        return res
        
    def _validate_assignment(self):
        for record in self:
            if record.assignment_id.shipment_id != record.shipment_id:
                raise ValidationError(_("The dispatch assignment does not match the selected shipment."))
            if record.assignment_id != record.shipment_id.active_assignment_id:
                raise ValidationError(_("POD can only be created for the active dispatch assignment."))
            if record.assignment_id.state != 'accepted':
                raise ValidationError(_("POD can only be created for an accepted assignment."))

    def action_submit(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft PODs can be submitted."))
                
            # Revalidate assignment at submission time
            record._validate_assignment()
            
            # Shipment must be near_delivery
            if record.shipment_id.state != 'near_delivery':
                raise UserError(_("Shipment must be in 'near_delivery' state to submit POD."))
                
            if not record.recipient_name:
                raise UserError(_("Recipient name is required."))
                
            # 1. Update POD state
            record.write({
                'state': 'submitted',
                'delivered_at': fields.Datetime.now(),
            })
            
            # 2. Complete the shipment
            record.shipment_id.action_complete_delivery()
            
            # 3. Complete the assignment (which releases driver/vehicle if no other active assignments)
            record.assignment_id.action_complete()
            
            # Link POD to shipment for convenience (already done by the one2many, but we update pod_id field)
            record.shipment_id.with_context(allow_financial_override=True).write({
                'pod_id': record.id
            })
            
            record.message_post(
                body=_('Proof of Delivery submitted. Shipment delivered to %s.') % record.recipient_name,
                subtype_xmlid='mail.mt_note',
            )
