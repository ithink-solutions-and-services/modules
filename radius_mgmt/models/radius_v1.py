from odoo import models, fields, api
import base64
import time
from odoo.tools.translate import _

class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    radius_account_ids = fields.One2many('radius.account', 'partner_id')
#    radius_product_id = fields.Many2many('product.template')
    radius_ippool_id = fields.Many2many('radius.ippool')

class IPPool(models.Model):
     _name = 'radius.ippool'

     def show_ips(self):
         pass

     name = fields.Char('Name')
     pool_type = fields.Selection([
        ('regular', 'Regular'),
        ('internal', 'Internal')
     ])
     pool_range = fields.Char('IP Range', help='Create a range (A.B.C.D-E)')
     partner_ids = fields.Many2many('res.partner')

class Product(models.Model):
     _name = 'product.template'
     _inherit = 'product.template'
     radius = fields.Boolean('Radius')
     download_rate = fields.Char('Download rate', help='Download rate (b,k,m,g)')
     upload_rate = fields.Char('Upload rate', help='Upload rate (b,k,m,g)')
     burst = fields.Boolean('Burst')
     burst_download_limit = fields.Char('Limit download', help='Limit burst download (b,k,m,g)')
     burst_upload_limit = fields.Char('Limit upload', help='Limit burst upload (b,k,m,g)')
     burst_download_thershold = fields.Char('Thershold download', help='Thershold burst download (b,k,m,g)')
     burst_upload_thershold  = fields.Char('Thershold upload', help='Thershold burst upload (b,k,m,g)')
     burst_download_time= fields.Char('Time download', help='Time burst download (b,k,m,g)')
     burst_upload_time = fields.Char('Time upload', help='Time burst upload (b,k,m,g)')
     radius_partner_id = fields.Many2many('res.partner')

class Account(models.Model):
    _name = 'radius.account'

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    username = fields.Char()
    password = fields.Char()
    contract_id = fields.Many2one('account.analytic.account')
    product_id = fields.Many2one('product.product')
    pool_type = fields.Selection([
        ('NAS', 'NAS'),
        ('pool', 'Pool'),
        ('static', 'Static'),
        ('dynamic', 'Dynamic')]
    )
    static_ip = fields.Char()
    ippool_id = fields.Many2one('radius.ippool')


