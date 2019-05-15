from odoo import models, fields, api, _
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import logging
_logger = logging.getLogger(__name__)

class AccountBilling(models.Model):
    _name = 'account.billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char("Billing #")
    partner_id = fields.Many2one('res.partner', string="Customer")
    state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'On Hold'),
                              ('close', 'Closed'), ('cancel', 'Cancelled')],
                             string='Status', required=True, track_visibility='onchange', copy=False, default='draft')
    date_start = fields.Date(string='Date Started', default=fields.Date.today)
    date_closed = fields.Date(string='Date Closed', track_visibility='onchange')
    billing_line_ids = fields.One2many('account.billing.line', 'billing_id', string="Billing Lines")
    billing_period_id = fields.Many2one('account.billing.period', string="Billing Period")
    
    @api.depends('partner_id')
    def _company_id(self):
        for rec in self:
            rec.company_id = rec.partner_id.company_id.id
    
    company_id = fields.Many2one('res.company', string="Company", compute="_company_id", store=True)
    
    @api.model
    def create(self, vals):
        res = super(AccountBilling, self).create(vals)
        res.name = self.env['ir.sequence'].next_by_code('account.billing')
        return res
    
    @api.depends('billing_line_ids')
    def _total(self):
        for rec in self:
            rec.total_amount = sum(line.subtotal for line in rec.billing_line_ids)
    
    total_amount = fields.Float("Recurring Total", compute="_total", store=True)
    recurring_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'),
                                            ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ],
                                           string='Recurrency',
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', track_visibility='onchange')
    recurring_type_interval = fields.Integer(string="Repeat Every", help="Repeat every (Days/Week/Month/Year)", default=1, track_visibility='onchange')
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.")
    suspend_reason = fields.Text("Reason for Suspension/Closure/Cancellation", track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Assigned User', track_visibility='onchange')
    invoice_ids = fields.One2many('account.invoice', 'billing_id', string="Invoices")
    template_id = fields.Many2one('account.billing.template', string="Billing Template")
    reading_ids = fields.One2many('account.billing.reading', 'billing_id', string="Water Meter Readings")
    
    @api.multi
    def apply_draft_readings(self):
        self.ensure_one()
        rec = self
        water_line_id = self.env['account.billing.line'].sudo().search([('billing_id','=',rec.id), ('product_id.water_product','=',True)], limit=1)
        reading_ids = rec.reading_ids.filtered( lambda r: r.state == "draft")
        total_cu_m = sum(reading_ids.mapped('cu_meter'))
        total_amount = 0
        if total_cu_m <= water_line_id.product_id.cu_m_fixed:
            total_amount = water_line_id.product_id.cu_m_fixed_price
        else:
            total_amount = water_line_id.product_id.cu_m_fixed_price + (water_line_id.product_id.cu_m_exceed_price * (total_cu_m-water_line_id.product_id.cu_m_fixed))
        water_line_id.unit_price = total_amount
        water_line_id.prev_cu_m = water_line_id.cu_m
        water_line_id.cu_m = total_cu_m
        water_line_id._product()
        rec._total()
        for reading_id in reading_ids:
            reading_id.write({'state': 'applied'})
        return True

    @api.onchange('template_id')
    def _on_change_template(self):
        for rec in self:
           if rec.template_id:
               billing_line_ids = []
               for line in rec.template_id.template_line_ids:
                   product = line.product_id
                   billing_line_ids.append((0, 0, {
                       'product_id': line.product_id.id,
                       'quantity': line.quantity,
                      'price_unit': product.price,
                   }))
               rec.billing_line_ids = billing_line_ids
               rec.recurring_type_interval = self.template_id.recurring_type_interval
               rec.recurring_type = self.template_id.recurring_type
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)
            
    invoice_count = fields.Integer(compute='_compute_invoice_count', store=True)
    
    @api.multi
    def action_open_invoices(self):
        self.ensure_one()
        invoices = self.env['account.invoice'].search([('billing_id', '=', self.id)])
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.invoice",
            "views": [[self.env.ref('account.invoice_tree').id, "tree"],
                      [self.env.ref('account.invoice_form').id, "form"]],
            "domain": [["id", "in", invoices.ids]],
            "context": {"create": False},
            "name": "Invoices",
        }
    
    @api.multi
    def set_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
        return True
    
    @api.multi
    def set_open(self):
        for rec in self:
            rec.write({'state': 'open', 'date_closed': False})
        return True

    @api.multi
    def set_pending(self):
        for rec in self:
            rec.write({'state': 'pending'})
        return True

    @api.multi
    def set_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
        return True

    @api.multi
    def set_close(self):
        for rec in self:
            rec.write({'state': 'close', 'date_closed': fields.Date.from_string(fields.Date.today())})
        return True
    
    @api.multi
    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Billing %s!") % self.name)

        company = self.partner_id.company_id

        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '', ))

        next_date = fields.Date.from_string(self.recurring_next_date)
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        end_date = next_date + relativedelta(**{periods[self.recurring_type]: self.recurring_type_interval})
        end_date = end_date - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
        # DO NOT FORWARDPORT
        format_date = self.env['ir.qweb.field.date'].value_to_html

        return {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': company.currency_id.id,
            'journal_id': journal.id,
            'origin': self.name,
            'fiscal_position_id': fpos_id,
            'payment_term_id': self.partner_id.property_payment_term_id.id,
            'company_id': company.id,
            'comment': _("This invoice covers the following period: %s - %s") % (format_date(fields.Date.to_string(next_date), {}), format_date(fields.Date.to_string(end_date), {})),
            'user_id': self.user_id.id,
            'billing_id': self.id,
            'billing_period_id': self.billing_period_id.id,
            'billing_template_id': self.template_id.id
        }

    @api.multi
    def _prepare_invoice_line(self, line, fiscal_position):
        self.ensure_one()
        company = self.partner_id.company_id

        account = line.product_id.property_account_income_id
        if not account:
            account = line.product_id.categ_id.property_account_income_categ_id
        account_id = fiscal_position.map_account(account).id

        tax = line.product_id.taxes_id.filtered(lambda r: r.company_id == company)
        tax = fiscal_position.map_tax(tax)

        return {
            'name': line.name + " - " + self.billing_period_id.name,
            'account_id': account_id,
            'price_unit': line.unit_price or 0.0,
            'quantity': line.quantity,
            'product_id': line.product_id.id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)],
        }

    @api.multi
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.billing_line_ids]

    @api.multi
    def _prepare_invoice(self):
        invoice = self._prepare_invoice_data()
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'])
        return invoice
    
    @api.multi
    def recurring_invoice(self):
        self.ensure_one()
        self._recurring_create_invoice()
        return self.action_open_invoices()
    
    @api.returns('account.invoice')
    def _recurring_create_invoice(self, automatic=False):
        AccountInvoice = self.env['account.invoice']
        BillingPeriod = self.env['account.billing.period']
        invoices = []
        current_date = fields.Date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        domain = [('id', 'in', self.ids)] if self.ids else [('recurring_next_date', '<=', current_date), ('state', '=', 'open')]
        sub_data = self.search_read(fields=['id', 'company_id'], domain=domain)
        for company_id in set(data['company_id'][0] for data in sub_data):
            sub_ids = map(lambda s: s['id'], filter(lambda s: s['company_id'][0] == company_id, sub_data))
            subs = self.with_context(company_id=company_id, force_company=company_id).browse(sub_ids)
            for sub in subs:
                try:
                    sub.apply_draft_readings()
                    invoices.append(AccountInvoice.create(sub._prepare_invoice()))
                    invoices[-1].message_post_with_view('mail.message_origin_link',
                     values={'self': invoices[-1], 'origin': sub},
                     subtype_id=self.env.ref('mail.mt_note').id)
                    invoices[-1].compute_taxes()
                    next_date = fields.Date.from_string(sub.recurring_next_date or current_date)
                    rule, interval = sub.recurring_type, sub.recurring_type_interval
                    new_date = next_date + relativedelta(**{periods[rule]: interval})
                    new_date_first_day = BillingPeriod.get_date_first_day(new_date)
                    new_date_last_day = BillingPeriod.get_date_last_day(new_date)
                    next_billing_period = BillingPeriod.search([('date_start','=',new_date_first_day),('date_end','=',new_date_last_day)])
                    if not next_billing_period:
                        next_billing_period = BillingPeriod.create({
                            'name': str(calendar.month_name[new_date.month]) + " " + str(new_date_first_day.day) + " - " + str(new_date_last_day.day) + ", " + str(new_date.year),
                            'date_start': new_date_first_day,
                            'date_end': new_date_last_day
                        })
                    sub.write({'recurring_next_date': new_date, 'billing_period_id': next_billing_period.id})
                    if automatic:
                        self.env.cr.commit()
                except Exception:
                    if automatic:
                        self.env.cr.rollback()
                        _logger.exception('Fail to create recurring invoice for subscription %s', sub.code)
                    else:
                        raise
        self._total()
        return invoices
    
    @api.model
    def generate_print_invoices(self):
        #return self.env.ref('account_billing.report_soa_report').report_action(self._recurring_create_invoice())
        invoices = self._recurring_create_invoice()
        ids = []
        for invoice in invoices:
            ids.append(invoice.id)
        invoice_ids = self.env['account.invoice'].browse(ids)
        return self.env.ref('account.account_invoices').report_action(invoice_ids)
    
