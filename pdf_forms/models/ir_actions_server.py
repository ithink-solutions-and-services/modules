from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    is_pdf_form = fields.Boolean("Used by PDF Forms module?")
    pdf_form_id = fields.Many2one('pdf_forms.form', string="Related PDF Form")
