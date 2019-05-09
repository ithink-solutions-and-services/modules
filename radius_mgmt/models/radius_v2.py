from odoo import models, fields, api
import base64
import time
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.exceptions import Warning
from odoo import SUPERUSER_ID
import datetime
import json
import calendar
import string
import random
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Groups
#----------------------------------------------------------
class radius_groups(models.Model):
    _name = "radius.groups"
    _description = "Groups"
    _inherit = ["mail.thread"]

    name = fields.Char('Name', size=64)
    attribute_ids = fields.One2many('radius.attributes', 'group_id' , string='Attributes',ondelete='cascade')
    category = fields.Selection([('time','Time-Based'),('volume','Volume-Based'),('time_volume','Time and Volume-Based'), ('expiration','Cutoff-Based')],string="Category")
    upload_speed = fields.Char('Upload Speed (bytes)')
    download_speed = fields.Char('Download Speed (bytes)')
    time_seconds = fields.Char('Time Limit (seconds)')
    expiration_time_hours = fields.Float(string="Cutoff Time", help="Hours until cutoff")

    @api.onchange('volume_megabytes')
    def _onchange_megabytes(self):
        for rec in self:
            rec.volume_bytes = "" if rec.volume_megabytes else rec.volume_bytes

    @api.onchange('volume_bytes')
    def _onchange_bytes(self):
        for rec in self:
            rec.volume_megabytes = "" if rec.volume_bytes else rec.volume_megabytes

    volume_bytes = fields.Char('Data Cap (bytes)', track_visibility='onchange')
    volume_megabytes = fields.Char('Data Cap (megabytes)', track_visibility='onchange')
    product_id = fields.Many2one('product.template', 'Product')
    price = fields.Float(related="product_id.list_price", string="Price")
    journal_id = fields.Many2one('account.journal', 'Journal')
    expiration_hours = fields.Float(string='Hours of Expiration')
    #expiration_days = fields.Integer("Days of Expiration")

    @api.one
    def _get_company_currency(self):
        if 'company_id' in self:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')


    @api.multi
    def group_clean(self):
#Deletes radgroupcheck and radgroupreply records with groupname equal to current group
        self.env['radius.radgroupcheck'].sudo().search([('groupname','=',self.id)]).unlink()
        self.env['radius.radgroupreply'].sudo().search([('groupname','=',self.id)]).unlink()
        return True

    @api.multi
    def group_generate(self):
        group = self.env['radius.groups'].sudo().browse(self.id)
        groupcheck_obj = self.env['radius.radgroupcheck']
        groupreply_obj = self.env['radius.radgroupreply']
        for attribute_id in group.attribute_ids:
            group_vals = {
                    'groupname': group.id,
                    'attribute': attribute_id.attribute_id.name,
                    'op': attribute_id.op,
                    'value': attribute_id.value
            }
            if attribute_id.type == 'radgroupcheck':
                groupcheck_obj.sudo().create(group_vals)
            else:
                groupreply_obj.sudo().create(group_vals)
        return True

    @api.multi
    def get_attributes(self):
        radattrs_obj = self.env['radius.attributes']
        if 'upload_speed' in self:
            radattrs_obj.sudo().search([('attribute_id.name','=','WISPr-Bandwidth-Max-Up'),('group_id','=',self.id)]).unlink()
            if self.upload_speed:
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'WISPr-Bandwidth-Max-Up')]).id,
                    'type': 'radreply',
                    'op': ':=',
                    'value': self.upload_speed,
                    'group_id': self.id
                })
        if 'download_speed' in self:
            radattrs_obj.sudo().search([('attribute_id.name','=','WISPr-Bandwidth-Max-Down'),('group_id','=',self.id)]).unlink()
            if self.download_speed:
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'WISPr-Bandwidth-Max-Down')]).id,
                    'type': 'radreply',
                    'op': ':=',
                    'value': self.download_speed,
                    'group_id': self.id
                })
        if 'time_seconds' in self:
            radattrs_obj.sudo().search([('attribute_id.name','=','Max-All-Session'),('group_id','=',self.id)]).unlink()
            radattrs_obj.sudo().search([('attribute_id.name','=','Session-Timeout'),('group_id','=',self.id)]).unlink()
            if self.time_seconds:
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'Max-All-Session')]).id,
                    'type': 'radcheck',
                    'op': ':=',
                    'value': self.time_seconds,
                    'group_id': self.id
                })
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'Session-Timeout')]).id,
                    'type': 'radreply',
                    'op': ':=',
                    'value': self.time_seconds,
                    'group_id': self.id
                })
        if 'volume_bytes' in self:
            radattrs_obj.sudo().search([('attribute_id.name','=','ZVendor-Byte-Amount'),('group_id','=',self.id)]).unlink()
            if self.volume_bytes:
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'ZVendor-Byte-Amount')]).id,
                    'type': 'radcheck',
                    'op': ':=',
                    'value': self.volume_bytes,
                    'group_id': self.id
                })
        if 'volume_megabytes' in self:
            radattrs_obj.sudo().search([('attribute_id.name','=','ZVendor-Byte-Amount-4GB'),('group_id','=',self.id)]).unlink()
            if self.volume_megabytes:
                radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'ZVendor-Byte-Amount-4GB')]).id,
                    'type': 'radcheck',
                    'op': ':=',
                    'value': self.volume_megabytes,
                    'group_id': self.id
                })
        radattrs_obj.sudo().search([('attribute_id.name','=','Acct-Interim-Interval'),('group_id','=',self.id)]).unlink()
        radattrs_obj.create({
                    'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'Acct-Interim-Interval')]).id,
                    'type': 'radreply',
                    'op': ':=',
                    'value': '15',
                    'group_id': self.id
        })
        return True

    @api.multi
    def write(self, vals):
        res = super(radius_groups, self).write(vals)
        group = self.env['radius.groups'].sudo().browse(self.id)
        group.get_attributes()
