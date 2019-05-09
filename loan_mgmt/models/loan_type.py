from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)

class LoanMgmtLoanType(models.Model):
    _name = 'loan_mgmt.loan_type'

    name = fields.Char("Loan Type", help="Loan Type Name")
    active = fields.Boolean(string="Active", default=True)
    interest_type = fields.Selection([('flat','Flat'), ('reducing','Reducing')], string="Interest Type", default="flat", help="Flat: interest rate that is calculated on the full amount of the loan throughout its tenure without considering that monthly EMIs gradually reduce the principal amount\nReducing: interest rate that is calculated every month on the outstanding loan amount")
    interest_rate = fields.Float(string='Interest Rate', help="Rate of interest in decimal. Example: 35% = 0.35")
    disburse_method = fields.Selection([('cash','Cash'), ('check','Check')], string="Disbursement Method", default="cash", help="Method of Loan Amount Disbursement")
    interest_account_id = fields.Many2one('account.account', string="Interest Account")
    requirement_ids = fields.Many2many('loan_mgmt.requirement', string="Requirements", help="Requirements for this Loan Type")
    categ_ids = fields.Many2many('res.partner.categ', string="Allowed Partner Categories")
    disburse_journal_id = fields.Many2one('account.journal', string="Disbursement Sales Journal")
    disburse_cash_journal_id = fields.Many2one('account.journal', string="Disbursement Cash Journal")
    disburse_expense_account_id = fields.Many2one('account.account', string="Disbursement Expense Account")
    disburse_payable_account_id = fields.Many2one('account.account', string="Disbursement Payable Account")
    emi_journal_id = fields.Many2one('account.journal', string="EMI Sales Journal")
    emi_cash_journal_id = fields.Many2one('account.journal', string="EMI Cash Journal")
    emi_account_id = fields.Many2one('account.account', string="EMI Income Account")
    emi_receivable_account_id = fields.Many2one('account.account', string="EMI Receivable Account")
