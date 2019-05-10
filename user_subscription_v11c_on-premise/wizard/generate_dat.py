from odoo import models, fields, api, SUPERUSER_ID, _
import datetime
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
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

class BirGenerateDat(models.TransientModel):
    _name = "bir.generate.dat"

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    dat_type = fields.Selection([('sales','Sales'),('purchases','Purchases')],string="Form")
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='1. For the of Month')
    of_year = fields.Selection(get_years(), string='Year')
    company_id = fields.Many2one('res.company',string="Company")
    generated_dat_file = fields.Many2one('ir.attachment', string='Generated dat')
    generated_dat_file_datas = fields.Binary(related="generated_dat_file.datas",store=True)
    generated_dat_file_name = fields.Char(related="generated_dat_file.datas_fname",store=True)
#    sch1_ids = fields.One2many('bir.generate.dat.sch1','dat_id',string="Schedule 1")
    sch1_ids = fields.Many2many('bir.generate.dat.sch1',string="Schedule 1")
    non_creditable = fields.Monetary(string="Non-Creditable")

    def strip_space(self, string):
        return " ".join(string.split() if string != False else '')

    @api.multi
    def generate_sch1(self):
        self.ensure_one()
        start_date = datetime.date(int(self.of_year),int(self.of_month),1)
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        if self.dat_type == 'sales':
            get_partners = self.env['account.invoice'].sudo().search([('type','=','out_invoice'),('date_invoice','>=',start_date),('date_invoice','<=',end_date),('state','in',['open','paid'])])
        elif self.dat_type == 'purchases':
            get_partners = self.env['account.invoice'].sudo().search([('type','=','in_invoice'),('date_invoice','>=',start_date),('date_invoice','<=',end_date),('state','in',['open','paid'])])
        else:
            return True
        self.sch1_ids = False
        partners_ids = []
        for get_partner in get_partners:
            if not get_partner.partner_id.id in partners_ids:
                partners_ids.append(get_partner.partner_id.id)
        get_partners = self.env['res.partner'].sudo().browse(partners_ids)
        for partner in get_partners:
            sch1_vals = {
#                'dat_id': self.id,
                'company_id': self.company_id.id,
                'partner_id': partner.id,
                'of_month': self.of_month,
                'of_year': self.of_year,
                'dat_type': self.dat_type,
            }
            self.sudo().write({'sch1_ids': [[4,self.env['bir.generate.dat.sch1'].sudo().create(sch1_vals).id]]})
        

    @api.multi
    def action_generate(self):
        self.ensure_one()
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        if end_date >= datetime.datetime.now().date():
            raise UserError("Cannot generate unfinished month")
        path = str("/opt/odoo11/addons/user_subscription_v11c_on-premise/static/src/birdat/")
        if self.dat_type == 'sales':
            letter = 'S'
        elif self.dat_type == 'purchases':
            letter = 'P'
        else:
            return True
        filename = str(str(self.company_id.vat) + letter + str(self.of_month) + str(self.of_year) + ".DAT")
        with open((path + filename), 'w') as myfile:
            wr = csv.writer(myfile,)
            end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
            self.generate_sch1()
            total = 0
            total2 = 0
            total3 = 0
            total4 = 0
            total5 = 0
            total_tax = 0
            for sch1 in self.sch1_ids:
