from odoo import api, fields, models
from odoo.osv import expression


class HelpdeskCategory(models.Model):
    _name = 'helpdesk.category'
    _description = 'Helpdesk Category'
    _order = 'code, name'
    _rec_name = 'name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code', index=True)
    category_code = fields.Char(string='Category Code (Import Alias)')
    category_name = fields.Char(string='Category Name (Import Alias)')
    service_id = fields.Many2one('helpdesk.service', string='Service Catalog')
    service_catalog_code = fields.Char(string='Service Catalog Code')
    service_catalog_name = fields.Char(string='Service Catalog Name (Import Alias)')
    type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type', related='service_id.type_id', store=True, readonly=True)
    type_code = fields.Char(string='Type Code', related='service_id.type_code', store=True, readonly=True)
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Jumlah Tiket / Case')
    ticket_ids = fields.One2many('helpdesk.ticket', 'category_id', string='Case Tiket')

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if vals.get('category_code') and not vals.get('code'):
                vals['code'] = vals.get('category_code')
            if vals.get('category_name') and not vals.get('name'):
                vals['name'] = vals.get('category_name')
            if vals.get('code') and not vals.get('category_code'):
                vals['category_code'] = vals.get('code')
            if vals.get('name') and not vals.get('category_name'):
                vals['category_name'] = vals.get('name')

            if vals.get('service_catalog_code') and not vals.get('service_id'):
                srv = self.env['helpdesk.service'].search([('code', '=', vals['service_catalog_code'])], limit=1)
                if srv:
                    vals['service_id'] = srv.id
            elif vals.get('service_id') and not vals.get('service_catalog_code'):
                srv = self.env['helpdesk.service'].browse(vals['service_id'])
                if srv.exists():
                    vals['service_catalog_code'] = srv.code

            code = vals.get('code')
            if code:
                existing = self.search([('code', '=', code)], limit=1)
                if existing:
                    existing.write(vals)
                    records |= existing
                    continue

            new_rec = super(HelpdeskCategory, self).create([vals])
            records |= new_rec
        return records

    def write(self, vals):
        if vals.get('category_code') and 'code' not in vals:
            vals['code'] = vals.get('category_code')
        if vals.get('category_name') and 'name' not in vals:
            vals['name'] = vals.get('category_name')
        if vals.get('service_catalog_code') and 'service_id' not in vals:
            srv = self.env['helpdesk.service'].search([('code', '=', vals['service_catalog_code'])], limit=1)
            if srv:
                vals['service_id'] = srv.id
        elif vals.get('service_id') and 'service_catalog_code' not in vals:
            srv = self.env['helpdesk.service'].browse(vals['service_id'])
            if srv.exists():
                vals['service_catalog_code'] = srv.code
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
        ticket_data = self.env['helpdesk.ticket'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = {data['category_id'][0]: data['category_id_count'] for data in ticket_data}
        for record in self:
            record.ticket_count = mapped_data.get(record.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tiket Case: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,kanban,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }


class HelpdeskSubcategory(models.Model):
    _name = 'helpdesk.subcategory'
    _description = 'Helpdesk Sub-Category'
    _order = 'code, name'
    _rec_name = 'name'

    name = fields.Char(string='Sub Category Name', required=True)
    code = fields.Char(string='Sub Category Code', index=True)
    subcategory_code = fields.Char(string='Sub Category Code (Import Alias)')
    subcategory_name = fields.Char(string='Sub Category Name (Import Alias)')
    category_id = fields.Many2one('helpdesk.category', string='Category', required=True)
    category_code = fields.Char(string='Category Code')
    category_name = fields.Char(string='Category Name (Import Alias)')
    service_id = fields.Many2one('helpdesk.service', string='Service Catalog', related='category_id.service_id', store=True, readonly=True)
    service_catalog_code = fields.Char(string='Service Catalog Code', related='category_id.service_catalog_code', store=True, readonly=True)
    service_catalog_name = fields.Char(string='Service Catalog Name (Import Alias)')
    type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type', related='category_id.type_id', store=True, readonly=True)
    type_code = fields.Char(string='Type Code', related='category_id.type_code', store=True, readonly=True)
    engineer_id = fields.Many2one('res.users', string='Default PIC IT / Engineer')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if vals.get('subcategory_code') and not vals.get('code'):
                vals['code'] = vals.get('subcategory_code')
            if vals.get('subcategory_name') and not vals.get('name'):
                vals['name'] = vals.get('subcategory_name')
            if vals.get('code') and not vals.get('subcategory_code'):
                vals['subcategory_code'] = vals.get('code')
            if vals.get('name') and not vals.get('subcategory_name'):
                vals['subcategory_name'] = vals.get('name')

            if vals.get('category_code') and not vals.get('category_id'):
                cat = self.env['helpdesk.category'].search([('code', '=', vals['category_code'])], limit=1)
                if cat:
                    vals['category_id'] = cat.id
            elif vals.get('category_id') and not vals.get('category_code'):
                cat = self.env['helpdesk.category'].browse(vals['category_id'])
                if cat.exists():
                    vals['category_code'] = cat.code

            code = vals.get('code')
            if code:
                existing = self.search([('code', '=', code)], limit=1)
                if existing:
                    existing.write(vals)
                    records |= existing
                    continue

            new_rec = super(HelpdeskSubcategory, self).create([vals])
            records |= new_rec
        return records

    def write(self, vals):
        if vals.get('subcategory_code') and 'code' not in vals:
            vals['code'] = vals.get('subcategory_code')
        if vals.get('subcategory_name') and 'name' not in vals:
            vals['name'] = vals.get('subcategory_name')
        if vals.get('category_code') and 'category_id' not in vals:
            cat = self.env['helpdesk.category'].search([('code', '=', vals['category_code'])], limit=1)
            if cat:
                vals['category_id'] = cat.id
        elif vals.get('category_id') and 'category_code' not in vals:
            cat = self.env['helpdesk.category'].browse(vals['category_id'])
            if cat.exists():
                vals['category_code'] = cat.code
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
