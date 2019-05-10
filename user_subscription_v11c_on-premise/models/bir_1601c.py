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

def get_years():
    year_list = []
    for i in range(2015, 2100):
        year_list.append((i, str(i)))
    return year_list


class Bir1601cLine(models.Model):
    _name = "bir.1601c.line"

    name = fields.Char()
    form_id = fields.Many2one("bir.1601c",'BIR 1601C')
    previous_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='Previous Month(s) (1) (MM/YYYY)')
    previous_year = fields.Selection(get_years(), string='Year')
    date_paid = fields.Date("Date Paid (2) (MM/DD/YYYY)")
    bank_validation = fields.Char("Bank Validation/ROR No. (3)")
    bank_code = fields.Char("Bank Code (4)")
    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')
    tax_paid = fields.Monetary("Tax Paid (Excluding Penalties) for the Month (5)")
    should_be_tax_due = fields.Monetary("Should be Tax Due for the Month (6)")
    adjustment_current = fields.Monetary("From Current Year (7a)")
    adjustment_yearend = fields.Monetary("From Year - End Adjustment of the Immediately Preceeding Year (7b)")

class Bir1601c(models.Model):
    _name = 'bir.1601c'

    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR 1601C - " + str(fields.Date.from_string(str(rec.create_date)))

    name = fields.Char(string="Name",compute="_get_name")
    path_id = fields.Many2one('bir.paths', string="File Path")
    generated_file = fields.Many2one('ir.attachment', string='Generated File')
    generated_file_datas = fields.Binary(related="generated_file.datas",store=True)
    generated_file_name = fields.Char(related="generated_file.datas_fname",store=True)

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')
    #company_id = fields.Many2one('res.company',string='Company')
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='1. For the of Month')
    of_year = fields.Selection(get_years(), string='Year')
    amended_return = fields.Boolean("2. Amended Return?",default=False)
    sheets_attached = fields.Integer("3. Number of sheets attached")
    any_taxes_withheld = fields.Boolean(string="4. Any Taxes Withheld?",default=False)
    vat = fields.Char(string="5. TIN",related="registered_name.vat",store=True)
    rdo = fields.Char(string="6. RDO Code", related="registered_name.rdo",store=True)
    line_of_business = fields.Char(string="7. Line of Business", related="registered_name.line_of_business",store=True)
    #registered_name = fields.Char(string="7. Registered Name",related="company_id.name",store=True)
    registered_name = fields.Many2one('res.company',string='8. Registered Name')
    telephone_number = fields.Char(string="9. Telephone Number",related="registered_name.phone",store=True)
    registered_address = fields.Char(string="10. Registered Address",related="registered_name.street",store=True)
    zip = fields.Char(string="11. Zip Code",related="registered_name.zip",store=True)
    category_of_withholding2 = fields.Selection([('private','Private'),('government','Government')],string="12. Category of Withholding Agent", related="registered_name.category_of_withholding2", store=True)
    under_special_law = fields.Boolean(string="13. Are there payees availing of tax relief under special law or international tax treaty?")
    under_special_law_spec = fields.Char(string="If yes, specify")
    total_amount_of_compensation = fields.Monetary(string="15. Total Amount of Compensation")
    statutory_mwe = fields.Monetary(string="16A. Statutory Minimum Wage (MWEs)")
    holiday_overtime = fields.Monetary(string="16B. Holiday Pay,Overtime Pay, Night Shift Differential Pay, Hazard Pay (Minimum Wage Earner)")
    other_nontaxable = fields.Monetary(string="16C. Other Non-Taxable Compensation")
    taxable_compensation = fields.Monetary(string="17. Taxable Compensation")
    tax_required_withheld = fields.Monetary(string="18. Tax Required to be Withheld")

    line_ids = fields.One2many('bir.1601c.line','form_id',string="Section A. Adjustment of Taxes Withheld on Compensation For Previous Months")

    @api.depends('line_ids','line_ids.adjustment_current','line_ids.adjustment_yearend')
    def _adjustments(self):
        for rec in self:
            total = 0
            for line in rec.line_ids:
                total += line.adjustment_current + line.adjustment_yearend
            rec.adjustment = total

    adjustment = fields.Monetary(string="19. Add/Less: Adjustment (from Item 26 of Section A)",compute="_adjustment",store=True)
    tax_required_remittance = fields.Monetary(string="20. Tax Required to be Withheld for Remittance")
    tax_remitted_previous_a = fields.Monetary(string="21A. Less: Tax Remitted in Return Previously Filed, if this is an amended return")
    tax_remitted_previous_b = fields.Monetary(string="21B. Other Payments Made (please attach proof of payment BIR Form No. 0605)")

    @api.depends('tax_remitted_previous_a','tax_remitted_previous_b')
    def _total_payments(self):
        for rec in self:
            rec.total_payments = rec.tax_remitted_previous_b + rec.tax_remitted_previous_a

    total_payments = fields.Monetary(string="22. Total Tax Payments Made (Sum of Item Nos. 21A & 21B)", compute="_total_payments",store=True)

    @api.depends('tax_required_withheld','total_payments')
    def _tax_still_due(self):
        for rec in self:
            rec.tax_still_due = rec.tax_required_withheld - rec.total_payments

    tax_still_due = fields.Monetary(string="23. Tax Still Due/(Overremittance) (Item No. 20 less Item No. 22)", compute="_tax_still_due",store=True)
    surcharge = fields.Monetary(string="24A. Surcharge")
    interest  = fields.Monetary(string="24B. Interest")
    compromise = fields.Monetary(string="24C. Compromise")

    @api.depends('surcharge','interest','compromise')
    def _add_penalties(self):
        for rec in self:
            rec.add_penalties = rec.surcharge + rec.interest + rec.compromise

    add_penalties = fields.Monetary(string="24D. Add: Penalties",compute="_add_penalties",store=True)
    total_amount_still_due = fields.Monetary(string="25. Total Amount Still Due/(Overremittance)")
    cash_bank = fields.Char("29A. Drawee Bank/Agency")
    cash_number = fields.Char("29B. Number")
    cash_date = fields.Date("29C. Date")
    cash_amount = fields.Monetary(string="29D. Amount")
    check_bank = fields.Char("30A. Drawee Bank/Agency")
    check_number = fields.Char("30B. Number")
    check_date = fields.Date("30C. Date")
    check_amount = fields.Monetary(string="30D. Amount")
    others_bank = fields.Char("31A. Drawee Bank/Agency")
    others_number = fields.Char("31B. Number")
    others_date = fields.Date("31C. Date")
    others_amount = fields.Monetary(string="31D. Amount")
    machine_validation = fields.Text(string="Machine Validation/Revenue Official Receipt Details (If not filed with the bank)")

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
                'res_model':'bir.1601c',
                'res_id': self.id,
            }
            attachment_id = attachment_obj.create(attachment_data)
            self.write({'generated_file' : attachment_id.id})
