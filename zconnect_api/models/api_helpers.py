# -*- coding: utf-8 -*-
from odoo import models, api


class ZConnectApiHelper(models.AbstractModel):
    _name = 'zconnect.api.helper'
    _description = 'ZConnect API Serialization Helper'

    @api.model
    def _fmt_dt(self, dt):
        return dt.isoformat() if dt else None

    @api.model
    def _fmt_date(self, d):
        return d.isoformat() if d else None

    @api.model
    def serialize_driver(self, driver):
        d = driver
        vehicles = []
        for v in d.vehicle_ids:
            vehicles.append({
                'id': v.id,
                'name': v.name,
                'license_plate': v.license_plate or None,
            })
        return {
            'id': d.id,
            'driver_code': d.driver_code or None,
            'name': d.name,
            'phone': d.phone or None,
            'email': d.email or None,
            'national_id': d.national_id or None,
            'verification_status': d.verification_status,
            'availability_status': d.availability_status,
            'licence': {
                'class': d.licence_class or None,
                'number': d.licence_number or None,
                'expiry': self._fmt_date(d.licence_expiry),
                'expired': d.is_licence_expired,
            },
            'primary_vehicle': {
                'id': d.primary_vehicle_id.id,
                'name': d.primary_vehicle_id.name,
                'license_plate': d.primary_vehicle_id.license_plate or None,
            } if d.primary_vehicle_id else None,
            'authorised_vehicles': vehicles,
            'partner_id': d.partner_id.id if d.partner_id else None,
            'user_id': d.user_id.id if d.user_id else None,
            'created_at': self._fmt_dt(d.create_date),
            'updated_at': self._fmt_dt(d.write_date),
        }

    @api.model
    def serialize_shipment(self, shipment):
        s = shipment

        driver_snap = self.serialize_driver(s.current_driver_id) if s.current_driver_id else None

        vehicle_snap = None
        if s.current_vehicle_id:
            v = s.current_vehicle_id
            vehicle_snap = {'id': v.id, 'name': v.name, 'license_plate': v.license_plate or None}

        pod_snap = None
        if s.pod_id:
            p = s.pod_id
            pod_snap = {
                'id': p.id,
                'state': p.state if hasattr(p, 'state') else None,
                'recipient_name': p.recipient_name if hasattr(p, 'recipient_name') else None,
                'submitted_at': self._fmt_dt(p.submitted_at) if hasattr(p, 'submitted_at') else None,
            }

        return {
            'id': s.id,
            'name': s.name,
            'state': s.state,
            'payment_state': s.payment_state,
            'is_pricing_confirmed': s.is_pricing_confirmed,
            'customer': {
                'id': s.customer_id.id,
                'name': s.customer_id.name,
                'email': s.customer_email or s.customer_id.email or None,
                'phone': s.customer_phone or s.customer_id.phone or None,
            } if s.customer_id else None,
            'pickup': {
                'address': s.pickup_address,
                'contact_name': s.pickup_contact_name or None,
                'contact_phone': s.pickup_contact_phone or None,
                'latitude': s.pickup_latitude or 0.0,
                'longitude': s.pickup_longitude or 0.0,
            },
            'delivery': {
                'address': s.delivery_address,
                'contact_name': s.delivery_contact_name or None,
                'contact_phone': s.delivery_contact_phone or None,
                'latitude': s.delivery_latitude or 0.0,
                'longitude': s.delivery_longitude or 0.0,
            },
            'cargo': {
                'category': s.shipment_category,
                'vehicle_category_required': s.vehicle_category,
                'description': s.description or None,
                'special_instructions': s.special_instructions or None,
                'weight_kg': s.weight_kg,
                'volume_cbm': s.volume_cbm or 0.0,
                'length_cm': s.length_cm or 0.0,
                'width_cm': s.width_cm or 0.0,
                'height_cm': s.height_cm or 0.0,
            },
            'route': {
                'distance_km': s.distance_km or 0.0,
                'zone': {
                    'id': s.zone_id.id,
                    'name': s.zone_id.name,
                } if s.zone_id else None,
            },
            'pricing': {
                'rule': {
                    'id': s.pricing_rule_id.id,
                    'name': s.pricing_rule_id.name,
                } if s.pricing_rule_id else None,
                'base_fare': s.base_fare or 0.0,
                'distance_charge': s.distance_charge or 0.0,
                'weight_charge': s.weight_charge or 0.0,
                'zone_charge': s.zone_charge or 0.0,
                'minimum_fare': s.minimum_fare or 0.0,
                'subtotal': s.subtotal or 0.0,
                'total_amount': s.total_amount or 0.0,
                'currency': s.currency_id.name if s.currency_id else 'USD',
                'currency_symbol': s.currency_id.symbol if s.currency_id else '$',
                'calculated_at': self._fmt_dt(s.pricing_calculated_at),
                'quoted_at': self._fmt_dt(s.quoted_at),
            },
            'assigned_driver': driver_snap,
            'assigned_vehicle': vehicle_snap,
            'pod': pod_snap,
            'exception': {
                'reason': s.exception_reason or None,
                'at': self._fmt_dt(s.exception_at),
            } if s.exception_reason else None,
            'cancellation': {
                'reason': s.cancellation_reason or None,
                'at': self._fmt_dt(s.cancelled_at),
                'by': s.cancelled_by.name if s.cancelled_by else None,
            } if s.cancellation_reason else None,
            'timeline': {
                'created_at': self._fmt_dt(s.create_date),
                'quoted_at': self._fmt_dt(s.quoted_at),
                'confirmed_at': self._fmt_dt(s.confirmed_at),
                'assigned_at': self._fmt_dt(s.assigned_at),
                'en_route_pickup_at': self._fmt_dt(s.en_route_pickup_at),
                'picked_up_at': self._fmt_dt(s.picked_up_at),
                'in_transit_at': self._fmt_dt(s.in_transit_at),
                'near_delivery_at': self._fmt_dt(s.near_delivery_at),
                'delivered_at': self._fmt_dt(s.delivered_at),
            },
            'created_at': self._fmt_dt(s.create_date),
            'updated_at': self._fmt_dt(s.write_date),
        }

    @api.model
    def serialize_assignment(self, assignment):
        a = assignment

        shipment_data = self.serialize_shipment(a.shipment_id) if a.shipment_id else None
        driver_data = self.serialize_driver(a.driver_id) if a.driver_id else None

        vehicle_data = None
        if a.vehicle_id:
            v = a.vehicle_id
            vehicle_data = {'id': v.id, 'name': v.name, 'license_plate': v.license_plate or None}

        return {
            'id': a.id,
            'name': a.name,
            'state': a.state,
            'payment_status': a.payment_status,
            'shipment_category': a.shipment_category,
            'shipment_description': a.shipment_description or None,
            'weight_kg': a.weight_kg or 0.0,
            'volume_cbm': a.volume_cbm or 0.0,
            'pickup': {
                'address': a.pickup_address or None,
                'contact_name': a.pickup_contact_name or None,
                'contact_phone': a.pickup_contact_phone or None,
                'latitude': a.shipment_id.pickup_latitude if a.shipment_id else 0.0,
                'longitude': a.shipment_id.pickup_longitude if a.shipment_id else 0.0,
            },
            'delivery': {
                'address': a.delivery_address or None,
                'contact_name': a.delivery_contact_name or None,
                'contact_phone': a.delivery_contact_phone or None,
                'latitude': a.shipment_id.delivery_latitude if a.shipment_id else 0.0,
                'longitude': a.shipment_id.delivery_longitude if a.shipment_id else 0.0,
            },
            'rejection_reason': a.rejection_reason or None,
            'timeline': {
                'assigned_at': self._fmt_dt(a.assigned_at),
                'accepted_at': self._fmt_dt(a.accepted_at),
                'rejected_at': self._fmt_dt(a.rejected_at),
            },
            'assigned_by': a.assigned_by.name if a.assigned_by else None,
            'driver': driver_data,
            'vehicle': vehicle_data,
            'shipment': shipment_data,
            'created_at': self._fmt_dt(a.create_date),
            'updated_at': self._fmt_dt(a.write_date),
        }
