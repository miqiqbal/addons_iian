from odoo import fields, models

SLA_STATUS_CODE_SELECTION = [
    ('on_track', 'On Track'),
    ('warning', 'Warning'),
    ('critical', 'Critical Warning'),
    ('breached', 'SLA Overdue'),
]

SLA_STATUS_COLOR_SELECTION = [
    ('success', 'Hijau (Success)'),
    ('info', 'Biru (Info)'),
    ('warning', 'Kuning (Warning)'),
    ('danger', 'Merah (Danger)'),
]


class HelpdeskSLAStatus(models.Model):
    _name = 'helpdesk.sla.status'
    _description = 'Helpdesk SLA Status Label'
    _order = 'id'

    code = fields.Selection(SLA_STATUS_CODE_SELECTION, required=True, readonly=True)
    name = fields.Char(string='Label', required=True)
    color = fields.Selection(
        SLA_STATUS_COLOR_SELECTION, string='Warna Badge', required=True, default='success')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Kode status SLA harus unik.'),
    ]