#        group.group_clean()
#        group.group_generate()
        return res

    @api.model
    def create(self, vals):
        if len(self.env['radius.groups'].sudo().search([('name', '=', vals['name'])])) > 0:
            raise UserError("Name already exists. Enter a unique name")
#        attribute_ids = []
#        if 'attribute_ids' in vals:
#            attribute_ids = vals['attribute_ids']
#        if 'upload_speed' in vals:
#            attribute_ids.append((0, 0, {
#                'attribute_id': self.env['radius.attribute'].sudo().search([('name','=', 'WISPr-Bandwidth-Max-Up')]).id,
#                'type': 'radreply',
#                'op': ':=',
#                'value': vals['upload_speed']
#            }))
#        vals['attribute_ids'] = attribute_ids
        res = super(radius_groups, self).create(vals)
        group = self.env['radius.groups'].sudo().browse(res.id)
        group.get_attributes()
#        self.env['radius.groups'].sudo().browse(res.id).group_generate()

        return res

#radius_groups()

#----------------------------------------------------------
# NAS
#----------------------------------------------------------
class radius_nas(models.Model):
    _name = "radius.nas"
    _rec_name = 'nasname'

    nasname = fields.Char('Nas IP/Host', size=128)
    shortname =  fields.Char('Nas Shortname', size=32)
#        'type': fields.char('Nas Type', size=32),
    type= fields.Selection([('cisco','cisco'),('portslave','portslave'),('other','other')], 'Nas Type')
    ports= fields.Integer('Nas Ports')
    secret= fields.Char('Nas Secret', size=64)
    community= fields.Char('Nas Community', size=64)
    description= fields.Text('Nas Description')
#radius_nas()

#----------------------------------------------------------
# Radacct
#----------------------------------------------------------
class radius_radacct(models.Model):
    _name = "radius.radacct"

    name= fields.Char('Name', size=64)
    radacctid= fields.Char('Radacctid', size=64)
    acctsessionid= fields.Char('Acctsessionid', size=64)
    acctuniqueid= fields.Char('Acctuniqueid', size=64)
    username= fields.Char('Username', size=128)
    groupname= fields.Char('Group Name', size=128)
    realm= fields.Char('Realm', size=64)
    nasipaddress= fields.Char('Nasipaddress', size=64)
    nasportid= fields.Char('Nasportid', size=64)
    nasporttype= fields.Char('Nasporttype', size=64)
    acctstarttime= fields.Datetime('Acctstarttime')
    acctstoptime= fields.Datetime('Acctstoptime')
    acctsessiontime= fields.Float('Acctsessiontime')
    acctauthentic= fields.Char('Acctauthentic', size=32)
    connectinfo_start= fields.Char('Connectinfo_start', size=64)
    connectinfo_stop= fields.Char('Connectinfo_stop', size=64)
    acctinputoctets= fields.Float('Acctinputoctets')
    acctoutputoctets= fields.Float('Acctoutputoctets')
    calledstationid= fields.Char('Calledstationid', size=64)
    callingstationid= fields.Char('Callingstationid', size=64)
    acctterminatecause= fields.Char('Acctterminatecause', size=32)
    servicetype= fields.Char('Servicetype', size=32)
    xascendsessionsvrkey= fields.Char('Xascendsessionsvrkey', size=32)
    framedprotocol= fields.Char('Framedprotocol', size=32)
    framedipaddress= fields.Char('Framedipaddress', size=128)
    acctstartdelay= fields.Integer('Acctstartdelay')
    acctstopdelay= fields.Integer('Acctstopdelay')

#radius_radacct()

#----------------------------------------------------------
# Radcheck
#----------------------------------------------------------
class radius_radcheck(models.Model):
    _name = "radius.radcheck"
    _rec_name = 'username'

    username= fields.Char('Username', size=64)
