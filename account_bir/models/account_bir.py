from odoo import models, fields, api

class AccountBir(models.Model):
    _name = 'account.bir'
    
    name = fields.Char("BIR Form")
    code = fields.Char("Code")
    active = fields.Boolean("Active", default=True)
    wizard_id = fields.Char("Wizard ID")
