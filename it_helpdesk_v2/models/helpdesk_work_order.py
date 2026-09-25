from odoo import api, fields, models


class HelpdeskWorkOrder(models.Model):
    _name = 'helpdesk.work.order'
    _description = 'Helpdesk Work Order'
    _inherit = ['mail.thread']
    _order = 'created_on desc'

    name = fields.Char(readonly=True, copy=False, default='New')
    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', ondelete='cascade')
    task = fields.Char(string='Task', required=True)
    description = fields.Text()
    created_on = fields.Datetime(default=fields.Datetime.now, readonly=True)
    assign_to = fields.Many2one('res.users', string='Assign To')
    service_id = fields.Many2one(
        'helpdesk.service', related='ticket_id.service_id',
        store=True, readonly=False, string='Service Catalog')
    category_id = fields.Many2one(
        'helpdesk.category', related='ticket_id.category_id',
        store=True, readonly=False, string='Kategori')
    subcategory_id = fields.Many2one(
        'helpdesk.subcategory', related='ticket_id.subcategory_id',
        store=True, readonly=False, string='Sub Kategori')
    starting_at = fields.Datetime(string='Starting At')
    deadline_at = fields.Datetime(string='Deadline At')
    progress = fields.Float(string='Progress', default=0.0)
    status = fields.Selection(
        [('open', 'Open'), ('done', 'Done'), ('closed', 'Closed')],
        default='open', tracking=True, string='Status')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'it.helpdesk.work.order') or 'New'
        return super().create(vals_list)
