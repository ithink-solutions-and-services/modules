from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
import calendar
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

class Bir2550m(models.Model):
    _name = 'bir.2550m'

    @api.depends('create_date')
    def _get_name(self):
        for rec in self:
            rec.name = "BIR 2550M - " + str(fields.Date.from_string(str(rec.create_date)))

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
    vat = fields.Char(string="4. TIN",related="registered_name.vat",store=True)
    rdo = fields.Char(string="5. RDO Code", related="registered_name.rdo",store=True)
    line_of_business = fields.Char(string="6. Line of Business", related="registered_name.line_of_business",store=True)
    #registered_name = fields.Char(string="7. Registered Name",related="company_id.name",store=True)
    registered_name = fields.Many2one('res.company',string='7. Registered Name')
    telephone_number = fields.Char(string="8. Telephone Number",related="registered_name.phone",store=True)
    registered_address = fields.Char(string="9. Registered Address",related="registered_name.street",store=True)
    zip = fields.Char(string="10. Zip Code",related="registered_name.zip",store=True)
    under_special_law = fields.Boolean(string="11. Are there payees availing of tax relief under special law or international tax treaty?")
    under_special_law_spec = fields.Char(string="If yes, specify")

    @api.depends('registered_name','of_month','of_year','vatable_sales_private_a','vatable_sales_private_b','sales_to_government_a','sales_to_government_b','zero_rated_sales','exempt_sales')
    def _vatable_sales_private(self):
        for rec in self:
            total = 0
            total_tax = 0
            start_date = datetime.date(int(rec.of_year),int(rec.of_month),1)
            end_date = datetime.date(int(rec.of_year),int(rec.of_month),calendar.monthrange(int(rec.of_year), int(rec.of_month))[1])
            move_ids = self.env['account.move'].sudo().search([('company_id','=',rec.registered_name.id),('date','>=',start_date),('date','<=',end_date)])
            for move_id in move_ids:
                amount = 0
                tax = 0
                for line in move_id.line_ids:
                    if line.account_id.user_type_id.name == 'Income' and line.tax_ids:
                        for tax_id in line.tax_ids:
                            tax = tax + (line.credit * (tax_id.amount/100))
                        amount = amount + line.credit + tax
                total_tax = total_tax + tax
                total = total + amount
            rec.vatable_sales_private_a = total
            rec.vatable_sales_private_b = total_tax
            rec.total_sales_a = rec.vatable_sales_private_a + rec.sales_to_government_a + rec.zero_rated_sales + rec.exempt_sales
            rec.total_sales_b = rec.vatable_sales_private_b + rec.sales_to_government_b

    vatable_sales_private_a = fields.Monetary(string="12A. Sales/Receipt for the Month (Exclusive of VAT)",compute="_vatable_sales_private",store=True)
    vatable_sales_private_b = fields.Monetary(string="12.B Output Tax Due for the Month",compute="_vatable_sales_private",store=True)
    sales_to_government_a = fields.Monetary(string="13A. Sales/Receipt for the Month (Exclusive of VAT)")
    sales_to_government_b = fields.Monetary(string="13B. Output Tax Due for the Month")
    zero_rated_sales = fields.Monetary(string="14. Sales/Receipt for the Month (Exclusive of VAT)")
    exempt_sales = fields.Monetary(string="15. Sales/Receipt for the Month (Exclusive of VAT)")
    total_sales_a = fields.Monetary(string="16A. Sales/Receipt for the Month (Exclusive of VAT)",compute="_vatable_sales_private",store=True)
    total_sales_b = fields.Monetary(string="16B. Output Tax Due for the Month",compute="_vatable_sales_private",store=True)
    input_tax_carried_over = fields.Char(string="17A. Input Tax Carried Over from Previous Period")
    input_tax_deferred_exceed = fields.Char(string="17B. Input Tax Deferred on Capital Goods Exceeding P1Million from Previous Period")
    transitional_input_tax = fields.Char("17C. Transitional Input Tax")
    presumptive_input_tax = fields.Char("17D. Presumptive Input Tax")
    others_allowable_input_tax = fields.Char("17E. Others")
    total_allowable_input_tax = fields.Char("17F. Total")
    capital_goods_not_exceed_a = fields.Char("18A. Purchase of Capital Goods not exceeding P1Million (see sch.2)")
    capital_goods_not_exceed_b = fields.Char("18B. Purchase of Capital Goods not exceeding P1Million (see sch.2)")
    capital_goods_exceed_c = fields.Char("18C. Purchase of Capital Goods exceeding P1Million (see sch.3)")
    capital_goods_exceed_d = fields.Char("18D. Purchase of Capital Goods exceeding P1Million (see sch.3)")
    domestic_purchases_goods_e =  fields.Char("18E. Domestic Purchases of Goods")
    domestic_purchases_goods_f =  fields.Char("18F. Domestic Purchases of Goods Output Tax Due")
    importation_of_goods_g = fields.Char("18G. Importation Purchases of Goods")
    importation_of_goods_h = fields.Char("18H. Importation Purchases of Goods Output Tax Due")
    domestic_purchases_services_i = fields.Char("18I. Domestic Purchases of Services")
    domestic_purchases_services_j = fields.Char("18J. Domestic Purchases of Services Output Tax Due")
    nonresident_services_k = fields.Char("18K. Services rendered by Non-residents")
    nonresident_services_l = fields.Char("18L. Services rendered by Non-residents Output Tax Due")
    not_qualified_purchases = fields.Char("18M. Purchases Not Qualified for Input Tax")
    others_current_transactions_n = fields.Char("18N. Others")
    others_current_transactions_o = fields.Char("18O. Others")
    total_current_purchases = fields.Char("18.P Total Current Purchases")
    total_available_input_tax = fields.Char("19. Total Available Input Tax")
    input_tax_capital_goods_exceed = fields.Char("20A. Input Tax on Purchases of Capital Goods exceeding P1Million deferred for the succeeding period (Sch.3)")
    input_tax_sale_to_gov = fields.Char("20B. Input Tax on Sale to Govt. closed to expense (Sch.4)")
    input_tax_exempt = fields.Char("20C. Input Tax allocable to Exempt Sales (Sch.5)")
    vat_refund_tcc = fields.Char("20D. VAT Refund/TCC claimed")
    deductions_others = fields.Char("20E. Others")
    total_deductions = fields.Char("20F. Total")
    total_allowable_input_tax = fields.Char("21. Total Allowable Input Tax")
    net_vat_payable = fields.Char("22. Net VAT Payable")
    creditable_vat_withheld = fields.Char("23A. Creditable Value-Added Tax Withheld (Sch.6)")
    advanced_sugar_flour = fields.Char("23B. Advanced Payments for Sugar and Flour Industries (Sch.7)")
    vat_withheld_sales_to_gov  = fields.Char("23C. VAT Withheld on Sales to Govertment")
    vat_paid_previous = fields.Char("23D. VAT paid in return previously filed, if this is an amended return")
    advanced_payments_made = fields.Char("23E. Advanced Payments made (please attach proof of payments - BIR Form No. 0605)")
    others_tax_credits = fields.Char("23F. Others")
    total_tax_credits = fields.Char("23G. Total")
    tax_still_payable = fields.Char("24. Tax Still Payable/(Overpayment)")
    surcharge = fields.Char("25A. Surcharge")
    interest = fields.Char("25B. Interest")
    compromise = fields.Char("25C. Compromise")

