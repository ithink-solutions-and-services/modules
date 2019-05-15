from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    or_no = fields.Char("OR#")
    particulars = fields.Char("Particulars")

    @api.model
    def create(self, vals):
        if not vals['or_no']:
            vals['or_no'] = self.env['ir.sequence'].next_by_code('account.payment')
        exist = self.env['account.payment'].sudo().search([('or_no','=',vals['or_no'])])
        if exist and len(exist)>0:
            raise UserError("OR# already existing!")
        return super(AccountPayment, self).create(vals)
