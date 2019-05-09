# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import string
import random
import logging

_logger = logging.getLogger(__name__)


class ResPartnerPrepaid(models.TransientModel):
    _name = "res.partner.prepaid"

    partner_id = fields.Many2one('res.partner', 'Reseller')
    quantity = fields.Integer('Quantity')
    group_id = fields.Many2one('radius.groups', 'Group/Plan')
#    expiration_date = fields.Datetime('Expiration')

    @api.onchange('group_id')
    def onchange_group_id(self):
#        self.expiration_date = fields.Date.from_string(str(datetime.now())) + relativedelta(hours=self.group_id.expiration_hours)
#        self.expiration_date = datetime.now() + relativedelta(hours=self.group_id.expiration_hours)
        self.env.cr.commit()

    @api.multi
    def generate_random(self, size):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))

    @api.multi
    def _prepare_invoice_data(self,vouchers):
        self.ensure_one()

        if not self.partner_id:
            raise UserError("You must first select a Customer!")

        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        journal = self.group_id.journal_id


        return {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'origin': vouchers.name,
            'fiscal_position_id': fpos_id,
        }

    @api.multi
    def _prepare_invoice_line(self, fiscal_position,vouchers):
        account = self.group_id.product_id.property_account_income_id
        if not account:
            account = self.group_id.product_id.categ_id.property_account_income_categ_id
        account_id = fiscal_position.map_account(account).id
        if 'force_company' in self.env.context:
            company = self.env['res.company'].browse(self.env.context['force_company'])
        else:
            company = self.env.user.company_id
            self = self.with_context(force_company=company.id, company_id=company.id)

        tax = self.group_id.product_id.taxes_id.filtered(lambda r: r.company_id == company)
        tax = fiscal_position.map_tax(tax)

        return {
            'name': self.group_id.product_id.name + " - " + vouchers.name,
            'account_id': account_id,
            'price_unit': self.group_id.product_id.list_price or 0.0,
            'quantity': self.quantity,
            'product_id': self.group_id.product_id.id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)],
        }

    @api.multi
    def _prepare_invoice_lines(self, fiscal_position,vouchers):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        line_ids = []
        line_ids.append((0, 0, self._prepare_invoice_line(fiscal_position,vouchers)))
        return line_ids

#        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.recurring_invoice_line_ids]

    @api.multi
    def _prepare_invoice(self, vouchers):
        invoice = self._prepare_invoice_data(vouchers)
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'], vouchers)
        return invoice

    @api.multi
    def _create_sale_order(self, vouchers):
        serials = ""
        for voucher in vouchers.voucher_ids:
            serials = (serials + ", " + str(voucher.id)) if serials != "" else str(voucher.id)
        order_vals = {    
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'origin': "B/N: " + vouchers.name.replace('Voucher ','') + "/ S/N: " + serials,
           # 'pricelist_id': self.group_id.product_id.pricelist_id.id,
            'user_id': self.partner_id.user_id.id,
        }
        order = self.env['sale.order'].create(order_vals)
        vouchers.order_id = order.id
        line_vals = {
            'product_id': self.env['product.product'].sudo().search([('product_tmpl_id','=',self.group_id.product_id.id)], limit=1).id,
            'name': "B/N: " + vouchers.name.replace('Voucher ','') + "/ S/N: " + serials,
            'product_uom_qty': self.quantity,
            'order_id': order.id,
        }
        o_line = self.env['sale.order.line'].create(line_vals)
        o_line._onchange_discount()
        order.recompute_lines_agents()
        order.action_confirm()
        return order

    @api.multi
    def action_create(self):
        self.ensure_one()
        vouchers = self.env['res.partner.vouchers'].sudo().create({
            'partner_id': self.partner_id.id,
            'quantity': self.quantity,
            'plan_id': self.group_id.id,
#            'expiration_date': self.expiration_date,
        })
        ids = []
        for vouch in self.partner_id.vouchers_ids:
            ids.append(vouch.id)
        ids.append(vouchers.id)
        self.partner_id.vouchers_ids = ids
        # go to results
        voucher_ids = []
        for voucher_id in vouchers.voucher_ids:
            voucher_ids.append(voucher_id.id)
        vouchers.name = "Voucher " + str(voucher_ids[0]) + " - " + str(voucher_ids[len(voucher_ids) - 1])
        #self.env['account.invoice'].sudo().create(self._prepare_invoice(vouchers)).recompute_lines_agents()
#        self._create_sale_order(vouchers).action_invoice_create()
        if len(voucher_ids):
            return {
                'name': _('Created Vouchers'),
                'type': 'ir.actions.act_window',
                #'views': [[False, 'list'], [False, 'form']],
                'views': [[False, 'form']],
                #'res_model': 'res.partner.vouchers.voucher',
                #'domain': [['id', 'in', voucher_ids]],
                'res_model': 'res.partner.vouchers',
                'res_id': vouchers.id,
            }

        else:
            return {'type': 'ir.actions.act_window_close'}


#    @api.multi
#    def action_create(self):
#        self.ensure_one()
#        partner_ids = []
#        for x in range(0,self.quantity):
#            username = self.generate_random(6)
#            while len(self.env['res.partner'].sudo().search([('username','=',username)])) > 0:
#                username = self.generate_random(6)
#            password = self.generate_random(6)
#            partner = self.env['res.partner'].create({
#                'name': username,
#                'username': username,
#                'password': password,
#                'is_radius': True,
#                'plan_id': self.group_id.id,
#                'expiration_date': self.expiration_date
#            })
#            partner_ids.append(partner.id)
        # go to results
#        if len(partner_ids):
#            return {
#                'name': _('Created Partners'),
#                'type': 'ir.actions.act_window',
#                'views': [[False, 'list'], [False, 'form']],
#                'res_model': 'res.partner',
#                'domain': [['id', 'in', partner_ids]],
#            }
#
#        else:
#            return {'type': 'ir.actions.act_window_close'}
