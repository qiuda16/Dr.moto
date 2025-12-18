from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


class DrMotoWorkOrder(models.Model):
    _name = 'drmoto.work.order'
    _description = 'Vehicle Work Order'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Enable Chatter

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    vehicle_plate = fields.Char(string='Vehicle Plate', required=True, tracking=True)
    vehicle_id = fields.Many2one('drmoto.vehicle', string='Vehicle Model')
    description = fields.Text(string='Description')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('diagnosing', 'Diagnosing'),
        ('quoted', 'Quoted'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], default='0', string="Priority", tracking=True)

    date_planned = fields.Datetime(string='Planned Date', default=fields.Datetime.now)
    date_deadline = fields.Datetime(string='Deadline')
    
    # Lines
    line_ids = fields.One2many('drmoto.work.order.line', 'order_id', string='Work Order Lines')
    
    # Totals
    amount_total = fields.Monetary(string='Total', compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # UI Fields
    color = fields.Integer('Color Index')

    # BFF Integration Fields
    bff_uuid = fields.Char(string='BFF UUID', help="UUID from the BFF system")
    
    # Procedure Integration
    procedure_id = fields.Many2one('drmoto.procedure', string='Standard Procedure')

    @api.onchange('procedure_id')
    def _onchange_procedure_id(self):
        """Auto-populate lines when a procedure is selected."""
        if not self.procedure_id:
            return
            
        # Clear existing lines if needed (optional)
        # self.line_ids = [(5, 0, 0)] 
        
        new_lines = []
        for part in self.procedure_id.part_ids:
            new_lines.append((0, 0, {
                'product_id': part.product_id.id,
                'name': part.product_id.name,
                'quantity': part.quantity,
                'price_unit': part.unit_price,
            }))
        
        # Add labor/steps as text lines (optional, here just parts)
        self.line_ids = new_lines

    def write(self, vals):
        res = super(DrMotoWorkOrder, self).write(vals)
        if 'state' in vals:
            for order in self:
                if order.bff_uuid:
                    self._sync_status_to_bff(order)
        return res

    def _sync_status_to_bff(self, order):
        """Notify BFF about status change."""
        bff_url = "http://bff:8080/mp/workorders/callback/status" # Hardcoded for MVP, use ir.config_parameter in prod
        payload = {
            "odoo_id": order.id,
            "new_status": order.state,
            "bff_uuid": order.bff_uuid
        }
        try:
            # Short timeout to avoid blocking Odoo UI
            requests.post(bff_url, json=payload, timeout=2)
        except Exception as e:
            _logger.error(f"Failed to sync status to BFF: {e}")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('drmoto.work.order') or 'New'
        
        # Auto-apply procedure lines if created via API with procedure_id
        if vals.get('procedure_id') and not vals.get('line_ids'):
            proc = self.env['drmoto.procedure'].browse(vals['procedure_id'])
            if proc.exists():
                lines = []
                for part in proc.part_ids:
                    lines.append((0, 0, {
                        'product_id': part.product_id.id,
                        'name': part.product_id.name,
                        'quantity': part.quantity,
                        'price_unit': part.unit_price,
                    }))
                vals['line_ids'] = lines

        return super(DrMotoWorkOrder, self).create(vals)

    @api.depends('line_ids.price_subtotal')
    def _compute_amount(self):
        for order in self:
            order.amount_total = sum(line.price_subtotal for line in order.line_ids)

    def _expand_states(self, states, domain, order=None):
        return [key for key, val in type(self).state.selection]

    @api.model
    def issue_part_bff(self, work_order_id, product_id, quantity):
        """Called by BFF to issue a part."""
        order = self.browse(work_order_id)
        if not order.exists():
            return False
            
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return False
            
        # 1. Create WO Line
        self.env['drmoto.work.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'name': product.name,
            'quantity': quantity,
            'price_unit': product.list_price,
        })
        
        # 2. Create Stock Move (Draft -> Confirmed)
        # Try to find a default outgoing location
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        if picking_type:
            source_loc = picking_type.default_location_src_id.id
        else:
            # Fallback
            source_loc = self.env.ref('stock.stock_location_stock').id
            
        move = self.env['stock.move'].create({
            'name': f'{order.name}: {product.name}',
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': product.uom_id.id,
            'location_id': source_loc,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'origin': order.name,
        })
        move._action_confirm()
        
        return True

class DrMotoWorkOrderLine(models.Model):
    _name = 'drmoto.work.order.line'
    _description = 'Work Order Line'

    order_id = fields.Many2one('drmoto.work.order', string='Work Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product/Service') # Optional integration with Product
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_amount', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
