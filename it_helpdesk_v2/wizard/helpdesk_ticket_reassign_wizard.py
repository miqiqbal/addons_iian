from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketReassignWizard(models.TransientModel):
    _name = 'helpdesk.ticket.reassign.wizard'
    _description = 'Wizard Eskalasi / Reassign Ticket'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Tiket', required=True, default=lambda self: self.env.context.get('active_id'))
    current_engineer_id = fields.Many2one('res.users', string='Engineer saat Ini', related='ticket_id.engineer_id', readonly=True)
    new_engineer_id = fields.Many2one(
        'res.users', string='Engineer Penerima Baru', required=True,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('it_helpdesk_v2.group_helpdesk_agent').id])]
    )
    reason = fields.Text(string='Alasan Pengalihan / Eskalasi', required=True)

    def action_confirm_reassign(self):
        self.ensure_one()
        if not self.ticket_id:
            raise UserError(_('Tiket tidak ditemukan.'))

        old_engineer_name = self.current_engineer_id.name if self.current_engineer_id else 'Unassigned'
        new_engineer_name = self.new_engineer_id.name

        # Update engineer pada tiket
        self.ticket_id.write({
            'engineer_id': self.new_engineer_id.id,
            'state': 'assigned' if self.ticket_id.state in ('open', 'draft') else self.ticket_id.state
        })

        # Catat log otomatis di Chatter
        message_body = _(
            "<b>🔄 Pengalihan / Eskalasi Tiket Manual</b><br/>"
            "• <b>Dari Engineer:</b> %s<br/>"
            "• <b>Ke Engineer Baru:</b> %s<br/>"
            "• <b>Oleh User:</b> %s<br/>"
            "• <b>Alasan:</b> %s"
        ) % (old_engineer_name, new_engineer_name, self.env.user.name, self.reason)

        self.ticket_id.message_post(body=message_body, message_type='notification')

        # Kirim email penugasan ke engineer baru
        if self.new_engineer_id:
            self.ticket_id._send_engineer_assignment_email()

        return {'type': 'ir.actions.act_window_close'}
