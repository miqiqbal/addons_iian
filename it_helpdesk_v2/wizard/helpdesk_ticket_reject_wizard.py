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

        # Update state dan rejection reason pada tiket
        self.ticket_id.write({
            'state': 'reject',
            'rejection_reason': self.reason
        })

        # Catat log otomatis di Chatter
        message_body = _(
            "<b>❌ Tiket Ditolak (Reject)</b><br/>"
            "• <b>Ditolak oleh:</b> %s<br/>"
            "• <b>Alasan Penolakan:</b> %s"
        ) % (self.env.user.name, self.reason)

        self.ticket_id.message_post(body=message_body, message_type='notification')

        return {'type': 'ir.actions.act_window_close'}
