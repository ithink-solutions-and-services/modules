from odoo import api, fields, models

class AccountBillingGenerate(models.TransientModel):
    _name = 'account.billing.generate'
    
    @api.multi
    def generate(self):
        self.ensure_one()
        invoices = self.env['account.billing'].generate_print_invoices()
        ids = []
        for invoice in invoices:
            ids.append(invoice.id)
        return self.env.ref('account.account_invoices').report_action(ids)
