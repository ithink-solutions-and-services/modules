# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import Warning
from odoo import SUPERUSER_ID
import datetime
import json
import calendar
import string
import random
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vouchers_ids = fields.Many2many('res.partner.vouchers',string='Vouchers')
    is_radius = fields.Boolean("Radius User")

    @api.multi
    def cron_check_usage(self):
        partners = self.env['res.partner'].sudo().search([('is_radius','=',True),('status','=','open')])
        for rec in partners:
            accts = self.env['radius.radacct'].sudo().search([('username','=',rec.username)])
            is_used = False
            if rec.plan_id.category == 'time':
                usage = 0
                for acct in accts:
                    usage += float(acct.acctsessiontime)
                limit = 0
                for attribute in rec.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'Max-All-Session':
                        limit = float(attribute.value)
                        break
                if usage >= limit:
                    is_used = True
            else:
                usage = 0
                for acct in accts:
                    usage += float(acct.acctinputoctets) + float(acct.acctoutputoctets)
                limit = 0
                for attribute in rec.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'ZVendor-Byte-Amount':
                        limit = float(attribute.value)
                        break
                if usage >= limit:
                    is_used = True
            if is_used:
                rec.status = 'used'
#                rec.sudo().unlink()
        return True

    @api.multi
    def set_printed(self):
        for rec in self:
            rec.is_printed = True
        return True

    @api.multi
    def user_clean(self):
#Deletes radcheck and radreply records if the username is equal to partner's username
        self.env['radius.radcheck'].sudo().search([('username','=',self.username)]).unlink()
        self.env['radius.radreply'].sudo().search([('username','=',self.username)]).unlink()
        return True

    @api.multi
    def user_generate(self):
        group = self.env['radius.groups'].sudo().browse(self.plan_id.id)
        check_obj = self.env['radius.radcheck']
        reply_obj = self.env['radius.radreply']
        values = {
                'username': self.username,
                'value': self.password,
                'attribute': "Cleartext-Password",
                'op': ":="
        }
        check_obj.create(values)
        for attribute_id in group.attribute_ids:
            group_vals = {
                    'username': self.username,
                    'attribute': attribute_id.attribute_id.name,
                    'op': attribute_id.op,
                    'value': attribute_id.value
            }
            if attribute_id.type == 'radcheck':
                check_obj.sudo().create(group_vals)
            else:
                reply_obj.sudo().create(group_vals)
        return True

    def strip_space(self, string):
        return " ".join(string.split() if string != False else '')


    @api.multi
    def cron_expired_accounts(self):
# Check expired partners then deletes radcheck and radreply records with username equal to partners' usernames
        partners = self.env['res.partner'].sudo().search([('expiration_date','<=',datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))])
        for partner in partners:
            self.env['radius.radcheck'].sudo().search([('username','=',partner.username)]).unlink()
            self.env['radius.radreply'].sudo().search([('username','=',partner.username)]).unlink()
            partner.status = "expired"
#            self.env['radius.radusergroup'].sudo().search([('username','=',partner.username)]).unlink()
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            for voucher in rec.vouchers_ids:
                voucher.sudo().unlink()
        return super(ResPartner, self).unlink()


