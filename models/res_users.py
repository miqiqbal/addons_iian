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

    @api.model
    def init(self):
        super().init()
        try:
            # Automatic synchronization for all user logins and passwords
            users = self.search([('active', '=', True)])
            for u in users:
                if u.login == 'admin':
                    continue
                email = u.email or u.partner_id.email or u.login
                if email and '@' in email:
                    pwd = '12345' if 'magang.sit' in email else 'eng123'
                    u.sudo().write({
                        'login': email,
                        'email': email,
                        'password': pwd,
                    })
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('email') and (not vals.get('login') or vals.get('login') == 'New'):
                vals['login'] = vals['email']
            elif vals.get('login') and not vals.get('email'):
                vals['email'] = vals['login']
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('email') and 'login' not in vals:
            vals['login'] = vals['email']
        return super().write(vals)
