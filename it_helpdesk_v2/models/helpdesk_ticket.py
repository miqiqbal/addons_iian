import re
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .helpdesk_priority_matrix import LEVEL_SELECTION


def _is_html_empty(html_content):
    if not html_content:
        return True
    clean = re.sub(r'<[^>]*>', '', str(html_content))
    clean = clean.replace('&nbsp;', '').replace('&#160;', '').replace('\xa0', '').strip()
    return not bool(clean)

TICKET_PRIORITY_SELECTION = [
    ('1', 'P1 - Critical'), ('2', 'P2 - High'),
    ('3', 'P3 - Medium'), ('4', 'P4 - Low'),
]
STATE_SELECTION = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('assigned', 'Assigned'),
    ('in_progress', 'Progress'),
    ('done', 'Done'),
    ('reject', 'Reject'),
    ('closed', 'Closed'),
]
CUSTOMER_RATING_SELECTION = [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')]
PROGRESS_BY_STATE = {
    'draft': 0.0, 'open': 15.0, 'assigned': 30.0, 'in_progress': 60.0,
    'done': 90.0, 'reject': 0.0, 'closed': 100.0,
}
SEQUENCE_CODE_BY_TYPE = {
    'incident': 'it.helpdesk.incident',
    'service_request': 'it.helpdesk.service.request',
}
OPEN_STATES = ['draft', 'open', 'assigned', 'in_progress']


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Ticket No', readonly=True, copy=False, default='New')
    title = fields.Char(string='Judul Kendala')
    ticket_type = fields.Selection(
        [('incident', 'Incident'), ('service_request', 'Service Request')],
        default='incident')
    requester_id = fields.Many2one(
        'res.users', default=lambda self: self.env.user)
    requester_name = fields.Char(string='Nama_PIC')
    department_id = fields.Many2one('hr.department')
    location_id = fields.Many2one('helpdesk.location')
    location_name = fields.Char(string='Proyek')
    phone = fields.Char(
        string='Whatsapp_PIC',
        default=lambda self: self.env.user.phone or self.env.user.mobile or self.env.user.partner_id.phone or self.env.user.partner_id.mobile)
    email = fields.Char(
        default=lambda self: self.env.user.email or self.env.user.partner_id.email)
    cc_partner_ids = fields.Many2many('res.partner', string='CC')
    excel_link = fields.Char(string='Link')
    expected_result = fields.Text(string='Nilai_seharusnya')
    registration_no = fields.Char(string='Keterangan')
    followup_date_it = fields.Char(string='Tanggal_TL_Laporan_(IT)')
    notes_it = fields.Text(string='Catatan')
    service_id = fields.Many2one('helpdesk.service', string='Service')
    category_id = fields.Many2one('helpdesk.category', string='Category', domain="[('service_id', '=?', service_id)]")
    subcategory_id = fields.Many2one('helpdesk.subcategory', string='Sub Category', domain="[('category_id', '=?', category_id)]")
    description = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment', string='Lampiran')
    resolution = fields.Html(string='Langkah-Langkah / Penjelasan Solusi Kendala (Tutorial)')
    solution_type = fields.Selection([
        ('text', 'Teks Tutorial Saja')
    ], string='Format Jenis Solusi', default='text')
    solution_attachment_ids = fields.Many2many(
        'ir.attachment', 'helpdesk_ticket_solution_rel', 'ticket_id', 'attachment_id',
        string='Bukti Foto / File Penyelesaian')
    is_kb_solution_available = fields.Selection([
        ('no', 'Tidak (Buat Tutorial / Bukti Baru)'),
        ('yes', 'Ya (Pilih dari Kamus Knowledge Base)')
    ], string='Apakah Penyelesaian Tersedia pada Knowledge Base?', default='no')
    selected_knowledge_id = fields.Many2one(
        'helpdesk.knowledge', string='Pilih Artikel Knowledge Base')
    is_published_to_kb = fields.Boolean(
        string='Simpan ke Knowledge Base (Kamus Solusi)', default=False)
    knowledge_id = fields.Many2one('helpdesk.knowledge', string='Artikel Knowledge Base Linked', copy=False)
    is_engineer_or_officer = fields.Boolean(
        compute='_compute_is_engineer_or_officer')
    can_reject = fields.Boolean(
        compute='_compute_can_reject')
    rejection_reason = fields.Text(
        string='Alasan Penolakan', copy=False, readonly=True)

    @api.onchange('selected_knowledge_id')
    def _onchange_selected_knowledge_id(self):
        if self.selected_knowledge_id:
            self.knowledge_id = self.selected_knowledge_id.id
            if self.selected_knowledge_id.content:
                self.resolution = self.selected_knowledge_id.content

    @api.depends_context('uid')
    def _compute_is_engineer_or_officer(self):
        is_agent_or_mgr = self.env.user.has_group('it_helpdesk_v2.group_helpdesk_agent') or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')
        for ticket in self:
            ticket.is_engineer_or_officer = is_agent_or_mgr

    @api.depends_context('uid')
    def _compute_can_reject(self):
        is_mgr = self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')
        is_agent = self.env.user.has_group('it_helpdesk_v2.group_helpdesk_agent')
        for ticket in self:
            if is_mgr:
                ticket.can_reject = True
            elif is_agent:
                ticket.can_reject = False
            else:
                ticket.can_reject = True

    engineer_id = fields.Many2one('res.users', string='Engineer', tracking=True)
    engineer_name = fields.Char(string='PIC_IT')
    team_id = fields.Many2one('helpdesk.team')
    state = fields.Selection(
        STATE_SELECTION, default='new', required=True, tracking=True)
    excel_status = fields.Char(string='Status')
    created_date = fields.Datetime(default=fields.Datetime.now)
    import_created_date = fields.Char(string='Tanggal_Input_Laporan')
    first_response_date = fields.Datetime()
    resolved_date = fields.Datetime()
    closed_date = fields.Datetime()
    auto_close_deadline = fields.Datetime(string='Batas Waktu Auto Close (Hari Kerja)', readonly=True)
    enable_auto_close = fields.Boolean(
        string='Auto Close Aktif', compute='_compute_enable_auto_close', store=True, readonly=False,
        help='Otomatis menutup tiket secara otomatis setelah status Done (High 4 hari, Med 3 hari, Low 2 hari kerja)'
    )
    last_update = fields.Datetime(compute='_compute_last_update', store=True)
    customer_rating = fields.Selection(CUSTOMER_RATING_SELECTION)
    is_security_incident = fields.Boolean()
    progress_percent = fields.Float(compute='_compute_progress')

    @api.depends('service_id', 'service_id.name', 'category_id', 'subcategory_id')
    def _compute_enable_auto_close(self):
        Keyword = self.env['helpdesk.keyword']
        for ticket in self:
            service_name = (ticket.service_id.name or '').upper() if ticket.service_id else ''
            if 'KEAMANAN' in service_name or 'SECURITY' in service_name:
                ticket.enable_auto_close = False
                continue

            matching_keywords = Keyword.search([('active', '=', True)])
            matched_rule = False
            for rule in matching_keywords:
                if (ticket.service_id and ticket.service_id in rule.service_ids) or \
                   (ticket.category_id and ticket.category_id in rule.category_ids) or \
                   (ticket.subcategory_id and ticket.subcategory_id in rule.subcategory_ids):
                    matched_rule = rule
                    break

            if matched_rule:
                ticket.enable_auto_close = matched_rule.enable_auto_close
            else:
                ticket.enable_auto_close = True

    # Priority engine (questionnaire dari Stage 3 & 4)
    q1_answer_id = fields.Many2one(
        'helpdesk.priority.answer', string='Siapa yang terdampak?',
        domain="[('question_id.code', '=', 'V2_Q1')]")
    q2_answer_id = fields.Many2one(
        'helpdesk.priority.answer', string='Apakah mengganggu operasional?',
        domain="[('question_id.code', '=', 'V2_Q2')]")
    q3_answer_id = fields.Many2one(
        'helpdesk.priority.answer', string='Layanan yang terdampak?',
        domain="[('question_id.code', '=', 'V2_Q3')]")
    q4_answer_id = fields.Many2one(
        'helpdesk.priority.answer', string='Apakah ada workaround?',
        domain="[('question_id.code', '=', 'V2_Q4')]")
    q5_answer_id = fields.Many2one(
        'helpdesk.priority.answer', string='Apakah terkait deadline proyek/pekerjaan?',
        domain="[('question_id.code', '=', 'V2_Q5')]")

    impact_score = fields.Integer(compute='_compute_scores', store=True)
    urgency_score = fields.Integer(compute='_compute_scores', store=True)
    impact_level = fields.Selection(
        LEVEL_SELECTION, compute='_compute_scores', store=True)
    urgency_level = fields.Selection(
        LEVEL_SELECTION, compute='_compute_scores', store=True)
    priority = fields.Selection(
        TICKET_PRIORITY_SELECTION, compute='_compute_priority', store=True)
    sla_id = fields.Many2one(
        'helpdesk.sla', compute='_compute_priority', store=True)
    priority_label = fields.Char(related='sla_id.label')
    sla_response_time_value = fields.Float(related='sla_id.response_time_value')
    sla_response_time_unit = fields.Selection(related='sla_id.response_time_unit')
    sla_resolution_time_value = fields.Float(related='sla_id.resolution_time_value')
    sla_resolution_time_unit = fields.Selection(related='sla_id.resolution_time_unit')
    sla_response_deadline = fields.Datetime(
        compute='_compute_sla_deadline', store=True)
    sla_resolution_deadline = fields.Datetime(
        compute='_compute_sla_deadline', store=True)
    sla_response_breached = fields.Boolean(
        compute='_compute_sla_status', store=True)
    sla_resolution_breached = fields.Boolean(
        compute='_compute_sla_status', store=True)
    start_progress_date = fields.Datetime(string='Tanggal Start Progress', readonly=True)
    publish_date = fields.Datetime(string='Tanggal Start (Publish)', readonly=True)
    sla_warning_sent = fields.Boolean(string='SLA Warning Email Sent', default=False, copy=False)

    SLA_STATUS_SELECTION = [
        ('on_track', 'On Track'),
        ('warning', 'Warning'),
        ('critical', 'Critical Warning'),
        ('breached', 'SLA Overdue')
    ]
    sla_status_label = fields.Selection(
        SLA_STATUS_SELECTION, string='SLA Status Code', compute='_compute_sla_status_label', store=False)
    sla_status_name = fields.Char(
        string='SLA Status', compute='_compute_sla_status_label', store=False)
    sla_status_color = fields.Selection(
        [('success', 'Success'), ('info', 'Info'), ('warning', 'Warning'), ('danger', 'Danger')],
        string='Warna SLA Status', compute='_compute_sla_status_label', store=False)

    work_order_ids = fields.One2many('helpdesk.work.order', 'ticket_id')
    work_order_count = fields.Integer(compute='_compute_work_order_count')

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for ticket in self:
            ticket.work_order_count = len(ticket.work_order_ids)

    @api.depends('write_date', 'create_date')
    def _compute_last_update(self):
        for ticket in self:
            ticket.last_update = ticket.write_date or ticket.create_date

    @api.depends('state')
    def _compute_progress(self):
        for ticket in self:
            ticket.progress_percent = PROGRESS_BY_STATE.get(ticket.state, 0.0)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            if self.category_id and self.category_id.service_id != self.service_id:
                self.category_id = False
                self.subcategory_id = False
            return {'domain': {
                'category_id': [('service_id', '=', self.service_id.id)],
                'subcategory_id': [('category_id.service_id', '=', self.service_id.id)],
            }}
        else:
            return {'domain': {'category_id': [('id', '!=', False)], 'subcategory_id': [('id', '!=', False)]}}

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if not self.service_id and self.category_id.service_id:
                self.service_id = self.category_id.service_id
            if self.subcategory_id and self.subcategory_id.category_id != self.category_id:
                self.subcategory_id = False
            return {'domain': {'subcategory_id': [('category_id', '=', self.category_id.id)]}}
        else:
            if self.service_id:
                return {'domain': {'subcategory_id': [('category_id.service_id', '=', self.service_id.id)]}}
            return {'domain': {'subcategory_id': [('id', '!=', False)]}}

    @api.onchange('subcategory_id')
    def _onchange_subcategory_id(self):
        if self.subcategory_id and self.subcategory_id.category_id:
            if not self.category_id:
                self.category_id = self.subcategory_id.category_id
            if not self.service_id and self.category_id and self.category_id.service_id:
                self.service_id = self.category_id.service_id

    @api.depends(
        'q1_answer_id.score', 'q1_answer_id.weight', 'q2_answer_id.score', 'q2_answer_id.weight',
        'q3_answer_id.score', 'q3_answer_id.weight', 'q4_answer_id.score', 'q4_answer_id.weight',
        'q5_answer_id.score', 'q5_answer_id.weight')
    def _compute_scores(self):
        for ticket in self:
            impact_answers = ticket.q1_answer_id | ticket.q2_answer_id | ticket.q3_answer_id
            urgency_answers = ticket.q4_answer_id | ticket.q5_answer_id
            impact_score = sum(a.score * a.weight for a in impact_answers)
            urgency_score = sum(a.score * a.weight for a in urgency_answers)
            ticket.impact_score = impact_score
            ticket.urgency_score = urgency_score
            ticket.impact_level = (
                'tinggi' if impact_score >= 12 else 'sedang' if impact_score >= 7 else 'rendah')
            ticket.urgency_level = (
                'tinggi' if urgency_score >= 8 else 'sedang' if urgency_score >= 5 else 'rendah')

    @api.depends('impact_level', 'urgency_level')
    def _compute_priority(self):
        Matrix = self.env['helpdesk.priority.matrix']
        SLA = self.env['helpdesk.sla']
        for ticket in self:
            priority = False
            sla = SLA.browse()
            if ticket.impact_level and ticket.urgency_level:
                matrix = Matrix.search([
                    ('impact_level', '=', ticket.impact_level),
                    ('urgency_level', '=', ticket.urgency_level),
                ], limit=1)
                if matrix:
                    priority = matrix.priority
                    sla = SLA.search([('priority', '=', priority)], limit=1)
            ticket.priority = priority
            ticket.sla_id = sla.id if sla else False

    @api.depends('sla_id', 'created_date', 'publish_date')
    def _compute_sla_deadline(self):
        for ticket in self:
            start_ref = ticket.publish_date or ticket.created_date or ticket.create_date
            if ticket.sla_id and start_ref:
                ticket.sla_response_deadline = ticket.sla_id.get_deadline(start_ref)
                ticket.sla_resolution_deadline = ticket.sla_id.get_resolution_deadline(start_ref)
            else:
                ticket.sla_response_deadline = False
                ticket.sla_resolution_deadline = False

    @api.depends(
        'sla_response_deadline', 'sla_resolution_deadline',
        'first_response_date', 'resolved_date')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            response_reference = ticket.first_response_date or now
            ticket.sla_response_breached = bool(
                ticket.sla_response_deadline and response_reference > ticket.sla_response_deadline)
            resolution_reference = ticket.resolved_date or ticket.closed_date or now
            ticket.sla_resolution_breached = bool(
                ticket.sla_resolution_deadline
                and resolution_reference > ticket.sla_resolution_deadline)

    @api.depends('created_date', 'create_date', 'sla_resolution_deadline', 'resolved_date', 'state')
    def _compute_sla_status_label(self):
        now = fields.Datetime.now()
        status_map = {s.code: s for s in self.env['helpdesk.sla.status'].sudo().search([])}
        fallback_name = dict(self.SLA_STATUS_SELECTION)
        fallback_color = {
            'on_track': 'success', 'warning': 'warning', 'critical': 'danger', 'breached': 'danger'}

        def apply_status(ticket, code):
            ticket.sla_status_label = code
            status = status_map.get(code)
            ticket.sla_status_name = status.name if status else fallback_name.get(code)
            ticket.sla_status_color = status.color if status else fallback_color.get(code)

        for ticket in self:
            c_date = ticket.created_date or ticket.create_date
            deadline = ticket.sla_resolution_deadline
            if not c_date or not deadline:
                apply_status(ticket, 'on_track')
                continue

            ref_date = (ticket.resolved_date or ticket.closed_date or now) if ticket.state in ('done', 'closed') else now
            if not ref_date:
                ref_date = now

            total_sec = (deadline - c_date).total_seconds()
            if total_sec <= 0:
                apply_status(ticket, 'breached' if ref_date > deadline else 'on_track')
                continue

            used_sec = (ref_date - c_date).total_seconds()
            used_ratio = used_sec / total_sec

            warn_ratio = (ticket.sla_id.warning_percent / 100.0) if ticket.sla_id and ticket.sla_id.warning_percent else 0.80
            crit_ratio = (ticket.sla_id.critical_percent / 100.0) if ticket.sla_id and ticket.sla_id.critical_percent else 0.90

            if ref_date > deadline or used_ratio >= 1.0:
                apply_status(ticket, 'breached')
            elif used_ratio >= crit_ratio:
                apply_status(ticket, 'critical')
            elif used_ratio >= warn_ratio:
                apply_status(ticket, 'warning')
            else:
                apply_status(ticket, 'on_track')

    def _send_engineer_assignment_email(self):
        template = self.env.ref('it_helpdesk_v2.email_template_helpdesk_engineer_assigned', raise_if_not_found=False)
        if not template:
            return
        for ticket in self:
            if ticket.engineer_id and ticket.engineer_id.email:
                try:
                    template.send_mail(ticket.id, force_send=True)
                except Exception:
                    pass

    @api.model
    def _cron_check_sla_warning(self):
        """Cron Job untuk mengecek dan mengirim email peringatan 80% SLA secara otomatis ke Engineer (1x pengiriman)."""
        template = self.env.ref('it_helpdesk_v2.email_template_helpdesk_sla_warning', raise_if_not_found=False)
        if not template:
            return

        tickets = self.search([
            ('state', 'in', ['open', 'in_progress']),
            ('sla_warning_sent', '=', False),
            ('engineer_id', '!=', False),
            ('sla_resolution_deadline', '!=', False),
        ])

        now = fields.Datetime.now()
        for ticket in tickets:
            c_date = ticket.created_date or ticket.create_date
            deadline = ticket.sla_resolution_deadline
            if not c_date or not deadline:
                continue

            total_sec = (deadline - c_date).total_seconds()
            if total_sec <= 0:
                continue

            used_sec = (now - c_date).total_seconds()
            used_ratio = used_sec / total_sec

            if used_ratio >= 0.80:
                if ticket.engineer_id and ticket.engineer_id.email:
                    try:
                        template.send_mail(ticket.id, force_send=True)
                    except Exception:
                        pass
                ticket.write({'sla_warning_sent': True})

    @api.model
    def _cron_auto_escalate_unassigned_tickets(self):
        """Cron Job untuk mengecek tiket Open yang belum di-assign dan sudah melewati Response SLA Deadline untuk di-eskalasikan otomatis ke Engineer."""
        now = fields.Datetime.now()
        overdue_tickets = self.search([
            ('state', '=', 'open'),
            ('engineer_id', '=', False),
            ('sla_response_deadline', '!=', False),
            ('sla_response_deadline', '<=', now),
        ])
        for ticket in overdue_tickets:
            try:
                vals = {'state': 'assigned'}
                ticket._auto_route_engineer(vals)
                if vals.get('engineer_id'):
                    ticket.write(vals)
                    ticket._send_engineer_assignment_email()
                    ticket.message_post(body="⚡ Tiket otomatis di-eskalasikan ke Engineer oleh sistem karena telah melewati batas waktu konfirmasi Helpdesk (Response SLA). Status: Assigned.")
            except Exception:
                pass

    @api.onchange('requester_id')
    def _onchange_requester_id(self):
        if self.requester_id:
            self.email = self.requester_id.email or self.requester_id.partner_id.email or ''
            self.phone = self.requester_id.phone or self.requester_id.mobile or self.requester_id.partner_id.phone or self.requester_id.partner_id.mobile or ''

    def _get_engineer_daily_ticket_count(self, user_id):
        """Hitung jumlah tiket aktif yang ditugaskan ke engineer pada hari ini"""
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.search_count([
            ('engineer_id', '=', user_id),
            ('create_date', '>=', today_start),
            ('state', 'not in', ('closed', 'reject'))
        ])

    def _get_failover_engineer(self, primary_engineer_id):
        """Cari engineer alternatif jika engineer utama sudah penuh kuotanya (Round-Robin / Least Loaded)"""
        agent_group = self.env.ref('it_helpdesk_v2.group_helpdesk_agent', raise_if_not_found=False)
        if not agent_group:
            return False

        engineers = agent_group.users.filtered(lambda u: u.id != primary_engineer_id and u.active)
        available_engineers = []
        for eng in engineers:
            count = self._get_engineer_daily_ticket_count(eng.id)
            quota = eng.max_daily_quota or 5
            if count < quota:
                available_engineers.append((eng.id, count))

        if available_engineers:
            available_engineers.sort(key=lambda x: x[1])
            return available_engineers[0][0]
        return False

    def _auto_route_engineer(self, vals):
        content_to_check = "%s %s" % (vals.get('title', self.title or ''), vals.get('description', self.description or ''))
        content_lower = content_to_check.lower()

        subcat_id = vals.get('subcategory_id', self.subcategory_id.id if self else False)
        cat_id = vals.get('category_id', self.category_id.id if self else False)
        srv_id = vals.get('service_id', self.service_id.id if self else False)

        keywords = self.env['helpdesk.keyword'].search([('active', '=', True)], order='sequence, id')
        best_rule = False
        max_score = 0

        for rule in keywords:
            score = 0

            # 1. Subcategory match (+8 points)
            if subcat_id and rule.subcategory_ids and subcat_id in rule.subcategory_ids.ids:
                score += 8

            # 2. Category match (+4 points - e.g. Category SAP)
            if cat_id and rule.category_ids and cat_id in rule.category_ids.ids:
                score += 4

            # 3. Keyword match (+2 points - e.g. Title/Description contains keyword)
            if rule.keyword_list:
                words = [k.strip().lower() for k in rule.keyword_list.split(',') if k.strip()]
                words.sort(key=len, reverse=True)
                if any(w in content_lower for w in words):
                    score += 2

            # 4. Service match (+1 point - e.g. Layanan Aplikasi)
            if srv_id and rule.service_ids and srv_id in rule.service_ids.ids:
                score += 1

            if score > max_score:
                max_score = score
                best_rule = rule

        matched_rule = best_rule if max_score > 0 else False

        if matched_rule:
            if not vals.get('service_id') and matched_rule.service_ids:
                vals['service_id'] = matched_rule.service_ids[0].id
            if not vals.get('category_id') and matched_rule.category_ids:
                vals['category_id'] = matched_rule.category_ids[0].id
            if not vals.get('subcategory_id') and matched_rule.subcategory_ids:
                vals['subcategory_id'] = matched_rule.subcategory_ids[0].id

        if not vals.get('engineer_id'):
            engineer_id = False
            if matched_rule and (matched_rule.engineer_line_ids or matched_rule.engineer_ids):
                # Ambil engineer sesuai urutan persis saat diinput user di form (bebas dari pengurutan abjad)
                rule_engineers = matched_rule.get_ordered_engineers()
                if rule_engineers:
                    avail_rule_engs = []
                    for eng in rule_engineers:
                        cnt = self._get_engineer_daily_ticket_count(eng.id)
                        qta = eng.max_daily_quota or 5
                        if cnt < qta:
                            avail_rule_engs.append((eng.id, cnt))
                    if avail_rule_engs:
                        # Pilih engineer pertama yang kuotanya masih tersedia sesuai urutan urut input user
                        engineer_id = avail_rule_engs[0][0]
                    else:
                        engineer_id = rule_engineers[0].id
            elif vals.get('subcategory_id'):
                subcat = self.env['helpdesk.subcategory'].browse(vals['subcategory_id'])
                if subcat.engineer_id:
                    engineer_id = subcat.engineer_id.id
                elif subcat.category_id and subcat.category_id.engineer_id:
                    engineer_id = subcat.category_id.engineer_id.id
                elif subcat.category_id and subcat.category_id.service_id and subcat.category_id.service_id.engineer_id:
                    engineer_id = subcat.category_id.service_id.engineer_id.id
            elif vals.get('category_id'):
                cat = self.env['helpdesk.category'].browse(vals['category_id'])
                if cat.engineer_id:
                    engineer_id = cat.engineer_id.id
                elif cat.service_id and cat.service_id.engineer_id:
                    engineer_id = cat.service_id.engineer_id.id
            elif vals.get('service_id'):
                srv = self.env['helpdesk.service'].browse(vals['service_id'])
                if srv.engineer_id:
                    engineer_id = srv.engineer_id.id

            if not engineer_id:
                engineer_id = self.env.uid

            if engineer_id:
                # Cek kuota harian engineer utama & lakukan auto-failover jika penuh
                primary_eng = self.env['res.users'].browse(engineer_id)
                daily_count = self._get_engineer_daily_ticket_count(engineer_id)
                quota = primary_eng.max_daily_quota or 5
                if daily_count >= quota:
                    failover_id = self._get_failover_engineer(engineer_id)
                    if failover_id:
                        engineer_id = failover_id
                vals['engineer_id'] = engineer_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                code = SEQUENCE_CODE_BY_TYPE.get(
                    vals.get('ticket_type'), SEQUENCE_CODE_BY_TYPE['incident'])
                vals['name'] = self.env['ir.sequence'].next_by_code(code) or 'New'

            if not vals.get('title'):
                desc = vals.get('description') or ''
                clean_desc = desc.replace('<p>', '').replace('</p>', '').strip()
                vals['title'] = clean_desc[:60] if clean_desc else 'Kendala Helpdesk'

            # Save default state as draft, or open if publish_ticket context
            if vals.get('state') == 'open' or self.env.context.get('publish_ticket'):
                vals['state'] = 'open'
                self._auto_route_engineer(vals)
            else:
                vals['state'] = 'draft'

        tickets = super().create(vals_list)
        for ticket in tickets:
            atts = ticket.attachment_ids | ticket.solution_attachment_ids
            if atts:
                atts.sudo().write({
                    'res_model': 'helpdesk.ticket',
                    'res_id': ticket.id,
                })
        tickets._send_creation_notifications()
        for ticket in tickets:
            if ticket.engineer_id:
                ticket._send_engineer_assignment_email()
        return tickets

    @api.model
    def init(self):
        super().init()
        try:
            self.env['ir.ui.view'].clear_caches()
            dash_menu = self.env.ref('it_helpdesk_v2.menu_it_helpdesk_dashboard', raise_if_not_found=False)
            dash_action = self.env.ref('it_helpdesk_v2.action_helpdesk_analytics_dashboard', raise_if_not_found=False)
            if dash_menu and dash_action:
                dash_menu.sudo().write({'action': 'ir.actions.client,%d' % dash_action.id})
        except Exception:
            pass

    def action_publish(self):
        for ticket in self:
            missing = []
            if not ticket.ticket_type: missing.append('Ticket Type')
            if not ticket.service_id: missing.append('Service')
            if not ticket.category_id: missing.append('Category')
            if not ticket.location_id: missing.append('Department / Location')
            if not ticket.phone: missing.append('Phone')
            if missing:
                raise UserError('Mohon lengkapi kolom berikut sebelum mempublikasikan tiket:\n• ' + '\n• '.join(missing))
            vals = {
                'state': 'open',
                'publish_date': ticket.publish_date or fields.Datetime.now()
            }
            ticket.write(vals)

    def action_save_draft(self):
        for ticket in self:
            ticket.write({'state': 'draft'})

    def action_assign_engineer(self):
        for ticket in self:
            vals = {'state': 'assigned'}
            if not ticket.engineer_id:
                ticket._auto_route_engineer(vals)
            if not ticket.engineer_id and not vals.get('engineer_id'):
                raise UserError('Silakan pilih Engineer terlebih dahulu pada kolom Engineer atau pastikan aturan keahlian Engineer sudah dikonfigurasi!')
            ticket.write(vals)
            ticket._send_engineer_assignment_email()
            ticket.message_post(body="👨‍💻 Tiket berhasil di-eskalasikan/ditugaskan ke Engineer %s (Status: Assigned)." % (ticket.engineer_id.name or ''))

    def action_assign(self):
        self.action_assign_engineer()

    def action_start_progress(self):
        for ticket in self:
            ticket.write({
                'state': 'in_progress',
                'start_progress_date': ticket.start_progress_date or fields.Datetime.now()
            })

    def action_save_to_kb(self):
        for ticket in self:
            if not ticket.resolution and not ticket.solution_attachment_ids:
                raise UserError('Mohon isi penjelasan langkah solusi atau unggah bukti foto terlebih dahulu sebelum menyimpan ke Knowledge Base!')
            
            kb_vals = {
                'name': ticket.title or ('Solusi Tiket %s' % (ticket.name or '')),
                'problem': ticket.title or '',
                'service_id': ticket.service_id.id if ticket.service_id else False,
                'category_id': ticket.category_id.id if ticket.category_id else False,
                'subcategory_id': ticket.subcategory_id.id if ticket.subcategory_id else False,
                'solution_type': ticket.solution_type or 'hybrid',
                'is_quick_solution': True,
                'summary': ticket.description or '',
                'content': ticket.resolution or '<p>Panduan penyelesaian solusi terlampir pada foto / file bukti.</p>',
                'attachment_ids': [(6, 0, ticket.solution_attachment_ids.ids)] if ticket.solution_attachment_ids else False,
                'author_id': self.env.uid,
            }
            kb_id = getattr(ticket, 'knowledge_id', False)
            if kb_id:
                kb_id.write(kb_vals)
            else:
                kb = self.env['helpdesk.knowledge'].create(kb_vals)
                ticket.knowledge_id = kb.id
            
            ticket.is_published_to_kb = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sukses Disimpan!',
                'message': 'Solusi kendala berhasil diterbitkan ke Knowledge Base!',
                'type': 'success',
                'sticky': False,
            }
        }

    def write(self, vals):
        if vals.get('state') == 'open':
            for ticket in self:
                if not ticket.publish_date:
                    vals['publish_date'] = fields.Datetime.now()

        if vals.get('state') in ('in_progress', 'done', 'resolved', 'closed'):
            for ticket in self:
                if not ticket.start_progress_date:
                    vals['start_progress_date'] = fields.Datetime.now()

        # Validasi Ketat Wajib Isi Solusi saat status diubah menjadi Done
        if vals.get('state') == 'done':
            for ticket in self:
                kb_opt = vals.get('is_kb_solution_available', ticket.is_kb_solution_available)
                if kb_opt == 'yes':
                    selected_kb = vals.get('selected_knowledge_id', ticket.selected_knowledge_id)
                    if not selected_kb:
                        raise UserError('Gagal mengubah status ke Done! Mohon pilih artikel Knowledge Base penyelesaian terlebih dahulu!')
                else:
                    res_val = vals.get('resolution', ticket.resolution)
                    att_val = vals.get('solution_attachment_ids', ticket.solution_attachment_ids)
                    has_text = not _is_html_empty(res_val)
                    has_images = bool(att_val)
                    if not has_text and not has_images:
                        raise UserError('Gagal mengubah status ke Done! Anda wajib mengisikan Langkah-Langkah Solusi (Teks Panduan) atau mengunggah Lampiran Bukti Foto Penyelesaian terlebih dahulu.')

        old_engineers = {t.id: t.engineer_id.id for t in self}
        res = super().write(vals)

        if 'attachment_ids' in vals or 'solution_attachment_ids' in vals:
            for ticket in self:
                atts = ticket.attachment_ids | ticket.solution_attachment_ids
                if atts:
                    atts.sudo().write({
                        'res_model': 'helpdesk.ticket',
                        'res_id': ticket.id,
                    })

        if 'engineer_id' in vals:
            for ticket in self:
                if ticket.engineer_id and ticket.engineer_id.id != old_engineers.get(ticket.id):
                    ticket._send_engineer_assignment_email()

        if 'is_published_to_kb' in vals or 'resolution' in vals or 'solution_attachment_ids' in vals or 'solution_type' in vals:
            for ticket in self:
                if ticket.is_published_to_kb:
                    ticket._sync_knowledge_base()
        return res

    def _sync_knowledge_base(self):
        for ticket in self:
            has_text = not _is_html_empty(ticket.resolution)
            has_images = bool(ticket.solution_attachment_ids)
            if not has_text and not has_images:
                continue

            kb_vals = {
                'name': ticket.title or ('Solusi Tiket %s' % (ticket.name or '')),
                'problem': ticket.title or '',
                'service_id': ticket.service_id.id if ticket.service_id else False,
                'category_id': ticket.category_id.id if ticket.category_id else False,
                'subcategory_id': ticket.subcategory_id.id if ticket.subcategory_id else False,
                'solution_type': ticket.solution_type or 'hybrid',
                'is_quick_solution': True,
                'summary': ticket.description or '',
                'content': ticket.resolution or '<p>Panduan penyelesaian solusi terlampir pada foto / file bukti.</p>',
                'attachment_ids': [(6, 0, ticket.solution_attachment_ids.ids)] if ticket.solution_attachment_ids else False,
                'author_id': self.env.uid,
            }
            if ticket.knowledge_id:
                ticket.knowledge_id.sudo().write(kb_vals)
            else:
                kb = self.env['helpdesk.knowledge'].sudo().create(kb_vals)
                ticket.sudo().write({'knowledge_id': kb.id})

    def action_done(self):
        if not (self.env.user.has_group('it_helpdesk_v2.group_helpdesk_agent') or self.env.user.has_group('it_helpdesk_v2.group_helpdesk_manager')):
            raise UserError('Hanya Engineer atau Helpdesk Officer yang berhak menyelesaikan tiket!')

        for ticket in self:
            log_body = ""
            if ticket.is_kb_solution_available == 'yes':
                if not ticket.selected_knowledge_id:
                    raise UserError('Mohon pilih artikel Knowledge Base penyelesaian terlebih dahulu sebelum mengklik Mark as Done!')
                ticket.knowledge_id = ticket.selected_knowledge_id.id
                if not ticket.resolution and ticket.selected_knowledge_id.content:
                    ticket.resolution = ticket.selected_knowledge_id.content

                kb_title = ticket.selected_knowledge_id.name or ticket.selected_knowledge_id.problem or 'Artikel Knowledge Base'
                log_body = (
                    "<b>🛠️ AKSI PENYELESAIAN TIKET (RESOLVED LOG)</b><br/>"
                    "• <b>Penyelesaian Dari</b>: Kamus Knowledge Base<br/>"
                    "• <b>Artikel KB Dipakai</b>: %s<br/>"
                    "• <b>Diselesaikan Oleh</b>: %s"
                ) % (kb_title, self.env.user.name)

            else:
                # Validasi Ketat Wajib Isi Solusi / Foto Bukti
                has_text = not _is_html_empty(ticket.resolution)
                has_images = bool(ticket.solution_attachment_ids)

                if not has_text and not has_images:
                    raise UserError('Gagal menyelesaikan tiket! Anda wajib mengisikan Langkah-Langkah Solusi (Teks Panduan) atau mengunggah Lampiran Bukti Foto Penyelesaian terlebih dahulu sebelum mengklik Mark as Done!')

                if has_text and has_images:
                    sol_type = 'hybrid'
                elif has_text:
                    sol_type = 'text'
                else:
                    sol_type = 'images'

                if ticket.is_published_to_kb:
                    ticket._sync_knowledge_base()

                sol_type_dict = {
                    'text': 'Teks Tutorial Saja',
                    'images': 'Kumpulan Capture / Foto Saja',
                    'hybrid': 'Teks & Capture (Kombinasi Inline)'
                }
                format_label = sol_type_dict.get(sol_type, 'Tutorial')
                kb_status = "Ya (Terbit ke Knowledge Base)" if ticket.is_published_to_kb else "Tidak"
                text_preview = ticket.resolution or "Panduan terlampir pada file/foto bukti."
                attachment_count = len(ticket.solution_attachment_ids)

                log_body = (
                    "<b>🛠️ AKSI PENYELESAIAN TIKET (RESOLVED LOG)</b><br/>"
                    "• <b>Format Solusi</b>: %s<br/>"
                    "• <b>Lampiran Foto/File Bukti</b>: %d file terlampir<br/>"
                    "• <b>Diterbitkan ke Knowledge Base</b>: %s<br/>"
                    "• <b>Detail Solusi / Tutorial</b>:<br/>%s<br/>"
                    "• <b>Diselesaikan Oleh</b>: %s"
                ) % (format_label, attachment_count, kb_status, text_preview, self.env.user.name)

            now_dt = fields.Datetime.now()
            vals_done = {
                'state': 'done',
                'resolved_date': now_dt
            }
            if not ticket.start_progress_date:
                vals_done['start_progress_date'] = now_dt

            # Hitung Batas Waktu Auto Close berdasarkan Konfigurasi SLA & Hari Kerja
            if ticket.enable_auto_close:
                sla = ticket.sla_id or self.env['helpdesk.sla'].search([('priority', '=', ticket.priority)], limit=1)
                if sla:
                    vals_done['auto_close_deadline'] = sla.get_auto_close_deadline(now_dt)
                else:
                    p_code = ticket.priority or '3'
                    work_days = 4 if p_code in ('1', '2') else 3 if p_code == '3' else 2
                    calendar = self.env.company.resource_calendar_id
                    if calendar:
                        try:
                            vals_done['auto_close_deadline'] = calendar.plan_days(work_days, now_dt, compute_leaves=True)
                        except Exception:
                            vals_done['auto_close_deadline'] = now_dt + timedelta(days=work_days)
                    else:
                        vals_done['auto_close_deadline'] = now_dt + timedelta(days=work_days)
            else:
                vals_done['auto_close_deadline'] = False

            ticket.write(vals_done)

            # Post explicit resolution action details to Chatter history log
            if log_body:
                if ticket.enable_auto_close and vals_done.get('auto_close_deadline'):
                    deadline_str = fields.Datetime.to_string(vals_done['auto_close_deadline'])
                    log_body += "<br/>• <b>Auto Close Target</b>: %s (Otomatis ditutup dalam %s hari kerja)" % (
                        deadline_str,
                        "4" if ticket.priority in ('1', '2') else "3" if ticket.priority == '3' else "2"
                    )
                ticket.message_post(body=log_body, subtype_xmlid='mail.mt_note')

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'name': _('Reject Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id},
        }

    def action_reject(self):
        return self.action_open_reject_wizard()


    def action_cancel(self):
        for ticket in self:
            ticket.write({'state': 'reject'})

    def action_close(self):
        for ticket in self:
            ticket.write({
                'state': 'closed',
                'closed_date': fields.Datetime.now()
            })

    def action_reopen_progress(self):
        """Dikembalikan dari status Done/Closed ke status Progress oleh Helpdesk Officer / Manager"""
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.state not in ('done', 'closed'):
                continue
            vals = {
                'state': 'in_progress',
                'resolved_date': False,
                'closed_date': False,
                'auto_close_deadline': False,
            }
            if ticket.sla_id:
                vals['sla_resolution_deadline'] = ticket.sla_id.get_resolution_deadline(now)
            ticket.write(vals)
            ticket.message_post(
                body=_("⚠️ <b>Tiket Dikembalikan ke Status Progress</b><br/>Status tiket dikembalikan ke <b>Progress</b> oleh Officer/Manager <b>%s</b> untuk dikerjakan ulang.<br/><i>Durasi SLA Resolution Due Date diaktifkan dan dihitung ulang sesuai tingkat prioritas (%s).</i>") % (self.env.user.name, ticket.priority or '-'),
                message_type='notification'
            )
            if ticket.engineer_id:
                ticket._send_engineer_assignment_email()

    def action_reopen_assigned(self):
        """Dikembalikan dari status Done/Closed ke status Assigned oleh Helpdesk Officer / Manager"""
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.state not in ('done', 'closed'):
                continue
            vals = {
                'state': 'assigned',
                'resolved_date': False,
                'closed_date': False,
                'auto_close_deadline': False,
            }
            if ticket.sla_id:
                vals['sla_resolution_deadline'] = ticket.sla_id.get_resolution_deadline(now)
            ticket.write(vals)
            ticket.message_post(
                body=_("⚠️ <b>Tiket Dibuka Kembali (Assigned)</b><br/>Status tiket dikembalikan ke <b>Assigned</b> oleh Officer/Manager <b>%s</b> karena laporan kendala belum sepenuhnya terselesaikan.<br/><i>Durasi SLA Resolution Due Date diaktifkan dan dihitung ulang sesuai tingkat prioritas (%s).</i>") % (self.env.user.name, ticket.priority or '-'),
                message_type='notification'
            )
            if ticket.engineer_id:
                ticket._send_engineer_assignment_email()

    @api.model
    def _cron_auto_close_tickets(self):
        """Cron Job: Penutupan otomatis tiket berstatus Done setelah melewati batas hari kerja Auto Close"""
        now = fields.Datetime.now()
        tickets = self.search([
            ('state', '=', 'done'),
            ('enable_auto_close', '=', True),
            ('auto_close_deadline', '!=', False),
            ('auto_close_deadline', '<=', now)
        ])
        for ticket in tickets:
            ticket.write({
                'state': 'closed',
                'closed_date': now,
            })
            days_label = "4 hari kerja (High)" if ticket.priority in ('1', '2') else "3 hari kerja (Medium)" if ticket.priority == '3' else "2 hari kerja (Low)"
            ticket.message_post(
                body=_("🤖 <b>Auto Close Tiket Otomatis</b><br/>Tiket telah ditutup secara otomatis oleh sistem setelah melewati batas waktu %s pasca penyelesaian.") % days_label,
                message_type='notification'
            )

    def action_open_reassign_wizard(self):
        """Membuka pop-up wizard untuk pengalihan/eskalasi engineer manual"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Eskalasi / Reassign Ticket',
            'res_model': 'helpdesk.ticket.reassign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_current_engineer_id': self.engineer_id.id if self.engineer_id else False,
            }
        }

    def _send_creation_notifications(self):
        template_requester = self.env.ref(
            'it_helpdesk_v2.mail_template_ticket_created_requester', raise_if_not_found=False)
        template_manager = self.env.ref(
            'it_helpdesk_v2.mail_template_ticket_created_manager', raise_if_not_found=False)
        for ticket in self:
            if ticket.cc_partner_ids:
                try:
                    ticket.message_subscribe(partner_ids=ticket.cc_partner_ids.ids)
                except Exception:
                    pass
            if template_requester:
                cc_emails = [p.email for p in ticket.cc_partner_ids if p.email]
                email_vals = {}
                if cc_emails:
                    email_vals['email_cc'] = ','.join(cc_emails)
                template_requester.send_mail(ticket.id, force_send=False, email_values=email_vals if email_vals else None)
            if template_manager:
                teams = self.env['helpdesk.team'].search(
                    [('service_ids', 'in', ticket.service_id.ids)])
                partners = teams.manager_id.partner_id
                if partners:
                    template_manager.send_mail(
                        ticket.id, force_send=False,
                        email_values={'recipient_ids': [(6, 0, partners.ids)]})

    def cron_check_sla_breach(self):
        """Dipanggil scheduled action 'Cek SLA Breach' tiap 5 menit."""
        now = fields.Datetime.now()
        tickets = self.search([
            ('state', 'in', OPEN_STATES),
            ('sla_resolution_deadline', '<', now),
            ('sla_resolution_breached', '=', False),
        ])
        template = self.env.ref(
            'it_helpdesk_v2.mail_template_ticket_sla_breach', raise_if_not_found=False)
        for ticket in tickets:
            ticket.sla_resolution_breached = True
            ticket.message_post(
                body='SLA resolution untuk tiket %s telah lewat batas waktu (%s).' % (
                    ticket.name, ticket.sla_resolution_deadline))
            partners = ticket.engineer_id.partner_id | ticket.team_id.manager_id.partner_id
            if template and partners:
                template.send_mail(
                    ticket.id, force_send=False,
                    email_values={'recipient_ids': [(6, 0, partners.ids)]})

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'helpdesk.work.order',
            'view_mode': 'tree,form',
            'domain': [('ticket_id', '=', self.id)],
            'context': {'default_ticket_id': self.id},
        }

    def action_submit_create(self):
        """Dipanggil dari tombol Submit di form Create Ticket (Stage 8);
        record sudah tersimpan otomatis oleh Odoo sebelum method ini jalan,
        di sini tinggal arahkan user ke form detail tiket yang baru dibuat."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'helpdesk.ticket',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('it_helpdesk.view_helpdesk_ticket_form').id, 'form')],
            'target': 'current',
        }


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        if mode == 'read' and self.env.user.has_group('base.group_user'):
            return True
        return super().check(mode, values=values)