#            for sch1 in self.env['bir.generate.dat.sch1'].sudo().search([('dat_id','=',self.id)]):
                total = total + sch1.amount
                total2 = total2 + sch1.amount2
                total3 = total3 + sch1.amount3
                total4 = total4 + sch1.amount4
                total5 = total5 + sch1.amount5
                total_tax = total_tax+sch1.tax
            row = []
            row = ['H',letter,('"'+self.company_id.vat+'"'),('"'+self.company_id.name.upper()+'"'),'"'+str(self.company_id.lastname or '').upper()+'"','"'+str(self.company_id.firstname or '').upper()+'"','"'+str(self.company_id.middlename or '').upper()+'"','"'+str(self.company_id.tradename or '').upper()+'"','"'+self.strip_space(str((self.company_id.street2 or '') + ' ' + (self.company_id.street or '') + ' ' + (self.company_id.barangay or ''))).upper()+'"','"'+self.strip_space(str((self.company_id.district or '') + ' ' + (self.company_id.city or '') + ' ' + (self.company_id.zip or ''))).upper()+'"',str('{0:.2f}'.format(total)) if total > 0 else '0',str('{0:.2f}'.format(total2)) if total2 > 0 else '0',str('{0:.2f}'.format(total3)) if total3 > 0 else '0']
            if self.dat_type == 'purchases':
                row.extend([str('{0:.2f}'.format(total4)) if total4 > 0 else '0',str('{0:.2f}'.format(total5)) if total5 > 0 else '0'])
            row.append(str(total_tax))
            if self.dat_type == 'purchases':
                row.extend([str('{0:.2f}'.format(total_tax-self.non_creditable)) if total_tax-self.non_creditable > 0 else '0','{0:.2f}'.format(self.non_creditable) if self.non_creditable > 0 else '0'])
            row.extend([str(self.company_id.rdo or ''),str(end_date.strftime('%m/%d/%Y')),'12'])
            wr.writerow(row)
            for sch1_id in self.sch1_ids.sorted(key=lambda r: r.partner_id.name,reverse=False):
#            for sch1_id in self.env['bir.generate.dat.sch1'].sudo().search([('dat_id','=',self.id)]).sorted(key=lambda r: r.partner_id.name,reverse=False):
                row = ['D',letter,'"'+str(sch1_id.partner_id.vat.replace('-','') if sch1_id.partner_id.vat else '')+'"',('"'+sch1_id.partner_id.name.upper()+'"'),'','','"'+ self.strip_space(str(str(sch1_id.partner_id.street2 or '') + ' ' + str(sch1_id.partner_id.street or '') + ' ' + str(sch1_id.partner_id.barangay or ''))).upper()+'"','"'+self.strip_space(str(str(sch1_id.partner_id.district or '') + ' ' + str(sch1_id.partner_id.city or '') + ' ' + str(sch1_id.partner_id.zip or ''))).upper()+'"',str('{0:.2f}'.format(sch1_id.amount)) if sch1_id.amount > 0 else '0',str('{0:.2f}'.format(sch1_id.amount2)) if sch1_id.amount2 > 0 else '0',str('{0:.2f}'.format(sch1_id.amount3)) if sch1_id.amount3 > 0 else '0']
                if self.dat_type == 'purchases':
                    row.extend([str('{0:.2f}'.format(sch1_id.amount4)) if sch1_id.amount4 > 0 else '0',str('{0:.2f}'.format(sch1_id.amount5)) if sch1_id.amount5 > 0 else '0'])
                row.extend([str('{0:.2f}'.format(sch1_id.tax)) if sch1_id.tax > 0 else '0',str(sch1_id.company_id.vat),str(end_date.strftime('%m/%d/%Y'))])
                wr.writerow(row)
        encoded_string = ''
        if os.path.exists(path+filename):
            with open((path+filename), "r") as pdf:
                encoded_string = base64.b64encode(pdf.read().replace('"""','"').replace(',,,',',,,,').encode('utf-8'))
        attachment_obj = self.env['ir.attachment']
        attachment_data = {
            'name':  (self._name or '') + _(' (Scheme attachment)'),
            'datas_fname': filename,
            'datas' : encoded_string,
            'type' : 'binary',
            'description': self._name or _('No Description'),
            'res_model':self._name,
            'res_id': self.id,
        }
        attachment_id = attachment_obj.create(attachment_data)
        self.write({'generated_dat_file' : attachment_id.id})
        try:
            os.remove(path+filename)
        except Exception as e:
            pass
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/ir.attachment/" + str(attachment_id.id) + "/datas/" + self.generated_dat_file_name + "?download=true",
            'target': 'self'
        }
