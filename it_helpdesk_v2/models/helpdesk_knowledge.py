from odoo import api, fields, models
from odoo.exceptions import UserError


class HelpdeskKnowledge(models.Model):
    _name = 'helpdesk.knowledge'
    _description = 'Knowledge Base / Solusi Mandiri'
    _order = 'sequence, name'

    name = fields.Char(string='Judul Solusi / Artikel', required=True)
    sequence = fields.Integer(default=10)
    service_id = fields.Many2one('helpdesk.service', string='Service / Layanan Terkait')
    category_id = fields.Many2one('helpdesk.category', string='Kategori Terkait')
    subcategory_id = fields.Many2one('helpdesk.subcategory', string='Sub Category')
    problem = fields.Char(string='Problem Title / Masalah')
    solution_type = fields.Selection([
        ('file', 'Dokumen / File Panduan (Upload Dokumen)'),
        ('text', 'Teks Tutorial Saja (Ketik Manual)'),
        ('hybrid', 'Kombinasi (Tutorial & File Lampiran)')
    ], string='Format Jenis Solusi', default='file', required=True)
    is_quick_solution = fields.Boolean(string='Quick Solution?', default=True)
    summary = fields.Text(string='Description / Ringkasan Masalah')
    content = fields.Html(string='Langkah-Langkah & Foto Solusi (Tutorial)')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment / Dokumen Panduan')
    author_id = fields.Many2one('res.users', string='Penulis Artikel', default=lambda self: self.env.user)
    active = fields.Boolean(default=True)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            if self.category_id and self.category_id.service_id and self.category_id.service_id != self.service_id:
                self.category_id = False
                self.subcategory_id = False
            return {'domain': {'category_id': [('service_id', '=', self.service_id.id)]}}
        return {'domain': {'category_id': []}}

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if not self.service_id and self.category_id.service_id:
                self.service_id = self.category_id.service_id.id
            if self.subcategory_id and self.subcategory_id.category_id and self.subcategory_id.category_id != self.category_id:
                self.subcategory_id = False
            return {'domain': {'subcategory_id': [('category_id', '=', self.category_id.id)]}}
        return {'domain': {'subcategory_id': []}}

    @api.onchange('subcategory_id')
    def _onchange_subcategory_id(self):
        if self.subcategory_id:
            if self.subcategory_id.category_id:
                self.category_id = self.subcategory_id.category_id.id
                if self.subcategory_id.category_id.service_id:
                    self.service_id = self.subcategory_id.category_id.service_id.id

    @api.model
    def create(self, vals):
        if not (self.env.is_superuser() or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')):
            raise UserError('Hanya pengguna dengan Role Akses "IT Admin" yang memiliki wewenang untuk membuat artikel Knowledge Base!')

        if vals.get('name') and not vals.get('problem'):
            vals['problem'] = vals['name']
        if vals.get('solution_type', 'file') == 'file' and not vals.get('content'):
            vals['content'] = '<p>Panduan teknis dan petunjuk penyelesaian lengkap tersedia pada berkas lampiran.</p>'
        if vals.get('subcategory_id') and not vals.get('category_id'):
            subcat = self.env['helpdesk.subcategory'].browse(vals['subcategory_id'])
            if subcat.category_id:
                vals['category_id'] = subcat.category_id.id
                if not vals.get('service_id') and subcat.category_id.service_id:
                    vals['service_id'] = subcat.category_id.service_id.id
        elif vals.get('category_id') and not vals.get('service_id'):
            cat = self.env['helpdesk.category'].browse(vals['category_id'])
            if cat.service_id:
                vals['service_id'] = cat.service_id.id
        rec = super().create(vals)
        if rec.attachment_ids:
            rec.attachment_ids.sudo().write({
                'res_model': 'helpdesk.knowledge',
                'res_id': rec.id,
            })
        return rec

    def write(self, vals):
        if not (self.env.is_superuser() or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')):
            raise UserError('Hanya pengguna dengan Role Akses "IT Admin" yang memiliki wewenang untuk mengubah artikel Knowledge Base!')

        if vals.get('name') and not vals.get('problem'):
            vals['problem'] = vals['name']
        if vals.get('solution_type') == 'file' and not vals.get('content') and not self.content:
            vals['content'] = '<p>Panduan teknis dan petunjuk penyelesaian lengkap tersedia pada berkas lampiran.</p>'
        if vals.get('subcategory_id') and not vals.get('category_id'):
            subcat = self.env['helpdesk.subcategory'].browse(vals['subcategory_id'])
            if subcat.category_id:
                vals['category_id'] = subcat.category_id.id
                if not vals.get('service_id') and subcat.category_id.service_id:
                    vals['service_id'] = subcat.category_id.service_id.id
        elif vals.get('category_id') and not vals.get('service_id'):
            cat = self.env['helpdesk.category'].browse(vals['category_id'])
            if cat.service_id:
                vals['service_id'] = cat.service_id.id
        res = super().write(vals)
        if 'attachment_ids' in vals:
            for rec in self:
                if rec.attachment_ids:
                    rec.attachment_ids.sudo().write({
                        'res_model': 'helpdesk.knowledge',
                        'res_id': rec.id,
                    })
        return res

    def unlink(self):
        if not (self.env.is_superuser() or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')):
            raise UserError('Hanya pengguna dengan Role Akses "IT Admin" yang diizinkan untuk menghapus artikel Knowledge Base!')
        return super().unlink()

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
