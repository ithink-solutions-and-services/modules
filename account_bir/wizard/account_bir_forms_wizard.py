from odoo import fields, models, api


class AccountBirForms(models.TransientModel):
    _name = "account.bir.forms"
    
    account_bir_id = fields.Many2one('account.bir', string="BIR Form")
    
    @api.multi
    def select_form(self):
        self.ensure_one()
        action = self.env.ref(self.account_bir_id.wizard_id)
        return {
            'name': action.name,
            'type': action.type,
            'target': 'new',
            'view_type': 'form',
            'view_mode': action.view_mode,
        }
