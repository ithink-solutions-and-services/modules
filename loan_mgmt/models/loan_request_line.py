from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)

class LoanMgmtLoanRequestLine(models.Model):
    _name = 'loan_mgmt.loan_request.line'
    _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    loan_request_id = fields.Many2one('loan_mgmt.loan_request', string="Loan Request")
    name = fields.Integer("Number")
    from_date = fields.Date('Date From')
    to_date = fields.Date('Date To')
    amount = fields.Float('Amount')
    interest = fields.Float('Interest')

    @api.depends('amount', 'interest')
    def _emi(self):
        for rec in self:
            rec.emi = rec.amount + rec.interest

    emi = fields.Float(string="EMI", compute="_emi", store=True)
    
    @api.depends('invoice_id', 'invoice_id.state')
    def _state(self):
        for rec in self:
            state = 'draft'
            if rec.invoice_id:
                state = 'invoiced'
            if rec.invoice_id.state == 'open':
                state = 'open'
            if rec.invoice_id.state == 'paid':
                state = 'paid'
            rec.state = state
    
    state = fields.Selection([('draft','Draft'),('invoiced','Invoiced'), ('open', 'Validated'), ('paid','Paid')], string="Status", index=True, default='draft', track_visibility='onchange', copy=False, compute="_state", store=True)
    partner_id = fields.Many2one(related="loan_request_id.partner_id")
    partner_categ_id = fields.Many2one(related="loan_request_id.partner_categ_id")
    loan_type_id = fields.Many2one(related="loan_request_id.loan_type_id")
    invoice_id = fields.Many2one('account.invoice', string="Invoice")
    
    @api.one
    def _invoiced(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        from_date = fields.Date.from_string(self.from_date).strftime('%b %d %Y')
        to_date = fields.Date.from_string(self.to_date).strftime('%b %d %Y')
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'type': 'out_invoice',
            'date_invoice': datetime.datetime.today().date(),
            'journal_id': self.loan_type_id.emi_journal_id.id,
            'state': 'draft',
            'account_id': self.loan_type_id.emi_receivable_account_id.id,
            'loan_payment': True,
            'loan_request_id': self.loan_request_id.id
        }
        invoice = invoice_obj.create(invoice_vals)
        self.write({
            'state': 'invoiced',
            'invoice_id': invoice.id
        })
        invoice_line_vals = {
            'invoice_id': self.invoice_id.id,
            'name': 'Principal: ' + from_date + ' - ' + to_date,
            'quantity': 1,
            'price_unit': self.amount,
            'account_id': self.loan_type_id.emi_account_id.id
        }
        invoice_line_obj.create(invoice_line_vals)
        invoice_line_vals = {
            'invoice_id': self.invoice_id.id,
            'name': 'Interest: ' + from_date + ' - ' + to_date,
            'quantity': 1,
            'price_unit': self.interest,
            'account_id': self.loan_type_id.interest_account_id.id
        }
        invoice_line_obj.create(invoice_line_vals)
        return True
        
    @api.multi
    def button_invoiced(self):
        for rec in self:
            rec._invoiced()
        return True
        
    @api.one
    def _validate(self):
        self.invoice_id.action_invoice_open()
        return True
        
    @api.multi
    def button_validate(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_tree1')
        result = {
            'name': action.name,
            'type': action.type,
            'target': 'new',
            'res_model': 'account.invoice',
        }
        invoice = self.invoice_id
        if invoice.id:
            result['views'] = [(self.sudo().env.ref('account.invoice_form').id, 'form')]
            result['res_id'] = invoice.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result
        return True
        
    @api.multi
    def button_pay(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_tree1')
        result = {
            'name': action.name,
            'type': action.type,
            'target': 'new',
            'res_model': 'account.invoice',
        }
        invoice = self.invoice_id
        if invoice.id:
            result['views'] = [(self.sudo().env.ref('account.invoice_form').id, 'form')]
            result['res_id'] = invoice.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result
#        action = self.env.ref('account.action_account_invoice_payment')
        #return {
            #'name': action.name,
            #'type': action.type,
            #'view_id': action.view_id.id,
            #'view_mode': action.view_mode,
            #'target': 'new',
            #'res_model': action.res_model,
            #'context': {'default_invoice_ids': [4, self.invoice_id.id, None], 'default_amount': self.emi, 'amount': self.emi, 'default_loan_request_id': self.loan_request_id.id, 'loan_request_id': self.loan_request_id.id, 'default_loan_payment': True, 'loan_payment': True, 'payment_type': 'inbound', 'default_payment_type': 'inbound'}
        #}
    