from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskCrRejectWizard(models.TransientModel):
    _name = 'helpdesk.cr.reject.wizard'
    _description = 'Wizard Reject Change Request'

    cr_id = fields.Many2one('helpdesk.change.request', string='Change Request', required=True, default=lambda self: self.env.context.get('active_id'))
    reason = fields.Text(string='Alasan Penolakan / Catatan Revisi', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.cr_id:
            raise UserError(_('Change Request tidak ditemukan.'))

        # Update state kembali ke draft dan simpan alasan penolakan
        self.cr_id.write({
            'state': 'draft',
            'rejection_reason': self.reason,
            'queue_number': 0,
        })
        self.cr_id._reindex_active_queue()

        # Kirim notifikasi email penolakan
        self.cr_id._send_rejected_email()

        # Catat log otomatis di Chatter
        message_body = _(
            "<b>❌ Change Request Ditolak & Dikembalikan ke Draft</b><br/>"
            "• <b>Ditolak oleh:</b> %s<br/>"
            "• <b>Alasan Penolakan / Catatan Revisi:</b> %s<br/>"
            "<i>Status Change Request dikembalikan ke Draft agar pemohon dapat merevisi dan mengajukan kembali.</i>"
        ) % (self.env.user.name, self.reason)

        self.cr_id.message_post(body=message_body, message_type='notification')

        return {'type': 'ir.actions.act_window_close'}