#    @api.depends('surcharge','interest','compromise')
#    def _add_penalties(self):
#        for rec in self:
#            rec.add_penalties = rec.surcharge + rec.interest + rec.compromise

#    add_penalties = fields.Monetary(string="Add: Penalties", compute="_add_penalties", store=True)
    add_penalties = fields.Char("25D. Add Penalties")
    total_amount_payable = fields.Char("26. Total Amount Payable/(Overpayment)")

    cash_bank = fields.Char("29A. Drawee Bank/Agency")
    cash_number = fields.Char("29B. Number")
    cash_date = fields.Date("29C. Date")
    cash_amount = fields.Char(string="29D. Amount")
    check_bank = fields.Char("30A. Drawee Bank/Agency")
    check_number = fields.Char("30B. Number")
    check_date = fields.Date("30C. Date")
    check_amount = fields.Char(string="30D. Amount")
    tax_number = fields.Char("31A. Number")
    tax_date = fields.Date("31B. Date")
    tax_amount = fields.Char(string="31C. Amount")
    others_bank = fields.Char(string="32A. Drawee Bank/Agency")
    others_number = fields.Char("32B. Number")
    others_date = fields.Date("32C. Date")
    others_amount = fields.Char(string="32D. Amount")
    machine_validation = fields.Text(string="Machine Validation (if filed with an accredited agent bank)/Revenue Official Receipt Details (If not filed with an Authorized Agent Bank)")

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
                'res_model':'bir.2550m',
                'res_id': self.id,
            }
            attachment_id = attachment_obj.create(attachment_data)
            self.write({'generated_file' : attachment_id.id})
