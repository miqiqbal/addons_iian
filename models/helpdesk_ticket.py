from odoo import api, fields, models
from odoo.exceptions import UserError

from .helpdesk_priority_matrix import LEVEL_SELECTION

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
    category_id = fields.Many2one('helpdesk.category', string='Category')
    subcategory_id = fields.Many2one('helpdesk.subcategory', string='Sub Category')
    description = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment', string='Lampiran')
    resolution = fields.Html(string='Langkah-Langkah / Penjelasan Solusi Kendala (Tutorial)')
    solution_type = fields.Selection([
        ('text', 'Teks Tutorial Saja'),
        ('images', 'Kumpulan Capture / Foto Saja'),
        ('hybrid', 'Teks & Capture (Kombinasi Inline)')
    ], string='Format Jenis Solusi', default='hybrid')
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
    last_update = fields.Datetime(compute='_compute_last_update', store=True)
    customer_rating = fields.Selection(CUSTOMER_RATING_SELECTION)
    is_major_incident = fields.Boolean()
    is_security_incident = fields.Boolean()
    progress_percent = fields.Float(compute='_compute_progress')

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
    sla_warning_sent = fields.Boolean(string='SLA Warning Email Sent', default=False, copy=False)

    SLA_STATUS_SELECTION = [
        ('on_track', 'On Track'),
        ('warning', 'Warning'),
        ('critical', 'Critical Warning'),
        ('breached', 'SLA Breached')
    ]
    sla_status_label = fields.Selection(
        SLA_STATUS_SELECTION, string='SLA Status', compute='_compute_sla_status_label', store=False)

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

    @api.depends('sla_id', 'created_date')
    def _compute_sla_deadline(self):
        for ticket in self:
            if ticket.sla_id and ticket.created_date:
                ticket.sla_response_deadline = ticket.sla_id.get_deadline(ticket.created_date)
                ticket.sla_resolution_deadline = ticket.sla_id.get_resolution_deadline(
                    ticket.created_date)
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
        for ticket in self:
            c_date = ticket.created_date or ticket.create_date
            deadline = ticket.sla_resolution_deadline
            if not c_date or not deadline:
                ticket.sla_status_label = 'on_track'
                continue

            ref_date = (ticket.resolved_date or ticket.closed_date or now) if ticket.state in ('done', 'closed') else now
            if not ref_date:
                ref_date = now

            total_sec = (deadline - c_date).total_seconds()
            if total_sec <= 0:
                ticket.sla_status_label = 'breached' if ref_date > deadline else 'on_track'
                continue

            used_sec = (ref_date - c_date).total_seconds()
            used_ratio = used_sec / total_sec

            warn_ratio = (ticket.sla_id.warning_percent / 100.0) if ticket.sla_id and ticket.sla_id.warning_percent else 0.80
            crit_ratio = (ticket.sla_id.critical_percent / 100.0) if ticket.sla_id and ticket.sla_id.critical_percent else 0.90

            if ref_date > deadline or used_ratio >= 1.0:
                ticket.sla_status_label = 'breached'
            elif used_ratio >= crit_ratio:
                ticket.sla_status_label = 'critical'
            elif used_ratio >= warn_ratio:
                ticket.sla_status_label = 'warning'
            else:
                ticket.sla_status_label = 'on_track'

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

    def _auto_route_engineer(self, vals):
        content_to_check = "%s %s" % (vals.get('title', self.title or ''), vals.get('description', self.description or ''))
        content_lower = content_to_check.lower()

        KeywordModel = self.env['helpdesk.keyword']
        keywords = KeywordModel.search([('active', '=', True)], order='sequence, id')

        matched_rule = False
        subcat_id = vals.get('subcategory_id', self.subcategory_id.id if self else False)
        cat_id = vals.get('category_id', self.category_id.id if self else False)
        srv_id = vals.get('service_id', self.service_id.id if self else False)

        # 1. First Priority: Keyword Match in Title / Description (Explicit User Intent, e.g. Lupa Password)
        for rule in keywords:
            if not rule.keyword_list:
                continue
            words = [k.strip().lower() for k in rule.keyword_list.split(',') if k.strip()]
            words.sort(key=len, reverse=True)
            if any(w in content_lower for w in words):
                matched_rule = rule
                break

        # 2. Second Priority: Explicit Subcategory Match
        if not matched_rule and subcat_id:
            for rule in keywords:
                if rule.subcategory_ids and subcat_id in rule.subcategory_ids.ids:
                    matched_rule = rule
                    break

        # 3. Third Priority: Explicit Category Match
        if not matched_rule and cat_id:
            for rule in keywords:
                if rule.category_ids and cat_id in rule.category_ids.ids:
                    matched_rule = rule
                    break

        # 4. Fourth Priority: Broad Service Fallback
        if not matched_rule and srv_id:
            for rule in keywords:
                if rule.service_ids and srv_id in rule.service_ids.ids:
                    matched_rule = rule
                    break

        if matched_rule:
            if not vals.get('service_id') and matched_rule.service_ids:
                vals['service_id'] = matched_rule.service_ids[0].id
            if not vals.get('category_id') and matched_rule.category_ids:
                vals['category_id'] = matched_rule.category_ids[0].id
            if not vals.get('subcategory_id') and matched_rule.subcategory_ids:
                vals['subcategory_id'] = matched_rule.subcategory_ids[0].id

        if not vals.get('engineer_id'):
            engineer_id = False
            if matched_rule and matched_rule.engineer_ids:
                engineer_id = matched_rule.engineer_ids[0].id
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
            vals = {'state': 'open'}
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
        if vals.get('state') == 'in_progress':
            for ticket in self:
                if not ticket.start_progress_date:
                    vals['start_progress_date'] = fields.Datetime.now()

        old_engineers = {t.id: t.engineer_id.id for t in self}
        res = super().write(vals)

        if 'engineer_id' in vals:
            for ticket in self:
                if ticket.engineer_id and ticket.engineer_id.id != old_engineers.get(ticket.id):
                    ticket._send_engineer_assignment_email()

        if 'is_published_to_kb' in vals or 'resolution' in vals or 'solution_attachment_ids' in vals or 'solution_type' in vals:
            for ticket in self:
                if ticket.is_published_to_kb:
                    ticket._sync_knowledge_base()
        return res
        if 'is_published_to_kb' in vals or 'resolution' in vals or 'solution_attachment_ids' in vals or 'solution_type' in vals:
            for ticket in self:
                if ticket.is_published_to_kb:
                    ticket._sync_knowledge_base()
        return res

    def _sync_knowledge_base(self):
        for ticket in self:
            has_text = bool(ticket.resolution and ticket.resolution.replace('<p>', '').replace('</p>', '').replace('<br>', '').replace('&nbsp;', '').strip())
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
                # Validasi Wajib Isi Bukti / Solusi Penyelesaian (Sesuai Format Pilihan)
                sol_type = ticket.solution_type or 'hybrid'
                has_text = bool(ticket.resolution and ticket.resolution.replace('<p>', '').replace('</p>', '').replace('<br>', '').replace('&nbsp;', '').strip())
                has_images = bool(ticket.solution_attachment_ids)

                if sol_type == 'text' and not has_text:
                    raise UserError('Mohon lengkapi Teks Tutorial Penyelesaian Kendala terlebih dahulu sebelum mengklik Mark as Done!')
                elif sol_type == 'images' and not has_images:
                    raise UserError('Mohon unggah minimal 1 Foto Screenshot / File Bukti Penyelesaian terlebih dahulu sebelum mengklik Mark as Done!')
                elif sol_type == 'hybrid' and not (has_text or has_images):
                    raise UserError('Mohon lengkapi Teks Tutorial atau unggah Bukti Foto Screenshot Penyelesaian terlebih dahulu sebelum mengklik Mark as Done!')

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

            ticket.write({
                'state': 'done',
                'resolved_date': fields.Datetime.now()
            })

            # Post explicit resolution action details to Chatter history log
            if log_body:
                ticket.message_post(body=log_body, subtype_xmlid='mail.mt_note')

    def action_reject(self):
        for ticket in self:
            ticket.write({'state': 'reject'})

    def action_close(self):
        for ticket in self:
            ticket.write({
                'state': 'closed',
                'closed_date': fields.Datetime.now()
            })

    def _send_creation_notifications(self):
        template_requester = self.env.ref(
            'it_helpdesk.mail_template_ticket_created_requester', raise_if_not_found=False)
        template_manager = self.env.ref(
            'it_helpdesk.mail_template_ticket_created_manager', raise_if_not_found=False)
        for ticket in self:
            if template_requester:
                template_requester.send_mail(ticket.id, force_send=False)
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
            'it_helpdesk.mail_template_ticket_sla_breach', raise_if_not_found=False)
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
