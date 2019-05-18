from odoo import api, fields, models

class AccountBillingGenerate(models.TransientModel):
    _name = 'account.billing.generate'
    
    @api.multi
    def generate(self):
        self.ensure_one()
        invoices = self.env['account.billing']._recurring_create_invoice()
        ids = []
        for invoice in invoices:
            invoice.action_open_invoice()
            ids.append(invoice.id)
        if len(ids)>0:
            return self.env.ref('account_billing.report_account_invoice_bill_report').report_action(ids)
        else:
            return True
