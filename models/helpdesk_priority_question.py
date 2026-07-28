from odoo import fields, models


class HelpdeskPriorityQuestion(models.Model):
    _name = 'helpdesk.priority.question'
    _description = 'Helpdesk Priority Question'
    _rec_name = 'question_text'
    _order = 'sequence, id'

    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    dimension = fields.Selection(
        [('impact', 'Impact'), ('urgency', 'Urgency')], required=True)
    question_text = fields.Char(required=True)
    answer_ids = fields.One2many('helpdesk.priority.answer', 'question_id')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Kode pertanyaan (code) harus unik.'),
    ]


class HelpdeskPriorityAnswer(models.Model):
    _name = 'helpdesk.priority.answer'
    _description = 'Helpdesk Priority Answer'
    _rec_name = 'answer_text'
    _order = 'sequence, id'

    question_id = fields.Many2one(
        'helpdesk.priority.question', required=True, ondelete='cascade')
    answer_text = fields.Char(required=True)
    score = fields.Integer(required=True)
    weight = fields.Integer(default=1)
    description = fields.Char()
    sequence = fields.Integer(default=10)

    def name_get(self):
        res = []
        for rec in self:
            name = rec.answer_text or f"Opsi {rec.id}"
            res.append((rec.id, name))
        return res
