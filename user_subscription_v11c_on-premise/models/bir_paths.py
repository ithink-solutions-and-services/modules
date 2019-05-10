from odoo import models, fields, api


class BirPaths(models.Model):
    _name = 'bir.paths'

    @api.depends('path','filename')
    def _get_name(self):
        for rec in self:
            rec.name = (rec.path + "/" + rec.filename) if rec.path and rec.filename else False

    name = fields.Char(string="Full Path",compute="_get_name",store=True)
    path = fields.Char(string="File Path", default="/opt/odoo11/addons/user_subscription_v11c_on-premise/static/src/birforms")
    filename = fields.Char(string="File Name")
