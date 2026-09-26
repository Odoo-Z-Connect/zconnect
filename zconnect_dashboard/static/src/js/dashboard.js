/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class ZConnectDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            data: null,
            dateFilter: 'all', // 'all', 'today', '7d', '30d'
            isLoading: true,
            isRefreshing: false,
            error: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    formatCurrency(amount) {
        const val = Number(amount) || 0;
        return val.toFixed(2);
    }

    async loadData() {
        this.state.isLoading = !this.state.data;
        this.state.isRefreshing = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "zconnect.dashboard",
                "get_dashboard_data",
                [this.state.dateFilter]
            );
        } catch (e) {
            this.state.error = e.message || "Failed to load logistics command center data.";
            console.error("ZConnect Dashboard Error:", e);
        } finally {
            this.state.isLoading = false;
            this.state.isRefreshing = false;
        }
    }

    async setDateFilter(filterValue) {
        if (this.state.dateFilter === filterValue) return;
        this.state.dateFilter = filterValue;
        await this.loadData();
    }

    async refresh() {
        await this.loadData();
    }

    getDateDomain() {
        const domain = [];
        if (this.state.dateFilter === 'today') {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            domain.push(['create_date', '>=', today.toISOString()]);
        } else if (this.state.dateFilter === '7d') {
            const date = new Date();
            date.setDate(date.getDate() - 7);
            domain.push(['create_date', '>=', date.toISOString()]);
        } else if (this.state.dateFilter === '30d') {
            const date = new Date();
            date.setDate(date.getDate() - 30);
            domain.push(['create_date', '>=', date.toISOString()]);
        }
        return domain;
    }

    // Drill-down actions
    openShipments(state) {
        let domain = this.getDateDomain();
        if (state) {
            domain.push(['state', '=', state]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: state ? `Shipments: ${state.toUpperCase()}` : 'All Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openActiveShipments() {
        const domain = this.getDateDomain();
        domain.push(['state', 'in', ['confirmed', 'assigned', 'en_route_pickup', 'picked_up', 'in_transit', 'near_delivery']]);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Active In-Flight Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openInTransit() {
        const domain = this.getDateDomain();
        domain.push(['state', 'in', ['in_transit', 'picked_up']]);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'In Transit Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openNearDelivery() {
        const domain = this.getDateDomain();
        domain.push(['state', '=', 'near_delivery']);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Near Delivery Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openDelivered() {
        const domain = this.getDateDomain();
        domain.push(['state', '=', 'delivered']);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Delivered Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openAwaitingPayment() {
        let domain = [['payment_state', 'in', ['pending', 'failed']]];
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Awaiting Payment Shipments',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openExceptions() {
        let domain = [['state', '=', 'exception']];
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Shipment Exceptions',
            res_model: 'zconnect.shipment',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openDrivers(status) {
        let domain = [];
        if (status === 'available') {
            domain.push(['availability_status', '=', 'available']);
        } else if (status === 'busy') {
            domain.push(['availability_status', '=', 'unavailable']);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: status ? `${status.toUpperCase()} Drivers` : 'Driver Registry',
            res_model: 'zconnect.driver',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openVehicles(status) {
        let domain = [];
        if (status === 'available') {
            domain.push(['zconnect_operational_status', '=', 'available']);
        } else if (status === 'busy' || status === 'assigned') {
            domain.push(['zconnect_operational_status', 'in', ['assigned', 'maintenance']]);
        } else if (status === 'maintenance') {
            domain.push(['zconnect_operational_status', '=', 'maintenance']);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: status ? `${status.toUpperCase()} Fleet Vehicles` : 'Fleet Registry',
            res_model: 'fleet.vehicle',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    openAssignments() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Dispatch Assignments',
            res_model: 'zconnect.dispatch.assignment',
            views: [[false, 'list'], [false, 'form']],
        });
    }

    openPricing() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Pricing & Tariffs',
            res_model: 'zconnect.pricing.rule',
            views: [[false, 'list'], [false, 'form']],
        });
    }

    openCustomers() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'ZConnect Customers',
            res_model: 'res.partner',
            views: [[false, 'list'], [false, 'form']],
            domain: [['zconnect_is_customer', '=', true]],
        });
    }

    openInvoices() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Customer Invoices',
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain: [['move_type', '=', 'out_invoice']],
        });
    }

    openShipmentDetail(id) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'zconnect.shipment',
            res_id: id,
            views: [[false, 'form']],
        });
    }

    openNewShipment() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'New Shipment',
            res_model: 'zconnect.shipment',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openRecord(resModel, resId) {
        if (!resModel || !resId) return;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: resModel,
            res_id: resId,
            views: [[false, 'form']],
        });
    }

    // Chart helpers for SVG path generation
    getSvgPoints(series, maxVal, width = 600, height = 150, paddingX = 35, paddingY = 25) {
        if (!series || series.length === 0) return '';
        const n = series.length;
        const effectiveWidth = width - (paddingX * 2);
        const effectiveHeight = height - (paddingY * 2);
        const step = n > 1 ? effectiveWidth / (n - 1) : effectiveWidth;
        const safeMax = maxVal > 0 ? maxVal : 1;

        return series.map((val, idx) => {
            const x = Math.round(paddingX + (idx * step));
            const ratio = val / safeMax;
            const y = Math.round(height - paddingY - (ratio * effectiveHeight));
            return `${x},${y}`;
        }).join(' ');
    }

    getSvgAreaPoints(series, maxVal, width = 600, height = 150, paddingX = 35, paddingY = 25, bottomY = 125) {
        if (!series || series.length === 0) return '';
        const n = series.length;
        const effectiveWidth = width - (paddingX * 2);
        const effectiveHeight = height - (paddingY * 2);
        const step = n > 1 ? effectiveWidth / (n - 1) : effectiveWidth;
        const safeMax = maxVal > 0 ? maxVal : 1;

        const points = series.map((val, idx) => {
            const x = Math.round(paddingX + (idx * step));
            const ratio = val / safeMax;
            const y = Math.round(height - paddingY - (ratio * effectiveHeight));
            return `${x},${y}`;
        });

        const firstX = Math.round(paddingX);
        const lastX = Math.round(paddingX + ((n - 1) * step));
        return `${firstX},${bottomY} ${points.join(' ')} ${lastX},${bottomY}`;
    }

    getPointCoords(series, maxVal, width = 600, height = 150, paddingX = 35, paddingY = 25) {
        if (!series || series.length === 0) return [];
        const n = series.length;
        const effectiveWidth = width - (paddingX * 2);
        const effectiveHeight = height - (paddingY * 2);
        const step = n > 1 ? effectiveWidth / (n - 1) : effectiveWidth;
        const safeMax = maxVal > 0 ? maxVal : 1;

        return series.map((val, idx) => {
            const cx = Math.round(paddingX + (idx * step));
            const ratio = val / safeMax;
            const cy = Math.round(height - paddingY - (ratio * effectiveHeight));
            return { cx, cy, val, idx };
        });
    }

    hasChartData(chartData) {
        if (!chartData) return false;
        const hasBookings = chartData.shipments && chartData.shipments.some(v => v > 0);
        const hasDelivered = chartData.delivered && chartData.delivered.some(v => v > 0);
        return hasBookings || hasDelivered;
    }

    getInitials(name) {
        if (!name || name === '—' || name === 'Unassigned') return null;
        const clean = name.trim();
        const parts = clean.split(/\s+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return clean.substring(0, 2).toUpperCase();
    }

    getStateColor(state) {
        const colors = {
            draft: '#64748B',
            quoted: '#6366F1',
            awaiting_payment: '#F59E0B',
            confirmed: '#3B82F6',
            assigned: '#8B5CF6',
            en_route_pickup: '#F97316',
            picked_up: '#06B6D4',
            in_transit: '#2563EB',
            near_delivery: '#F59E0B',
            delivered: '#10B981',
            cancelled: '#EF4444',
            exception: '#DC2626',
        };
        return colors[state] || '#64748B';
    }
}

ZConnectDashboard.template = "zconnect_dashboard.MainDashboard";
registry.category("actions").add("zconnect_dashboard.main", ZConnectDashboard);
