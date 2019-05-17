from odoo import api, fields, models

class AccountBillingGenerateDisconnect(models.TransientModel):
    _name = 'account.billing.generate.disconnect'
    
    @api.multi
    def generate(self):
        self.ensure_one()
        invoices = self.env['account.billing']._recurring_create_invoice()
        ids = []
        for invoice in invoices:
            ids.append(invoice.id)
        return self.env.ref('account_billing.report_account_invoice_bill_report').report_action(ids)
