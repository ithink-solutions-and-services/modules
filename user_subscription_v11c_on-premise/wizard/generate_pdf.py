from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

def get_years():
    year_list = []
    for i in range(2015, 2100):
        year_list.append((i, str(i)))
    return year_list
class BirGeneratePdfSch1(models.TransientModel):
    _name = "bir.generate.pdf.sch1"


    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    parent_id = fields.Many2one('bir.generate.pdf',string="Parent Form")
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='1. For the of Month')
    of_year = fields.Selection(get_years(), string='Year')
    company_id = fields.Many2one('res.company',string="Company")
    tax_id = fields.Many2one('account.tax', string="ATC")

    @api.one
    @api.depends('tax_id','of_month','of_year','company_id')
    def _calc(self):
        str_split = self.tax_id.name.split(" - ") if self.tax_id else False
        self.desc = str_split[len(str_split)-1].strip() if str_split else False
        start_date = datetime.date(int(self.of_year),int(self.of_month),1)
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        total = 0
        total_tax = 0
        invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',self.tax_id.id)])
        for invoice_tax in invoice_taxes:
            total = total + invoice_tax.base
            total_tax = total_tax + invoice_tax.amount_total
        self.amount = total
        self.tax = total_tax

    desc = fields.Char(string="Description",compute="_calc",store=True)
    amount = fields.Monetary(string="Amount",compute="_calc",store=True)
    tax = fields.Monetary(string="Tax", compute="_calc",store=True)