#        'attribute': fields.char('Attribute', size=64),
#    attribute= fields.Selection([('Cleartext-Password','Cleartext-Password'),('Auth-Type','Auth-Type'),('ChilliSpot-Max-Total-Octets','Quota Attribute'),('ChilliSpot-Max-Total-Gigawords','Quota Gigawords'),('Simultaneous-Use','Simultaneous-Use'),('Max-All-Session','Max-All-Session'),('Access-Period','Access-Period'),('uptime_limit','uptime_limit')], 'Attribute', size=64)       
    attribute = fields.Char('Attribute', size=64)
#attribute= fields.Selection([('Cleartext-Password','Cleartext-Password'),('Auth-Type','Auth-Type'),('ChilliSpot-Max-Total-Octets','Quota Attribute'),('ChilliSpot-Max-Total-Gigawords','Quota Gigawords'),('Simultaneous-Use','Simultaneous-Use')], 'Attribute', size=64)
    op= fields.Selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP')
    value= fields.Char('Value', size=253)
#radius_radcheck()

#----------------------------------------------------------
# Radreply
#----------------------------------------------------------
class radius_radreply(models.Model):
    _name = "radius.radreply"
    _rec_name = 'username'

    username= fields.Char('Username', size=64)
    attribute =  fields.Char('Attribute', size=64)
#    attribute= fields.Selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Session-Terminate-Time','WISPr-Session-Terminate-Time'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down'),('Max-All-Session','Max-All-Session')], 'Attribute', size=64)
#attribute= fields.Selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Session-Terminate-Time','WISPr-Session-Terminate-Time'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down')], 'Attribute', size=64)
    op= fields.Selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP')
    value= fields.Char('Value', size=253)
    
#radius_radreply()

#----------------------------------------------------------
# Radgroupcheck
#----------------------------------------------------------
class radius_radgroupcheck(models.Model):
    _name = "radius.radgroupcheck"
    _rec_name = 'groupname'

    groupname = fields.Many2one('radius.groups','Group')
#        'attribute': fields.char('Attribute', size=64),
#    attribute= fields.Selection([('Auth-Type','Auth-Type'),('Max-All-Session','Max-All-Session'),('Max-Monthly-Session','Max-Monthly-Session'),('Simultaneous-Use','Simultaneous-Use')], 'Attribute', size=64)
    attribute = fields.Char('Attribute', size=64)
#attribute= fields.Selection([('Auth-Type','Auth-Type'),('Max-All-Session','Max-All-Session'),('Max-Monthly-Session','Max-Monthly-Session'),('Simultaneous-Use','Simultaneous-Use')], 'Attribute', size=64)
    op= fields.Selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP')
    value= fields.Char('Value', size=253)
    
#radius_radgroupcheck()

#----------------------------------------------------------
# Radgroupreply
#----------------------------------------------------------
class radius_radgroupreply(models.Model):
    _name = "radius.radgroupreply"
    _rec_name = 'groupname'

    groupname = fields.Many2one('radius.groups','Group')
#        'attribute': fields.char('Attribute', size=64),
#    attribute= fields.Selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Session-Terminate-Time','WISPr-Session-Terminate-Time'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down')], 'Attribute', size=64)
    attribute = fields.Char("Attribute", size=64)
#attribute= fields.Selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Session-Terminate-Time','WISPr-Session-Terminate-Time'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down')], 'Attribute', size=64)
    op= fields.Selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP')
    value= fields.Char('Value', size=253)
    
#radius_radgroupreply()

#----------------------------------------------------------
# Radusergroup
#----------------------------------------------------------
class radius_radusergroup(models.Model):
    _name = "radius.radusergroup"
    _rec_name = 'username'

    username= fields.Char('Username', size=64)
    groupname= fields.Many2one('radius.groups','Group')
    priority= fields.Integer('priority')
    
#radius_radusergroup()

#----------------------------------------------------------
# Radpostauth
#----------------------------------------------------------
class radius_radpostauth(models.Model):
    _name = "radius.radpostauth"
    _rec_name = 'username'

    username= fields.Char('Username', size=128)
    password= fields.Char('Password', size=64)
    reply= fields.Char('Radius Reply', size=64)
    calledstationid= fields.Char('Calledstationid', size=64)
    callingstationid= fields.Char('Callingstationid', size=64)
    authdate= fields.Datetime('Authdate')
    
#radius_radpostauth()


class radius_attribute(models.Model):
    _name = "radius.attribute"
    _inherit = ['mail.thread']
#    name = fields.Selection([('Max-All-Session','Max-All-Session'),('Cleartext-Password','Cleartext-Password')],'Attribute')
    name = fields.Char("Attribute")

class radius_attributes(models.Model):
    _name = "radius.attributes"
    _inherit = ['mail.thread']

    name = fields.Char("Name (label)")
    attribute_id = fields.Many2one('radius.attribute','Attribute',required=True)
    value = fields.Char("Value",required=True)
    op= fields.Selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'Operator',required=True)
    type = fields.Selection([('radcheck','radcheck'),('radreply','radreply')],'Type',required=True)
    group_id = fields.Many2one('radius.groups','Group')
