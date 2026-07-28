from odoo import api, fields, models


class HelpdeskKnowledge(models.Model):
    _name = 'helpdesk.knowledge'
    _description = 'Knowledge Base / Solusi Mandiri'
    _order = 'sequence, name'

    name = fields.Char(string='Problem', required=True)
    sequence = fields.Integer(default=10)
    service_id = fields.Many2one('helpdesk.service', string='Service Terkait')
    category_id = fields.Many2one('helpdesk.category', string='Kategori Terkait')
    subcategory_id = fields.Many2one('helpdesk.subcategory', string='Sub Category')
    problem = fields.Char(string='Problem Title')
    solution_type = fields.Selection([
        ('text', 'Teks Tutorial Saja'),
        ('images', 'Kumpulan Capture / Foto Saja'),
        ('hybrid', 'Teks & Capture (Kombinasi Inline)')
    ], string='Format Jenis Solusi', default='hybrid')
    is_quick_solution = fields.Boolean(string='Quick Solution?', default=True)
    summary = fields.Text(string='Description (Masalah)')
    content = fields.Html(string='Langkah-Langkah & Foto Solusi (Tutorial)')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment / Screenshot Solusi')
    author_id = fields.Many2one('res.users', string='Penulis Artikel', default=lambda self: self.env.user)
    active = fields.Boolean(default=True)

    @api.model
    def init(self):
        super().init()
        try:
            menu = self.env.ref('it_helpdesk_v2.menu_it_helpdesk_knowledge_base', raise_if_not_found=False)
            action = self.env.ref('it_helpdesk_v2.action_helpdesk_knowledge', raise_if_not_found=False)
            if menu and action:
                menu.sudo().write({'action': 'ir.actions.act_window,%d' % action.id})
        except Exception:
            pass
