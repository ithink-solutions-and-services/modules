from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ResPartnerCateg(models.Model):
    _name = 'res.partner.categ'

    name = fields.Char('Category')
    active = fields.Boolean('Active', default=True)
    policy_ids = fields.Many2many('loan_mgmt.policy', string="Policies", help="Policies applicable to this partner category")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    categ_id = fields.Many2one('res.partner.categ', string="Category", help="Partner Category that will define allowed Loan Types")
    policy_ids = fields.Many2many(related="categ_id.policy_ids")
    loan_customer = fields.Boolean("Loan Customer?")