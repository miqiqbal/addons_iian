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

    # Detail Pengajuan
    cr_type_id = fields.Many2one('helpdesk.cr.type', string='CR Type', tracking=True)
    category_id = fields.Many2one('helpdesk.category', string='Category', tracking=True)
    subcategory_id = fields.Many2one('helpdesk.subcategory', string='Sub Category', domain="[('category_id', '=?', category_id)]", tracking=True)
    target_department_id = fields.Many2one('hr.department', string='CR to Departement', tracking=True)
    impact_on = fields.Selection(
        [
            ('scope', 'Scope'),
            ('other', 'Other'),
            ('authorization', 'Authorization'),
            ('Training/SOP/Socialization', 'Training/SOP/Socialization'),
            ('design', 'Design'),
            ('development', 'Development'),
            ('masterdata', 'Master Data')
        ],
        string='Impact On',
        tracking=True
    )
    module = fields.Char(string='Module', tracking=True)

    enable_auto_close = fields.Boolean(string='Enable Auto Close', default=True)
    auto_close_deadline = fields.Datetime(string='Batas Auto Close', copy=False, readonly=True)
    closed_date = fields.Datetime(string='Closed Date', copy=False)
    resolved_date = fields.Datetime(string='Tanggal Done', copy=False)
    estimated_completion_date = fields.Date(string='Estimasi Tanggal Penyelesaian', tracking=True)

    # ---------------------------------------------------------
    # Helper Methods to Resolve Approver Users Dynamically
    # ---------------------------------------------------------
    def _get_dept_manager_user(self, employee):
        """Mendapatkan User Approval Manager Dept Terkait:
        1. Cek indirect_manager dan kadep_id.
        2. Jika indirect_manager != kadep_id -> indirect_manager.user_id.
        3. Jika indirect_manager == kadep_id -> parent_id.user_id (Direct Manager).
        4. Fallback jika kosong.
        """
        if not employee:
            return False
        kadep = getattr(employee, 'kadep_id', False) or getattr(employee, 'kadept_id', False) or getattr(employee, 'head_of_placement_id', False)
        indirect_mgr = getattr(employee, 'indirect_manager', False) or getattr(employee, 'indirect_manager_id', False)
        direct_mgr = getattr(employee, 'parent_id', False) or getattr(employee, 'expense_manager_id', False) or getattr(employee, 'leave_manager_id', False)

        # Step 1: Jika Indirect Manager != Head of Placement -> gunakan Indirect Manager
        if indirect_mgr and indirect_mgr != kadep and indirect_mgr.user_id:
            return indirect_mgr.user_id.id

        # Step 2: Jika Sama -> gunakan Direct Manager
        if direct_mgr and direct_mgr.user_id:
            return direct_mgr.user_id.id

        # Step 3: Fallbacks
        if kadep and kadep.user_id:
            return kadep.user_id.id
        if employee.department_id and employee.department_id.manager_id and employee.department_id.manager_id.user_id:
            return employee.department_id.manager_id.user_id.id
        return False

    def _get_kadept_manager_user(self, employee):
        """Mendapatkan User Approval Kadept Terkait (Head of Placement / kadep_id)"""
        if not employee:
            return False
        kadep = getattr(employee, 'kadep_id', False) or getattr(employee, 'kadept_id', False) or getattr(employee, 'head_of_placement_id', False)
        if kadep and kadep.user_id:
            return kadep.user_id.id
        if employee.department_id and employee.department_id.manager_id and employee.department_id.manager_id.user_id:
            return employee.department_id.manager_id.user_id.id
        return False

    def _get_bpo_kadept_manager_user(self, department):
        """Mendapatkan User Approval Kadept BPO berdasarkan CR to Departement (target_department_id)"""
        if not department:
            return False
        kadep = getattr(department, 'kadep_id', False) or getattr(department, 'kadept_id', False)
        if kadep and kadep.user_id:
            return kadep.user_id.id
        if department.manager_id and department.manager_id.user_id:
            return department.manager_id.user_id.id

        # Cari karyawan di departemen target dengan jabatan Kadept
        kadept_emp = self.env['hr.employee'].search([
            ('department_id', '=', department.id),
            '|', '|',
            ('job_id.name', 'ilike', 'Kepala Departemen'),
            ('job_id.name', 'ilike', 'Kadept'),
            ('job_title', 'ilike', 'Kepala Departemen')
        ], limit=1)
        if kadept_emp and kadept_emp.user_id:
            return kadept_emp.user_id.id
        return False

    @api.model
    def _default_dept_manager(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return self._get_dept_manager_user(employee)

    @api.model
    def _default_kadept_manager(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return self._get_kadept_manager_user(employee)

    @api.model
    def _default_manager_it(self):
        # 1. Cek karyawan dengan job_id ID 4992 atau nama 'Manager IT'
        emp = self.env['hr.employee'].search([
            '|', ('job_id', '=', 4992),
            ('job_id.name', 'ilike', 'Manager IT')
        ], limit=1)
        if emp and emp.user_id:
            return emp.user_id.id
        # 2. Cek user dengan group IT Manager
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

    @api.model
    def _default_kadept_it_manager(self):
        # 1. Cek karyawan dengan job_id ID 2174 atau nama 'Kepala Departemen Sistem, IT & Digitalisasi'
        emp = self.env['hr.employee'].search([
            '|', ('job_id', '=', 2174),
            '|', ('job_id.name', 'ilike', 'Kepala Departemen Sistem, IT & Digitalisasi'),
            ('job_id.name', 'ilike', 'Kepala Departemen Sistem')
        ], limit=1)
        if emp and emp.user_id:
            return emp.user_id.id
        # 2. Fallback: Kadept departemen IT / Digitalisasi
        it_dept = self.env['hr.department'].search([
            '|', '|',
            ('name', 'ilike', 'Sistem, TI'),
            ('name', 'ilike', 'Sistem, IT'),
            ('name', 'ilike', 'Digitalisasi')
        ], limit=1)
        if it_dept:
            bpo_user = self._get_bpo_kadept_manager_user(it_dept)
            if bpo_user:
                return bpo_user
        return False

    @api.model
    def _default_department_id(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.department_id:
            return employee.department_id.id
        return False

    # ---------------------------------------------------------
    # Approvers & Hierarki Fields
    # ---------------------------------------------------------
    department_id = fields.Many2one('hr.department', string='Placement / Unit Kerja', default=_default_department_id, tracking=True)
    kadept_manager_id = fields.Many2one('res.users', string='Approval Kadept Terkait', default=_default_kadept_manager, tracking=True)
    dept_manager_id = fields.Many2one('res.users', string='Approval Manager Dept Terkait', default=_default_dept_manager, tracking=True)
    bpo_kadept_manager_id = fields.Many2one('res.users', string='Approval Kadept BPO', tracking=True)
    manager_it_id = fields.Many2one('res.users', string='Review Manager IT', default=_default_manager_it, tracking=True)
    kadept_it_manager_id = fields.Many2one('res.users', string='Approval Kadept IT', default=_default_kadept_it_manager, tracking=True)
    engineer_id = fields.Many2one('res.users', string='Engineer / PIC IT', tracking=True)

    pic_teknis_id = fields.Char(string='PIC Teknis', tracking=True)
    queue_number = fields.Integer(string='Nomor Antrian CR', copy=False, readonly=True, tracking=True)
    current_processing_queue_number = fields.Integer(string='Antrian Sedang Dikerjakan Saat Ini', compute='_compute_queue_info')
    queue_ahead_count = fields.Integer(string='Antrian di Depan Anda', compute='_compute_queue_info')

    # ---------------------------------------------------------
    # Access Rights & Permissions Computes
    # ---------------------------------------------------------
    can_approve_dept_mgr = fields.Boolean(compute='_compute_approval_rights')
    can_approve_kadept = fields.Boolean(compute='_compute_approval_rights')
    can_approve_bpo = fields.Boolean(compute='_compute_approval_rights')
    can_review_it_mgr = fields.Boolean(compute='_compute_approval_rights')
    can_approve_it_kadept = fields.Boolean(compute='_compute_approval_rights')
    can_reject = fields.Boolean(compute='_compute_approval_rights')
    can_reopen = fields.Boolean(compute='_compute_can_reopen')
    is_admin = fields.Boolean(compute='_compute_is_admin')
    is_target_dept_it = fields.Boolean(compute='_compute_is_target_dept_it')

    def _is_target_dept_it(self):
        """Mengecek apakah CR to Departement mengarah ke IT/Sistem/Digitalisasi"""
        self.ensure_one()
        if not self.target_department_id:
            return False
        name = (self.target_department_id.name or '').lower()
        return any(k in name for k in ['sistem, ti', 'sistem, it', 'sistem ti', 'sistem it', 'digitalisasi', 'it', 'ti'])

    @api.depends('target_department_id')
    def _compute_is_target_dept_it(self):
        for cr in self:
            cr.is_target_dept_it = cr._is_target_dept_it()

    @api.depends('dept_manager_id', 'kadept_manager_id', 'bpo_kadept_manager_id', 'manager_it_id', 'kadept_it_manager_id', 'state')
    def _compute_approval_rights(self):
        for cr in self:
            uid = cr.env.uid
            is_superuser = cr.env.is_superuser()
            user = cr.env.user
            is_admin = user.has_group('it_helpdesk_v2.group_helpdesk_manager')

            cr.can_approve_dept_mgr = is_superuser or is_admin or bool(cr.dept_manager_id and cr.dept_manager_id.id == uid)
            cr.can_approve_kadept = is_superuser or is_admin or bool(cr.kadept_manager_id and cr.kadept_manager_id.id == uid)
            cr.can_approve_bpo = is_superuser or is_admin or bool(cr.bpo_kadept_manager_id and cr.bpo_kadept_manager_id.id == uid)
            cr.can_review_it_mgr = is_superuser or is_admin or bool(cr.manager_it_id and cr.manager_it_id.id == uid) or user.has_group('it_helpdesk_v2.group_helpdesk_it_manager')
            cr.can_approve_it_kadept = is_superuser or is_admin or bool(cr.kadept_it_manager_id and cr.kadept_it_manager_id.id == uid) or user.has_group('it_helpdesk_v2.group_helpdesk_it_manager')

            # Can reject per state
            if cr.state == 'dept_mgr_approval':
                cr.can_reject = cr.can_approve_dept_mgr
            elif cr.state == 'kadept_approval':
                cr.can_reject = cr.can_approve_kadept
            elif cr.state == 'bpo_approval':
                cr.can_reject = cr.can_approve_bpo
            elif cr.state == 'it_mgr_review':
                cr.can_reject = cr.can_review_it_mgr
            elif cr.state == 'it_kadept_approval':
                cr.can_reject = cr.can_approve_it_kadept
            else:
                cr.can_reject = is_superuser or is_admin


    @api.depends_context('uid')
    def _compute_is_admin(self):
        has_admin = self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager') or self.env.is_superuser()
        for cr in self:
            cr.is_admin = has_admin

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

    # ---------------------------------------------------------
    # Queue Management
    # ---------------------------------------------------------
    @api.model
    def _reindex_active_queue(self):
        active_crs = self.search([('state', '=', 'in_progress')], order='queue_number asc, id asc')
        for index, cr in enumerate(active_crs, start=1):
            if cr.queue_number != index:
                cr.write({'queue_number': index})

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

    # ---------------------------------------------------------
    # Requester Contact & Onchange Logics
    # ---------------------------------------------------------
    created_by = fields.Many2one('res.users', string='Dibuat Oleh', default=lambda self: self.env.user)
    email = fields.Char(string='E-Mail', default=lambda self: self.env.user.email or self.env.user.partner_id.email)
    phone = fields.Char(string='Phone', default=lambda self: self.env.user.phone or self.env.user.mobile or self.env.user.partner_id.phone or self.env.user.partner_id.mobile)

    @api.onchange('created_by')
    def _onchange_created_by(self):
        if self.created_by:
            self.email = self.created_by.email or self.created_by.partner_id.email or ''
            self.phone = self.created_by.phone or self.created_by.mobile or self.created_by.partner_id.phone or self.created_by.partner_id.mobile or ''
            employee = self.env['hr.employee'].search([('user_id', '=', self.created_by.id)], limit=1)
            if employee:
                self.department_id = employee.department_id.id if employee.department_id else False
                self.dept_manager_id = self._get_dept_manager_user(employee)
                self.kadept_manager_id = self._get_kadept_manager_user(employee)

    @api.onchange('target_department_id')
    def _onchange_target_department_id(self):
        if self.target_department_id:
            self.bpo_kadept_manager_id = self._get_bpo_kadept_manager_user(self.target_department_id)
        else:
            self.bpo_kadept_manager_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if self.subcategory_id and self.subcategory_id.category_id != self.category_id:
                self.subcategory_id = False
            return {'domain': {'subcategory_id': [('category_id', '=', self.category_id.id)]}}
        return {'domain': {'subcategory_id': [('id', '!=', False)]}}

    note = fields.Text(string='Note')
    rejection_reason = fields.Text(string='Alasan Penolakan')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment File')
    analysis_and_solution = fields.Html(string='Analysis & Solution')
    propose_solution = fields.Html(string='Propose Solution')

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('dept_mgr_approval', 'Approval Manager Dept Terkait'),
            ('kadept_approval', 'Approval Kadept Terkait'),
            ('bpo_approval', 'Approval Kadept BPO'),
            ('it_mgr_review', 'Review Manager IT'),
            ('it_kadept_approval', 'Approval Kadept IT'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('closed', 'Closed'),
            ('rejected', 'Rejected'),
        ],
        default='draft', tracking=True, string='Status'
    )

    posted_date = fields.Datetime()

    def get_next_cr_code(self):
        self.ensure_one()
        seq = self.env['ir.sequence'].next_by_code('it.helpdesk.change.request') or '001'
        date_str = fields.Date.today().strftime('%Y%m%d')
        return 'HKICR-%s-%s' % (seq, date_str)

    # ---------------------------------------------------------
    # Email Notifications
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Approval Workflow Actions
    # ---------------------------------------------------------
    def action_publish(self):
        return self.action_submit()

    def action_submit(self):
        """Submit CR from Draft -> Approval Manager Dept Terkait"""
        for cr in self:
            if not cr.code:
                cr.code = cr.get_next_cr_code()
            cr.posted_date = fields.Datetime.now()
            cr.state = 'dept_mgr_approval'
            cr._send_dept_approval_email()

    def action_approve_dept_mgr(self):
        """Manager Dept Terkait approves -> goes to Approval Kadept Terkait"""
        for cr in self:
            if not cr.can_approve_dept_mgr:
                raise UserError(_("Hanya Manager Departemen terkait (%s) yang berhak menyetujui pengajuan ini!") % (cr.dept_manager_id.name or 'Manager Dept'))
            cr.state = 'kadept_approval'

    def action_approve_kadept(self):
        """Kadept Terkait approves:
        - If CR to Departement is IT -> Bypass Kadept BPO and go directly to Review Manager IT.
        - Else -> go to Approval Kadept BPO.
        """
        for cr in self:
            if not cr.can_approve_kadept:
                raise UserError(_("Hanya Kadept Terkait (%s) yang berhak menyetujui pengajuan ini!") % (cr.kadept_manager_id.name or 'Kadept Terkait'))

            if cr._is_target_dept_it():
                cr.state = 'it_mgr_review'
            else:
                cr.state = 'bpo_approval'

    def action_approve_bpo(self):
        """Kadept BPO approves -> goes to Review Manager IT"""
        for cr in self:
            if not cr.can_approve_bpo:
                raise UserError(_("Hanya Kadept BPO / Kadept Departemen Tujuan (%s) yang berhak menyetujui pengajuan ini!") % (cr.bpo_kadept_manager_id.name or 'Kadept BPO'))
            cr.state = 'it_mgr_review'

    def action_review_it_mgr(self):
        """Review Manager IT: Assigns Engineer & Estimated Date -> goes to Approval Kadept IT"""
        for cr in self:
            if not cr.can_review_it_mgr:
                raise UserError(_("Hanya Manager IT (%s) yang berhak melakukan review pengajuan ini!") % (cr.manager_it_id.name or 'Manager IT'))
            if not cr.engineer_id:
                raise UserError(_("Silakan pilih Engineer / PIC IT yang ditugaskan terlebih dahulu!"))
            if not cr.estimated_completion_date:
                raise UserError(_("Silakan tentukan Estimasi Tanggal Penyelesaian terlebih dahulu sebelum melanjutkan!"))
            cr.state = 'it_kadept_approval'

    def action_approve_it_kadept(self):
        """Kadept IT approves -> goes to In Progress (Engineering queue)"""
        for cr in self:
            if not cr.can_approve_it_kadept:
                raise UserError(_("Hanya Kepala Departemen IT (%s) yang berhak memberikan persetujuan final ini!") % (cr.kadept_it_manager_id.name or 'Kadept IT'))
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
        now_dt = fields.Datetime.now()
        for cr in self:
            res_dt = cr.resolved_date or now_dt
            vals = {'state': 'done', 'queue_number': 0, 'resolved_date': res_dt}
            if cr.enable_auto_close:
                vals['auto_close_deadline'] = cr._compute_auto_close_deadline()
            cr.write(vals)
            cr._send_done_email()
            msg = cr.message_post(body=_("<b>✅ Change Request Selesai (Done)</b><br/>Diselesaikan pada: %s") % fields.Datetime.to_string(res_dt))
            if msg and res_dt:
                msg.sudo().write({'date': res_dt})
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
            if cr.state == 'closed':
                max_cr = self.search([('queue_number', '>', 0)], order='queue_number desc', limit=1)
                vals['queue_number'] = (max_cr.queue_number + 1) if max_cr else 1
            cr.write(vals)
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
            if not cr.can_reject:
                raise UserError(_("Anda tidak memiliki hak akses untuk menolak pengajuan ini pada tahapan saat ini."))
            cr.state = 'rejected'
            cr.queue_number = 0
            cr._send_rejected_email()
        self._reindex_active_queue()

    def action_draft(self):
        self.write({'state': 'draft', 'queue_number': 0})
        self._reindex_active_queue()

    def write(self, vals):
        res = super().write(vals)
        if 'resolved_date' in vals or 'closed_date' in vals:
            for cr in self:
                if 'resolved_date' in vals and vals['resolved_date']:
                    msgs = cr.message_ids.filtered(
                        lambda m: 'Done' in (m.body or '') or 'Selesai' in (m.body or '')
                    )
                    if msgs:
                        msgs.sudo().write({'date': vals['resolved_date']})
                if 'closed_date' in vals and vals['closed_date']:
                    msgs = cr.message_ids.filtered(
                        lambda m: 'Closed' in (m.body or '') or 'Tutup' in (m.body or '')
                    )
                    if msgs:
                        msgs.sudo().write({'date': vals['closed_date']})
        return res
