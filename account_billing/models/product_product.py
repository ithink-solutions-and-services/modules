from odoo import api, models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    water_product = fields.Boolean("Water Consumption?", default=False)
    cu_m_fixed_days = fields.Integer("Fixed Rate Days")
    cu_m_fixed_price = fields.Float("Fixed Price")
    cu_m_exceed_price = fields.Float("Exceeding Price per cu. m")
    
    
