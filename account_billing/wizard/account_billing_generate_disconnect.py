from odoo import api, fields, models
import datetime

class AccountBillingGenerateDisconnect(models.TransientModel):
    _name = 'account.billing.generate.disconnect'
    
    @api.multi
    def generate(self):
        self.ensure_one()
        invoice_ids = self.env['account.invoice'].sudo().search([('state','=','open'), ('billing_id','!=',False), ('billing_id.state', '=', 'open'), ('date_due','<',datetime.datetime.today().date())])
        if invoice_ids and len(invoice_ids)>0:
            return self.env.ref('account_billing.report_account_invoice_disconnect_report').report_action(ids)
        else
            raise UserError("There are no overdue invoices!")
