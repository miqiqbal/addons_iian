from odoo import api, fields, models
from odoo.exceptions import UserError


class HelpdeskChangeRequest(models.Model):
    _name = 'helpdesk.change.request'
    _description = 'Helpdesk Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(readonly=True, default='New Change Request', tracking=True)
    code = fields.Char(string='No. CR', readonly=True, copy=False, tracking=True)
    request_identification = fields.Text(string='Request Identification')
    category = fields.Selection(
        [('form', 'Form'), ('enhancement', 'Enhancement'), ('configuration', 'Konfigurasi')],
        string='Kategori', tracking=True)
    module = fields.Char(string='Module', tracking=True)
    impact_on = fields.Selection(
        [('scope', 'Scope'), ('other', 'Other')], string='Impact On', tracking=True)

    department_id = fields.Many2one('hr.department', string='Departemen Terkait', tracking=True)
    dept_manager_id = fields.Many2one('res.users', string='Manager Departemen [Terkait]', compute='_compute_dept_manager', store=True, readonly=False, tracking=True)
    manager_it_id = fields.Many2one('res.users', string='Manager IT', tracking=True)
    engineer_id = fields.Many2one('res.users', string='Engineer / PIC IT', tracking=True)
    pic_teknis_id = fields.Char(string='PIC Teknis', tracking=True)

    created_by = fields.Many2one(
        'res.users', string='Dibuat Oleh', default=lambda self: self.env.user)
    email = fields.Char(
        string='E-Mail',
        default=lambda self: self.env.user.email or self.env.user.partner_id.email)
    phone = fields.Char(
        string='Phone',
        default=lambda self: self.env.user.phone or self.env.user.mobile or self.env.user.partner_id.phone or self.env.user.partner_id.mobile)

    @api.onchange('created_by')
    def _onchange_created_by(self):
        if self.created_by:
            self.email = self.created_by.email or self.created_by.partner_id.email or ''
            self.phone = self.created_by.phone or self.created_by.mobile or self.created_by.partner_id.phone or self.created_by.partner_id.mobile or ''
    note = fields.Text(string='Note')
    rejection_reason = fields.Text(string='Alasan Penolakan')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachment File')
    analysis_and_solution = fields.Html(string='Analysis & Solution')
    propose_solution = fields.Html(string='Propose Solution')

    state = fields.Selection(
        [('draft', 'Draft'),
         ('dept_approval', 'Approval Manager Dept'),
         ('it_approval', 'Approval Manager IT'),
         ('in_progress', 'In Progress (Engineering)'),
         ('done', 'Done'),
         ('closed', 'Closed'),
         ('rejected', 'Rejected')],
        default='draft', tracking=True, string='Status')
    posted_date = fields.Datetime()

    @api.depends('department_id')
    def _compute_dept_manager(self):
        for cr in self:
            if cr.department_id and cr.department_id.manager_id and cr.department_id.manager_id.user_id:
                cr.dept_manager_id = cr.department_id.manager_id.user_id.id

    def get_next_cr_code(self):
        self.ensure_one()
        seq = self.env['ir.sequence'].next_by_code('it.helpdesk.change.request') or '001'
        date_str = fields.Date.today().strftime('%Y%m%d')
        return 'HKICR-%s-%s' % (seq, date_str)

    def action_publish(self):
        for cr in self:
            if not cr.code:
                cr.code = cr.get_next_cr_code()
            cr.posted_date = fields.Datetime.now()
            if cr.engineer_id:
                cr.state = 'in_progress'
            else:
                cr.state = 'dept_approval'

    def action_submit(self):
        for cr in self:
            if not cr.code:
                cr.code = cr.get_next_cr_code()
            cr.state = 'dept_approval'
            cr.posted_date = fields.Datetime.now()

    def action_approve_dept(self):
        for cr in self:
            cr.state = 'it_approval'

    def action_approve_it(self):
        for cr in self:
            # Auto assign to engineer if not set
            if not cr.engineer_id:
                cr.engineer_id = self.env.uid
            cr.state = 'in_progress'

    def action_done(self):
        for cr in self:
            cr.state = 'done'

    def action_close(self):
        for cr in self:
            cr.state = 'closed'

    def action_reject(self):
        for cr in self:
            cr.state = 'rejected'

    def action_draft(self):
        self.write({'state': 'draft'})