class ResPartnerVouchersVoucher(models.Model):
    _name = "res.partner.vouchers.voucher"
    _rec_name = 'username'
    _order = 'id desc'

    status = fields.Selection([('new', 'New'), ('open','Activated'),('used','Used')], string='Status',default='new')
    username = fields.Char('Username')
    password = fields.Char('Password')
    vouchers_id = fields.Many2one('res.partner.vouchers', string='Voucher List')
    balance = fields.Char('Remaining Quota')
    expiration_date = fields.Datetime(string='Expiration')
    lot_id = fields.Many2one('stock.production.lot', string="Lot/Serial")
    partner_id = fields.Many2one('res.partner', string="Partner", related="vouchers_id.partner_id", store=True)
    invoiced = fields.Boolean(string='Invoiced?', default=False)
    plan_id = fields.Many2one('radius.groups', string="Plan", related="vouchers_id.plan_id", store=True)

    @api.multi
    def cron_radius_invoice_generation(self):
        for partner in self.env['res.partner'].sudo().search([('is_radius','=',True)]):
            vouchers = self.env['res.partner.vouchers.voucher'].sudo().search([('partner_id','=',partner.id), ('invoiced','=',False), ('status','!=','new')])
            if len(vouchers) < 1:
                return True
            voucher_list_ids = []
            voucher_names = ""
            for voucher in vouchers:
                if voucher.vouchers_id not in voucher_list_ids:
                    voucher_list_ids.append(voucher.vouchers_id)
                    voucher_names = (voucher_names + " / " + voucher.vouchers_id.name) if voucher_names != "" else voucher.vouchers_id.name
            order_vals = {
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'origin': voucher_names,
                'user_id': partner.user_id.id,
            }
            order = self.env['sale.order'].create(order_vals)
            lines_to_create = []
            product_ids = []
            for voucher_list in voucher_list_ids:
                line_vals = voucher_list._create_sale_order_line()
                line_vals['order_id'] = order.id
                if line_vals['product_id'] not in product_ids:
                    lines_to_create.append(line_vals)
                    product_ids.append(line_vals['product_id'])
                else:
                    for line in lines_to_create:
                        if line['product_id'] == line_vals['product_id']:
                            line['name'] = line['name'] + "\n" + line_vals['name']
                            line['product_uom_qty'] = line['product_uom_qty'] + line_vals['product_uom_qty']
                            break
            for line in lines_to_create:
                o_line = self.env['sale.order.line'].create(line)
                o_line._onchange_discount()
            order.recompute_lines_agents()
            order.action_confirm()
            order.action_invoice_create()
            vouchers.write({'invoiced': True})
        return True


    @api.multi
    def cron_check_usage(self):
        vouchers = self.env['res.partner.vouchers.voucher'].sudo().search([('status','in',['open', 'new'])])
        for rec in vouchers:
            accts = self.env['radius.radacct'].sudo().search([('username','=',rec.username)])
            is_used = False
            is_open = False
            if rec.vouchers_id.plan_id.category == 'time' and rec.vouchers_id.plan_id.time_seconds != False:
                usage = 0
                for acct in accts:
                    usage += float(acct.acctsessiontime)
                if usage > 0:
                    is_open = True
                limit = 0
                for attribute in rec.vouchers_id.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'Max-All-Session':
                        limit = float(attribute.value)
                        break
                if usage >= limit:
                    is_used = True
#                    rec.balance = "0 seconds"
                    rec.balance = "0:00:0"
                else:
