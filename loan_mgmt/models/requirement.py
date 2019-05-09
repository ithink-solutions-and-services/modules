from odoo import fields, models, api, SUPERUSER_ID
import logging
import datetime

_logger = logging.getLogger(__name__)

class LoanMgmtRequirement(models.Model):
    _name = 'loan_mgmt.requirement'

    name = fields.Char("Requirement")
    active = fields.Boolean(string="Active", default=True)


    
