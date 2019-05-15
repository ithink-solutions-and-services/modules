from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    or_no = fields.Char("OR#")
