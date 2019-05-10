from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    barangay = fields.Char("Barangay")
    district = fields.Char("District/Municipality")
    rdo = fields.Char("RDO Code")
    branch_code = fields.Char(string="Branch Code", default="0000")
    line_of_business = fields.Char("Line of Business")
    taxpayer_classification = fields.Selection([('ind','Individual'),('corp','Non-Individual')],string="Taxpayer Classification")
    category_of_withholding = fields.Selection([('private','Private'),('government','Government')],string="Category of Withholding Agent")
    foreign_address = fields.Char("Foreign Address")
    foreign_zip = fields.Char("Foreign Zip Code")

    def strip_space(self, string):
        return " ".join(string.split() if string != False else '')


#    @api.depends('firstname','middlename','lastname')
#    def _get_name(self):
#        for rec in self:
#            rec.name = self.concat_name(rec.firstname,rec.middlename,rec.lastname) if not rec.is_company else self.strip_space(rec.registered_name)

    firstname = fields.Char(string="Firstname")
    middlename = fields.Char(string="Middlename")
    lastname = fields.Char(string="Lastname")
    tradename = fields.Char(string="Trade Name")
#    def concat_name(self, first, middle, last):
#        return self.strip_space(self.strip_space(first if first else " ") + " " + self.strip_space(middle if middle else " ") + " " + self.strip_space(last if last else " "))


    @api.model
    def im_search(self, name, limit=20):
        """ Search partner with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the partner name to search
            :param limit : the limit of result to return
        """
        # This method is supposed to be used only in the context of channel creation or
        # extension via an invite. As both of these actions require the 'create' access
        # right, we check this specific ACL.

        if self.env['mail.channel'].check_access_rights('create', raise_exception=False):
            name = '%' + name + '%'
            excluded_partner_ids = [self.env.user.partner_id.id]
            self.env.cr.execute("""
                SELECT
                    U.id as user_id,
                    P.id as id,
                    P.name as name,
                    CASE WHEN B.last_poll IS NULL THEN 'offline'
                         WHEN age(now() AT TIME ZONE 'UTC', B.last_poll) > interval %s THEN 'offline'
                         WHEN age(now() AT TIME ZONE 'UTC', B.last_presence) > interval %s THEN 'away'
                         ELSE 'online'
                    END as im_status
                FROM res_users U
                    JOIN res_partner P ON P.id = U.partner_id
                    LEFT JOIN bus_presence B ON B.user_id = U.id
                WHERE P.name ILIKE %s
                    AND P.id NOT IN %s
                    AND U.active = 't'
                    AND U.id != %s
                LIMIT %s
            """, ("%s seconds" % DISCONNECTION_TIMER, "%s seconds" % AWAY_TIMER, name, tuple(excluded_partner_ids), SUPERUSER_ID,limit))
            return self.env.cr.dictfetchall()
        else:
            return {}
