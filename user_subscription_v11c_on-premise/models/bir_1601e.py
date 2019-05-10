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
import csv

import logging
_logger = logging.getLogger(__name__)


def get_years():
    year_list = []
    for i in range(2015, 2100):
        year_list.append((i, str(i)))
    return year_list

class Bir1601eLine(models.Model):
    _name = "bir.1601e.line"

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    name = fields.Char("Name")
    form_id = fields.Many2one('bir.1601e',string="1601E")
    atc = fields.Many2one('bir.atc','ATC')
    nip = fields.Char(string="Nature of Income Payment",related="atc.nip", store=True)
    tax_base = fields.Monetary(string='Tax Base')
    tax_rate = fields.Float(string="Tax Rate", related="atc.tax_rate",store=True)

    @api.depends('tax_rate','tax_base')
    def _tax_withheld(self):
        for rec in self:
            rec.tax_withheld = rec.tax_base * (rec.tax_rate/100)

    tax_withheld = fields.Monetary(string="Tax Required to be Withheld",compute="_tax_withheld",store=True)

class Bir1601e(models.Model):
    _name = 'bir.1601e'

    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR 1601e - " + str(fields.Date.from_string(str(rec.create_date)))

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
    generated_dat_file = fields.Many2one('ir.attachment', string='Generated dat')
    generated_dat_file_datas = fields.Binary(related="generated_dat_file.datas",store=True)
    generated_dat_file_name = fields.Char(related="generated_dat_file.datas_fname",store=True)


    line_ids = fields.One2many('bir.1601e.line','form_id',string="Lines")
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='Month')
    of_year = fields.Selection(get_years(), string='Year')
    amended_return = fields.Boolean('Amended Return?', default=False)
    sheets_attached = fields.Integer("No. of Sheets Attached")
    taxes_withheld = fields.Boolean("Any Taxes Withheld?")
    company_id = fields.Many2one('res.company','Company')
    vat = fields.Char(string="TIN",related="company_id.vat",store=True)
    branch_code = fields.Char(string="Branch Code", related="company_id.branch_code",store=True)
    rdo = fields.Char(string="RDO Code", related="company_id.rdo", store=True)
    line_of_business = fields.Char(string="Line of Business", related="company_id.line_of_business",store=True)
    registered_name = fields.Char(string="Registered Name", related="company_id.name", store=True)
    telephone_number = fields.Char(string="Telephone Number", related="company_id.phone", store=True)
    registered_address = fields.Char(string="Registered Address", related="company_id.street", store=True)
    zip = fields.Char(string="Zip Code",related="company_id.zip",store=True)
    category_of_withholding = fields.Selection([('ind','Ind'),('corp','Cort')],string="Category of Withholding Agent",related="company_id.category_of_withholding",store=True)
    under_special_law = fields.Boolean("Are there payees availing of tax relief under special law or international tax treaty?",default=False)
    under_special_law_spec = fields.Char("If yes, specify")
    schedule1_ids = fields.One2many('bir.schedule1','form_id',string="Schedule 1")


    @api.depends('schedule1_ids','schedule1_ids.amount')
    def _schedule1_total(self):
        for rec in self:
            total = 0
            for line_id in rec.schedule1_ids:
                total = total + line_id.amount
            rec.schedule1_total = total

    @api.depends('schedule1_ids','schedule1_ids.amount_withheld')
    def _schedule1_total_withheld(self):
        for rec in self:
            total = 0
            for line_id in rec.schedule1_ids:
                total = total + line_id.amount_withheld
            rec.schedule1_total_withheld = total

    schedule1_total = fields.Monetary(string='Schedule 1s Total',compute="_schedule1_total",store=True)
    schedule1_total_withheld = fields.Monetary(string='Schedule 1s Total Withheld',compute="_schedule1_total_withheld",store=True)


    @api.depends('line_ids')
    def _total_withheld(self):
        for rec in self:
            total = 0
            for line_id in rec.line_ids:
                total = total + line_id.tax_withheld
            rec.total_withheld = total

    total_withheld = fields.Monetary(string="Total Tax Required to be Withheld and Remitted",compute="_total_withheld", store=True)
    amended_return_previous_filed = fields.Monetary(string="Less: Tax Remitted in Return Previously Filed, if this is an amended return")
    overremitance = fields.Monetary(string="Tax  Still Due/(Overremittance)")
    surcharge = fields.Monetary("Surcharge")
    interest = fields.Monetary("Interest")
    compromise = fields.Monetary("Compromise")

    @api.depends('surcharge','interest','compromise')
    def _add_penalties(self):
        for rec in self:
            rec.add_penalties = rec.surcharge + rec.interest + rec.compromise

    add_penalties = fields.Monetary(string="Add: Penalties", compute="_add_penalties", store=True)

    @api.depends('overremitance','add_penalties')
    def _total_still_due(self):
        for rec in self:
            rec.total_still_due = rec.overremitance + rec.add_penalties

    total_still_due = fields.Monetary(string="Total Amount Still Due/(Overremittance)", compute="_total_still_due", store=True)

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
                'res_model':'bir.1601e',
                'res_id': self.id,
            }
            attachment_id = attachment_obj.create(attachment_data)
            self.write({'generated_file' : attachment_id.id})





    @api.one
    def generate_dat(self):
        path = str("/opt/odoo11/addons/user_subscription_v11c_on-premise/static/src/birdat/")
        filename = str(str(self.vat) + str(self.branch_code) + str(self.of_month) + str(self.of_year) + "1601E.dat")
#        lists = []
#        for line_id in self.schedule1_ids:
#            list = [line_id.,,]
#        lists = []
#        lists.append(['HMAP','H1601E',self.vat,self.branch_code,('"'+self.registered_name+'"'),(str(self.of_month) + '/' + str(self.of_year)),self.rdo])
        with open((path + filename), 'w') as myfile:
            wr = csv.writer(myfile,)
            wr.writerow(['HMAP','H1601E',self.vat,self.branch_code,('"'+self.registered_name.upper()+'"'),(str(self.of_month) + '/' + str(self.of_year)),self.rdo])
            count = 1
            for line_id in self.schedule1_ids:
                wr.writerow(['DMAP','D1601E',str(count),line_id.vat,line_id.branch_code,('"'+line_id.vendor_id.name.upper()+'"'),'','',(str(line_id.of_month) + '/' + str(line_id.of_year)),line_id.atc.name,'',('%.2f' % line_id.tax_rate),('%.2f' % line_id.amount),('%.2f' % line_id.amount_withheld)])
                count = count + 1
            wr.writerow(['CMAP','C1601E',self.vat,self.branch_code,(str(self.of_month) + '/' + str(self.of_year)),('%.2f' % self.schedule1_total),('%.2f' % self.schedule1_total_withheld)])
        encoded_string = ''
        if os.path.exists(path+filename):
            with open((path+filename), "r") as pdf:
                encoded_string = base64.b64encode(pdf.read().replace('"""','"').replace(',,,',',,,,').encode('utf-8'))
        attachment_obj = self.env['ir.attachment']
        attachment_data = {
            'name':  (self.name or '') + _(' (Scheme attachment)'),
            'datas_fname': filename,
            'datas' : encoded_string,
            'type' : 'binary',
            'description': self.name or _('No Description'),
            'res_model':'bir.1601e',
            'res_id': self.id,
        }
        attachment_id = attachment_obj.create(attachment_data)
        self.write({'generated_dat_file' : attachment_id.id})
        try:
            os.remove(path+filename)
        except Exception as e:
            pass
