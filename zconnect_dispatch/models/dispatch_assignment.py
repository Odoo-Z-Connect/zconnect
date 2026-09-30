from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class DispatchAssignment(models.Model):
    _name = 'zconnect.dispatch.assignment'
    _description = 'Dispatch Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    shipment_id = fields.Many2one('zconnect.shipment', string='Shipment', required=True, ondelete='cascade', readonly=True)
    driver_id = fields.Many2one('zconnect.driver', string='Driver', required=True, readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, readonly=True)
    
    # Related Shipment Fields
    pickup_address = fields.Char(related='shipment_id.pickup_address', string='Pickup Address', readonly=True)
    pickup_contact_name = fields.Char(related='shipment_id.pickup_contact_name', string='Contact Name', readonly=True)
    pickup_contact_phone = fields.Char(related='shipment_id.pickup_contact_phone', string='Contact Phone', readonly=True)
    delivery_address = fields.Char(related='shipment_id.delivery_address', string='Delivery Address', readonly=True)
    delivery_contact_name = fields.Char(related='shipment_id.delivery_contact_name', string='Del. Contact Name', readonly=True)
    delivery_contact_phone = fields.Char(related='shipment_id.delivery_contact_phone', string='Del. Contact Phone', readonly=True)
    shipment_category = fields.Selection(related='shipment_id.shipment_category', string='Category', readonly=True)
    shipment_description = fields.Text(related='shipment_id.description', string='Description', readonly=True)
    payment_status = fields.Selection(related='shipment_id.payment_state', string='Payment Status', readonly=True)
    weight_kg = fields.Float(related='shipment_id.weight_kg', string='Weight (kg)', readonly=True)
    volume_cbm = fields.Float(related='shipment_id.volume_cbm', string='Volume (m³)', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    ], string='Status', default='draft', required=True, tracking=True)
    
    assigned_by = fields.Many2one('res.users', string='Assigned By', readonly=True)
    assigned_at = fields.Datetime(string='Assigned At', readonly=True)
    accepted_at = fields.Datetime(string='Accepted At', readonly=True)
    rejected_at = fields.Datetime(string='Rejected At', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('zconnect.dispatch.assignment.ref') or _('New')
        return super().create(vals_list)

    def _validate_eligibility(self):
        for record in self:
            driver = record.driver_id
            vehicle = record.vehicle_id
            shipment = record.shipment_id

            if not driver:
                raise ValidationError(_("Driver is required."))
            if not vehicle:
                raise ValidationError(_("Vehicle is required."))
            if not shipment:
                raise ValidationError(_("Shipment is required."))

            if driver.verification_status != 'verified':
                raise ValidationError(_("Driver %s is not verified.") % driver.name)
            if driver.availability_status != 'available':
                raise ValidationError(_("Driver %s is not available.") % driver.name)

            if vehicle.zconnect_operational_status != 'available':
                raise ValidationError(_("Vehicle %s is not available.") % vehicle.name)
            
            if vehicle.zconnect_vehicle_category != shipment.vehicle_category:
                raise ValidationError(_("Vehicle category does not match the shipment requirement."))

            if vehicle.zconnect_payload_capacity_kg < shipment.weight_kg:
                raise ValidationError(_("Vehicle payload capacity is insufficient for this shipment."))
                
            if vehicle.zconnect_volume_capacity_cbm < shipment.volume_cbm:
                raise ValidationError(_("Vehicle volume capacity is insufficient for this shipment."))

    def action_accept(self):
        for record in self:
            if record.state != 'offered':
                raise UserError(_("Only offered assignments can be accepted."))
                
            # Revalidate eligibility at acceptance time
            record._validate_eligibility()
            
            # Revalidate shipment state
            if record.shipment_id.state != 'assigned':
                raise UserError(_("Shipment is no longer in 'assigned' state."))
            
            # Check for other accepted assignments for this shipment
            existing_accepted = self.search([
                ('shipment_id', '=', record.shipment_id.id),
                ('state', '=', 'accepted'),
                ('id', '!=', record.id)
            ])
            if existing_accepted:
                raise UserError(_("This shipment already has an accepted assignment."))

            record.write({
                'state': 'accepted',
                'accepted_at': fields.Datetime.now(),
            })
            
            # Establish operational relationship
            record.driver_id.sudo().availability_status = 'unavailable'
            record.vehicle_id.sudo().zconnect_operational_status = 'assigned'
            
            record.message_post(
                body=_('Assignment accepted by driver %s.') % record.driver_id.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_reject_wizard(self):
        """Opens a wizard to provide a rejection reason."""
        self.ensure_one()
        return {
            'name': _('Reject Assignment'),
            'type': 'ir.actions.act_window',
            'res_model': 'zconnect.dispatch.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_assignment_id': self.id},
        }

    def action_reject(self, reason):
        for record in self:
            if record.state != 'offered':
                raise UserError(_("Only offered assignments can be rejected."))
            if not reason:
                raise UserError(_("A rejection reason is required."))

            record.write({
                'state': 'rejected',
                'rejected_at': fields.Datetime.now(),
                'rejection_reason': reason,
            })
            
            if record.shipment_id.active_assignment_id == record:
                record.shipment_id.write({
                    'state': 'confirmed',
                    'active_assignment_id': False,
                })
            
            record.message_post(
                body=_('Assignment rejected by driver %s. Reason: %s') % (record.driver_id.name, reason),
                subtype_xmlid='mail.mt_note',
            )

    def action_complete(self):
        """
        Transition assignment to 'completed' and release the driver and vehicle
        if they have no other active assignments.
        """
        for record in self:
            if record.state != 'accepted':
                raise UserError(_("Only accepted assignments can be completed."))
            
            record.write({
                'state': 'completed',
            })
            
            # Check for other active assignments for the driver
            other_driver_assignments = self.search_count([
                ('driver_id', '=', record.driver_id.id),
                ('state', 'in', ['offered', 'accepted']),
                ('id', '!=', record.id)
            ])
            if other_driver_assignments == 0:
                record.driver_id.sudo().availability_status = 'available'
                
            # Check for other active assignments for the vehicle
            other_vehicle_assignments = self.search_count([
                ('vehicle_id', '=', record.vehicle_id.id),
                ('state', 'in', ['offered', 'accepted']),
                ('id', '!=', record.id)
            ])
            if other_vehicle_assignments == 0:
                record.vehicle_id.sudo().zconnect_operational_status = 'available'
                
            record.message_post(
                body=_('Assignment completed.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_view_shipment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'zconnect.shipment',
            'view_mode': 'form',
            'res_id': self.shipment_id.id,
            'target': 'current',
        }
