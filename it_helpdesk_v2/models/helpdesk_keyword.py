from odoo import api, fields, models


class HelpdeskKeywordEngineer(models.Model):
    _name = 'helpdesk.keyword.engineer'
    _description = 'PIC IT Auto Assign Engineer Order'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Urutan', default=10)
    keyword_id = fields.Many2one('helpdesk.keyword', string='Keyword Rule', ondelete='cascade', required=True)
    user_id = fields.Many2one(
        'res.users', string='Engineer', required=True,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('it_helpdesk_v2.group_helpdesk_agent').id])]
    )


class HelpdeskKeyword(models.Model):
    _name = 'helpdesk.keyword'
    _description = 'Helpdesk Keyword Routing'
    _order = 'sequence, name'

    name = fields.Char(string='Nama Rules / Topik', required=True)
    sequence = fields.Integer(default=10)
    service_ids = fields.Many2many('helpdesk.service', string='Layanan / Topik Target')
    category_ids = fields.Many2many('helpdesk.category', string='Kategori Target')
    subcategory_ids = fields.Many2many('helpdesk.subcategory', string='Sub Kategori Target')
    engineer_ids = fields.Many2many('res.users', string='PIC IT Auto Assign (Legacy)')
    engineer_line_ids = fields.One2many(
        'helpdesk.keyword.engineer', 'keyword_id',
        string='PIC IT Auto Assign (Berurutan)'
    )
    engineer_summary = fields.Char(
        string='PIC IT Auto Assign (Urutan Prioritas)',
        compute='_compute_engineer_summary', store=True
    )
    keyword_list = fields.Text(
        string='Keywords / Kata Kunci (Dipisahkan Koma)',
        help='Contoh: sap, keuangan, bap, ptpp, retensi',
        required=True)
    enable_auto_close = fields.Boolean(
        string='Auto Close Tiket', default=True,
        help='Aktifkan otomatis penutupan tiket (Auto Close) setelah status Done sesuai durasi priority (High 4 hari, Med 3 hari, Low 2 hari kerja)'
    )
    active = fields.Boolean(default=True)

    @api.depends('engineer_line_ids', 'engineer_line_ids.sequence', 'engineer_line_ids.user_id', 'engineer_ids')
    def _compute_engineer_summary(self):
        for rec in self:
            if rec.engineer_line_ids:
                lines = rec.engineer_line_ids.sorted('sequence')
                names = [line.user_id.name for line in lines if line.user_id]
                if names:
                    rec.engineer_summary = " ➔ ".join(["%d. %s" % (idx + 1, name) for idx, name in enumerate(names)])
                else:
                    rec.engineer_summary = "-"
            else:
                rec.engineer_summary = "-"

    def get_ordered_engineers(self):
        """Mengambil daftar engineer sesuai urutan persis sequence saat diinput user"""
        self.ensure_one()
        if self.engineer_line_ids:
            ordered_lines = self.engineer_line_ids.sorted('sequence')
            users = [line.user_id for line in ordered_lines if line.user_id and line.user_id.active]
            if users:
                return users
        return []

    def write(self, vals):
        if 'engineer_line_ids' in vals:
            vals['engineer_ids'] = [(5, 0, 0)]
        return super().write(vals)


