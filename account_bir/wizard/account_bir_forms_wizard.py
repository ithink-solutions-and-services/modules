from odoo import fields, models, api


class AccountBirForms(models.TransientModel):
    _name = "account.bir.forms"
    
    account_bir_id = fields.Many2one('account.bir', string="BIR Form")
    
    @api.multi
    def select_form(self):
        self.ensure_one()
        return self.env.ref('self.account_bir_id.wizard_id')
