from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountBilling(models.Model):
    _name = 'account.billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char("Billing #")
    partner_id = fields.Many2one('res.partner', string="Customer")
    state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'On Hold'),
                              ('close', 'Closed'), ('cancel', 'Cancelled')],
                             string='Status', required=True, track_visibility='onchange', copy=False, default='draft')
    date_start = fields.Date(string='Date Started', default=fields.Date.today)
    date_closed = fields.Date(string='Date Closed', track_visibility='onchange')
    billing_line_ids = fields.One2many('account.billing.line', 'billing_id', string="Billing Lines")
    
    @api.depends('billing_line_ids')
    def _total(self):
        for rec in self:
            rec.total_amount = sum(line.subtotal for line in rec.billing_line_ids)
    
    total_amount = fields.Float("Recurring Total", compute="_total", store=True)
    recurring_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'),
                                            ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ],
                                           string='Recurrency',
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', track_visibility='onchange')
    recurring_type_interval = fields.Integer(string="Repeat Every", help="Repeat every (Days/Week/Month/Year)", default=1, track_visibility='onchange')
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.")
    suspend_reason = fields.Text("Reason for Suspension/Closure/Cancellation", track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Assigned User', track_visibility='onchange')
    invoice_ids = fields.One2many('account.invoice', 'billing_id', string="Invoices")
    
    
class AccountBillingLine(models.Model):
    _name = 'account.billing.line'
    
    billing_id = fields.Many2one('account.billing', string="Linked to Billing")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float('Quantity', default=1)
    
    @api.depends('product_id', 'quantity')
    def _product(self):
        for rec in self:
            unit_price = 0
            subtotal = 0
            if rec.product_id:
                unit_price = rec.product_id.lst_price
                tax_price = 0
                for tax in rec.product_id.taxes_id:
                    if tax.amount_type == 'percent':
                        tax_price = tax_price + unit_price * (tax.amount/100)
                rec.unit_price = unit_price
                rec.taxed_price = unit_price + tax_price
                rec.subtotal = rec.unit_price * rec.quantity
    
    unit_price = fields.Float('Unit Price(non-VAT)', compute="_product", store=True)
    taxed_price = fields.Float('Taxed Price', compute="_product", store=True)
    subtotal = fields.Float('Subtotal', compute="_product", store=True)
    
