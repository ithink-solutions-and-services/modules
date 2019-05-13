from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
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
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        for rec in self:
            if rec.template_id and rec.state == 'draft':
                rec.recurring_type = rec.template_id.recurring_type
                rec.recurring_type_interval = rec.template_id.recurring_type_interval
                rec.billing_line_ids.sudo().unlink()
                for line_id in rec.template_id.template_line_ids:
                    vals = {
                        'billing_id': rec.id,
                        'product_id': line_id.product_id.id,
                        'quantity': line_id.quantity
                    }
                    self.env['account.billing.line'].sudo().create(vals)
    
    
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
    def set_open(self):
        for rec in self:
            rec.write({'state': 'open', 'date': False})
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
            rec.write({'state': 'close', 'date': fields.Date.from_string(fields.Date.today())})
        return True
    
    @api.multi
    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Billing %s!") % self.name)

        company_id = self.partner_id.company_id

        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '', ))

        next_date = fields.Date.from_string(self.recurring_next_date)
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        end_date = next_date + relativedelta(**{periods[self.recurring_type]: self.recurring_interval})
        end_date = end_date - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
        # DO NOT FORWARDPORT
        format_date = self.env['ir.qweb.field.date'].value_to_html

        return {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': company_id.currency_id.id,
            'journal_id': journal.id,
            'origin': self.name,
            'fiscal_position_id': fpos_id,
            'payment_term_id': self.partner_id.property_payment_term_id.id,
            'company_id': company.id,
            'comment': _("This invoice covers the following period: %s - %s") % (format_date(fields.Date.to_string(next_date), {}), format_date(fields.Date.to_string(end_date), {})),
            'user_id': self.user_id.id,
            'billing_id': self.id,
            'billing_period': self.billing_period_id.id,
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
            'name': line.name + " - " + self.billing_period.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.analytic_account_id.id,
            'price_unit': line.price_unit or 0.0,
            'quantity': line.quantity,
            'product_id': line.product_id.id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)],
        }

    @api.multi
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.recurring_invoice_line_ids]

    @api.multi
    def _prepare_invoice(self):
        invoice = self._prepare_invoice_data()
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'])
        return invoice
    
class AccountBillingLine(models.Model):
    _name = 'account.billing.line'
    
    billing_id = fields.Many2one('account.billing', string="Linked to Billing")
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
    
class AccountBillingPeriod(models.Model):
    _name = 'account.billing.period'
    
    name = fields.Char("Billing Period")
    date_start = fields.Date("Date Start")
    date_end = fields.Date("Date End")
    
class AccountBillingTemplate(models.Model):
    _name = 'account.billing.template
    
    name = fields.Char("Template Name")
    journal_id = fields.Many2one('account.jounal', string="Sales Journal")
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
                                        
