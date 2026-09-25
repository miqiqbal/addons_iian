from datetime import datetime, timedelta
from odoo import _, api, fields, models
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
        [('scope', 'Scope'), ('other', 'Other'), ('authorization', 'Authorization'),('Training/SOP/Socialization', 'Training/SOP/Socialization'), ('design', 'Design'), ('development', 'Development'), ('masterdata', 'Master Data')], string='Impact On', tracking=True)

    enable_auto_close = fields.Boolean(string='Enable Auto Close', default=True)
    auto_close_deadline = fields.Datetime(string='Batas Auto Close', copy=False, readonly=True)
    closed_date = fields.Datetime(string='Closed Date', copy=False, readonly=True)
    estimated_completion_date = fields.Date(string='Estimasi Tanggal Penyelesaian', tracking=True)


    @api.model
    def _default_manager_it(self):
        it_manager_group = self.env.ref('it_helpdesk_v2.group_helpdesk_it_manager', raise_if_not_found=False)
        if it_manager_group:
            user = self.env['res.users'].search([('groups_id', 'in', [it_manager_group.id])], limit=1)
            if user:
                return user.id
        manager_group = self.env.ref('it_helpdesk_v2.group_helpdesk_manager', raise_if_not_found=False)
        if manager_group:
            user = self.env['res.users'].search([('groups_id', 'in', [manager_group.id])], limit=1)
            if user:
                return user.id
        return False


    location_id = fields.Many2one('helpdesk.location', string='Departemen Terkait', tracking=True)
    department_id = fields.Many2one('hr.department', string='Departemen Terkait (Old)', tracking=True)
    dept_manager_id = fields.Many2one('res.users', string='Manager Departemen [Terkait]', tracking=True)
    manager_it_id = fields.Many2one(
        'res.users', string='Manager IT', tracking=True,
        default=_default_manager_it,
        domain=lambda self: [('groups_id', 'in', [
            self.env.ref('it_helpdesk_v2.group_helpdesk_it_manager', raise_if_not_found=False).id if self.env.ref('it_helpdesk_v2.group_helpdesk_it_manager', raise_if_not_found=False) else self.env.ref('it_helpdesk_v2.group_helpdesk_manager').id
        ])]
    )
    engineer_id = fields.Many2one('res.users', string='Engineer / PIC IT', tracking=True)

    pic_teknis_id = fields.Char(string='PIC Teknis', tracking=True)

    queue_number = fields.Integer(string='Nomor Antrian CR', copy=False, readonly=True, tracking=True)
    current_processing_queue_number = fields.Integer(string='Antrian Sedang Dikerjakan Saat Ini', compute='_compute_queue_info')
    queue_ahead_count = fields.Integer(string='Antrian di Depan Anda', compute='_compute_queue_info')

    can_approve_dept = fields.Boolean(compute='_compute_approval_rights')
    can_approve_it = fields.Boolean(compute='_compute_approval_rights')
    can_reopen = fields.Boolean(compute='_compute_can_reopen')

    def _compute_approval_rights(self):
        is_superuser = self.env.is_superuser()
        for cr in self:
            # Stage 1 (dept_approval): Strictly restricted to designated dept_manager_id
            cr.can_approve_dept = is_superuser or (cr.dept_manager_id and cr.dept_manager_id.id == self.env.uid)
            # Stage 2 (it_approval): Restricted strictly to designated manager_it_id or IT Manager role
            cr.can_approve_it = is_superuser or (cr.manager_it_id and cr.manager_it_id.id == self.env.uid) or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_it_manager')

    @api.depends('state', 'created_by')
    def _compute_can_reopen(self):
        is_superuser = self.env.is_superuser()
        user = self.env.user
        for cr in self:
            is_manager = user.has_group('it_helpdesk_v2.group_helpdesk_it_manager') or user.has_group('it_helpdesk_v2.group_helpdesk_manager')
            is_requester = (cr.created_by and cr.created_by.id == user.id) or (cr.create_uid and cr.create_uid.id == user.id)

            if cr.state == 'done':
                cr.can_reopen = is_superuser or is_manager or is_requester
            elif cr.state == 'closed':
                cr.can_reopen = is_superuser or is_manager
            else:
                cr.can_reopen = False


    @api.model
    def _reindex_active_queue(self):
        """Mengurutkan ulang nomor antrian aktif (1, 2, 3...) untuk CR berstatus in_progress"""
        active_crs = self.search([('state', '=', 'in_progress')], order='queue_number asc, id asc')
        for index, cr in enumerate(active_crs, start=1):
            if cr.queue_number != index:
                cr.write({'queue_number': index})

    def action_reopen_progress(self):
        for cr in self:
            if not cr.can_reopen:
                raise UserError(_("Anda tidak memiliki hak akses untuk mengembalikan pengajuan ini ke Progress."))
            if cr.state not in ('done', 'closed'):
                raise UserError(_("Pengajuan Change Request hanya dapat dikembalikan ke Progress dari status Done atau Closed."))

            vals = {
                'state': 'in_progress',
                'auto_close_deadline': False,
            }
            # Jika dikembalikan dari status CLOSED -> dapatkan nomor antrian BARU (terakhir)
            if cr.state == 'closed':
                max_cr = self.search([('queue_number', '>', 0)], order='queue_number desc', limit=1)
                vals['queue_number'] = (max_cr.queue_number + 1) if max_cr else 1
            cr.write(vals)
        self._reindex_active_queue()






    def _compute_queue_info(self):
        in_progress_crs = self.search([('state', '=', 'in_progress')], order='queue_number asc, id asc')
        active_queue_numbers = [cr.queue_number for cr in in_progress_crs if cr.queue_number]
        min_queue = min(active_queue_numbers) if active_queue_numbers else 0

        for cr in self:
            cr.current_processing_queue_number = min_queue
            if cr.state == 'in_progress' and cr.queue_number:
                cr.queue_ahead_count = sum(1 for other in in_progress_crs if other.queue_number and other.queue_number < cr.queue_number)
            else:
                cr.queue_ahead_count = 0



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

    def _send_dept_approval_email(self):
        template = self.env.ref('it_helpdesk_v2.email_template_cr_dept_approval', raise_if_not_found=False)
        if not template:
            return
        for cr in self:
            if cr.dept_manager_id and cr.dept_manager_id.email:
                try:
                    template.send_mail(cr.id, force_send=True)
                except Exception:
                    pass

    def _send_it_approval_email(self):
        template = self.env.ref('it_helpdesk_v2.email_template_cr_it_approval', raise_if_not_found=False)
        if not template:
            return
        for cr in self:
            if cr.manager_it_id and cr.manager_it_id.email:
                try:
                    template.send_mail(cr.id, force_send=True)
                except Exception:
                    pass

    def _send_rejected_email(self):
        template = self.env.ref('it_helpdesk_v2.email_template_cr_rejected', raise_if_not_found=False)
        if not template:
            return
        for cr in self:
            if cr.email:
                try:
                    template.send_mail(cr.id, force_send=True)
                except Exception:
                    pass

    def _send_done_email(self):
        template = self.env.ref('it_helpdesk_v2.email_template_cr_done', raise_if_not_found=False)
        if not template:
            return
        for cr in self:
            if cr.email:
                try:
                    template.send_mail(cr.id, force_send=True)
                except Exception:
                    pass

    def action_publish(self):
        for cr in self:
            if not cr.code:
                cr.code = cr.get_next_cr_code()
            cr.posted_date = fields.Datetime.now()
            cr.state = 'dept_approval'
            cr._send_dept_approval_email()


    def action_submit(self):
        for cr in self:
            if not cr.code:
                cr.code = cr.get_next_cr_code()
            cr.state = 'dept_approval'
            cr.posted_date = fields.Datetime.now()
            cr._send_dept_approval_email()

    def action_approve_dept(self):
        for cr in self:
            if not cr.can_approve_dept:
                raise UserError(_("Hanya Manager Departemen terkait (%s) yang berhak menyetujui pengajuan ini!") % (cr.dept_manager_id.name or 'Manager Dept'))
            cr.state = 'it_approval'
            cr._send_it_approval_email()

    def action_approve_it(self):
        for cr in self:
            if not cr.can_approve_it:
                raise UserError(_("Hanya Manager IT (%s) yang berhak menyetujui pengajuan ini!") % (cr.manager_it_id.name or 'Manager IT'))
            if not cr.engineer_id:
                raise UserError(_("Silakan pilih Engineer / PIC IT yang ditugaskan terlebih dahulu!"))
            if not cr.estimated_completion_date:
                raise UserError(_("Silakan pilih Estimasi Tanggal Penyelesaian terlebih dahulu sebelum menyetujui pengajuan ini!"))
            if not cr.queue_number:
                max_cr = self.search([('queue_number', '>', 0)], order='queue_number desc', limit=1)
                cr.queue_number = (max_cr.queue_number + 1) if max_cr else 1
            cr.state = 'in_progress'
        self._reindex_active_queue()


    def action_start_progress(self):
        for cr in self:
            if not cr.queue_number:
                max_cr = self.search([('queue_number', '>', 0)], order='queue_number desc', limit=1)
                cr.queue_number = (max_cr.queue_number + 1) if max_cr else 1
            cr.state = 'in_progress'
        self._reindex_active_queue()

    def _compute_auto_close_deadline(self):
        """Menghitung 3 hari kerja pasca status Done untuk Auto-Close CR"""
        now = fields.Datetime.now()
        count = 0
        cur_date = now.date()
        while count < 3:
            cur_date += timedelta(days=1)
            if cur_date.weekday() < 5:  # Senin-Jumat
                count += 1
        return datetime.combine(cur_date, now.time())

    def action_done(self):
        for cr in self:
            vals = {'state': 'done', 'queue_number': 0}
            if cr.enable_auto_close:
                vals['auto_close_deadline'] = cr._compute_auto_close_deadline()
            cr.write(vals)
            cr._send_done_email()
        self._reindex_active_queue()

    def init(self):
        super().init()
        # Reset queue_number to 0 for closed, done, or rejected CRs in database
        self.env.cr.execute("UPDATE helpdesk_change_request SET queue_number = 0 WHERE state IN ('closed', 'rejected', 'done');")
        self._reindex_active_queue()

    def action_close(self):
        now = fields.Datetime.now()
        for cr in self:
            cr.write({
                'state': 'closed',
                'closed_date': now,
                'auto_close_deadline': False,
                'queue_number': 0,
            })
        self._reindex_active_queue()

    @api.model
    def _cron_auto_close_change_requests(self):
        """Cron Job: Penutupan otomatis Change Request berstatus Done setelah 3 hari kerja"""
        now = fields.Datetime.now()
        crs = self.search([
            ('state', '=', 'done'),
            ('enable_auto_close', '=', True),
            ('auto_close_deadline', '!=', False),
            ('auto_close_deadline', '<=', now)
        ])
        for cr in crs:
            cr.write({
                'state': 'closed',
                'closed_date': now,
                'auto_close_deadline': False,
                'queue_number': 0,
            })
            cr.message_post(
                body=_("🤖 <b>Auto Close CR Otomatis</b><br/>Change Request telah ditutup secara otomatis oleh sistem setelah melewati batas waktu 3 hari kerja pasca penyelesaian."),
                message_type='notification'
            )
        self._reindex_active_queue()

    def action_reject(self):
        for cr in self:
            cr.state = 'rejected'
            cr.queue_number = 0
            cr._send_rejected_email()
        self._reindex_active_queue()

    def action_draft(self):
        self.write({'state': 'draft', 'queue_number': 0})
        self._reindex_active_queue()


