from odoo import api, fields, models


class HelpdeskService(models.Model):
    _name = 'helpdesk.service'
    _description = 'Helpdesk Service'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)
    description = fields.Text()
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')
    ticket_ids = fields.One2many('helpdesk.ticket', 'service_id', string='Case Tiket')

    def _compute_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('service_id', 'in', self.ids)], ['service_id'], ['service_id'])
        mapped_data = {data['service_id'][0]: data['service_id_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('service_id', '=', self.id)],
            'context': {'default_service_id': self.id},
        }
