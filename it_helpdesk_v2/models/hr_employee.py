from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    kadept_id = fields.Many2one(
        'hr.employee',
        string='Head of Placement / Kepala Dept.',
        tracking=True,
        help='Atasan Kepala Departemen untuk approval Change Request'
    )
    indirect_manager_id = fields.Many2one(
        'hr.employee',
        string='Indirect Manager',
        tracking=True,
        help='Manager Tidak Langsung untuk approval Change Request'
    )


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    kadept_id = fields.Many2one(
        'hr.employee',
        string='Head of Placement / Kepala Dept.',
        tracking=True,
        help='Kepala Departemen (BPO / Target Dept) untuk approval Change Request'
    )
