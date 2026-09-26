# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError, AccessError

class ZConnectApi(http.Controller):
    def _json_response(self, data, status=200):
        return Response(json.dumps(data), status=status, content_type='application/json')
        
    def _success(self, data):
        return self._json_response({'success': True, 'data': data})
        
    def _error(self, code, message, status=400):
        return self._json_response({'success': False, 'error': {'code': code, 'message': message}}, status=status)

    def _handle_exception(self, e):
        if isinstance(e, AccessError):
            return self._error('FORBIDDEN', str(e), 403)
        elif isinstance(e, ValidationError):
            return self._error('VALIDATION_ERROR', str(e), 400)
        elif isinstance(e, UserError):
            return self._error('USER_ERROR', str(e), 400)
        return self._error('SERVER_ERROR', "An internal error occurred", 500)

    @http.route('/api/v1/zconnect/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health_check(self):
        return self._success({'service': 'zconnect', 'status': 'ok'})

    @http.route('/api/v1/zconnect/me', type='http', auth='user', methods=['GET'], csrf=False)
    def me(self):
        user = request.env.user
        return self._success({'id': user.id, 'name': user.name, 'login': user.login, 'partner_id': user.partner_id.id})

    # --- CUSTOMER ---
    @http.route('/api/v1/zconnect/shipments', type='http', auth='user', methods=['GET'], csrf=False)
    def list_shipments(self):
        partner = request.env.user.partner_id
        shipments = request.env['zconnect.shipment'].search([('customer_id', '=', partner.id)])
        data = [request.env['zconnect.api.helper'].serialize_shipment(s) for s in shipments]
        return self._success(data)
        
    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id != partner:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
            
        data = request.env['zconnect.api.helper'].serialize_shipment(shipment)
        return self._success(data)

    @http.route('/api/v1/zconnect/shipments', type='http', auth='user', methods=['POST'], csrf=False)
    def create_shipment(self, **post):
        partner = request.env.user.partner_id
        try:
            payload = json.loads(request.httprequest.data)
            payload['customer_id'] = partner.id
            shipment = request.env['zconnect.shipment'].create(payload)
            data = request.env['zconnect.api.helper'].serialize_shipment(shipment)
            return self._success(data)
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/quote', type='http', auth='user', methods=['POST'], csrf=False)
    def quote_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id != partner:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
        try:
            shipment.action_calculate_quote()
            return self._success(request.env['zconnect.api.helper'].serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id != partner:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
        try:
            shipment.action_confirm()
            return self._success(request.env['zconnect.api.helper'].serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    # --- DRIVER ---
    def _get_driver(self):
        # Match driver by partner_id
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].search([('partner_id', '=', partner.id)], limit=1)
        return driver

    @http.route('/api/v1/zconnect/driver/assignments', type='http', auth='user', methods=['GET'], csrf=False)
    def list_assignments(self):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
        
        assignments = request.env['zconnect.dispatch.assignment'].search([('driver_id', '=', driver.id)])
        data = [request.env['zconnect.api.helper'].serialize_assignment(a) for a in assignments]
        return self._success(data)

    @http.route('/api/v1/zconnect/driver/assignments/<int:assignment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id != driver:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        return self._success(request.env['zconnect.api.helper'].serialize_assignment(assignment))

    @http.route('/api/v1/zconnect/assignments/<int:assignment_id>/accept', type='http', auth='user', methods=['POST'], csrf=False)
    def accept_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id != driver:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        try:
            assignment.action_accept()
            return self._success(request.env['zconnect.api.helper'].serialize_assignment(assignment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/assignments/<int:assignment_id>/reject', type='http', auth='user', methods=['POST'], csrf=False)
    def reject_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id != driver:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        try:
            payload = json.loads(request.httprequest.data)
            reason = payload.get('reason', 'No reason provided')
            
            # The method requires a rejection_reason on the assignment or wizard.
            # In our implementation of dispatch, how is action_reject implemented?
            # It might require context or wizard.
            # I will write `assignment.action_reject_api(reason)` if needed, but let's see.
            # If action_reject() opens a wizard, we'll need a way to pass reason directly.
            # For now, let's just write `rejection_reason` then call `action_reject()`.
            # If action_reject is meant to be called from a wizard, it might just need the field populated.
            assignment.rejection_reason = reason
            assignment.action_reject()
            return self._success(request.env['zconnect.api.helper'].serialize_assignment(assignment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/status', type='http', auth='user', methods=['POST'], csrf=False)
    def update_shipment_status(self, shipment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        
        # Security: ensure this driver is assigned to this shipment
        active_assignment = request.env['zconnect.dispatch.assignment'].search([
            ('shipment_id', '=', shipment.id),
            ('driver_id', '=', driver.id),
            ('state', 'in', ['accepted', 'in_progress'])
        ], limit=1)
        if not active_assignment:
            return self._error('FORBIDDEN', 'You are not actively assigned to this shipment.', 403)

        try:
            payload = json.loads(request.httprequest.data)
            new_status = payload.get('status')
            
            # Use domain methods
            if new_status == 'en_route_pickup':
                shipment.action_start_pickup()
            elif new_status == 'picked_up':
                shipment.action_mark_picked_up()
            elif new_status == 'in_transit':
                shipment.action_start_delivery()
            elif new_status == 'near_delivery':
                shipment.action_mark_near_delivery()
            else:
                return self._error('VALIDATION_ERROR', 'Invalid or prohibited status transition requested', 400)
                
            return self._success(request.env['zconnect.api.helper'].serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/pod', type='http', auth='user', methods=['POST'], csrf=False)
    def submit_pod(self, shipment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
            
        active_assignment = request.env['zconnect.dispatch.assignment'].search([
            ('shipment_id', '=', shipment.id),
            ('driver_id', '=', driver.id),
            ('state', 'in', ['in_progress'])
        ], limit=1)
        if not active_assignment:
            return self._error('FORBIDDEN', 'You are not assigned to this shipment.', 403)
            
        try:
            payload = json.loads(request.httprequest.data)
            
            # Create POD
            pod_vals = {
                'shipment_id': shipment.id,
                'driver_id': driver.id,
                'recipient_name': payload.get('recipient_name'),
                'recipient_phone': payload.get('recipient_phone'),
                'delivery_notes': payload.get('delivery_notes'),
                'latitude': payload.get('latitude', 0.0),
                'longitude': payload.get('longitude', 0.0),
                'signature': payload.get('signature'), # Base64
                'photo': payload.get('photo'), # Base64
            }
            pod = request.env['zconnect.pod'].create(pod_vals)
            
            # Submit POD and complete shipment
            pod.action_submit()
            return self._success(request.env['zconnect.api.helper'].serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)
