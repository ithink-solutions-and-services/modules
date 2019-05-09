from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    loan_request_id = fields.Many2one('loan_mgmt.loan_request', string="Loan Request")
    disbursement = fields.Boolean('Is Disbursement?')
    disburse_cash_journal_id = fields.Many2one(related="loan_request_id.loan_type_id.disburse_cash_journal_id")
    loan_payment = fields.Boolean('Is Loan Payment?')
    loan_cash_journal_id = fields.Many2one(related="loan_request_id.loan_type_id.emi_cash_journal_id")