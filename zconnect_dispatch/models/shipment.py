from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Shipment(models.Model):
    _inherit = 'zconnect.shipment'

    active_assignment_id = fields.Many2one('zconnect.dispatch.assignment', string='Active Assignment', readonly=True, help="The current offered or accepted assignment.")
    current_driver_id = fields.Many2one('zconnect.driver', related='active_assignment_id.driver_id', string='Current Driver', readonly=True, store=True)
    current_vehicle_id = fields.Many2one('fleet.vehicle', related='active_assignment_id.vehicle_id', string='Current Vehicle', readonly=True, store=True)

    def action_offer_assignment(self, driver_id, vehicle_id):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Shipment must be in confirmed state to offer an assignment."))
            
        driver = self.env['zconnect.driver'].browse(driver_id)
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        
        # We simulate the assignment creation which has validation hooks
        # But we also do validation here explicitly as requested:
        if driver.verification_status != 'verified':
            raise UserError(_("Driver %s is not verified.") % driver.name)
        if driver.availability_status != 'available':
            raise UserError(_("Driver %s is not available.") % driver.name)

        if vehicle.zconnect_operational_status != 'available':
            raise UserError(_("Vehicle %s is not available.") % vehicle.name)
        
        if vehicle.zconnect_vehicle_category != self.vehicle_category:
            raise UserError(_("Vehicle category does not match the shipment requirement."))

        if vehicle.zconnect_payload_capacity_kg < self.weight_kg:
            raise UserError(_("Vehicle payload capacity is insufficient for this shipment."))
            
        if vehicle.zconnect_volume_capacity_cbm < self.volume_cbm:
            raise UserError(_("Vehicle volume capacity is insufficient for this shipment."))

        # Prevent another active offered/accepted assignment
        active_assignments = self.env['zconnect.dispatch.assignment'].search([
            ('shipment_id', '=', self.id),
            ('state', 'in', ['offered', 'accepted'])
        ])
        if active_assignments:
            raise UserError(_("This shipment already has an active (offered or accepted) assignment."))

        # Create assignment
        assignment = self.env['zconnect.dispatch.assignment'].create({
            'shipment_id': self.id,
            'driver_id': driver.id,
            'vehicle_id': vehicle.id,
            'state': 'offered',
            'assigned_by': self.env.user.id,
            'assigned_at': fields.Datetime.now(),
        })

        # Update shipment state and references
        self.write({
            'state': 'assigned',
            'active_assignment_id': assignment.id,
            'assigned_at': fields.Datetime.now(),
        })
        
        self.message_post(
            body=_('Assignment %s offered to driver %s.') % (assignment.name, driver.name),
            subtype_xmlid='mail.mt_note',
        )
        return assignment

    def action_start_pickup(self):
        for record in self:
            record._validate_transition('en_route_pickup')
            if not record.active_assignment_id or record.active_assignment_id.state != 'accepted':
                raise UserError(_("There must be an accepted assignment to start pickup."))
            record.write({
                'state': 'en_route_pickup',
                'en_route_pickup_at': fields.Datetime.now(),
            })

    def action_mark_picked_up(self):
        for record in self:
            record._validate_transition('picked_up')
            record.write({
                'state': 'picked_up',
                'picked_up_at': fields.Datetime.now(),
            })

    def action_start_delivery(self):
        for record in self:
            record._validate_transition('in_transit')
            record.write({
                'state': 'in_transit',
                'in_transit_at': fields.Datetime.now(),
            })

    def action_mark_near_delivery(self):
        for record in self:
            record._validate_transition('near_delivery')
            record.write({
                'state': 'near_delivery',
                'near_delivery_at': fields.Datetime.now(),
            })

    def action_complete_delivery(self):
        """
        Transition shipment to 'delivered' state.
        This is called by the zconnect_pod module when a POD is submitted.
        """
        for record in self:
            record._validate_transition('delivered')
            record.write({
                'state': 'delivered',
                'delivered_at': fields.Datetime.now(),
            })
