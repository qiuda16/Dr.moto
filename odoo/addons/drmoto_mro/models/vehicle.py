from odoo import models, fields, api

class DrMotoVehicle(models.Model):
    _name = 'drmoto.vehicle'
    _description = 'Motorcycle Vehicle'
    _rec_name = 'key'

    key = fields.Char(string='Unique Key', required=True, index=True, help="Format: MAKE|MODEL|YEAR|ENGINE")
    make = fields.Char(string='Make', required=True)
    model = fields.Char(string='Model', required=True)
    year_from = fields.Integer(string='Year From', required=True)
    year_to = fields.Integer(string='Year To')
    engine_code = fields.Char(string='Engine Code')
    
    _sql_constraints = [
        ('key_unique', 'unique(key)', 'The vehicle key must be unique!')
    ]

class DrMotoPartnerVehicle(models.Model):
    _name = 'drmoto.partner.vehicle'
    _description = 'Customer Vehicle Instance'
    _rec_name = 'license_plate'

    partner_id = fields.Many2one('res.partner', string='Owner', required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('drmoto.vehicle', string='Vehicle Model', required=True)
    license_plate = fields.Char(string='License Plate', required=True)
    vin = fields.Char(string='VIN')
    color = fields.Char(string='Color')
    
    _sql_constraints = [
        ('plate_unique', 'unique(license_plate)', 'License plate must be unique!')
    ]
