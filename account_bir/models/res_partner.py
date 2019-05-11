from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    barangay = fields.Char("Barangay")
    district = fields.Char("District/Municipality")
    rdo = fields.Char("RDO Code")
    branch_code = fields.Char(string="Branch Code", default="0000")
    line_of_business = fields.Char("Line of Business")
    taxpayer_classification = fields.Selection([('ind','Individual'),('corp','Non-Individual')],string="Taxpayer Classification")
    category_of_withholding = fields.Selection([('private','Private'),('government','Government')],string="Category of Withholding Agent")
    foreign_address = fields.Char("Foreign Address")
    foreign_zip = fields.Char("Foreign Zip Code")

    def strip_space(self, string):
        return " ".join(string.split() if string != False else '')
    
    firstname = fields.Char(string="Firstname")
    middlename = fields.Char(string="Middlename")
    lastname = fields.Char(string="Lastname")
    tradename = fields.Char(string="Trade Name")
