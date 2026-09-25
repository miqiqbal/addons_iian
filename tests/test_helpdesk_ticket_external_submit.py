from odoo.tests import common


class TestHelpdeskTicketExternalSubmit(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['helpdesk.service'].create({'name': 'Jaringan'})
        self.category = self.env['helpdesk.category'].create({'name': 'Internet'})
        self.location = self.env['helpdesk.location'].create({'name': 'Kantor Pusat'})
        self.outsider = self.env['res.users'].create({
            'name': 'Outsider Test',
            'login': 'outsider.test@example.com',
            'email': 'outsider.test@example.com',
        })

    def test_create_and_publish_sets_open_state(self):
        ticket = self.env['helpdesk.ticket'].sudo().create({
            'requester_id': self.outsider.id,
            'email': self.outsider.email,
            'phone': '0812345678',
            'title': 'Tidak bisa konek wifi',
            'description': 'Wifi mati sejak pagi',
            'service_id': self.service.id,
            'category_id': self.category.id,
            'location_id': self.location.id,
        })
        ticket.action_publish()
        self.assertEqual(ticket.state, 'open')
        self.assertEqual(ticket.requester_id, self.outsider)
        self.assertEqual(ticket.service_id, self.service)

    def test_outsider_without_helpdesk_group_can_be_used_as_requester_via_sudo(self):
        self.assertFalse(self.outsider.has_group('it_helpdesk_v2.group_helpdesk_user'))
        Ticket = self.env['helpdesk.ticket'].sudo()
        ticket = Ticket.create({
            'requester_id': self.outsider.id,
            'email': self.outsider.email,
            'phone': '0812345678',
            'title': 'Butuh reset password SAP',
            'service_id': self.service.id,
            'category_id': self.category.id,
            'location_id': self.location.id,
        })
        ticket.action_publish()
        self.assertEqual(ticket.state, 'open')
