from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    initials = fields.Char(string='Initial')


class ResUsers(models.Model):
    _inherit = 'res.users'

    initials = fields.Char(related='partner_id.initials', readonly=False, store=True, string='Initial')

    helpdesk_role = fields.Selection([
        ('user', 'Employee / Requester'),
        ('agent', 'Engineer'),
        ('manager', 'Helpdesk Officer')
    ], string='Role / Peran', compute='_compute_helpdesk_role', inverse='_inverse_helpdesk_role', store=True, readonly=False)

    role_id = fields.Char(string='Role / Peran System')
    max_daily_quota = fields.Integer(
        string='Batas Kuota Harian (Tiket)', default=5,
        help='Jumlah tiket maksimal per hari yang dapat ditugaskan ke engineer'
    )


    @api.depends('groups_id')
    def _compute_helpdesk_role(self):
        manager_group = self.env.ref('it_helpdesk_v2.group_helpdesk_manager', raise_if_not_found=False)
        agent_group = self.env.ref('it_helpdesk_v2.group_helpdesk_agent', raise_if_not_found=False)
        user_group = self.env.ref('it_helpdesk_v2.group_helpdesk_user', raise_if_not_found=False)
        for user in self:
            if manager_group and manager_group in user.groups_id:
                user.helpdesk_role = 'manager'
            elif agent_group and agent_group in user.groups_id:
                user.helpdesk_role = 'agent'
            elif user_group and user_group in user.groups_id:
                user.helpdesk_role = 'user'
            else:
                user.helpdesk_role = 'user'

    def _inverse_helpdesk_role(self):
        manager_group = self.env.ref('it_helpdesk_v2.group_helpdesk_manager', raise_if_not_found=False)
        agent_group = self.env.ref('it_helpdesk_v2.group_helpdesk_agent', raise_if_not_found=False)
        user_group = self.env.ref('it_helpdesk_v2.group_helpdesk_user', raise_if_not_found=False)
        for user in self:
            groups_to_remove = [g.id for g in (manager_group | agent_group | user_group) if g]
            if user.helpdesk_role == 'manager' and manager_group:
                user.groups_id = [(3, g_id) for g_id in groups_to_remove] + [(4, manager_group.id)]
            elif user.helpdesk_role == 'agent' and agent_group:
                user.groups_id = [(3, g_id) for g_id in groups_to_remove] + [(4, agent_group.id)]
            elif user.helpdesk_role == 'user' and user_group:
                user.groups_id = [(3, g_id) for g_id in groups_to_remove] + [(4, user_group.id)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('email') and (not vals.get('login') or vals.get('login') == 'New'):
                vals['login'] = vals['email']
            elif vals.get('login') and not vals.get('email'):
                vals['email'] = vals['login']
        users = super().create(vals_list)
        for user in users:
            user._sync_hr_employee()
        return users

    def write(self, vals):
        if vals.get('email') and 'login' not in vals:
            vals['login'] = vals['email']
        res = super().write(vals)
        if any(f in vals for f in ['name', 'email', 'phone', 'function']):
            for user in self:
                user._sync_hr_employee()
        return res

    def _sync_hr_employee(self):
        """Menghubungkan/membuat data hr.employee secara otomatis jika belum ada."""
        self.ensure_one()
        if self.share or not self.active or self.id in (1, 2):  # Skip system users if needed
            pass
        Emp = self.env['hr.employee'].sudo()
        emp = Emp.search([('user_id', '=', self.id)], limit=1)
        email = self.email or self.login
        if not emp and email:
            emp = Emp.search(['|', ('work_email', '=ilike', email), ('private_email', '=ilike', email)], limit=1)
        if not emp and self.name:
            emp = Emp.search([('name', '=ilike', self.name)], limit=1)

        emp_vals = {
            'name': self.name,
            'user_id': self.id,
            'work_email': email or '',
            'work_phone': self.phone or '',
            'job_title': self.function or '',
        }
        if emp:
            update_vals = {}
            if not emp.user_id:
                update_vals['user_id'] = self.id
            if not emp.work_email and emp_vals['work_email']:
                update_vals['work_email'] = emp_vals['work_email']
            if update_vals:
                emp.write(update_vals)
        else:
            if self.name:
                Emp.create(emp_vals)