class BirGenerateDatSch1(models.TransientModel):
    _name = "bir.generate.dat.sch1"


    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')

    dat_id = fields.Many2one('bir.generate.pdf',string="Parent Form")
    dat_type = fields.Selection([('sales','Sales'),('purchases','Purchases')],string="Form")
    of_month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                          ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                          ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                          string='1. For the of Month')
    of_year = fields.Selection(get_years(), string='Year')
    company_id = fields.Many2one('res.company',string="Company")
    partner_id = fields.Many2one('res.partner',string="Customer")

    @api.one
    @api.depends('partner_id','of_month','of_year','company_id','dat_id')
    def _calc(self):
        start_date = datetime.date(int(self.of_year),int(self.of_month),1)
        end_date = datetime.date(int(self.of_year),int(self.of_month),calendar.monthrange(int(self.of_year), int(self.of_month))[1])
        total = 0
        total2 = 0
        total3 = 0
        total4 = 0
        total5 = 0
        total_tax = 0
        invoice_taxes = []
        if self.dat_type == 'sales':
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('invoice_id.partner_id','=',self.partner_id.id),('invoice_id.type','=','out_invoice'),('invoice_id.state','in',['open','paid'])])
        elif self.dat_type == 'purchases':
            invoice_taxes = self.env['account.invoice.tax'].sudo().search([('invoice_id.date_invoice','>=',start_date),('invoice_id.date_invoice','<=',end_date),('invoice_id.partner_id','=',self.partner_id.id),('invoice_id.type','=','in_invoice'),('invoice_id.state','in',['open','paid'])])
        for invoice_tax in invoice_taxes:
            if invoice_tax.base > 0:
                if self.dat_type == 'sales':
                    if 'exempt' in invoice_tax.tax_id.name.lower():
                        total = total + invoice_tax.base
                    elif 'zero' in invoice_tax.tax_id.name.lower() and 'rated' in invoice_tax.tax_id.name.lower():
                        total2 = total2 + invoice_tax.base
                    elif 'sales' in invoice_tax.tax_id.name.lower() and 'private' in invoice_tax.tax_id.name.lower():
                        total3 = total3 + invoice_tax.base
                    elif 'sales' in invoice_tax.tax_id.name.lower() and 'government' in invoice_tax.tax_id.name.lower():
                        total3 = total3 + invoice_tax.base
                    total_tax = total_tax + invoice_tax.amount_total
                elif self.dat_type == 'purchases':
                    if invoice_tax.amount_total >= 0:
                        if 'exempt' in invoice_tax.tax_id.name.lower():
                            total = total + invoice_tax.base
                        elif 'zero' in invoice_tax.tax_id.name.lower() and 'rated' in invoice_tax.tax_id.name.lower():
                            total2 = total2 + invoice_tax.base
                        elif 'service' in invoice_tax.tax_id.name.lower():
                            total3 = total3 + invoice_tax.base
                        elif 'capital goods' in invoice_tax.tax_id.name.lower() and 'other than' not in invoice_tax.tax_id.name.lower():
                            total4 = total4 + invoice_tax.base
                        elif 'capital goods' in invoice_tax.tax_id.name.lower() and 'other than' in invoice_tax.tax_id.name.lower():
                            total5 = total5 + invoice_tax.base
                        elif 'others' in invoice_tax.tax_id.name.lower():
                            total5 = total5 + invoice_tax.base
                        total_tax = total_tax + invoice_tax.amount_total
        self.amount = total
        self.amount2 = total2
        self.amount3 = total3
        self.amount4 = total4
        self.amount5 = total5
        self.tax = total_tax

    amount = fields.Monetary(string="Amount",compute="_calc",store=True)
    amount2 = fields.Monetary(string="Amount2",compute="_calc",store=True)
    amount3 = fields.Monetary(string="Amount3",compute="_calc",store=True)
    amount4 = fields.Monetary(string="Amount4",compute="_calc",store=True)
    amount5 = fields.Monetary(string="Amount5",compute="_calc",store=True)
    tax = fields.Monetary(string="Tax", compute="_calc",store=True)


