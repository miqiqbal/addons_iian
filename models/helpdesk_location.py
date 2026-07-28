from odoo import api, fields, models


class HelpdeskLocation(models.Model):
    _name = 'helpdesk.location'
    _description = 'Helpdesk Location'
    _order = 'name'

    name = fields.Char(required=True)
    address = fields.Char()
    active = fields.Boolean(default=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')
    ticket_ids = fields.One2many('helpdesk.ticket', 'location_id', string='Case Tiket')

    def _compute_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('location_id', 'in', self.ids)], ['location_id'], ['location_id'])
        mapped_data = {data['location_id'][0]: data['location_id_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id},
        }
