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
        import traceback
        traceback.print_exc()
        if isinstance(e, AccessError):
            return self._error('FORBIDDEN', str(e), 403)
        elif isinstance(e, ValidationError):
            return self._error('VALIDATION_ERROR', str(e), 400)
        elif isinstance(e, UserError):
            return self._error('USER_ERROR', str(e), 400)
        return self._error('SERVER_ERROR', "An internal error occurred: " + str(e), 500)

    # --- AUTHENTICATION ---
    @http.route('/api/v1/zconnect/auth/login', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_login(self, **post):
        try:
            payload = json.loads(request.httprequest.data)
            db = payload.get('db') or request.env.cr.dbname
            login = payload.get('login')
            password = payload.get('password')
            
            credential = {'login': login, 'password': password, 'type': 'password'}
            auth_info = request.session.authenticate(request.env, credential)
            uid = auth_info.get('uid') if isinstance(auth_info, dict) else auth_info
            if not uid:
                return self._error('UNAUTHORIZED', 'Invalid login credentials', 401)
                
            user = request.env['res.users'].browse(uid)
            session_id = request.session.sid
            
            role = 'customer'
            driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)
            if driver:
                role = 'driver'
                
            data = {
                'uid': uid,
                'session_id': session_id,
                'name': user.name,
                'role': role,
                'partner_id': user.partner_id.id
            }
            return self._success(data)
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/auth/signup', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_signup(self, **post):
        try:
            payload = json.loads(request.httprequest.data)
            name = payload.get('name')
            login = payload.get('login')
            password = payload.get('password')
            phone = payload.get('phone')
            
            existing = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if existing:
                return self._error('VALIDATION_ERROR', 'User with this email already exists', 400)
                
            portal_group = request.env.ref('base.group_portal')
            customer_group = request.env.ref('zconnect_base.group_zconnect_customer')
            user_vals = {
                'name': name,
                'login': login,
                'password': password,
                'group_ids': [(6, 0, [portal_group.id, customer_group.id])]
            }
            user = request.env['res.users'].sudo().create(user_vals)
            
            if phone:
                user.partner_id.sudo().with_context(skip_duplicate_check=True).write({'phone': phone})
                
            credential = {'login': login, 'password': password, 'type': 'password'}
            auth_info = request.session.authenticate(request.env, credential)
            uid = auth_info.get('uid') if isinstance(auth_info, dict) else auth_info
            session_id = request.session.sid
            
            data = {
                'uid': uid,
                'session_id': session_id,
                'name': user.name,
                'role': 'customer',
                'partner_id': user.partner_id.id
            }
            return self._success(data)
        except Exception as e:
            return self._handle_exception(e)

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
        shipments = request.env['zconnect.shipment'].sudo().search([('customer_id', '=', partner.id)])
        data = [request.env['zconnect.api.helper'].sudo().serialize_shipment(s) for s in shipments]
        return self._success(data)
        
    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id.id != partner.id:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
            
        data = request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment)
        return self._success(data)

    @http.route('/api/v1/zconnect/shipments', type='http', auth='user', methods=['POST'], csrf=False)
    def create_shipment(self, **post):
        partner = request.env.user.partner_id
        try:
            payload = json.loads(request.httprequest.data)
            payload['customer_id'] = partner.id
            sudo_env = request.env(user=1)
            shipment = sudo_env['zconnect.shipment'].create(payload)
            data = sudo_env['zconnect.api.helper'].serialize_shipment(shipment)
            return self._success(data)
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/quote', type='http', auth='user', methods=['POST'], csrf=False)
    def quote_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id.id != partner.id:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
        try:
            shipment.sudo().action_calculate_quote()
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/prepare_payment', type='http', auth='user', methods=['POST'], csrf=False)
    def prepare_payment(self, shipment_id):
        """Transition shipment from quoted → awaiting_payment. Customer accepts the quote."""
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id.id != partner.id:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
        try:
            shipment.sudo().action_prepare_payment()
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm_shipment(self, shipment_id):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        if shipment.customer_id.id != partner.id:
            return self._error('FORBIDDEN', 'You do not have access to this shipment.', 403)
        try:
            shipment.sudo().action_confirm()
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    # --- DRIVER ---
    def _get_driver(self):
        # Match driver by partner_id
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        return driver

    @http.route('/api/v1/zconnect/driver/assignments', type='http', auth='user', methods=['GET'], csrf=False)
    def list_assignments(self):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
        
        assignments = request.env['zconnect.dispatch.assignment'].sudo().search([('driver_id', '=', driver.id)])
        data = [request.env['zconnect.api.helper'].sudo().serialize_assignment(a) for a in assignments]
        return self._success(data)

    @http.route('/api/v1/zconnect/driver/assignments/<int:assignment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].sudo().browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id.id != driver.id:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        return self._success(request.env['zconnect.api.helper'].sudo().serialize_assignment(assignment))

    @http.route('/api/v1/zconnect/assignments/<int:assignment_id>/accept', type='http', auth='user', methods=['POST'], csrf=False)
    def accept_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].sudo().browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id.id != driver.id:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        try:
            assignment.sudo().action_accept()
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_assignment(assignment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/assignments/<int:assignment_id>/reject', type='http', auth='user', methods=['POST'], csrf=False)
    def reject_assignment(self, assignment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        assignment = request.env['zconnect.dispatch.assignment'].sudo().browse(assignment_id)
        if not assignment.exists():
            return self._error('NOT_FOUND', 'Assignment not found', 404)
        if assignment.driver_id.id != driver.id:
            return self._error('FORBIDDEN', 'You do not have access to this assignment.', 403)
            
        try:
            payload = json.loads(request.httprequest.data)
            reason = payload.get('reason', 'No reason provided')
            assignment.sudo().write({'rejection_reason': reason})
            assignment.sudo().action_reject()
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_assignment(assignment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/status', type='http', auth='user', methods=['POST'], csrf=False)
    def update_shipment_status(self, shipment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
        
        # Security: ensure this driver is assigned to this shipment
        active_assignment = request.env['zconnect.dispatch.assignment'].sudo().search([
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
                shipment.sudo().action_start_pickup()
            elif new_status == 'picked_up':
                shipment.sudo().action_mark_picked_up()
            elif new_status == 'in_transit':
                shipment.sudo().action_start_delivery()
            elif new_status == 'near_delivery':
                shipment.sudo().action_mark_near_delivery()
            else:
                return self._error('VALIDATION_ERROR', 'Invalid or prohibited status transition requested', 400)
                
            return self._success(request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)

    @http.route('/api/v1/zconnect/shipments/<int:shipment_id>/pod', type='http', auth='user', methods=['POST'], csrf=False)
    def submit_pod(self, shipment_id):
        driver = self._get_driver()
        if not driver:
            return self._error('FORBIDDEN', 'User is not a driver', 403)
            
        shipment = request.env['zconnect.shipment'].sudo().browse(shipment_id)
        if not shipment.exists():
            return self._error('NOT_FOUND', 'Shipment not found', 404)
            
        active_assignment = request.env['zconnect.dispatch.assignment'].sudo().search([
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
                'signature': payload.get('signature'),  # Base64
                'photo': payload.get('photo'),           # Base64
            }
            pod = request.env['zconnect.pod'].sudo().create(pod_vals)
            
            # Submit POD and complete shipment
            pod.sudo().action_submit()
            
            # Automatic payment trigger if driver collects Cash On Delivery
            if shipment.payment_state == 'pending':
                invoices = shipment.invoice_ids.filtered(
                    lambda i: i.state == 'posted' and i.payment_state == 'not_paid'
                )
                for invoice in invoices:
                    payment_vals = {
                        'payment_type': 'inbound',
                        'partner_type': 'customer',
                        'partner_id': invoice.partner_id.id,
                        'amount': invoice.amount_residual,
                        'currency_id': invoice.currency_id.id,
                        'payment_method_line_id': request.env['account.payment.method.line'].sudo().search([], limit=1).id,
                        'journal_id': request.env['account.journal'].sudo().search([('type', 'in', ['cash', 'bank'])], limit=1).id,
                    }
                    payment = request.env['account.payment'].sudo().create(payment_vals)
                    payment.sudo().action_post()
                    # Reconcile
                    lines = (invoice.line_ids + payment.line_ids).filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                    )
                    lines.reconcile()
                
                shipment.sudo().write({'payment_state': 'paid'})

            return self._success(request.env['zconnect.api.helper'].sudo().serialize_shipment(shipment))
        except Exception as e:
            return self._handle_exception(e)
