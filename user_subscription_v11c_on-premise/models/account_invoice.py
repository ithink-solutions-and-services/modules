from odoo import models, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def print_2307(self):
        self.ensure_one()
        return self.env.ref('user_subscription_v11c_on-premise.report_bir_2307_custom_report').report_action(self)
