from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class WebsiteConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    company_logo = fields.Binary(related='company_id.logo', string="Company Logo",
                                 help="This field holds the image used for the Company Logo")
    company_name = fields.Char(related="company_id.name", string="Company Name")
    company_website = fields.Char(related='company_id.website')
    favicon = fields.Binary(string="Favicon", related="company_id.favicon", help="This field holds the image used to display a favicon on the system")


    # Sample Error Dialogue
    @api.multi
    def error(self):
        raise ValueError

    # Sample Warning Dialogue
    @api.multi
    def warning(self):
        raise Warning(_("This is a Warning"))

