from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import io as StringIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import base64
import os.path

import logging
_logger = logging.getLogger(__name__)

class Bir2307Line(models.Model):
    _name = 'bir.2307.line'

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    name = fields.Char("Name")
    form_id = fields.Many2one('bir.2307',string="2307")
    atc = fields.Many2one('bir.atc','ATC')
    nip = fields.Char(string="Nature of Income Payment",related="atc.nip", store=True)

    amount_quarter_1 = fields.Monetary("1st Month of the Quarter")
    amount_quarter_2 = fields.Monetary("2nd Month of the Quarter")
    amount_quarter_3 = fields.Monetary("3rd Month of the Quarter")

    @api.depends('amount_quarter_1','amount_quarter_2','amount_quarter_3')
    def _tax_base(self):
        for rec in self:
            rec.tax_base = rec.amount_quarter_1 + rec.amount_quarter_2 + rec.amount_quarter_3

    tax_base = fields.Monetary(string='Tax Base',compute="_tax_base", store=True)
    tax_rate = fields.Float(string="Tax Rate", related="atc.tax_rate",store=True)

    @api.depends('tax_rate','tax_base')
    def _tax_withheld(self):
        for rec in self:
            rec.tax_withheld = rec.tax_base * (rec.tax_rate/100)

    tax_withheld = fields.Monetary(string="Tax Required to be Withheld",compute="_tax_withheld",store=True)


