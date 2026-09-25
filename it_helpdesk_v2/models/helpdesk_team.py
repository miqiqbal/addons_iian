from odoo import api, fields, models


class HelpdeskTeam(models.Model):
    _name = 'helpdesk.team'
    _description = 'Helpdesk Team'
    _order = 'name'

    name = fields.Char(required=True)
    member_ids = fields.Many2many('res.users', string='Engineers')
    service_ids = fields.Many2many('helpdesk.service')
    manager_id = fields.Many2one('res.users')

    @api.model_create_multi
    def create(self, vals_list):
        teams = super().create(vals_list)
        if any({'member_ids', 'service_ids'} & vals.keys() for vals in vals_list):
            self.env['ir.rule'].clear_caches()
        return teams

    def write(self, vals):
        res = super().write(vals)
        if {'member_ids', 'service_ids'} & vals.keys():
            # helpdesk.ticket punya record rule (Stage 10) yang melakukan subquery
            # dinamis ke member_ids/service_ids tim ini; hasil evaluasi ir.rule
            # di-cache per user dan TIDAK otomatis invalid saat model lain (tim ini)
            # berubah, jadi cache harus dibersihkan manual di sini.
            self.env['ir.rule'].clear_caches()
        return res
