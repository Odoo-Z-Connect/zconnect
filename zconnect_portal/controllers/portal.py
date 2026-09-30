# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class ZConnectPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'zconnect_shipment_count' in counters:
            values['zconnect_shipment_count'] = request.env['zconnect.shipment'].search_count([('customer_id', '=', partner.id)])
        
        # Check if driver
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if driver:
            if 'zconnect_assignment_count' in counters:
                values['zconnect_assignment_count'] = request.env['zconnect.dispatch.assignment'].search_count([('driver_id', '=', driver.id)])
            values['is_zconnect_driver'] = True
        return values

    # --- CUSTOMER REGISTRATION / SIGNUP ---
    @http.route(['/customer/signup'], type='http', auth="public", methods=['GET', 'POST'], website=True)
    def customer_signup(self, **post):
        redirect_target = post.get('redirect', '/my/shipments/new')
        values = {'redirect': redirect_target, 'error': None, 'form_data': {}}
        
        if request.httprequest.method == 'POST':
            name = (post.get('name') or '').strip()
            email = (post.get('email') or '').strip().lower()
            phone = (post.get('phone') or '').strip()
            street = (post.get('street') or '').strip()
            city = (post.get('city') or 'Harare').strip()
            password = post.get('password') or ''
            confirm_password = post.get('confirm_password') or ''

            values['form_data'] = {
                'name': name, 'email': email, 'phone': phone,
                'street': street, 'city': city
            }

            if not name or not email or not password:
                values['error'] = 'Name, email, and password are required.'
                return request.render('zconnect_portal.customer_signup', values)

            if password != confirm_password:
                values['error'] = 'Passwords do not match. Please verify your password.'
                return request.render('zconnect_portal.customer_signup', values)

            # Check existing user
            existing = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if existing:
                values['error'] = 'An account with this email already exists. Please sign in or use another email.'
                return request.render('zconnect_portal.customer_signup', values)

            try:
                portal_group = request.env.ref('base.group_portal')
                user_vals = {
                    'name': name,
                    'login': email,
                    'email': email,
                    'password': password,
                    'groups_id': [(6, 0, [portal_group.id])],
                    'company_id': 1,
                }
                user = request.env['res.users'].sudo().create(user_vals)
                
                # Update partner details with phone, location, address
                user.partner_id.sudo().write({
                    'phone': phone,
                    'mobile': phone,
                    'street': street,
                    'city': city,
                    'country_id': 249, # Zimbabwe
                    'zconnect_is_customer': True,
                })

                # Authenticate and login immediately
                request.session.authenticate(request.db, email, password)
                return request.redirect(redirect_target)
            except Exception as e:
                values['error'] = f'Registration error: {str(e)}'
                return request.render('zconnect_portal.customer_signup', values)

        return request.render('zconnect_portal.customer_signup', values)

    # --- CONTACT US ---
    @http.route(['/contactus'], type='http', auth="public", methods=['GET', 'POST'], website=True)
    def contactus_page(self, **post):
        values = {'success': False}
        if request.httprequest.method == 'POST':
            values['success'] = True
        return request.render('zconnect_portal.zconnect_contactus', values)

    # --- CUSTOMER PORTAL ---
    @http.route(['/my/shipments', '/my/shipments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shipments(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Shipment = request.env['zconnect.shipment']

        domain = [('customer_id', '=', partner.id)]
        shipment_count = Shipment.search_count(domain)
        pager = portal_pager(
            url="/my/shipments",
            total=shipment_count,
            page=page,
            step=self._items_per_page
        )
        shipments = Shipment.search(domain, limit=self._items_per_page, offset=pager['offset'], order="create_date desc")
        values.update({
            'shipments': shipments,
            'page_name': 'shipments',
            'pager': pager,
            'default_url': '/my/shipments',
        })
        return request.render("zconnect_portal.portal_my_shipments", values)

    @http.route(['/my/shipments/<int:shipment_id>'], type='http', auth="user", website=True)
    def portal_my_shipment_detail(self, shipment_id, **kw):
        partner = request.env.user.partner_id
        try:
            shipment = request.env['zconnect.shipment'].browse(shipment_id)
            if not shipment.exists():
                raise MissingError("Shipment not found")
            if shipment.customer_id != partner:
                raise AccessError("You do not have access to this shipment.")
        except (MissingError, AccessError):
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'shipment': shipment,
            'page_name': 'shipment_detail',
        })
        return request.render("zconnect_portal.portal_shipment_detail", values)

    @http.route(['/my/shipments/new'], type='http', auth="public", website=True)
    def portal_new_shipment(self, **kw):
        values = self._prepare_portal_layout_values()
        api_key = request.env['ir.config_parameter'].sudo().get_param('zconnect.google_maps_api_key', 'AIzaSyCxVvPpOrhUw2O0-PwSfy6BaFIGfiFHBr8')
        is_logged_in = not request.env.user._is_public()
        values.update({
            'page_name': 'new_shipment',
            'google_maps_api_key': api_key,
            'is_logged_in': is_logged_in,
            'vehicle_categories': request.env['zconnect.shipment']._fields['vehicle_category'].selection,
            'shipment_categories': request.env['zconnect.shipment']._fields['shipment_category'].selection,
        })
        return request.render("zconnect_portal.portal_new_shipment", values)

    @http.route(['/my/shipments/create'], type='http', auth="public", methods=['POST'], website=True)
    def portal_create_shipment(self, **post):
        if request.env.user._is_public():
            # If not logged in, redirect to signup
            return request.redirect('/customer/signup?redirect=/my/shipments/new')

        partner = request.env.user.partner_id
        vals = {
            'customer_id': partner.id,
            'pickup_address': post.get('pickup_address'),
            'delivery_address': post.get('delivery_address'),
            'vehicle_category': post.get('vehicle_category'),
            'shipment_category': post.get('shipment_category'),
            'weight_kg': float(post.get('weight_kg') or 0.0),
            'distance_km': float(post.get('distance_km') or 0.0),
            'pickup_contact_name': post.get('pickup_contact_name') or partner.name,
            'pickup_phone': post.get('pickup_phone') or partner.phone,
            'delivery_contact_name': post.get('delivery_contact_name'),
            'delivery_phone': post.get('delivery_phone'),
        }
        try:
            shipment = request.env['zconnect.shipment'].create(vals)
            shipment.action_calculate_quote()
            return request.redirect(f'/my/shipments/{shipment.id}')
        except Exception:
            return request.redirect('/my/shipments/new?error=1')

    @http.route(['/my/shipments/<int:shipment_id>/confirm'], type='http', auth="user", methods=['POST'], website=True)
    def portal_confirm_shipment(self, shipment_id, **kw):
        partner = request.env.user.partner_id
        shipment = request.env['zconnect.shipment'].browse(shipment_id)
        if shipment.exists() and shipment.customer_id == partner:
            shipment.action_confirm()
        return request.redirect(f'/my/shipments/{shipment_id}')

    # --- DRIVER PORTAL ---
    @http.route(['/my/assignments', '/my/assignments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_assignments(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not driver:
            return request.redirect('/my')

        Assignment = request.env['zconnect.dispatch.assignment']
        domain = [('driver_id', '=', driver.id)]
        assignment_count = Assignment.search_count(domain)
        pager = portal_pager(
            url="/my/assignments",
            total=assignment_count,
            page=page,
            step=self._items_per_page
        )
        assignments = Assignment.search(domain, limit=self._items_per_page, offset=pager['offset'], order="create_date desc")
        values.update({
            'assignments': assignments,
            'page_name': 'assignments',
            'pager': pager,
            'default_url': '/my/assignments',
        })
        return request.render("zconnect_portal.portal_my_assignments", values)

    @http.route(['/my/assignments/<int:assignment_id>'], type='http', auth="user", website=True)
    def portal_my_assignment_detail(self, assignment_id, **kw):
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not driver:
            return request.redirect('/my')

        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if not assignment.exists() or assignment.driver_id != driver:
            return request.redirect('/my/assignments')

        values = self._prepare_portal_layout_values()
        values.update({
            'assignment': assignment,
            'page_name': 'assignment_detail',
        })
        return request.render("zconnect_portal.portal_assignment_detail", values)

    @http.route(['/my/assignments/<int:assignment_id>/accept'], type='http', auth="user", methods=['POST'], website=True)
    def portal_accept_assignment(self, assignment_id, **kw):
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if assignment.exists() and assignment.driver_id == driver:
            assignment.action_accept()
        return request.redirect(f'/my/assignments/{assignment_id}')

    @http.route(['/my/assignments/<int:assignment_id>/reject'], type='http', auth="user", methods=['POST'], website=True)
    def portal_reject_assignment(self, assignment_id, **kw):
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if assignment.exists() and assignment.driver_id == driver:
            assignment.rejection_reason = kw.get('reason', 'No reason provided')
            assignment.action_reject()
        return request.redirect(f'/my/assignments')

    @http.route(['/my/assignments/<int:assignment_id>/status'], type='http', auth="user", methods=['POST'], website=True)
    def portal_update_assignment_status(self, assignment_id, **kw):
        partner = request.env.user.partner_id
        driver = request.env['zconnect.driver'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        assignment = request.env['zconnect.dispatch.assignment'].browse(assignment_id)
        if assignment.exists() and assignment.driver_id == driver:
            status = kw.get('status')
            if status == 'en_route_pickup':
                assignment.shipment_id.action_start_pickup()
            elif status == 'picked_up':
                assignment.shipment_id.action_mark_picked_up()
            elif status == 'in_transit':
                assignment.shipment_id.action_start_delivery()
            elif status == 'near_delivery':
                assignment.shipment_id.action_mark_near_delivery()
        return request.redirect(f'/my/assignments/{assignment_id}')
