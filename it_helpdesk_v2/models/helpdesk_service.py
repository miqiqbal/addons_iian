from odoo import api, fields, models
from odoo.osv import expression


class HelpdeskService(models.Model):
    _name = 'helpdesk.service'
    _description = 'Helpdesk Service'
    _order = 'code, name'
    _rec_name = 'name'

    name = fields.Char(string='Service Catalog Name', required=True)
    code = fields.Char(string='Catalog Code', index=True)
    catalog_code = fields.Char(string='Catalog Code (Import Alias)')
    service_catalog_name = fields.Char(string='Service Catalog Name (Import Alias)')
    type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type', ondelete='restrict')
    type_code = fields.Char(string='Type Code', index=True)
    type_name = fields.Char(string='Type Name (Import Alias)')
    ticket_type = fields.Selection([
        ('service_request', 'Service Request'),
        ('incident', 'Incident – Operasional TI'),
        ('security_incident', 'Incident – Keamanan Informasi'),
    ], string='Type Name', default='incident', index=True)
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)
    description = fields.Text()
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')
    ticket_ids = fields.One2many('helpdesk.ticket', 'service_id', string='Case Tiket')

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            self.type_code = self.type_id.code
            mapping = {
                'TYP-01': 'service_request',
                'TYP-02': 'incident',
                'TYP-03': 'security_incident',
            }
            if self.type_id.code in mapping:
                self.ticket_type = mapping[self.type_id.code]

    @api.onchange('type_code')
    def _onchange_type_code(self):
        mapping = {
            'TYP-01': 'service_request',
            'TYP-02': 'incident',
            'TYP-03': 'security_incident',
        }
        if self.type_code in mapping:
            self.ticket_type = mapping[self.type_code]
        if self.type_code and not self.type_id:
            tt = self.env['helpdesk.ticket.type'].search([('code', '=', self.type_code)], limit=1)
            if tt:
                self.type_id = tt.id

    @api.onchange('ticket_type')
    def _onchange_ticket_type(self):
        mapping = {
            'service_request': 'TYP-01',
            'incident': 'TYP-02',
            'security_incident': 'TYP-03',
        }
        if self.ticket_type in mapping and not self.type_code:
            self.type_code = mapping[self.ticket_type]
            tt = self.env['helpdesk.ticket.type'].search([('code', '=', self.type_code)], limit=1)
            if tt:
                self.type_id = tt.id

    @api.model_create_multi
    def create(self, vals_list):
        mapping_code = {
            'TYP-01': 'service_request',
            'TYP-02': 'incident',
            'TYP-03': 'security_incident',
        }
        mapping_type = {
            'service_request': 'TYP-01',
            'incident': 'TYP-02',
            'security_incident': 'TYP-03',
        }
        records = self.browse()
        for vals in vals_list:
            if vals.get('catalog_code') and not vals.get('code'):
                vals['code'] = vals.get('catalog_code')
            if vals.get('service_catalog_name') and not vals.get('name'):
                vals['name'] = vals.get('service_catalog_name')
            if vals.get('code') and not vals.get('catalog_code'):
                vals['catalog_code'] = vals.get('code')
            if vals.get('name') and not vals.get('service_catalog_name'):
                vals['service_catalog_name'] = vals.get('name')

            if vals.get('type_code') and not vals.get('type_id'):
                tt = self.env['helpdesk.ticket.type'].search([('code', '=', vals['type_code'])], limit=1)
                if tt:
                    vals['type_id'] = tt.id
            if vals.get('type_id') and not vals.get('type_code'):
                tt = self.env['helpdesk.ticket.type'].browse(vals['type_id'])
                if tt.exists():
                    vals['type_code'] = tt.code
            if vals.get('type_code') and not vals.get('ticket_type'):
                vals['ticket_type'] = mapping_code.get(vals['type_code'], 'incident')
            elif vals.get('ticket_type') and not vals.get('type_code'):
                vals['type_code'] = mapping_type.get(vals['ticket_type'])
                if not vals.get('type_id') and vals.get('type_code'):
                    tt = self.env['helpdesk.ticket.type'].search([('code', '=', vals['type_code'])], limit=1)
                    if tt:
                        vals['type_id'] = tt.id

            code = vals.get('code')
            if code:
                existing = self.search([('code', '=', code)], limit=1)
                if existing:
                    existing.write(vals)
                    records |= existing
                    continue

            new_rec = super(HelpdeskService, self).create([vals])
            records |= new_rec
        return records

    def write(self, vals):
        mapping_code = {
            'TYP-01': 'service_request',
            'TYP-02': 'incident',
            'TYP-03': 'security_incident',
        }
        mapping_type = {
            'service_request': 'TYP-01',
            'incident': 'TYP-02',
            'security_incident': 'TYP-03',
        }
        if vals.get('catalog_code') and 'code' not in vals:
            vals['code'] = vals.get('catalog_code')
        if vals.get('service_catalog_name') and 'name' not in vals:
            vals['name'] = vals.get('service_catalog_name')
        if vals.get('type_code') and 'type_id' not in vals:
            tt = self.env['helpdesk.ticket.type'].search([('code', '=', vals['type_code'])], limit=1)
            if tt:
                vals['type_id'] = tt.id
        if vals.get('type_id') and 'type_code' not in vals:
            tt = self.env['helpdesk.ticket.type'].browse(vals['type_id'])
            if tt.exists():
                vals['type_code'] = tt.code
        if vals.get('type_code') and 'ticket_type' not in vals:
            vals['ticket_type'] = mapping_code.get(vals['type_code'], 'incident')
        elif vals.get('ticket_type') and 'type_code' not in vals:
            vals['type_code'] = mapping_type.get(vals['ticket_type'])
            if 'type_id' not in vals and vals.get('type_code'):
                tt = self.env['helpdesk.ticket.type'].search([('code', '=', vals['type_code'])], limit=1)
                if tt:
                    vals['type_id'] = tt.id
        return super().write(vals)

    def name_get(self):
        result = []
        for record in self:
            label = f"[{record.code}] {record.name}" if record.code else record.name
            result.append((record.id, label))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def _compute_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('service_id', 'in', self.ids)], ['service_id'], ['service_id'])
        mapped_data = {data['service_id'][0]: data['service_id_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('service_id', '=', self.id)],
            'context': {'default_service_id': self.id},
        }
