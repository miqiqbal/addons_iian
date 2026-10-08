from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketRejectWizard(models.TransientModel):
    _name = 'helpdesk.ticket.reject.wizard'
    _description = 'Wizard Reject Ticket'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Tiket', required=True, default=lambda self: self.env.context.get('active_id'))
    reason = fields.Text(string='Alasan Penolakan', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.ticket_id:
            raise UserError(_('Tiket tidak ditemukan.'))

        # Update state langsung kembali ke draft dan simpan alasan penolakan pada tiket
        self.ticket_id.sudo().with_context(bypass_draft_write_check=True).write({
            'state': 'draft',
            'rejection_reason': self.reason
        })

        # Catat log otomatis di Chatter
        message_body = _(
            "<b>❌ Tiket Ditolak & Dikembalikan ke Draft</b><br/>"
            "• <b>Ditolak oleh:</b> %s<br/>"
            "• <b>Alasan Penolakan / Catatan Revisi:</b> %s<br/>"
            "<i>Status tiket telah dikembalikan ke <b>Draft</b> agar pemohon dapat langsung merevisi formulir dan mengajukan ulang.</i>"
        ) % (self.env.user.name, self.reason)

        self.ticket_id.message_post(body=message_body, message_type='notification')

        return {'type': 'ir.actions.act_window_close'}