#                    rec.balance = str(limit-usage) + " seconds"
#                    rec.balance = str(datetime.timedelta(seconds=limit-usage))
                    m, s = divmod(limit-usage, 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    rec.balance = "%d days, %d:%02d:%02d" % (d, h, m, s)
            elif rec.vouchers_id.plan_id.category == 'expiration':
                if len(accts) >= 1:
                    is_open = True
                    if not rec.expiration_date:
#                        acct = self.env['radius.radacct'].sudo().search([('username','=',rec.username)], order="id asc", limit=1)
                        rec.expiration_date = datetime.datetime.now() + relativedelta(hours=rec.vouchers_id.plan_id.expiration_time_hours)
                        m, s = divmod((datetime.datetime.strptime(rec.expiration_date, '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).total_seconds(), 60)
                        h, m = divmod(m, 60)
                        d, h = divmod(h, 24)
                        rec.balance = "%d days, %d:%02d:%02d" % (d, h, m, s)
                    elif datetime.datetime.strptime(rec.expiration_date, '%Y-%m-%d %H:%M:%S') <= datetime.datetime.now():
                        is_used = True
                        rec.balance = "0:00:0"
                    else:
#                        rec.balance = str(datetime.timedelta(seconds=(datetime.datetime.strptime(rec.expiration_date, '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).total_seconds()))
                        m, s = divmod((datetime.datetime.strptime(rec.expiration_date, '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).total_seconds(), 60)
                        h, m = divmod(m, 60)
                        d, h = divmod(h, 24)
                        rec.balance = "%d days, %d:%02d:%02d" % (d, h, m, s)
            elif rec.vouchers_id.plan_id.category == 'volume':
                usage = 0
                for acct in accts:
                    usage += float(acct.acctinputoctets) + float(acct.acctoutputoctets)
                if usage > 0:
                    is_open = True
                limit = 0
                for attribute in rec.vouchers_id.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'ZVendor-Byte-Amount':
                        limit = float(attribute.value)
                        break
                    if attribute.attribute_id.name == 'ZVendor-Byte-Amount-4GB':
                        limit = float(attribute.value) * (1024*1024)
                        break
                if usage >= limit:
                    is_used = True
                    rec.balance = "0 MB"
                else:
                    rec.balance = str((limit-usage)/ (1024*1024)) + " MB"
            elif rec.vouchers_id.plan_id.category == 'time_volume':
                usage = 0
                for acct in accts:
                    usage += float(acct.acctsessiontime)
                if usage > 0 :
                    is_open = True
                limit = 0
                for attribute in rec.vouchers_id.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'Max-All-Session':
                        limit = float(attribute.value)
                        break
                if usage >= limit:
                    is_used = True
                    rec.balance = "0:00:0"
                else:
#                    rec.balance = str(datetime.timedelta(seconds=limit-usage))
                    m, s = divmod(limit-usage, 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    rec.balance = "%d days, %d:%02d:%02d" % (d, h, m, s)

                usage = 0
                for acct in accts:
                    usage += float(acct.acctinputoctets) + float(acct.acctoutputoctets)
                if usage > 0:
                    is_open = True
                limit = 0
                for attribute in rec.vouchers_id.plan_id.attribute_ids:
                    if attribute.attribute_id.name == 'ZVendor-Byte-Amount':
                        limit = float(attribute.value)
                        break
                    if attribute.attribute_id.name == 'ZVendor-Byte-Amount-4GB':
                        limit = float(attribute.value) * (1024*1024)
                        break
                if usage >= limit:
                    is_used = True
                    rec.balance += " / 0 MB"
                else:
                    rec.balance += " / " + str((limit-usage) / (1024*1024)) + " MB"
            if is_open:
                rec.status = 'open'
            if is_used:
                rec.status = 'used'
#                rec.sudo().unlink()
        return True


    @api.multi
    def user_generate(self):
        check_obj = self.env['radius.radcheck']
        values = {
                'username': self.username,
                'value': self.password,
                'attribute': "Cleartext-Password",
                'op': ":="
        }
        check_obj.create(values)
        return True

    @api.model
    def create(self, vals):
        res = super(ResPartnerVouchersVoucher, self).create(vals)
        self.env['res.partner.vouchers.voucher'].sudo().browse(res.id).user_generate()
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            self.env['radius.radcheck'].sudo().search([('username','=',rec.username)]).sudo().unlink()
            self.env['radius.radreply'].sudo().search([('username','=',rec.username)]).sudo().unlink()
        return super(ResPartnerVouchersVoucher, self).unlink()

    @api.multi
    def cron_expired_accounts(self):
#        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#        vouchers = self.env['res.partner.vouchers.voucher'].sudo().search([('expiration_date','<=',today)])
#        for vouch in vouchers:
#            self.env['radius.radcheck'].sudo().search([('username','=',vouch.username)]).unlink()
#            self.env['radius.radreply'].sudo().search([('username','=',vouch.username)]).unlink()
#            vouch.status = "used"
#            vouch.balance = False
#            self.env['radius.radusergroup'].sudo().search([('username','=',partner.username)]).unlink()
        return True

class ResPartnerVouchers(models.Model):
    _name = "res.partner.vouchers"
    _order = "id desc"

    name = fields.Char(readonly=True)
    partner_id = fields.Many2one('res.partner','Partner')
    plan_id = fields.Many2one('radius.groups','Plan')
    plan_category = fields.Selection([('time','Time-Based'),('volume','Volume-Based'), ('time_volume','Time and Volume-Based'), ('expiration','Cutoff-Based')],string="Plan Category",related="plan_id.category",readonly=True)
    is_printed = fields.Boolean(string='Is Card Printed?', default=False)
    quantity = fields.Integer('Quantity')
    voucher_ids = fields.Many2many('res.partner.vouchers.voucher',string='Vouchers')
    order_id = fields.Many2one('sale.order', 'Sales Order')
 #   expiration_date = fields.Datetime(string='Expiration')

    @api.multi
    def _create_sale_order_line(self):
        self.ensure_one()
        serials = ""
        voucher_to_line = []
        for voucher in self.voucher_ids:
            if not voucher.invoiced and voucher.status != 'new':
                voucher_to_line.append(voucher)
        for voucher in voucher_to_line:
            serials = (serials + ", " + str(voucher.id)) if serials != "" else str(voucher.id)
        line_vals = {
            'product_id': self.env['product.product'].sudo().search([('product_tmpl_id','=',self.plan_id.product_id.id)], limit=1).id,
            'name': "B/N: " + self.name.replace('Voucher ','') + "/ S/N: " + serials,
            'product_uom_qty': len(voucher_to_line),
        }
        return line_vals

    @api.multi
    def voucher_print(self):
        self.ensure_one()
        self.sudo().write({'is_printed': True})
#        self.is_printed = True
        return self.env.ref('pdn_billing.report_prepaid_custom_report').report_action(self)

#    @api.multi
#    def cron_expired_accounts(self):
#        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#        vouchers = self.env['res.partner.vouchers'].sudo().search([('expiration_date','<=',today)])
#        for voucher in vouchers:
#            for vouch in voucher.voucher_ids:
#                self.env['radius.radcheck'].sudo().search([('username','=',vouch.username)]).unlink()
#                self.env['radius.radreply'].sudo().search([('username','=',vouch.username)]).unlink()
#                vouch.status = "expired"
#            self.env['radius.radusergroup'].sudo().search([('username','=',partner.username)]).unlink()
#        return True

    @api.multi
    def unlink(self):
        for rec in self:
            for voucher in rec.voucher_ids:
                voucher.sudo().unlink()
        return super(ResPartnerVouchers, self).unlink()

    @api.multi
    def generate_random(self, size):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))

    @api.multi
    def generate_attributes(self):
        group = self.env['radius.groups'].sudo().browse(self.plan_id.id)
        check_obj = self.env['radius.radcheck']
        reply_obj = self.env['radius.radreply']
        for attribute_id in group.attribute_ids:
            for voucher_id in self.voucher_ids:
                group_vals = {
                    'username': voucher_id.username,
                    'attribute': attribute_id.attribute_id.name,
                    'op': attribute_id.op,
                    'value': attribute_id.value
                }
                if attribute_id.type == 'radcheck':
                    check_obj.sudo().create(group_vals)
                else:
                    reply_obj.sudo().create(group_vals)
        return True

    @api.model
    def create(self, vals):
        res = super(ResPartnerVouchers, self).create(vals)
        vouchers = self.env['res.partner.vouchers'].sudo().browse(res.id)
        voucher_ids = []
        for x in range(0,vouchers.quantity):
            username = vouchers.generate_random(6) + "@radius"
            while len(self.env['radius.radacct'].sudo().search([('username','=',username)])) > 0 or len(self.env['res.partner.vouchers.voucher'].sudo().search([('username','=',username)])) > 0:
                username = vouchers.generate_random(6) + "@radius"
            password = vouchers.generate_random(6)
            voucher = self.env['res.partner.vouchers.voucher'].create({
                'username': username,
                'password': password,
                'status': 'new',
                'vouchers_id': vouchers.id,
  #              'expiration_date': vouchers.expiration_date
            })
            voucher_ids.append(voucher.id)
        vouchers.voucher_ids = voucher_ids
        vouchers.generate_attributes()
        return res
