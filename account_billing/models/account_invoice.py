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
    
    total_cu_ms_fixed = fields.Float("Total Fixed Cu. m", compute="_water_total", store=True)
    total_cu_ms_fixed_price = fields.Float("Total Fixed Cu. m Price", compute="_water_total", store=True)
    total_cu_ms_exceed_price = fields.Float("Total Exceed Cu. m Price", compute="_water_total", store=True)
    
    total_cu_ms = fields.Float("Total Water Consumption")
    latest_cu_ms = fields.Float("Latest Water Consumption")
    
    @api.depends('invoice_line_ids', 'invoice_line_ids.cu_m', 'invoice_line_ids.prev_cu_m')
    def _cu_m(self):
        for rec in self:
            rec.cu_m_total = sum(rec.invoice_line_ids.mapped("cu_m"))
            rec.prev_cu_m_total = sum(rec.invoice_line_ids.mapped("prev_cu_m"))
    
    cu_m_total = fields.Float("Total Cu. M", compute="_cu_m", store=True)
    prev_cu_m_total = fields.Float("Total Previous Cu. M", compute="_cu_m", store=True)
    
    @api.depends('invoice_line_ids', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id.water_product', 'invoice_line_ids.product_id.monthly_due_product', 'invoice_line_ids.cu_m_fixed')
    def _water_total(self):
        for rec in self:
            rec.water_total = sum(rec.invoice_line_ids.filtered(lambda r: r.water_product == True).mapped("price_subtotal"))
            rec.monthly_due_total = sum(rec.invoice_line_ids.filtered(lambda r: r.monthly_due_product == True).mapped("price_subtotal"))
            rec.water_days = sum(rec.invoice_line_ids.filtered(lambda r: r.water_product == True).mapped("price_subtotal"))
            rec.total_cu_ms_fixed = sum(rec.invoice_line_ids.filtered(lambda r: r.water_product == True).mapped("cu_m_fixed"))
            rec.total_cu_ms_fixed_price = sum(rec.invoice_line_ids.filtered(lambda r: r.water_product == True).mapped("cu_m_fixed_price"))
            rec.total_cu_ms_exceed_price = sum(rec.invoice_line_ids.filtered(lambda r: r.water_product == True).mapped("cu_m_exceed_price"))
    
    water_total = fields.Float("Total Water Consumption Price", compute="_water_total", store=True)
    monthly_due_total = fields.Float("Total Monthly Dues Price", compute="_water_total", store=True)
    water_days = fields.Integer("1st number of days", compute="_water_total", store=True)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    water_product = fields.Boolean(related="product_id.water_product")
    monthly_due_product = fields.Boolean(related="product_id.monthly_due_product")
    cu_m = fields.Float("Cu. M")
    prev_cu_m = fields.Float("Previous Cu. M")
    cu_m_fixed = fields.Float("Fixed Cu. m")
    cu_m_fixed_price = fields.Float("Fixed Cu. m Price")
    cu_m_exceed_price = fields.Float("Exceed Cu. m Price")
