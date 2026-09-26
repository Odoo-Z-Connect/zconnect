# -*- coding: utf-8 -*-
from odoo import models, api

class ZConnectApiHelper(models.AbstractModel):
    _name = 'zconnect.api.helper'
    _description = 'ZConnect API Serialization Helper'

    @api.model
    def serialize_shipment(self, shipment):
        return {
            'id': shipment.id,
            'name': shipment.name,
            'state': shipment.state,
            'payment_state': shipment.payment_state,
            'pickup_address': shipment.pickup_address,
            'delivery_address': shipment.delivery_address,
            'weight_kg': shipment.weight_kg,
            'total_amount': shipment.total_amount,
        }

    @api.model
    def serialize_assignment(self, assignment):
        return {
            'id': assignment.id,
            'name': assignment.name,
            'shipment_id': assignment.shipment_id.id,
            'shipment_name': assignment.shipment_id.name,
            'state': assignment.state,
            'driver_id': assignment.driver_id.id,
            'vehicle_id': assignment.vehicle_id.id,
        }
