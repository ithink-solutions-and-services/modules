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
