from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import io as StringIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import base64
import os.path

import logging
_logger = logging.getLogger(__name__)


def get_years():
    year_list = []
    for i in range(2015, 2100):
        year_list.append((i, str(i)))
    return year_list

class BirSchedule1(models.Model):
    _name = 'bir.schedule1'

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')


    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR Schedule 1 - " + str(fields.Date.from_string(str(rec.create_date)))

    name = fields.Char(string="Name",compute="_get_name")
    form_id = fields.Many2one('bir.1601e','1601E')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier','=',True)]")
    vat = fields.Char(string='TIN', related="vendor_id.vat",store=True)
    branch_code = fields.Char(string='Branch Code', related="vendor_id.branch_code", store=True)
    amount = fields.Monetary(string="Amount of Income Payment")
    atc = fields.Many2one('bir.atc','ATC')
    atc_nip = fields.Char(string="Nature of Income Payment", related="atc.nip", store=True)
    tax_rate = fields.Float(string='Tax Rate', related="atc.tax_rate", store=True)

    @api.depends('amount','tax_rate')
    def _amount_withheld(self):
        for rec in self:
            rec.amount_withheld = rec.amount * (rec.tax_rate/100)


    amount_withheld = fields.Monetary(string="Amount of Tax Withheld",compute="_amount_withheld", store=True)
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='Month')
    of_year = fields.Selection(get_years(), string='Year')
