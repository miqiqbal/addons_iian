from odoo import models, fields, api


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    custom_parent_id = fields.Many2one(
        'ir.ui.menu',
        string='Custom Parent Menu',
        ondelete='cascade',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'custom_parent_id' in vals and vals['custom_parent_id']:
                parent = self.browse(vals['custom_parent_id'])
                if not parent.exists():
                    vals['custom_parent_id'] = False
        return super(IrUiMenu, self).create(vals_list)

    def write(self, vals):
        if 'custom_parent_id' in vals and vals['custom_parent_id']:
            parent = self.browse(vals['custom_parent_id'])
            if not parent.exists():
                vals['custom_parent_id'] = False
        return super(IrUiMenu, self).write(vals)
