from datetime import timedelta

from odoo import fields, models

TIME_UNIT_SELECTION = [
    ('minute', 'Menit'), ('hour', 'Jam'),
    ('working_hour', 'Jam Kerja'), ('working_day', 'Hari Kerja'),
]
PRIORITY_SELECTION = [('1', 'P1'), ('2', 'P2'), ('3', 'P3'), ('4', 'P4')]


class HelpdeskSLA(models.Model):
    _name = 'helpdesk.sla'
    _description = 'Helpdesk SLA'
    _order = 'priority'

    priority = fields.Selection(PRIORITY_SELECTION, required=True)
    label = fields.Char()
    response_time_value = fields.Float(required=True)
    response_time_unit = fields.Selection(TIME_UNIT_SELECTION, required=True)
    update_frequency_text = fields.Char()
    resolution_time_value = fields.Float(required=True)
    resolution_time_unit = fields.Selection(TIME_UNIT_SELECTION, required=True)
    auto_close_value = fields.Float(string='Durasi Auto Close (Nilai)', default=4.0)
    auto_close_unit = fields.Selection(TIME_UNIT_SELECTION, string='Satuan Auto Close', default='working_day')
    warning_percent = fields.Float(string='Batas Warning (%)', default=80.0, help='Persentase durasi SLA untuk memicu status Warning & Email Alert')
    critical_percent = fields.Float(string='Batas Critical (%)', default=90.0, help='Persentase durasi SLA untuk memicu status Critical Warning')
    active = fields.Boolean(default=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')

    def _compute_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('priority', 'in', [s.priority for s in self if s.priority])], ['priority'], ['priority'])
        mapped_data = {data['priority']: data['priority_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.priority, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case Priority: %s' % (self.label or self.priority),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('priority', '=', self.priority)],
            'context': {'default_priority': self.priority},
        }

    _sql_constraints = [
        ('priority_unique', 'unique(priority)', 'Priority SLA harus unik.'),
    ]

    def _compute_deadline(self, start_datetime, value, unit):
        self.ensure_one()
        if not start_datetime:
            return False
        calendar = self.env.company.resource_calendar_id
        if not calendar:
            if unit == 'minute':
                return start_datetime + timedelta(minutes=value)
            if unit in ('hour', 'working_hour'):
                return start_datetime + timedelta(hours=value)
            return start_datetime + timedelta(days=value)

        if unit == 'minute':
            return calendar.plan_hours(value / 60.0, start_datetime, compute_leaves=True)
        if unit in ('hour', 'working_hour'):
            return calendar.plan_hours(value, start_datetime, compute_leaves=True)
        return calendar.plan_days(value, start_datetime, compute_leaves=True)


    def get_deadline(self, start_datetime):
        self.ensure_one()
        return self._compute_deadline(
            start_datetime, self.response_time_value, self.response_time_unit)

    def get_resolution_deadline(self, start_datetime):
        self.ensure_one()
        return self._compute_deadline(
            start_datetime, self.resolution_time_value, self.resolution_time_unit)

    def get_auto_close_deadline(self, start_datetime):
        self.ensure_one()
        val = self.auto_close_value or (4.0 if self.priority in ('1', '2') else 3.0 if self.priority == '3' else 2.0)
        unit = self.auto_close_unit or 'working_day'
        return self._compute_deadline(start_datetime, val, unit)