class AccountBillingLine(models.Model):
    _name = 'account.billing.line'
    
    name = fields.Char("Name", compute="_product", store=True)
    billing_id = fields.Many2one('account.billing', string="Linked to Billing")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float('Quantity', default=1)
    cu_m = fields.Float("Cubic Meters")
    prev_cu_m = fields.Float("Previous Cubic Meters")
    
    @api.depends('product_id', 'quantity')
    def _product(self):
        for rec in self:
            unit_price = 0
            subtotal = 0
            if rec.product_id:
                unit_price = rec.product_id.lst_price if rec.unit_price == 0 else rec.unit_price
                tax_price = 0
                for tax in rec.product_id.taxes_id:
                    if tax.amount_type == 'percent':
                        tax_price = tax_price + unit_price * (tax.amount/100)
                rec.unit_price = unit_price
                rec.taxed_price = unit_price + tax_price
                rec.subtotal = rec.unit_price * rec.quantity
                name = rec.product_id.display_name
                if rec.product_id.description_sale:
                    name += '\n' + rec.product_id.description_sale
                rec.name = name
    
    unit_price = fields.Float('Unit Price(non-VAT)', compute="_product", store=True)
    taxed_price = fields.Float('Taxed Price', compute="_product", store=True)
    subtotal = fields.Float('Subtotal', compute="_product", store=True)
    