class Bir2307(models.Model):
    _name = 'bir.2307'

    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR 2307 - " + str(fields.Date.from_string(str(rec.create_date)))

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    name = fields.Char(string="Name",compute="_get_name")
    path_id = fields.Many2one('bir.paths', string="File Path")
    generated_file = fields.Many2one('ir.attachment', string='Generated File')
    generated_file_datas = fields.Binary(related="generated_file.datas",store=True)
    generated_file_name = fields.Char(related="generated_file.datas_fname",store=True)

    for_the_period_from = fields.Date("1. For the Period From")
    to = fields.Date("To")
    payees_name = fields.Many2one('res.partner',"3. Payee's Name")
    payees_vat = fields.Char(string='2. Tax Identification Number',related="payees_name.vat",store=True)
    payees_rdo = fields.Char(string="RDO",related="payees_name.rdo",store=True)
    payees_registered_address = fields.Char(string="4. Registered Address", related="payees_name.vat",store=True)
    payees_zip = fields.Char(string="4A. Zip Code",related="payees_name.zip",store=True)
    payees_foreign_address = fields.Char(string="5. Foreign Address", related="payees_name.foreign_address",store=True)
    payees_foreign_zip = fields.Char(string="5A. Zip Code", related="payees_name.foreign_zip",store=True)

    payors_name = fields.Many2one("res.company","7. Payors's Name")
    payors_vat = fields.Char(string="6. Taxpayer Identification Number",related="payors_name.vat",store=True)
    payors_rdo = fields.Char(string="RDO Code", related="payors_name.rdo", store=True)
    payors_registered_address = fields.Char(string="8. Registered Address", related="payors_name.street", store=True)
    payors_zip = fields.Char(string="8A. Zip Code",related="payors_name.zip",store=True)

    income_payment_ids = fields.One2many('bir.2307.line','form_id',string="Income Payments Subject to Expanded Withholding Tax")
    money_payment_ids = fields.One2many('bir.2307.line','form_id',string="Money Payments Subject to Withholding of Business Tax (Goverment & Private)")

    @api.depends('income_payment_ids','income_payment_ids.amount_quarter_1')
    def _income_payment_quarter_1_total(self):
        for rec in self:
            total = 0
            for line in rec.income_payment_ids:
                total = total + line.amount_quarter_1
            rec.income_payment_quarter_1_total = total

    @api.depends('income_payment_ids','income_payment_ids.amount_quarter_2')
    def _income_payment_quarter_2_total(self):
        for rec in self:
            total = 0
            for line in rec.income_payment_ids:
                total = total + line.amount_quarter_2
            rec.income_payment_quarter_2_total = total

    @api.depends('income_payment_ids','income_payment_ids.amount_quarter_3')
    def _income_payment_quarter_3_total(self):
        for rec in self:
            total = 0
            for line in rec.income_payment_ids:
                total = total + line.amount_quarter_3
            rec.income_payment_quarter_3_total = total

    @api.depends('income_payment_ids','income_payment_ids.tax_base')
    def _income_payment_total(self):
        for rec in self:
            total = 0
            for line in rec.income_payment_ids:
                total = total + line.tax_base
            rec.income_payment_total = total

    @api.depends('income_payment_ids','income_payment_ids.tax_withheld')
    def _income_payment_total_withheld(self):
        for rec in self:
            total = 0
            for line in rec.income_payment_ids:
                total = total + line.tax_withheld
            rec.income_payment_total_withheld = total


    income_payment_quarter_1_total = fields.Monetary(string="Q1 Total",compute="_income_payment_quarter_1_total",store=True)
    income_payment_quarter_2_total = fields.Monetary(string="Q2 Total",compute="_income_payment_quarter_2_total",store=True)
    income_payment_quarter_3_total = fields.Monetary(string="Q3 Total",compute="_income_payment_quarter_3_total",store=True)
    income_payment_total = fields.Monetary(string="Total",compute="_income_payment_total",store=True)
    income_payment_total_withheld = fields.Monetary(string="Total Tax Withheld For the Quarter", compute="_income_payment_total_withheld",store=True)

    @api.depends('money_payment_ids','money_payment_ids.amount_quarter_1')
    def _money_payment_quarter_1_total(self):
        for rec in self:
            total = 0
            for line in rec.money_payment_ids:
                total = total + line.amount_quarter_1
            rec.money_payment_quarter_1_total = total

    @api.depends('money_payment_ids','money_payment_ids.amount_quarter_2')
    def _money_payment_quarter_2_total(self):
        for rec in self:
            total = 0
            for line in rec.money_payment_ids:
                total = total + line.amount_quarter_2
            rec.money_payment_quarter_2_total = total

    @api.depends('money_payment_ids','money_payment_ids.amount_quarter_3')
    def _money_payment_quarter_3_total(self):
        for rec in self:
            total = 0
            for line in rec.money_payment_ids:
                total = total + line.amount_quarter_3
            rec.money_payment_quarter_3_total = total

    @api.depends('money_payment_ids','money_payment_ids.tax_base')
    def _money_payment_otal(self):
        for rec in self:
            total = 0
            for line in rec.money_payment_ids:
                total = total + line.tax_base
            rec.money_payment_total = total

    @api.depends('money_payment_ids','money_payment_ids.tax_withheld')
    def _money_payment_total_withheld(self):
        for rec in self:
            total = 0
            for line in rec.money_payment_ids:
                total = total + line.tax_withheld
            rec.money_payment_total_withheld = total

    money_payment_quarter_1_total = fields.Monetary(string="Total",compute="_money_payment_quarter_1_total",store=True)
    money_payment_quarter_2_total = fields.Monetary(string="Total",compute="_money_payment_quarter_2_total",store=True)
    money_payment_quarter_3_total = fields.Monetary(string="Total",compute="_money_payment_quarter_3_total",store=True)
    money_payment_total = fields.Monetary(string="Total",compute="_money_payment_total",store=True)
    money_payment_total_withheld = fields.Monetary(string="Total Tax Withheld", compute="_money_payment_total_withheld",store=True)


    @api.one
    def generate_pdf(self):
        fullpath = str(self.path_id.name)
        path = str(self.path_id.path)
        filename = str(self.path_id.filename)
        packet = StringIO.BytesIO()
        cv=canvas.Canvas(packet, pagesize=letter)
        cv.setFont("Courier", 8)
        cv.drawString(1, 1, "Test Output")
#        cv.showPage()
        cv.save()
        packet.seek(0)
        result = PdfFileWriter()
        new_pdf = PdfFileReader(packet)
        if os.path.exists(fullpath):
            existing_pdf = PdfFileReader(open(fullpath, "rb"))
            page = existing_pdf.getPage(0)
            page.mergePage(new_pdf.getPage(0))
            result.addPage(page)
            outputStream = open(path+"/"+self.name+".pdf", "wb")
            result.write(outputStream)
            outputStream.close()
            attachment_data = {}
            encoded_string = ''
            if os.path.exists(path+"/"+self.name+".pdf"):
                with open((path+"/"+self.name+".pdf"), "rb") as pdf:
                    encoded_string = base64.b64encode(pdf.read())
            attachment_obj = self.env['ir.attachment']
            attachment_data = {
                'name':  (self.name or '') + _(' (Scheme attachment)'),
                'datas_fname': self.name+".pdf",
                'datas' : encoded_string,
                'type' : 'binary',
                'description': self.name or _('No Description'),
                'res_model':'bir.2307',
                'res_id': self.id,
            }
            attachment_id = attachment_obj.create(attachment_data)
            self.write({'generated_file' : attachment_id.id})
