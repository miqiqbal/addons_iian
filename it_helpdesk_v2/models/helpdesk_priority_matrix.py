from odoo import fields, models

LEVEL_SELECTION = [('tinggi', 'TINGGI'), ('sedang', 'SEDANG'), ('rendah', 'RENDAH')]
PRIORITY_SELECTION = [('1', 'P1'), ('2', 'P2'), ('3', 'P3'), ('4', 'P4')]


class HelpdeskPriorityMatrix(models.Model):
    _name = 'helpdesk.priority.matrix'
    _description = 'Helpdesk Priority Matrix'
    _order = 'priority'

    impact_level = fields.Selection(LEVEL_SELECTION, required=True)
    urgency_level = fields.Selection(LEVEL_SELECTION, required=True)
    priority = fields.Selection(PRIORITY_SELECTION, required=True)
    label = fields.Char()

    _sql_constraints = [
        ('impact_urgency_unique', 'unique(impact_level, urgency_level)',
         'Kombinasi Impact Level dan Urgency Level harus unik.'),
    ]
