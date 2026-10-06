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

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for emp in employees:
            if not emp.user_id:
                email = emp.work_email or emp.private_email
                if email:
                    user = self.env['res.users'].sudo().search([
                        '|', ('email', '=ilike', email), ('login', '=ilike', email)
                    ], limit=1)
                    if user:
                        emp.user_id = user.id
                if not emp.user_id and emp.name:
                    user = self.env['res.users'].sudo().search([('name', '=ilike', emp.name)], limit=1)
                    if user:
                        emp.user_id = user.id
        return employees


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    kadept_id = fields.Many2one(
        'hr.employee',
        string='Head of Placement / Kepala Dept.',
        tracking=True,
        help='Kepala Departemen (BPO / Target Dept) untuk approval Change Request'
    )
