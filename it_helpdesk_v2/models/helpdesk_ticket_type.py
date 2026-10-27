from odoo import api, fields, models
from odoo.osv import expression


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'
    _order = 'code, name'
    _rec_name = 'name'

    code = fields.Char(string='Type Code', required=True, index=True)
    name = fields.Char(string='Type Name', required=True)
    type_code = fields.Char(string='Type Code (Import Alias)')
    type_name = fields.Char(string='Type Name (Import Alias)')
    sequence_code = fields.Char(string='Sequence Code')
    active = fields.Boolean(default=True)
    description = fields.Text(string='Deskripsi')
    service_count = fields.Integer(compute='_compute_service_count', string='Jumlah Service')
    service_ids = fields.One2many('helpdesk.service', 'type_id', string='Service Catalog')

    def _compute_service_count(self):
        for rec in self:
            rec.service_count = len(rec.service_ids)

    @api.model_create_multi
    def create(self, vals_list):
        seq_map = {
            'TYP-01': 'service_request',
            'TYP-02': 'incident',
            'TYP-03': 'security_incident',
        }
        records = self.browse()
        for vals in vals_list:
            if vals.get('type_code') and not vals.get('code'):
                vals['code'] = vals.get('type_code')
            if vals.get('type_name') and not vals.get('name'):
                vals['name'] = vals.get('type_name')
            if vals.get('code') and not vals.get('type_code'):
                vals['type_code'] = vals.get('code')
            if vals.get('name') and not vals.get('type_name'):
                vals['type_name'] = vals.get('name')
            if not vals.get('sequence_code') and vals.get('code'):
                vals['sequence_code'] = seq_map.get(str(vals['code']).strip().upper(), '')

            code = vals.get('code')
            if code:
                existing = self.search([('code', '=', code)], limit=1)
                if existing:
                    existing.write(vals)
                    records |= existing
                    continue

            new_rec = super(HelpdeskTicketType, self).create([vals])
            records |= new_rec
        return records

    def write(self, vals):
        seq_map = {
            'TYP-01': 'service_request',
            'TYP-02': 'incident',
            'TYP-03': 'security_incident',
        }
        if vals.get('type_code') and 'code' not in vals:
            vals['code'] = vals.get('type_code')
        if vals.get('type_name') and 'name' not in vals:
            vals['name'] = vals.get('type_name')
        if vals.get('code') and 'type_code' not in vals:
            vals['type_code'] = vals.get('code')
        if vals.get('name') and 'type_name' not in vals:
            vals['type_name'] = vals.get('name')
        if 'sequence_code' not in vals and vals.get('code'):
            vals['sequence_code'] = seq_map.get(str(vals['code']).strip().upper(), '')
        return super().write(vals)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.name or ''))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