class BirGeneratePdf(models.TransientModel):
    _name = "bir.generate.pdf"

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    form_type = fields.Selection([('2550M','2550M')],string="Form")
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='1. For the of Month')
    of_year = fields.Selection(get_years(), string='Year')
    company_id = fields.Many2one('res.company',string="Company")
    amended_return = fields.Boolean("2. Amended Return?",default=False)
    sheets_attached = fields.Integer("3. Number of sheets attached")
    under_special_law = fields.Boolean(string="11. Are there payees availing of tax relief under special law or international tax treaty?")
    under_special_law_spec = fields.Char(string="If yes, specify")

    @api.one
    @api.depends('company_id','of_month','of_year','vatable_sales_private_a','vatable_sales_private_b','sales_to_government_a','sales_to_government_b','zero_rated_sales','exempt_sales')
    def _vatable_sales_private(self):
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Receipt'),('name','ilike','Sales'),('name','ilike','Private')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            start_date = datetime.date(int(self.of_year),int(self.of_month),1)
            end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.vatable_sales_private_a = total
            self.vatable_sales_private_b = total_tax
        self.total_sales_a = self.vatable_sales_private_a + self.sales_to_government_a + self.zero_rated_sales + self.exempt_sales
        self.total_sales_b = self.vatable_sales_private_b + self.sales_to_government_b

    vatable_sales_private_a = fields.Monetary(string="12A. Sales/Receipt for the Month (Exclusive of VAT)",compute="_vatable_sales_private",store=True)
    vatable_sales_private_b = fields.Monetary(string="12.B Output Tax Due for the Month",compute="_vatable_sales_private",store=True)

    @api.one
    @api.depends('of_year','of_month')
    def _sales_to_government(self):
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Government'),('name','ilike','Sales')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            start_date = datetime.date(int(self.of_year),int(self.of_month),1)
            end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.sales_to_government_a = total
            self.sales_to_government_b = total_tax

    sales_to_government_a = fields.Monetary(string="13A. Sales/Receipt for the Month (Exclusive of VAT)",compute="_sales_to_government", store=True)
    sales_to_government_b = fields.Monetary(string="13B. Output Tax Due for the Month" ,compute="_sales_to_government", store=True)

    @api.one
    @api.depends('of_year','of_month')
    def _get_exempt_zero(self):
        total = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Exempt'),('name','ilike','Sales'),('name','ilike','Receipt')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            start_date = datetime.date(int(self.of_year),int(self.of_month),1)
            end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
            self.exempt_sales = total
        total = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Zero'),('name','ilike','Sales'),('name','ilike','Receipt')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            start_date = datetime.date(int(self.of_year),int(self.of_month),1)
            end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
            self.zero_rated_sales = total

    zero_rated_sales = fields.Monetary(string="14. Sales/Receipt for the Month (Exclusive of VAT)",compute="_get_exempt_zero",store=True)
    exempt_sales = fields.Monetary(string="15. Sales/Receipt for the Month (Exclusive of VAT)", compute="_get_exempt_zero",store=True)
    total_sales_a = fields.Monetary(string="16A. Sales/Receipt for the Month (Exclusive of VAT)",compute="_vatable_sales_private",store=True)
    total_sales_b = fields.Monetary(string="16B. Output Tax Due for the Month",compute="_vatable_sales_private",store=True)

    @api.one
    @api.depends('of_year','of_month','capital_goods_not_exceed_a','importation_of_goods_a','domestic_purchases_services_a','others_a','capital_goods_not_exceed_b','importation_of_goods_b','domestic_purchases_services_b','others_b')
    def _purchases(self):
        start_date = datetime.date(int(self.of_year),int(self.of_month),1)
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Purchase'),('name','ilike','Goods'),('name','ilike','Capital'),('name','ilike','not')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.capital_goods_not_exceed_a = total
            self.capital_goods_not_exceed_b = total_tax
        
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Importation'),('name','ilike','Goods'),('name','ilike','Capital'),('name','ilike','Other')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.importation_of_goods_a = total
            self.importation_of_goods_b = total_tax
        
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Domestic'),('name','ilike','Purchase'),('name','ilike','Service')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.domestic_purchases_services_a = total
            self.domestic_purchases_services_b = total_tax
        
        total = 0
        total_tax = 0
        get_tax_id = self.env['account.tax'].sudo().search([('name','ilike','Others')])
        if get_tax_id:
            get_tax_id = get_tax_id[0] and get_tax_id
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('tax_id','=',get_tax_id.id)])
            for invoice_tax in invoice_taxes:
                total = total + invoice_tax.base
                total_tax = total_tax + invoice_tax.amount_total
            self.others_a = total
            self.others_b = total_tax

        self.total_current_purchases = self.capital_goods_not_exceed_a + self.importation_of_goods_a + self.domestic_purchases_services_a + self.others_a
        self.total_available_input_tax = self.capital_goods_not_exceed_b + self.importation_of_goods_b + self.domestic_purchases_services_b + self.others_b

    capital_goods_not_exceed_a = fields.Monetary("18A. Purchase of Capital Goods not exceeding P1Million (see sch.2)",compute="_purchases",store=True)
    capital_goods_not_exceed_b = fields.Monetary("18B. Purchase of Capital Goods not exceeding P1Million (see sch.2)",compute="_purchases",store=True)
    importation_of_goods_a = fields.Monetary("18G. Importation Purchases of Goods",compute="_purchases",store=True)
    importation_of_goods_b = fields.Monetary("18H. Importation Purchases of Goods Output Tax Due",compute="_purchases",store=True)
    domestic_purchases_services_a = fields.Monetary("18I. Domestic Purchases of Services",compute="_purchases",store=True)
    domestic_purchases_services_b = fields.Monetary("18J. Domestic Purchases of Services Output Tax Due",compute="_purchases",store=True)
    others_a = fields.Monetary("18N. Others",compute="_purchases",store=True)
    others_b = fields.Monetary("18O. Others",compute="_purchases",store=True)
    total_current_purchases = fields.Monetary("18.P Total Current Purchases",compute="_purchases",store=True)
    total_available_input_tax = fields.Monetary("19. Total Available Input Tax",compute="_purchases",store=True)


    @api.one
    @api.depends('total_available_input_tax')
    def _total_allowable_input_tax(self):
        self.total_allowable_input_tax = self.total_available_input_tax

    total_allowable_input_tax = fields.Monetary("21. Total Allowable Input Tax",compute="_total_allowable_input_tax",store=True)

    @api.one
    @api.depends('total_sales_b','total_allowable_input_tax')
    def _net_vat_payable(self):
        self.net_vat_payable = self.total_sales_b - self.total_allowable_input_tax

    net_vat_payable = fields.Monetary("22. Net VAT Payable",compute="_net_vat_payable",store=True)

    @api.one
    @api.depends('net_vat_payable')
    def _tax_still_payable(self):
        self.tax_still_payable = self.net_vat_payable

    tax_still_payable = fields.Monetary("24. Tax Still Payable/(Overpayment)",compute="_tax_still_payable",store=True)

    @api.one
    @api.depends('tax_still_payable')
    def _total_amount_payable(self):
        self.total_amount_payable = self.tax_still_payable

    total_amount_payable = fields.Monetary("26. Total Amount Payable/(Overpayment)",compute="_total_amount_payable",store=True)


    @api.multi
    def action_generate(self):
        self.ensure_one()
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        if end_date >= datetime.datetime.now().date():
            raise UserError("Cannot generate unfinished month")
        if self.form_type == '2550M':
            return self.env.ref('user_subscription_v11c_on-premise.report_bir_2550m_custom_report').report_action(self)
        return True
