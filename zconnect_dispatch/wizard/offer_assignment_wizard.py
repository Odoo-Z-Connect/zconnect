from odoo import models, fields, api, _

class OfferAssignmentWizard(models.TransientModel):
    _name = 'zconnect.dispatch.offer.wizard'
    _description = 'Offer Assignment Wizard'

    shipment_id = fields.Many2one('zconnect.shipment', string='Shipment', required=True, readonly=True)
    driver_id = fields.Many2one('zconnect.driver', string='Driver', required=True, domain="[('verification_status', '=', 'verified'), ('availability_status', '=', 'available')]")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, domain="[('zconnect_operational_status', '=', 'available')]")

    @api.onchange('shipment_id')
    def _onchange_shipment_id(self):
        if self.shipment_id:
            # Domain for vehicle based on shipment category and capacity
            return {'domain': {
                'vehicle_id': [
                    ('zconnect_operational_status', '=', 'available'),
                    ('zconnect_vehicle_category', '=', self.shipment_id.vehicle_category),
                    ('zconnect_payload_capacity_kg', '>=', self.shipment_id.weight_kg),
                    ('zconnect_volume_capacity_cbm', '>=', self.shipment_id.volume_cbm)
                ]
            }}

    def action_offer(self):
        self.ensure_one()
        self.shipment_id.action_offer_assignment(self.driver_id.id, self.vehicle_id.id)
        return {'type': 'ir.actions.act_window_close'}
