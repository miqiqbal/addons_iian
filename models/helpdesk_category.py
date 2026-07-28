from odoo import api, fields, models


class HelpdeskCategory(models.Model):
    _name = 'helpdesk.category'
    _description = 'Helpdesk Category'
    _order = 'name'

    name = fields.Char(required=True)
    service_id = fields.Many2one('helpdesk.service', string='Service')
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')
    ticket_ids = fields.One2many('helpdesk.ticket', 'category_id', string='Case Tiket')

    def _compute_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = {data['category_id'][0]: data['category_id_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }


class HelpdeskSubcategory(models.Model):
    _name = 'helpdesk.subcategory'
    _description = 'Helpdesk Sub-Category'
    _order = 'name'

    name = fields.Char(required=True)
    category_id = fields.Many2one('helpdesk.category', required=True)
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)
