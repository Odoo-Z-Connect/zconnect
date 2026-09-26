# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.
#
# Architecture Decision (ADR-004):
#   Pricing rules are configuration; shipment price components are immutable
#   historical snapshots.
#
# The pricing engine calculates quote breakdown based on:
#   - Base Fare
#   - Distance Charge (distance_km * price_per_km)
#   - Cargo Weight Charge (weight_kg * price_per_kg)
#   - Vehicle Category Pricing
#   - Zone Surcharge (zone.surcharge)
#   - Minimum Fare enforcement (max(subtotal, minimum_fare))
#
# The result is returned as a structured dictionary to be snapshotted onto
# future zconnect.shipment records.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.zconnect_fleet.models.fleet_vehicle import ZCONNECT_VEHICLE_CATEGORY


class ZconnectPricingRule(models.Model):
    """
    Zimbabwe Connect Tariff & Pricing Rule Configuration.

    Defines distance, weight, base fare, and vehicle-tier pricing parameters.
    """
    _name = 'zconnect.pricing.rule'
    _description = 'Zimbabwe Connect Pricing Rule'
    _order = 'vehicle_category asc, effective_from desc, id desc'

    name = fields.Char(
        string='Rule Name',
        required=True,
        help='Descriptive title for this pricing tariff (e.g. "Standard Motorcycle Harare 2026").',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive rules are excluded from quote calculations.',
    )

    vehicle_category = fields.Selection(
        selection=ZCONNECT_VEHICLE_CATEGORY,
        string='Vehicle Category',
        required=True,
        index=True,
        help='The fleet vehicle category this pricing tariff applies to. '
             'Reuses the vehicle category vocabulary from zconnect_fleet.',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    # ── Pricing Rate Components ──────────────────────────────────────────────

    base_fare = fields.Monetary(
        string='Base Fare',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Flat base fee charged for initiating the delivery before distance and weight.',
    )

    price_per_km = fields.Monetary(
        string='Price Per Km',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Variable charge per kilometer of delivery distance.',
    )

    price_per_kg = fields.Monetary(
        string='Price Per Kg',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Variable charge per kilogram of package cargo weight.',
    )

    minimum_fare = fields.Monetary(
        string='Minimum Fare',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='The minimum total amount charged for a delivery. '
             'If the calculated subtotal is lower than this minimum, this amount is charged.',
    )

    # ── Effective Validity Dates ─────────────────────────────────────────────

    effective_from = fields.Date(
        string='Effective From',
        default=fields.Date.context_today,
        help='Date from which this pricing rule becomes active.',
    )

    effective_to = fields.Date(
        string='Effective To',
        help='Date after which this pricing rule is no longer active. '
             'Leave blank for open-ended tariffs.',
    )

    description = fields.Text(
        string='Tariff Notes',
        help='Internal operational notes regarding this tariff schedule.',
    )

    # ── UI Interactive Demonstration & Testing Fields ─────────────────────────

    test_distance_km = fields.Float(
        string='Test Distance (km)',
        default=10.0,
        help='Distance parameter to test quote calculation directly from the UI.',
    )

    test_weight_kg = fields.Float(
        string='Test Weight (kg)',
        default=5.0,
        help='Cargo weight parameter to test quote calculation directly from the UI.',
    )

    test_zone_id = fields.Many2one(
        'zconnect.pricing.zone',
        string='Test Zone',
        help='Optional service zone surcharge to include in the test calculation.',
    )

    test_result_subtotal = fields.Monetary(
        string='Calculated Subtotal',
        currency_field='currency_id',
        readonly=True,
    )

    test_result_total = fields.Monetary(
        string='Calculated Total Quote',
        currency_field='currency_id',
        readonly=True,
    )

    test_result_breakdown = fields.Text(
        string='Calculation Breakdown',
        readonly=True,
    )

    # ── Server-Side Validations ──────────────────────────────────────────────

    @api.constrains('base_fare', 'price_per_km', 'price_per_kg', 'minimum_fare')
    def _check_non_negative_rates(self):
        for rule in self:
            if rule.base_fare < 0:
                raise ValidationError(_('Base fare cannot be negative.'))
            if rule.price_per_km < 0:
                raise ValidationError(_('Price per kilometer cannot be negative.'))
            if rule.price_per_kg < 0:
                raise ValidationError(_('Price per kilogram cannot be negative.'))
            if rule.minimum_fare < 0:
                raise ValidationError(_('Minimum fare cannot be negative.'))

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for rule in self:
            if rule.effective_from and rule.effective_to:
                if rule.effective_to < rule.effective_from:
                    raise ValidationError(_(
                        'Effective To date (%s) cannot be earlier than Effective From date (%s).',
                        rule.effective_to,
                        rule.effective_from,
                    ))

    # ── Deterministic Pricing Calculation API ────────────────────────────────

    def compute_quote(self, distance_km=0.0, weight_kg=0.0, zone=None):
        """
        Calculate deterministic shipment quote using this pricing rule.

        Formula:
            distance_charge = distance_km * price_per_km
            weight_charge   = weight_kg * price_per_kg
            vehicle_charge  = 0.0 (baseline covered by rule category)
            zone_charge     = zone.surcharge (if zone specified)
            subtotal        = base_fare + distance_charge + weight_charge + vehicle_charge + zone_charge
            total_amount    = max(subtotal, minimum_fare)

        :param float distance_km: Route distance in kilometers.
        :param float weight_kg: Cargo weight in kilograms.
        :param zconnect.pricing.zone zone: Optional pricing zone record.
        :return: dict with full structured component breakdown.
        """
        self.ensure_one()

        d_km = max(0.0, float(distance_km or 0.0))
        w_kg = max(0.0, float(weight_kg or 0.0))

        distance_charge = round(d_km * self.price_per_km, 2)
        weight_charge = round(w_kg * self.price_per_kg, 2)
        vehicle_charge = 0.0
        zone_charge = round(zone.surcharge, 2) if zone else 0.0
        base_fare = round(self.base_fare, 2)
        minimum_fare = round(self.minimum_fare, 2)

        subtotal = round(base_fare + distance_charge + weight_charge + vehicle_charge + zone_charge, 2)
        total_amount = round(max(subtotal, minimum_fare), 2)

        return {
            'pricing_rule_id': self.id,
            'pricing_rule_name': self.name,
            'vehicle_category': self.vehicle_category,
            'base_fare': base_fare,
            'distance_km': d_km,
            'price_per_km': self.price_per_km,
            'distance_charge': distance_charge,
            'weight_kg': w_kg,
            'price_per_kg': self.price_per_kg,
            'weight_charge': weight_charge,
            'vehicle_charge': vehicle_charge,
            'zone_id': zone.id if zone else False,
            'zone_name': zone.name if zone else '',
            'zone_charge': zone_charge,
            'subtotal': subtotal,
            'minimum_fare': minimum_fare,
            'total_amount': total_amount,
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
        }

    # ── Rule Selection Service ───────────────────────────────────────────────

    @api.model
    def get_applicable_rule(self, vehicle_category, quote_date=None, company_id=None):
        """
        Find the single deterministic pricing rule for the specified context.

        :param str vehicle_category: Vehicle category code.
        :param date quote_date: Date to evaluate effective date bounds (defaults to today).
        :param int company_id: Target company ID (defaults to current company).
        :return: zconnect.pricing.rule record.
        :raises UserError: If no rule is found or if ambiguous overlapping rules exist.
        """
        if not vehicle_category:
            raise UserError(_('A vehicle category must be specified to select a pricing rule.'))

        date_eval = quote_date or fields.Date.context_today(self)
        comp_id = company_id or self.env.company.id

        candidates = self.search([
            ('vehicle_category', '=', vehicle_category),
            ('active', '=', True),
            ('company_id', '=', comp_id),
        ])

        # Filter by effective dates
        valid_rules = candidates.filtered(
            lambda r: (not r.effective_from or r.effective_from <= date_eval) and
                      (not r.effective_to or r.effective_to >= date_eval)
        )

        if not valid_rules:
            category_label = dict(ZCONNECT_VEHICLE_CATEGORY).get(vehicle_category, vehicle_category)
            raise UserError(_(
                'No active pricing rule found for vehicle category "%(category)s" on date %(date)s.',
                category=category_label,
                date=date_eval,
            ))

        if len(valid_rules) == 1:
            return valid_rules[0]

        # Prioritise rules with explicit date ranges over unbounded rules
        bounded_rules = valid_rules.filtered(lambda r: r.effective_from and r.effective_to)
        if len(bounded_rules) == 1:
            return bounded_rules[0]

        from_bounded = valid_rules.filtered(lambda r: r.effective_from and not r.effective_to)
        if len(from_bounded) == 1 and not bounded_rules:
            return from_bounded[0]

        # If still ambiguous, raise explicit business error (no silent arbitrary picks)
        rule_names = ', '.join(f'"{r.name}" (ID: {r.id})' for r in valid_rules)
        raise UserError(_(
            'Ambiguous pricing configuration: multiple active rules match vehicle category "%(cat)s" on %(date)s: %(rules)s. '
            'Please deactivate or adjust effective dates on redundant rules.',
            cat=dict(ZCONNECT_VEHICLE_CATEGORY).get(vehicle_category, vehicle_category),
            date=date_eval,
            rules=rule_names,
        ))

    # ── UI Interactive Demonstration Action ──────────────────────────────────

    def action_test_quote(self):
        """
        Execute a test calculation using the parameters configured on the rule form.
        Updates test result fields for direct UI demonstration.
        """
        self.ensure_one()
        quote = self.compute_quote(
            distance_km=self.test_distance_km,
            weight_kg=self.test_weight_kg,
            zone=self.test_zone_id,
        )

        currency_symbol = self.currency_id.symbol or self.currency_id.name or '$'
        breakdown_text = (
            f"--- QUOTE CALCULATION BREAKDOWN ---\n"
            f"Rule: {quote['pricing_rule_name']} [{quote['vehicle_category']}]\n"
            f"Base Fare: {currency_symbol}{quote['base_fare']:.2f}\n"
            f"Distance: {quote['distance_km']} km @ {currency_symbol}{quote['price_per_km']:.2f}/km = {currency_symbol}{quote['distance_charge']:.2f}\n"
            f"Cargo Weight: {quote['weight_kg']} kg @ {currency_symbol}{quote['price_per_kg']:.2f}/kg = {currency_symbol}{quote['weight_charge']:.2f}\n"
            f"Zone Surcharge ({quote['zone_name'] or 'None'}): {currency_symbol}{quote['zone_charge']:.2f}\n"
            f"Subtotal: {currency_symbol}{quote['subtotal']:.2f}\n"
            f"Configured Minimum Fare: {currency_symbol}{quote['minimum_fare']:.2f}\n"
            f"-----------------------------------\n"
            f"FINAL TOTAL QUOTE: {currency_symbol}{quote['total_amount']:.2f}"
        )

        self.write({
            'test_result_subtotal': quote['subtotal'],
            'test_result_total': quote['total_amount'],
            'test_result_breakdown': breakdown_text,
        })
        return True
