from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    billing_id = fields.Many2one('account.billing', string="Linked to Billing")
    billing_period_id = fields.Many2one('account.billing.period', string="Billing Period")
    billing_template_id = fields.Many2one('account.billing.template', string="Billing Template")
    
    
    @api.depends('invoice_line_ids', 'invoice_line_ids.cu_m', 'invoice_line_ids.prev_cu_m')
    def _cu_m(self):
        for rec in self:
            rec.cu_m_total = sum(rec.invoice_line_ids.mapped("cu_m"))
            rec.prev_cu_m_total = sum(rec.invoice_line_ids.mapped("prev_cu_m"))
    
    cu_m_total = fields.Float("Total Cu. M", compute="_cu_m", store=True)
    prev_cu_m_total = fields.Float("Total Previous Cu. M", compute="_cu_m", store=True)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    cu_m = fields.Float("Cu. M")
    prev_cu_m = fields.Float("Previous Cu. M)
