from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class AccountBir(models.Model):
    _name = 'account.bir'
    
    name = fields.Char("BIR Form")
    code = fields.Char("Code")
    active = fields.Boolean("Active", default=True)
    wizard_id = fields.Char("Wizard ID")

