# -*- coding: utf-8 -*-
# Part of Zimbabwe Connect Platform.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    zconnect_is_customer = fields.Boolean(
        string='ZConnect Customer',
        default=False,
        tracking=True,
        help='Designates this contact as a registered customer of the Zimbabwe Connect platform.'
    )
    zconnect_is_driver = fields.Boolean(
        string='ZConnect Driver',
        default=False,
        tracking=True,
        help='Designates this contact as an individual operating as a driver in Zimbabwe Connect.'
    )
    zconnect_customer_code = fields.Char(
        string='ZConnect Customer Code',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Unique identification code for Zimbabwe Connect customers.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('zconnect_is_customer') and not vals.get('zconnect_customer_code'):
                vals['zconnect_customer_code'] = self.env['ir.sequence'].next_by_code('zconnect.customer.code') or _('New')
        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        if vals.get('zconnect_is_customer'):
            for partner in self:
                if not partner.zconnect_customer_code and not vals.get('zconnect_customer_code'):
                    partner.zconnect_customer_code = self.env['ir.sequence'].next_by_code('zconnect.customer.code') or _('New')
        return super(ResPartner, self).write(vals)
