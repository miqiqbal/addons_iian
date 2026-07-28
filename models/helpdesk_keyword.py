from odoo import fields, models


class HelpdeskKeyword(models.Model):
    _name = 'helpdesk.keyword'
    _description = 'Helpdesk Keyword Routing'
    _order = 'sequence, name'

    name = fields.Char(string='Nama Rules / Topik', required=True)
    sequence = fields.Integer(default=10)
    service_ids = fields.Many2many('helpdesk.service', string='Layanan / Topik Target')
    category_ids = fields.Many2many('helpdesk.category', string='Kategori Target')
    subcategory_ids = fields.Many2many('helpdesk.subcategory', string='Sub Kategori Target')
    engineer_ids = fields.Many2many('res.users', string='PIC IT Auto Assign')
    keyword_list = fields.Text(
        string='Keywords / Kata Kunci (Dipisahkan Koma)',
        help='Contoh: sap, keuangan, bap, ptpp, retensi',
        required=True)
    active = fields.Boolean(default=True)
