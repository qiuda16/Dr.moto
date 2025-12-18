from odoo import models, fields, api

class DrMotoProcedure(models.Model):
    _name = 'drmoto.procedure'
    _description = 'Maintenance Procedure'
    
    name = fields.Char(string='Procedure Name', required=True)
    vehicle_id = fields.Many2one('drmoto.vehicle', string='Vehicle', required=True)
    description = fields.Text(string='Description')
    
    step_ids = fields.One2many('drmoto.procedure.step', 'procedure_id', string='Steps')
    part_ids = fields.One2many('drmoto.procedure.part', 'procedure_id', string='Required Parts')
    
    total_cost = fields.Monetary(string='Estimated Cost', compute='_compute_cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('part_ids.total_price')
    def _compute_cost(self):
        for rec in self:
            rec.total_cost = sum(part.total_price for part in rec.part_ids)

class DrMotoProcedurePart(models.Model):
    _name = 'drmoto.procedure.part'
    _description = 'Procedure Required Part'
    
    procedure_id = fields.Many2one('drmoto.procedure', string='Procedure', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    
    unit_price = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True)
    total_price = fields.Float(string='Total Price', compute='_compute_total')
    
    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price

class DrMotoProcedureStep(models.Model):
    _name = 'drmoto.procedure.step'
    _description = 'Procedure Step'
    _order = 'sequence, id'
    
    procedure_id = fields.Many2one('drmoto.procedure', string='Procedure', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    instruction = fields.Text(string='Instruction', required=True)
    tools = fields.Char(string='Required Tools')
    torque = fields.Char(string='Torque Spec')
