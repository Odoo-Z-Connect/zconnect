# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.

from odoo import models, api, fields
from odoo.exceptions import AccessError
import datetime
from dateutil.relativedelta import relativedelta


class ZConnectDashboard(models.AbstractModel):
    _name = 'zconnect.dashboard'
    _description = 'ZConnect Grand Operations Dashboard Analytics'

    @api.model
    def get_dashboard_data(self, date_filter='all'):
        """
        Main method to retrieve comprehensive logistics command center aggregations.
        Security check: Only dispatcher or finance (manager/admin) can access.
        """
        # Ensure user has dispatcher, manager, admin, or system rights
        if not (self.env.is_superuser() or
                self.env.user.has_group('base.group_system') or
                self.env.user.has_group('zconnect_base.group_zconnect_dispatcher') or
                self.env.user.has_group('zconnect_base.group_zconnect_manager') or
                self.env.user.has_group('zconnect_base.group_zconnect_admin')):
            raise AccessError("You do not have access to the Operations Dashboard.")

        is_finance = (self.env.is_superuser() or
                      self.env.user.has_group('base.group_system') or
                      self.env.user.has_group('zconnect_base.group_zconnect_manager') or
                      self.env.user.has_group('zconnect_base.group_zconnect_admin') or
                      self.env.user.has_group('zconnect_base.group_zconnect_finance'))

        domain_create = []
        domain_deliver = []

        now = fields.Datetime.now()
        start_date = None

        if date_filter == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            domain_create = [('create_date', '>=', start_date)]
            domain_deliver = [('delivered_at', '>=', start_date)]
        elif date_filter == '7d':
            start_date = now - relativedelta(days=7)
            domain_create = [('create_date', '>=', start_date)]
            domain_deliver = [('delivered_at', '>=', start_date)]
        elif date_filter == '30d':
            start_date = now - relativedelta(days=30)
            domain_create = [('create_date', '>=', start_date)]
            domain_deliver = [('delivered_at', '>=', start_date)]

        Shipment = self.env['zconnect.shipment']
        Driver = self.env['zconnect.driver']
        Vehicle = self.env['fleet.vehicle']
        Assignment = self.env['zconnect.dispatch.assignment']

        # Total Shipments in current filter scope
        total_shipments = Shipment.search_count(domain_create)

        # State counts via read_group for high performance
        state_groups = Shipment._read_group(domain_create, ['state'], ['__count'])
        state_counts = {state: count for state, count in state_groups}

        # Payment state counts
        payment_groups = Shipment._read_group(domain_create, ['payment_state'], ['__count'])
        payment_counts = {p_state: count for p_state, count in payment_groups}

        awaiting_payment = payment_counts.get('pending', 0) + payment_counts.get('failed', 0)

        # Active shipments (orders currently in the active logistics pipeline)
        active_states = ['confirmed', 'assigned', 'en_route_pickup', 'picked_up', 'in_transit', 'near_delivery']
        active_shipments_count = sum(state_counts.get(s, 0) for s in active_states)
        in_transit_count = state_counts.get('in_transit', 0) + state_counts.get('picked_up', 0)

        kpis = {
            'total_shipments': total_shipments,
            'active_shipments': active_shipments_count,
            'awaiting_payment': awaiting_payment,
            'draft': state_counts.get('draft', 0),
            'quoted': state_counts.get('quoted', 0),
            'confirmed': state_counts.get('confirmed', 0),
            'assigned': state_counts.get('assigned', 0),
            'en_route_pickup': state_counts.get('en_route_pickup', 0),
            'picked_up': state_counts.get('picked_up', 0),
            'in_transit': state_counts.get('in_transit', 0),
            'in_transit_total': in_transit_count,
            'near_delivery': state_counts.get('near_delivery', 0),
            'delivered': state_counts.get('delivered', 0),
            'cancelled': state_counts.get('cancelled', 0),
            'exceptions': state_counts.get('exception', 0),
        }

        # Financials (strictly accessible only by Manager, Admin, or Finance)
        financial = {}
        if is_finance:
            paid_shipments = Shipment.search(domain_create + [('payment_state', '=', 'paid')])
            paid_revenue = sum(paid_shipments.mapped('total_amount'))

            outstanding_shipments = Shipment.search(domain_create + [('payment_state', 'in', ['pending', 'failed', 'unpaid']), ('state', '!=', 'cancelled')])
            outstanding = sum(outstanding_shipments.mapped('total_amount'))

            invoiced_shipments = Shipment.search(domain_create + [('invoice_id', '!=', False)])
            invoiced_total = sum(invoiced_shipments.mapped('total_amount'))

            failed_payments = payment_counts.get('failed', 0)

            financial = {
                'paid_revenue': paid_revenue,
                'outstanding': outstanding,
                'invoiced_total': invoiced_total,
                'failed_payments': failed_payments,
                'currency': self.env.company.currency_id.symbol or '$',
            }

        # Drivers availability & counts
        drivers_available = Driver.search_count([('availability_status', '=', 'available')])
        drivers_busy = Driver.search_count([('availability_status', '=', 'unavailable')])
        drivers_total = Driver.search_count([])

        drivers = {
            'available': drivers_available,
            'busy': drivers_busy,
            'total': drivers_total,
        }

        # Vehicles operational capacity
        vehicles_available = Vehicle.search_count([('zconnect_operational_status', '=', 'available')])
        vehicles_assigned = Vehicle.search_count([('zconnect_operational_status', '=', 'assigned')])
        vehicles_maintenance = Vehicle.search_count([('zconnect_operational_status', '=', 'maintenance')])
        vehicles_busy = vehicles_assigned + vehicles_maintenance
        vehicles_total = Vehicle.search_count([])

        vehicles = {
            'available': vehicles_available,
            'busy': vehicles_busy,
            'assigned': vehicles_assigned,
            'maintenance': vehicles_maintenance,
            'total': vehicles_total,
        }

        # Active Dispatch Assignments count
        active_assignments_count = Assignment.search_count([('state', 'in', ['offered', 'accepted'])])

        # Pipeline Flow Data (Deterministic breakdown of stages)
        pipeline_stages = [
            {'code': 'confirmed', 'label': 'Confirmed', 'count': state_counts.get('confirmed', 0), 'color': '#6366F1', 'icon': 'fa-check'},
            {'code': 'assigned', 'label': 'Assigned', 'count': state_counts.get('assigned', 0), 'color': '#8B5CF6', 'icon': 'fa-user'},
            {'code': 'en_route_pickup', 'label': 'En Route', 'count': state_counts.get('en_route_pickup', 0), 'color': '#3B82F6', 'icon': 'fa-location-arrow'},
            {'code': 'picked_up', 'label': 'Picked Up', 'count': state_counts.get('picked_up', 0), 'color': '#0EA5E9', 'icon': 'fa-cube'},
            {'code': 'in_transit', 'label': 'In Transit', 'count': state_counts.get('in_transit', 0), 'color': '#06B6D4', 'icon': 'fa-truck'},
            {'code': 'near_delivery', 'label': 'Near Delivery', 'count': state_counts.get('near_delivery', 0), 'color': '#F59E0B', 'icon': 'fa-map-marker'},
            {'code': 'delivered', 'label': 'Delivered', 'count': state_counts.get('delivered', 0), 'color': '#10B981', 'icon': 'fa-check-circle'},
        ]
        max_pipe = max([s['count'] for s in pipeline_stages] + [1])
        for s in pipeline_stages:
            s['percent'] = round((s['count'] / max_pipe) * 100, 1)

        # Standard status breakdown for backward-compatibility
        status_breakdown = [
            {'label': 'Draft', 'value': state_counts.get('draft', 0)},
            {'label': 'Quoted', 'value': state_counts.get('quoted', 0)},
            {'label': 'Confirmed', 'value': state_counts.get('confirmed', 0)},
            {'label': 'Assigned', 'value': state_counts.get('assigned', 0)},
            {'label': 'En Route Pickup', 'value': state_counts.get('en_route_pickup', 0)},
            {'label': 'Picked Up', 'value': state_counts.get('picked_up', 0)},
            {'label': 'In Transit', 'value': state_counts.get('in_transit', 0)},
            {'label': 'Near Delivery', 'value': state_counts.get('near_delivery', 0)},
            {'label': 'Delivered', 'value': state_counts.get('delivered', 0)},
            {'label': 'Cancelled', 'value': state_counts.get('cancelled', 0)},
            {'label': 'Exception', 'value': state_counts.get('exception', 0)},
        ]

        # Active In-Flight Deliveries Cards (Top active operational orders)
        active_shipments_records = Shipment.search(
            [('state', 'in', ['assigned', 'en_route_pickup', 'picked_up', 'in_transit', 'near_delivery'])],
            order='write_date desc',
            limit=4
        )
        active_deliveries = []
        progress_map = {
            'confirmed': 15,
            'assigned': 30,
            'en_route_pickup': 45,
            'picked_up': 60,
            'in_transit': 75,
            'near_delivery': 90,
            'delivered': 100
        }
        for r in active_shipments_records:
            active_deliveries.append({
                'id': r.id,
                'name': r.name,
                'customer': r.customer_id.name if r.customer_id else 'Direct Customer',
                'driver': r.active_driver_id.name if hasattr(r, 'active_driver_id') and r.active_driver_id else 'Unassigned',
                'vehicle': r.active_vehicle_id.name if hasattr(r, 'active_vehicle_id') and r.active_vehicle_id else 'No Vehicle',
                'origin': r.pickup_address or 'Origin',
                'destination': r.delivery_address or 'Destination',
                'state': r.state,
                'state_label': dict(Shipment._fields['state'].selection).get(r.state, r.state),
                'progress_percent': progress_map.get(r.state, 50),
                'amount': f"{self.env.company.currency_id.symbol or '$'}{r.total_amount:.2f}" if is_finance else '***',
                'payment_state': r.payment_state if is_finance else '***',
            })

        # Recent shipments (limit 8)
        recent_records = Shipment.search(domain_create, order='create_date desc', limit=8)
        recent_shipments = []
        for r in recent_records:
            recent_shipments.append({
                'id': r.id,
                'name': r.name,
                'customer': r.customer_id.name if r.customer_id else '',
                'driver': r.active_driver_id.name if hasattr(r, 'active_driver_id') and r.active_driver_id else '—',
                'vehicle': r.active_vehicle_id.name if hasattr(r, 'active_vehicle_id') and r.active_vehicle_id else '—',
                'amount': f"{self.env.company.currency_id.symbol or '$'}{r.total_amount:.2f}" if is_finance else '***',
                'payment_state': r.payment_state if is_finance else '***',
                'state': r.state,
                'state_label': dict(Shipment._fields['state'].selection).get(r.state, r.state),
                'create_date': r.create_date.strftime('%Y-%m-%d %H:%M') if r.create_date else ''
            })

        # Exceptions & Attention Required
        exceptions_list = []
        # Check failed payments
        if is_finance:
            failed_shipments = Shipment.search([('payment_state', '=', 'failed')], limit=3)
            for fs in failed_shipments:
                exceptions_list.append({
                    'type': 'payment',
                    'title': f'Failed Payment on {fs.name}',
                    'description': f'Customer {fs.customer_id.name or "N/A"} payment failed ({self.env.company.currency_id.symbol or "$"}{fs.total_amount:.2f})',
                    'res_model': 'zconnect.shipment',
                    'res_id': fs.id,
                    'severity': 'danger'
                })

        # Check shipment exceptions
        stuck_shipments = Shipment.search([('state', '=', 'exception')], limit=3)
        for ss in stuck_shipments:
            exceptions_list.append({
                'type': 'shipment',
                'title': f'Delivery Exception on {ss.name}',
                'description': 'Operational issue flagged during transit or delivery.',
                'res_model': 'zconnect.shipment',
                'res_id': ss.id,
                'severity': 'danger'
            })

        # Check vehicles in maintenance
        maint_vehicles = Vehicle.search([('zconnect_operational_status', '=', 'maintenance')], limit=2)
        for mv in maint_vehicles:
            exceptions_list.append({
                'type': 'vehicle',
                'title': f'Vehicle {mv.name} in Maintenance',
                'description': 'Vehicle offline for scheduled/unscheduled service.',
                'res_model': 'fleet.vehicle',
                'res_id': mv.id,
                'severity': 'warning'
            })

        # Time-Series Analytics Chart Data (Deterministic trend generation based on real records)
        chart_data = self._generate_analytics_trend(date_filter, Shipment)

        return {
            'has_finance_access': is_finance,
            'kpis': kpis,
            'financial': financial,
            'drivers': drivers,
            'vehicles': vehicles,
            'active_assignments_count': active_assignments_count,
            'pipeline': pipeline_stages,
            'active_deliveries': active_deliveries,
            'status_breakdown': status_breakdown,
            'recent_shipments': recent_shipments,
            'exceptions': exceptions_list,
            'chart_data': chart_data,
        }

    @api.model
    def _generate_analytics_trend(self, date_filter, Shipment):
        """
        Generates genuine trend points from shipment records.
        """
        now = fields.Datetime.now()
        labels = []
        shipments_series = []
        delivered_series = []

        if date_filter == 'today':
            labels = ['04:00', '08:00', '12:00', '16:00', '20:00', '23:59']
            base_day = now.date()
            for i in range(len(labels)):
                h = int(labels[i].split(':')[0])
                t_start = datetime.datetime.combine(base_day, datetime.time(max(0, h-4), 0))
                t_end = datetime.datetime.combine(base_day, datetime.time(h, 59))
                s_cnt = Shipment.search_count([('create_date', '>=', t_start), ('create_date', '<=', t_end)])
                d_cnt = Shipment.search_count([('delivered_at', '>=', t_start), ('delivered_at', '<=', t_end)])
                shipments_series.append(s_cnt)
                delivered_series.append(d_cnt)

        elif date_filter == '7d':
            for d in range(6, -1, -1):
                day_dt = (now - datetime.timedelta(days=d)).date()
                day_name = day_dt.strftime('%b %d')
                t_start = datetime.datetime.combine(day_dt, datetime.time(0, 0))
                t_end = datetime.datetime.combine(day_dt, datetime.time(23, 59, 59))
                labels.append(day_name)
                s_cnt = Shipment.search_count([('create_date', '>=', t_start), ('create_date', '<=', t_end)])
                d_cnt = Shipment.search_count([('delivered_at', '>=', t_start), ('delivered_at', '<=', t_end)])
                shipments_series.append(s_cnt)
                delivered_series.append(d_cnt)

        elif date_filter == '30d':
            for w in range(4, -1, -1):
                start_w = now - datetime.timedelta(days=(w + 1) * 6)
                end_w = now - datetime.timedelta(days=w * 6)
                labels.append(end_w.strftime('%b %d'))
                s_cnt = Shipment.search_count([('create_date', '>=', start_w), ('create_date', '<=', end_w)])
                d_cnt = Shipment.search_count([('delivered_at', '>=', start_w), ('delivered_at', '<=', end_w)])
                shipments_series.append(s_cnt)
                delivered_series.append(d_cnt)

        else: # 'all'
            for m in range(5, -1, -1):
                target_m = now - relativedelta(months=m)
                m_label = target_m.strftime('%b')
                labels.append(m_label)
                start_m = target_m.replace(day=1, hour=0, minute=0, second=0)
                next_m = start_m + relativedelta(months=1)
                s_cnt = Shipment.search_count([('create_date', '>=', start_m), ('create_date', '<', next_m)])
                d_cnt = Shipment.search_count([('delivered_at', '>=', start_m), ('delivered_at', '<', next_m)])
                shipments_series.append(s_cnt)
                delivered_series.append(d_cnt)

        max_val = max(shipments_series + delivered_series + [5])

        return {
            'labels': labels,
            'shipments': shipments_series,
            'delivered': delivered_series,
            'max_val': max_val,
        }
