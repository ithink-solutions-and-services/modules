from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    or_no = fields.Char("OR#")
    particulars = fields.Char("Particulars")
    
    @api.depends('invoice_ids', 'invoice_ids.residual')
    def _total_due(self):
        for rec in self:
            total = sum(rec.invoice_ids.mapped("residual"))
            rec.invoices_total_due = total + rec.amount
    
    invoices_total_due = fields.Float("Total Due on Invoices", compute="_total_due", store=True)

    @api.model
    def create(self, vals):
        if not vals['or_no']:
            vals['or_no'] = self.env['ir.sequence'].next_by_code('account.payment')
        exist = self.env['account.payment'].sudo().search([('or_no','=',vals['or_no'])])
        if exist and len(exist)>0:
            raise UserError("OR# already existing!")
        return super(AccountPayment, self).create(vals)
