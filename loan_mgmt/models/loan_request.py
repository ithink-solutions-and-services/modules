from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class LoanMgmtLoanRequest(models.Model):
    _name = 'loan_mgmt.loan_request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Loan Request #")
    partner_id = fields.Many2one('res.partner', string="Customer", help="Loan Requester/Lendee")
    partner_categ_id = fields.Many2one(related="partner_id.categ_id")
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user and self.env.user.id or False)
    applied_date = fields.Date(string="Applied Date", help="Date of loan application")
    approved_date = fields.Date(string="Approved Date", help="Date of Loan Approval")
    loan_type_id = fields.Many2one('loan_mgmt.loan_type', string='Loan Type')
    principal_amount = fields.Float('Principal Amount')
    interest_type = fields.Selection(related="loan_type_id.interest_type")
    duration = fields.Integer('Duration', help="Number of months")
    interest_rate = fields.Float(related="loan_type_id.interest_rate")
    loan_line_ids = fields.One2many('loan_mgmt.loan_request.line', 'loan_request_id', string="Loan Lines")

    @api.depends('loan_line_ids', 'loan_line_ids.amount', 'loan_line_ids.interest', 'loan_line_ids.emi')
    def _total_loan(self):
        for rec in self:
            total_loan = 0
            total_interest = 0
            for line in rec.loan_line_ids:
                total_loan = total_loan + line.emi
                total_interest = total_interest + line.interest
            rec.total_loan = total_loan
            rec.total_interest = total_interest

    total_loan = fields.Float(string="Total Loan", compute="_total_loan", store=True)
    total_interest = fields.Float(string="Total Interest", compute="_total_loan", store=True)

    @api.depends('payment_ids', 'payment_ids.amount')
    def _total_payments(self):
        for rec in self:
            total_payments = 0
            for payment in rec.payment_ids:
                if payment.partner_type == 'customer':
                    total_payments = total_payments + payment.amount
            rec.total_payments = total_payments
    
    payment_ids = fields.One2many('account.payment', 'loan_request_id', string="Payments")
    total_payments = fields.Float(string="Received from Partner", compute="_total_payments", store=True)
    
    @api.depends('total_payments', 'total_loan')
    def _balance(self):
        for rec in self:
            rec.balance = rec.total_loan - rec.total_payments
        
    balance = fields.Float(string="Balance", compute="_balance", store=True)
    requirement_ids = fields.Many2many(related="loan_type_id.requirement_ids")
    policy_ids = fields.Many2many(related="partner_id.policy_ids")
    state = fields.Selection([('draft','Draft'), ('applied','Applied'), ('approved','Approved'), ('disbursed','Disbursed')], string="Status", index=True, default='draft', track_visibility='onchange', copy=False)
    disburse_date = fields.Date('Disbursement Date')
    bill_id = fields.Many2one('account.invoice', string="Vendor Bill")
    computed = fields.Boolean()

    
    @api.one
    def _applied(self):
        last_loan = self.env['loan_mgmt.loan_request'].sudo().search([('partner_id','=',self.partner_id.id), ('state','!=', 'closed')])
        if last_loan and len(last_loan)>0:
            raise UserError("There is an existing loan for this customer")
        limit = 0
        if self.policy_ids and len(self.policy_ids)>0:
            for policy in self.policy_ids:
                if policy.type == 'gap':
                    if policy.num_days > limit:
                        limit = policy.num_days
        if limit > 0:
            last_loan = self.env['loan_mgmt.loan_request'].sudo().search([('partner_id','=',self.partner_id.id), ('state','=', 'closed')], order="closed_date desc")
            if last_loan and len(last_loan)>0:
                allow_date = fields.Date.from_string(last_loan[0].closed_date) + relativedelta(days=limit+1)
                if datetime.datetime.today().date < allow_date:
                    raise UserError("This customer can only apply for a loan starting on " + allow_date.strftime("%B %d, %Y"))
                
        self.write({
            'state': 'applied',
            'name': self.env['ir.sequence'].sudo().next_by_code('loan_mgmt.loan_request'),
            'applied_date': datetime.datetime.today().date()
        })
        return True

    @api.one
    def _approved(self):
        self.write({
            'state': 'approved',
            'approved_date': datetime.datetime.today().date()
        })
        return True
        
    @api.one
    def _disbursed(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'type': 'in_invoice',
            'date_invoice': datetime.datetime.today().date(),
            'journal_id': self.loan_type_id.disburse_journal_id.id,
            'state': 'draft',
            'account_id': self.loan_type_id.disburse_payable_account_id.id,
            'loan_request_id': self.id,
            'disbursement': True
        }
        invoice = invoice_obj.create(invoice_vals)
        self.write({
            'state': 'disbursed',
            'disburse_date': datetime.datetime.today().date(),
            'bill_id': invoice.id
        })
        invoice_line_vals = {
            'invoice_id': self.bill_id.id,
            'name': 'Loan Disbursement',
            'quantity': 1,
            'price_unit': self.principal_amount,
            'account_id': self.loan_type_id.disburse_expense_account_id.id
        }
        invoice_line_obj.create(invoice_line_vals)
        return True

    @api.one
    def _compute_monthly(self):
        if self.loan_line_ids and len(self.loan_line_ids)>1:
            self.loan_line_ids.sudo().unlink()
        date = fields.Date.from_string(self.disburse_date)
        amount = self.principal_amount/self.duration
        for i in range(0, self.duration):
            vals = {
                'loan_request_id': self.id,
                'name': i+1,
                'from_date': date,
                'amount': amount,
                'interest': amount*self.interest_rate,
                'state': 'draft'
            }
            date = date + relativedelta(months=1)
            vals['to_date'] = date
            self.env['loan_mgmt.loan_request.line'].create(vals)
        self.computed = True
        return True
        
    @api.multi
    def button_applied(self):
        for rec in self:
            rec._applied()
        return True
        
    @api.multi
    def button_approved(self):
        for rec in self:
            rec._approved()
        return True

    @api.multi
    def button_disbursed(self):
        for rec in self:
            rec._disbursed()
        return True
        
    @api.multi
    def button_compute_monthly(self):
        for rec in self:
            rec._compute_monthly()
        return True

    @api.model
    def create(self, vals):
        limit = 0
        try:
            partner = self.env['res.partner'].sudo().browse(vals['partner_id'])
            policy_ids = partner.categ_id.policy_ids.ids
            policies = self.env['loan_mgmt.policy'].sudo().search([('id','in',policy_ids), ('type','=','max')])
            if policies and len(policies) >= 1:
                limit = 0
                for policy in policies:
                    if policy.max_loan_amount > limit:
                        limit = policy.max_loan_amount
        except Exception as e:
            pass
        if limit != 0 and vals['principal_amount'] > limit:
            raise UserError("This customer has a maximum limit of " + str(limit))
            
        try:
            if self.categ_id.id not in self.loan_type_id.categ_ids.ids:
                raise UserError("This customer cannot apply for loan type " + str(self.loan_type_id.name))
        except:
            pass
            
        res = super(LoanMgmtLoanRequest, self).create(vals)
        return res
        
    @api.multi
    def open_bill(self):
        invoices = self.env['account.invoice'].browse(self.bill_id.id)
        action = self.env.ref('account.action_invoice_tree2')
        list_view_id = self.env.ref('account.invoice_supplier_tree').id
        form_view_id = self.env.ref('account.invoice_supplier_form').id
        result = {
            'name': action.name,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            #'target': 'new',
            'target': 'current',
            'res_model': 'account.invoice',
        }
        if len(invoices) > 1:
            result['domain'] = "[('id','in',%s)]" % invoices.ids
        elif len(invoices) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
