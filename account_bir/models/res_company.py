from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_cr
    def init(self):
        try:
            php_cur = self.env.ref('base.PHP')
            php_cur.sudo().write({'active': True})
            company_cur = self.env.ref('base.main_company')
            company_cur.sudo().write({'currency_id': php_cur.id})
        except Exception as e:
            pass


    barangay = fields.Char("Barangay",related="partner_id.barangay",store=True)
    district = fields.Char("District/Municipality",related="partner_id.district",store=True)
    rdo = fields.Char("RDO Code",related="partner_id.rdo",store=True)
    branch_code = fields.Char(string="Branch Code", related="partner_id.branch_code",store=True)
    line_of_business = fields.Char("Line of Business",related="partner_id.line_of_business",store=True)
    taxpayer_classification = fields.Selection([('ind','Individual'),('corp','Non-Individual')],string="Taxpayer Classification",related="partner_id.taxpayer_classification",store=True)
    category_of_withholding = fields.Selection([('private','Private'),('government','Government')],string="Category of Withholding Agent",related="partner_id.category_of_withholding",store=True)
    foreign_address = fields.Char("Foreign Address",related="partner_id.foreign_address",store=True)
    foreign_zip = fields.Char("Foreign Zip Code",related="partner_id.foreign_zip",store=True)
    firstname = fields.Char("First Name",related="partner_id.firstname",store=True)
    middlename = fields.Char("Middle Name",related="partner_id.middlename",store=True)
    lastname = fields.Char("Last Name",related="partner_id.lastname",store=True)
    tradename = fields.Char("Trade Name",related="partner_id.tradename",store=True)

    def strip_space(self, string):
        return " ".join(string.split() if string != False else '')