class AccountBillingPeriod(models.Model):
    _name = 'account.billing.period'
    
    def get_date_first_day(self, get_date):
        if get_date.day > 25:
            get_date += datetime.timedelta(7)
        return get_date.replace(day=1)

    def get_date_last_day(self, get_date):
        return get_date.replace(day=calendar.monthrange(get_date.year,get_date.month)[1])    
    
    name = fields.Char("Billing Period")
    date_start = fields.Date("Date Start")
    date_end = fields.Date("Date End")
    
class AccountBillingTemplate(models.Model):
    _name = 'account.billing.template'
    
    name = fields.Char("Template Name")
    journal_id = fields.Many2one('account.journal', string="Sales Journal")
    template_line_ids = fields.One2many('account.billing.template.line', 'template_id', string="Template Lines")
    recurring_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'),
                                            ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ],
                                           string='Recurrency',
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', track_visibility='onchange')
    recurring_type_interval = fields.Integer(string="Repeat Every", help="Repeat every (Days/Week/Month/Year)", default=1, track_visibility='onchange')
    
class AccountBillingTemplateLine(models.Model):
    _name = 'account.billing.template.line'
    
    template_id = fields.Many2one('account.billing.template', string="Linked to Template")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float('Quantity', default=1)
    
    @api.depends('product_id', 'quantity')
    def _product(self):
        for rec in self:
            unit_price = 0
            subtotal = 0
            if rec.product_id:
                unit_price = rec.product_id.lst_price
                tax_price = 0
                for tax in rec.product_id.taxes_id:
                    if tax.amount_type == 'percent':
                        tax_price = tax_price + unit_price * (tax.amount/100)
                rec.unit_price = unit_price
                rec.taxed_price = unit_price + tax_price
                rec.subtotal = rec.unit_price * rec.quantity
    
    unit_price = fields.Float('Unit Price(non-VAT)', compute="_product", store=True)
    taxed_price = fields.Float('Taxed Price', compute="_product", store=True)
    subtotal = fields.Float('Subtotal', compute="_product", store=True)
    
class AccountBillingReading(models.Model):
    _name = 'account.billing.reading'    
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    cu_meter = fields.Float("Cubic Meter")
    billing_id = fields.Many2one('account.billing', string="Linked to Billing")
    user_id = fields.Many2one('res.users', "Meter Reader", default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'New'), ('applied', 'Applied in Billing'), ('cancel', 'Cancelled')],
                             string='Status', required=True, track_visibility='onchange', copy=False, default='draft')  
    create_date_custom = fields.Date("Create Date", default=datetime.datetime.today().date())
