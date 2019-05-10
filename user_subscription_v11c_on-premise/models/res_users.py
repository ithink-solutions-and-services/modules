# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

duration_type = "days"
duration_count = 7

class ResUsersToken(models.Model):
    _name = "res.users.token"

    user_id = fields.Many2one("res.users")
    name = fields.Char("Token")


class ResUsers(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in System')],
        'Notification Management', required=True, default='email',
        help="Policy on how to handle Chatter notifications:\n"
             "- Emails: notifications are sent to your email\n"
             "- System: notifications appear in your System Inbox")
    sub_type = fields.Selection([('trial','Trial'),('activated','Activated')],string="User")
    expiry_date = fields.Date("Expiry Date")
    token_ids = fields.One2many('res.users.token','user_id',string="Tokens")
    first_notice = fields.Boolean(string='First Notice',default=False)
    second_notice = fields.Boolean(string='Second Notice',default=False)
    renew_request = fields.Boolean(string='Renew Requested',default=False)

    def cron_expired_accounts(self):
        users_to_remind = self.env['res.users'].sudo().search([('id','!=', SUPERUSER_ID),('active','=',True),('expiry_date','!=',False)])
        for user_to_remind in users_to_remind:
            days_remaining = (fields.Date.from_string(user_to_remind.expiry_date) - datetime.datetime.now().date()).days
            if days_remaining == 7 and not user_to_remind.first_notice:
                recipient_ids = []
                recipient_ids.append(user_to_remind)
                recipient_links = [(4, user_id.partner_id.id) for user_id in recipient_ids]
                ref = self.env['mail.message.subtype'].sudo().search([('name','=','Discussions')])
#                url = '/renew?x=' + user_to_remind.login + '&xx=jksdiq'
#                url = 'mailto:mis@prodatanet.com.ph'
                url = 'https://www.prodatanet.com.ph/contactus'
                message_data = {
                   'message_type': 'notification',
                   'subject' : 'Account Expiration',
                   'body' : "Account will expire on " + str(days_remaining) + " days. " + "<a href='"+ url +"'>Renew</a>",
                   'partner_ids': recipient_links,
                   'subtype_id': ref.id,
                }
                msg_obj = self.env['mail.message']
                msg_obj.sudo().create(message_data)
                user_to_remind.sudo().write({'first_notice': True})
            if days_remaining == 3 and not user_to_remind.second_notice:
                recipient_ids = []
                recipient_ids.append(user_to_remind)
                recipient_links = [(4, user_id.partner_id.id) for user_id in recipient_ids]
                ref = self.env['mail.message.subtype'].sudo().search([('name','=','Discussions')])
#                url = '/renew?x=' + user_to_remind.login + '&xx=jksdiq'
                url = 'mailto:mis@prodatanet.com.ph'
                message_data = {
                   'message_type': 'notification',
                   'subject' : 'Account Expiration',
                   'body' : "Account will expire on " + str(days_remaining) + " days. " + "<a href='"+ url +"'>Renew</a>",
                   'partner_ids': recipient_links,
                   'subtype_id': ref.id,
                }
                msg_obj = self.env['mail.message']
                msg_obj.sudo().create(message_data)
                user_to_remind.sudo().write({'second_notice': True})
        self.env['res.users'].sudo().search([('id','!=', SUPERUSER_ID),('active','=',True),('expiry_date','<=',str(datetime.datetime.now().date()))]).sudo().write({'active': False})
        return True


    @api.model
    def _update_last_login(self):
        if self.id == SUPERUSER_ID:
            pass
        else:
            if not self.sudo().expiry_date and self.sub_type == 'trial':
                global duration_type
                global duration_count
                if duration_type == 'months':
                    self.sudo().write({'expiry_date': datetime.datetime.now() + relativedelta(months=duration_count)})
                elif duration_type == 'years':
                    self.sudo().write({'expiry_date': datetime.datetime.now() + relativedelta(years=duration_count)})
                elif duration_type == 'days':
                    self.sudo().write({'expiry_date': datetime.datetime.now() + relativedelta(days=duration_count)})
                else:
                    pass
        return super(ResUsers, self.sudo())._update_last_login()



