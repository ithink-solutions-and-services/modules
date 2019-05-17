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
        self.env['account.billing.dashboard'].sudo().search([]).unlink()
        records = self.env['account.billing.dashboard'].sudo().search([])
        if records:
            if len(records) == 0:
                self.env['account.billing.dashboard'].sudo().create({'name': 'Dashboard 1'})
            elif len(records) > 1:
                count = 0
                for rec in records:
                    if count > 0:
                        rec.sudo().unlink()
        else:
            self.env['account.billing.dashboard'].sudo().create({'name': 'Dashboard 1', 'type': 'combined', 'content_type': 'col_day'})
        self.env['account.billing.dashboard'].sudo().search([('content_type','=',False)]).unlink()
                    
                    

    def _count(self):
        for rec in self:
            if rec.content_type == 'col_day':
                total_count = 0
                rec.total_count = self.env['account.']
                
                
        
    @api.one
    def _kanban_dashboard_graph(self):
        if self.type in ['combined', 'graph']:
            self.kanban_dashboard_graph = json.dumps(self.get_kanban_dashboard_line_datas()) if self.kanban_dashboard_graph_type == 'line' else json.dumps(self.get_kanban_dashboard_bar_datas())

    def _graph_title_and_key(self):
        return ['', _('Leads')]

    @api.one
    def get_kanban_dashboard_bar_datas(self):
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
            count = len(self.env['crm.lead'].sudo().search([('create_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('create_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]))
            data.append({'label':get_date_short_name,'value': count, 'type': 'past' if i<today.day else 'future'})
        [graph_title, graph_key] = self._graph_title_and_key()
        return {'values': data, 'title': graph_title, 'key': graph_key}

    @api.one
    def get_kanban_dashboard_line_datas(self):
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
            count = len(self.env['crm.lead'].sudo().search([('create_date','>=',get_date_start.strftime("%Y-%m-%d %H:%M:%S")), ('create_date','<=',get_date_end.strftime("%Y-%m-%d %H:%M:%S"))]))
            data.append({'x': get_date_short_name, 'y':count, 'name': get_date_name})
        [graph_title, graph_key] = self._graph_title_and_key()
        color = '#875A7B' if '+e' in version else '#7c7bad'
        return {'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}

    @api.one
    def _get_name(self):
        self.name = datetime.today().strftime("%B %Y")
        
    

    name = fields.Char("Dashboard", compute="_get_name")
    total_count = fields.Float("Count", compute="_count")
    color = fields.Integer("Color")
    type = fields.Selection([('combined','Combined'), ('text','Text'), ('graph','Graph')], string="Dashboard Content Type", default="combined")
    kanban_dashboard_graph = fields.Text(compute="_kanban_dashboard_graph")
    kanban_dashboard_graph_type = fields.Selection([('line','Line'),('bar','Bar')], string="Graph Type", default='line')    
    content_type = fields.Selection([('lead_mo','Monthly Leads'), ('lead_all','Total Leads')], string="Content Type")
