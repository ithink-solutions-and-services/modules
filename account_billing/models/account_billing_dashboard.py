from odoo import fields, models, tools, api, SUPERUSER_ID, _
import json
from odoo.release import version
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)

class AccountBillingDashboard(models.Model):
    _name = "account.billing.dashboard"

    @api.one
    def toggle_graph_type(self):
        if self.kanban_dashboard_graph_type == 'line':
            self.kanban_dashboard_graph_type = 'bar'
        else:
            self.kanban_dashboard_graph_type = 'line'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.one
    def type_change(self):
        self.type = self.env.context['ch']
        return True


    @api.model_cr
    def init(self):
        try:
            self.env.ref('account_billing.property_payment_term_account_billing').sudo().value_reference = 'account.payment.term,' + str(self.env.ref('account_billing.term_account_billing_fifth_day').id)
        except:
            pass
        self.env['account.billing.dashboard'].sudo().search([]).unlink()
        records = self.env['account.billing.dashboard'].sudo().search([])
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "Today's Collection", 'type': 'text', 'content_type': 'col_day'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "Today's Collection", 'type': 'text', 'content_type': 'col_day'})
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Collection", 'type': 'combined', 'content_type': 'col_mo'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Collection", 'type': 'combined', 'content_type': 'col_mo'})
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "Today's Dues Collection (Water and Association Dues)", 'type': 'text', 'content_type': 'dues_col_day'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "Today's Dues Collection (Water and Association Dues)", 'type': 'text', 'content_type': 'dues_col_day'})
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Dues Collection (Water and Association Dues)", 'type': 'combined', 'content_type': 'dues_col_mo'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Dues Collection (Water and Association Dues)", 'type': 'combined', 'content_type': 'dues_col_mo'})
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "Today's Other Collection (Rentals, Water meter charges, etc.)", 'type': 'text', 'content_type': 'other_col_day'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "Today's Other Collection (Rentals, Water meter charges, etc.)", 'type': 'text', 'content_type': 'other_col_day'})
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Other Collection (Rentals, Water meter charges, etc.)", 'type': 'combined', 'content_type': 'other_col_mo'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': "This Month's Other Collection (Rentals, Water meter charges, etc.)", 'type': 'combined', 'content_type': 'other_col_mo'})
        self.env['account.billing.dashboard'].sudo().search([('content_type','=',False)]).unlink()
                    
                    
    @api.one
    def _count(self):
        if self.content_type == 'col_day':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('payment_ids.payment_date','=',datetime.today().date())])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',datetime.today().date())]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
        elif self.content_type == 'col_mo':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('payment_ids.payment_date','>=',datetime.today().date().replace(day=1)), ('payment_ids.payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','>=',datetime.today().date().replace(day=1)), ('payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
        elif self.content_type == 'dues_col_day':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','!=',False), ('payment_ids.payment_date','=',datetime.today().date())])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',datetime.today().date())]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
        elif self.content_type == 'dues_col_mo':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','!=',False), ('payment_ids.payment_date','>=',datetime.today().date().replace(day=1)), ('payment_ids.payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','>=',datetime.today().date().replace(day=1)), ('payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
        elif self.content_type == 'other_col_day':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','==',False), ('payment_ids.payment_date','=',datetime.today().date())])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',datetime.today().date())]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
        elif self.content_type == 'other_col_mo':
            total_count = 0
            invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','==',False), ('payment_ids.payment_date','>=',datetime.today().date().replace(day=1)), ('payment_ids.payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))])
            for invoice_billing in invoices_billing:
                total_count = total_count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','>=',datetime.today().date().replace(day=1)), ('payment_date','<',datetime.today().date().replace(day=1)+relativedelta(months=1))]).mapped('amount'))
            self.total_count = total_count
            self.short_count = self.human_format(total_count)
                
    def human_format(self, num):
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])   
        
    @api.one
    def _kanban_dashboard_graph(self):
        if self.type in ['combined', 'graph']:
            self.kanban_dashboard_graph = json.dumps(self.get_kanban_dashboard_line_datas()) if self.kanban_dashboard_graph_type == 'line' else json.dumps(self.get_kanban_dashboard_bar_datas())

    def _graph_title_and_key(self):
        return ['', _('Collection')]

    @api.one
    def get_kanban_dashboard_bar_datas(self):
        if self.content_type == 'col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_short_name = get_date.strftime("%d")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.day else 'future'})
            [graph_title, graph_key] = self._graph_title_and_key()
            return {'values': data, 'title': graph_title, 'key': graph_key}
        elif self.content_type == 'dues_col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_short_name = get_date.strftime("%d")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','!=',False),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.day else 'future'})
            [graph_title, graph_key] = self._graph_title_and_key()
            return {'values': data, 'title': graph_title, 'key': graph_key}
        elif self.content_type == 'other_col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_short_name = get_date.strftime("%d")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','==',False),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.day else 'future'})
            [graph_title, graph_key] = self._graph_title_and_key()
            return {'values': data, 'title': graph_title, 'key': graph_key}
        return True

    @api.one
    def get_kanban_dashboard_line_datas(self):
        if self.content_type == 'col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_name = get_date.strftime("%d %B %Y")
                get_date_short_name = get_date.strftime("%d-%b")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
            [graph_title, graph_key] = self._graph_title_and_key()
            color = '#875A7B' if '+e' in version else '#7c7bad'
            return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}
        elif self.content_type == 'dues_col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_name = get_date.strftime("%d %B %Y")
                get_date_short_name = get_date.strftime("%d-%b")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','!=',False),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
            [graph_title, graph_key] = self._graph_title_and_key()
            color = '#875A7B' if '+e' in version else '#7c7bad'
            return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}
        elif self.content_type == 'other_col_mo':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_name = get_date.strftime("%d %B %Y")
                get_date_short_name = get_date.strftime("%d-%b")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                invoices_billing = self.env['account.invoice'].sudo().search([('state','in',['open','in_payment','paid']),('billing_id','==',False),('payment_ids.payment_date','=',get_date_start)])
                count = 0
                for invoice_billing in invoices_billing:
                    count = count + sum(self.env['account.payment'].sudo().search([('id','in',invoice_billing.payment_ids.ids), ('payment_date','=',get_date_start)]).mapped('amount'))
                data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
            [graph_title, graph_key] = self._graph_title_and_key()
            color = '#875A7B' if '+e' in version else '#7c7bad'
            return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}
        return True
    

    name = fields.Char("Dashboard")
    total_count = fields.Float("Count", compute="_count")
    short_count = fields.Float("Short Count", compute="_count")
    color = fields.Integer("Color")
    type = fields.Selection([('combined','Combined'), ('text','Text'), ('graph','Graph')], string="Dashboard Content Type", default="combined")
    kanban_dashboard_graph = fields.Text(compute="_kanban_dashboard_graph")
    kanban_dashboard_graph_type = fields.Selection([('line','Line'),('bar','Bar')], string="Graph Type", default='line')    
    content_type = fields.Selection([('col_day','Daily Collection'), ('col_mo','Monthly Collection'),
                                     ('dues_col_day','Daily Dues Collection'), ('dues_col_mo','Monthly Dues Collection'),
                                     ('other_col_day','Daily Other Collection'), ('other_col_mo','Monthly Other Collection'),
                                    ], string="Content Type")
