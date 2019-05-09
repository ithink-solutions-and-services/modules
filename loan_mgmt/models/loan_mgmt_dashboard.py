from odoo import fields, models, tools, api, SUPERUSER_ID, _
import json
from odoo.release import version
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)

class LoanMgmtDashboard(models.Model):
    _name = "loan_mgmt.dashboard"

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

    @api.multi
    def toggle_active(self):
        for rec in self:
            if rec.state == 'off':
                rec.state = 'on'
            else:
                rec.state = 'off'
        return True

    @api.model_cr
    def init(self):
        records = self.env['loan_mgmt.dashboard'].sudo().search([('type','=','cur_mo_disb')])
        if records:
            if len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
                    count = count + 1
        else:
            self.env['loan_mgmt.dashboard'].sudo().create({'type': 'cur_mo_disb'})
        records = self.env['loan_mgmt.dashboard'].sudo().search([('type','=','cur_yr_disb')])
        if records:
            if len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
                    count = count + 1
        else:
            self.env['loan_mgmt.dashboard'].sudo().create({'type': 'cur_yr_disb'})
        records = self.env['loan_mgmt.dashboard'].sudo().search([('type','=','collection_mo')])
        if records:
            if len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
                    count = count + 1
        else:
            self.env['loan_mgmt.dashboard'].sudo().create({'type': 'collection_mo'})
        records = self.env['loan_mgmt.dashboard'].sudo().search([('type','=','collection_yr')])
        if records:
            if len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
                    count = count + 1
        else:
            self.env['loan_mgmt.dashboard'].sudo().create({'type': 'collection_yr'})
        self.env['loan_mgmt.dashboard'].sudo().search([('type','=',False)]).unlink()
                              
    def _count(self):
        for rec in self:
            if rec.type == 'cur_mo_disb':
                today = datetime.today()
                date_start = datetime(month=today.month, day=1, year=today.year, hour=0, minute=0, second=0).strftime('%Y-%m-%d')
                date_end =  ((datetime(month=today.month, day=1, year=today.year, hour=0, minute=0, second=0) + relativedelta(months=1)) - relativedelta(days=1)).strftime('%Y-%m-%d')
                rec.total_count = sum(self.env['loan_mgmt.loan_request'].sudo().search([('state', '=', 'disbursed'), ('bill_id.state', '=', 'paid'), ('disburse_date', '>=', date_start), ('disburse_date', '<=', date_end)]).mapped(lambda r: r.principal_amount))
                rec.short_count = rec.human_format(rec.total_count)
            elif rec.type == 'cur_yr_disb':
                today = datetime.today()
                date_start = datetime(month=1, day=1, year=today.year, hour=0, minute=0, second=0).strftime('%Y-%m-%d')
                date_end =  ((datetime(month=1, day=1, year=today.year, hour=0, minute=0, second=0) + relativedelta(years=1)) - relativedelta(days=1)).strftime('%Y-%m-%d')
                rec.total_count = sum(self.env['loan_mgmt.loan_request'].sudo().search([('state', '=', 'disbursed'), ('bill_id.state', '=', 'paid'), ('disburse_date', '>=', date_start), ('disburse_date', '<=', date_end)]).mapped(lambda r: r.principal_amount))
                rec.short_count = rec.human_format(rec.total_count)
            elif rec.type == 'collection_mo':
                today = datetime.today()
                date_start = datetime(month=today.month, day=1, year=today.year, hour=0, minute=0, second=0).strftime('%Y-%m-%d')
                date_end =  ((datetime(month=today.month, day=1, year=today.year, hour=0, minute=0, second=0) + relativedelta(months=1)) - relativedelta(days=1)).strftime('%Y-%m-%d')
                rec.total_count = sum(self.env['account.payment'].sudo().search([('partner_type','=','customer'),('state', 'not in', ['cancelled', 'draft']),('payment_date', '>=', date_start), ('payment_date', '<=', date_end)]).mapped(lambda r: r.amount))
                rec.short_count = rec.human_format(rec.total_count)
            elif rec.type == 'collection_yr':
                today = datetime.today()
                date_start = datetime(month=1, day=1, year=today.year, hour=0, minute=0, second=0).strftime('%Y-%m-%d')
                date_end =  ((datetime(month=1, day=1, year=today.year, hour=0, minute=0, second=0) + relativedelta(years=1)) - relativedelta(days=1)).strftime('%Y-%m-%d')
                rec.total_count = sum(self.env['account.payment'].sudo().search([('partner_type','=','customer'),('state', 'not in', ['cancelled', 'draft']),('payment_date', '>=', date_start), ('payment_date', '<=', date_end)]).mapped(lambda r: r.amount))
                rec.short_count = rec.human_format(rec.total_count)
                
                
    def human_format(self, num):
        num = float('{:.3g}'.format(num))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])     

    @api.one
    def _get_name(self):
        if self.type == 'cur_mo_disb':
            self.name = 'Disbursed Loans This Month'
        if self.type == 'cur_yr_disb':
            self.name = 'Disbursed Loans This Year'
        if self.type == 'collection_mo':
            self.name = 'Collection This Month'
        if self.type == 'collection_yr':
            self.name = 'Collection This Year'

    @api.one
    def _kanban_dashboard_graph(self):
        if self.type in ['cur_mo_disb', 'cur_yr_disb']:
            if self.kanban_dashboard_graph_type == 'line':
                json.dumps(self.get_kanban_dashboard_line_datas())
            elif self.kanban_dashboard_graph_type == 'bar':
                json.dumps(self.get_kanban_dashboard_bar_datas())

    def _graph_title_and_key(self):
        return ['', _('Disbursed')]

    @api.one
    def get_kanban_dashboard_bar_datas(self):
        if self.type == 'cur_mo_disb':
            data = []
            today = datetime.today()
            date_start = date(month=today.month, year=today.year, day=1)
            date_end = date(month=today.month+1, year=today.year, day=1)
            num_days = (date_end - relativedelta(days=1)).day
            for i in range(1,num_days+1):
                get_date = date(month=today.month, year=today.year, day=i)
                get_date_short_name = get_date.strftime("%d")
                get_date_start = datetime(month=today.month, year=today.year, day=i, hour=0, minute=0, second=0)
                get_date_end = datetime(month=today.month, year=today.year, day=i, hour=23, minute=59, second=59)
                count = sum(self.env['loan_mgmt.loan_request'].sudo().search([('state','=', 'disbursed'), ('bill_id.state','=','paid'), ('disburse_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('disburse_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]).mapped(lambda r: r.principal_amount))
                data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.day else 'future'})
            [graph_title, graph_key] = self._graph_title_and_key()
            return {'values': data, 'title': graph_title, 'key': graph_key}
        elif self.type == 'cur_yr_disb':
            data = []
            today = datetime.today()
            date_start = date(month=1, year=today.year, day=1)
            date_end = date(month=1, year=today.year+1, day=1)
            num_mo = (date_end - relativedelta(days=1)).month
            for i in range(1,num_mo+1):
                get_date = date(month=i, year=today.year, day=1)
                get_date_short_name = get_date.strftime("%B")
                get_date_start = datetime(month=get_date.month, year=get_date.year, day=1, hour=0, minute=0, second=0)
                get_date_end = (datetime(month=get_date.month, year=today.year, day=1, hour=23, minute=59, second=59)+relativedelta(months=1)) - relativedelta(days=1)
                count = sum(self.env['loan_mgmt.loan_request'].sudo().search([('state','=', 'disbursed'), ('bill_id.state','=','paid'), ('disburse_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('disburse_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]).mapped(lambda r: r.principal_amount))
                data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.month else 'future'})
            [graph_title, graph_key] = self._graph_title_and_key()
            return {'values': data, 'title': graph_title, 'key': graph_key}
        return {}

    @api.one
    def get_kanban_dashboard_line_datas(self):
        if self.type == 'cur_mo_disb':
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
                get_date_end = datetime(month=today.month, year=today.year, day=i, hour=23, minute=59, second=59)
                count = sum(self.env['loan_mgmt.loan_request'].sudo().search([('state','=', 'disbursed'), ('bill_id.state','=','paid'),('disburse_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('disburse_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]).mapped(lambda r: r.principal_amount))
                data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
            [graph_title, graph_key] = self._graph_title_and_key()
            color = '#875A7B' if '+e' in version else '#7c7bad'
            return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}
        elif self.type == 'cur_yr_disb':
            data = []
            today = datetime.today()
            date_start = date(month=1, year=today.year, day=1)
            date_end = date(month=1, year=today.year+1, day=1)
            num_mo = (date_end - relativedelta(days=1)).month
            for i in range(1,num_mo+1):
                get_date = date(month=i, year=today.year, day=1)
                get_date_name = get_date.strftime("%d %B %Y")
                get_date_short_name = get_date.strftime("%d-%b")
                get_date_start = datetime(month=get_date.month, year=get_date.year, day=1, hour=0, minute=0, second=0)
                get_date_end = (datetime(month=get_date.month, year=today.year, day=1, hour=23, minute=59, second=59)+relativedelta(months=1)) - relativedelta(days=1)
                count = len(self.env['loan_mgmt.loan_request'].sudo().search([('state','=', 'disbursed'), ('bill_id.state','=','paid'),('disburse_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('disburse_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]))
                data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
            [graph_title, graph_key] = self._graph_title_and_key()
            color = '#875A7B' if '+e' in version else '#7c7bad'
            return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}
        return {}
        

            
    name = fields.Char("Dashboard", compute="_get_name")
    total_count = fields.Float("Total", compute="_count")
    short_count = fields.Char("Short Total", compute="_count")
    color = fields.Integer("Color")
    type = fields.Selection([('cur_mo_disb','Disbursed Loans This Month'), ('cur_yr_disb','Disbursed Loans This Year'), ('collection_mo','Collection This Month'), ('collection_yr','Collection This Year')], string="Dashboard Content Type")
    state = fields.Selection([('off','Off'), ('on','On')], string="Status", default="on")
    kanban_dashboard_graph = fields.Text(compute="_kanban_dashboard_graph")
    kanban_dashboard_graph_type = fields.Selection([('line','Line'),('bar','Bar')], string="Graph Type", default='line')
    
