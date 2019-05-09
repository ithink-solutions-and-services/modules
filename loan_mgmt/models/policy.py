from odoo import fields, models, api, SUPERUSER_ID
import logging
import datetime

_logger = logging.getLogger(__name__)

class LoanMgmtPolicy(models.Model):
    _name = 'loan_mgmt.policy'

    name = fields.Char("Policy Name")
    type = fields.Selection([('max','Max Loan Amount'), ('gap', 'Gap Between Loans')], string="Policy Type", default="max", help="Max Loan Amount: Set Maximum Loan Amount\nGap Between Loans: Set number of days before applying for another loan")
    active = fields.Boolean(string="Active", default=True)
    max_loan_amount = fields.Float(string="Max Loan Amount")
    num_days = fields.Integer(string="Gap Between Loans")
    
    @api.depends('type')
    def _condition(self):
        for rec in self:
            if rec.type == 'max':
                rec.condition = str(rec.max_loan_amount) if rec.max_loan_amount else False
            elif rec.type == 'gap':
                rec.condition = (rec.num_days) if rec.num_days else False
    
    condition = fields.Char(string="Value", compute="_condition", store=True)
