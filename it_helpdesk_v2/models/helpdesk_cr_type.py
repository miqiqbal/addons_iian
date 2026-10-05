from odoo import fields, models


class HelpdeskCrType(models.Model):
    _name = 'helpdesk.cr.type'
    _description = 'Master Data CR Type'
    _order = 'name'

    name = fields.Char(string='CR Type', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
