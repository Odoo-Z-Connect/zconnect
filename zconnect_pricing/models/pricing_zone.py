# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ZconnectPricingZone(models.Model):
    """
    Zimbabwe Connect Pricing Zone.

    Represents service areas and regional pricing surcharge zones
    (e.g., "Harare Urban", "Harare Outskirts", "Bulawayo Central", "Cross-Border").
    Used by the pricing engine to apply location-specific surcharges.
    """
    _name = 'zconnect.pricing.zone'
    _description = 'Zimbabwe Connect Pricing Zone'
    _order = 'name asc'

    name = fields.Char(
        string='Zone Name',
        required=True,
        translate=True,
        help='Descriptive name of the pricing zone (e.g., "Harare Urban Zone").',
    )

    code = fields.Char(
        string='Zone Code',
        required=True,
        index=True,
        help='Unique identifier for the pricing zone (e.g., "HRE-URBAN").',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Deactivate to disable this pricing zone without deleting historical references.',
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

    surcharge = fields.Monetary(
        string='Zone Surcharge',
        currency_field='currency_id',
        default=0.0,
        help='Fixed additional surcharge applied to deliveries within or to this zone.',
    )

    description = fields.Text(
        string='Description',
        help='Coverage details, boundary notes, or operational information.',
    )

    # ── Constraints ─────────────────────────────────────────────────────────

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'The pricing zone code must be unique across all zones.',
    )

    @api.constrains('surcharge')
    def _check_surcharge(self):
        for zone in self:
            if zone.surcharge < 0:
                raise ValidationError(_('Zone surcharge cannot be negative.'))
