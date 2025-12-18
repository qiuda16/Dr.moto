from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_ids = fields.One2many('drmoto.partner.vehicle', 'partner_id', string='Vehicles')
    vehicle_count = fields.Integer(string='Vehicle Count', compute='_compute_vehicle_count')

    @api.depends('vehicle_ids')
    def _compute_vehicle_count(self):
        for partner in self:
            partner.vehicle_count = len(partner.vehicle_ids)
            
    def action_view_vehicles(self):
        self.ensure_one()
        return {
            'name': 'Vehicles',
            'type': 'ir.actions.act_window',
            'res_model': 'drmoto.partner.vehicle',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
