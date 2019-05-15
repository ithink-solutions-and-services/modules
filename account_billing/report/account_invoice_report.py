from odoo import api, models, fields

class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'
    
    water_product = fields.Boolean(related="product_id.water_product")
    monthly_due_product = fields.Boolean(related="product_id.monthly_due_product")
