from odoo.tests import common


class TestHelpdeskTicketExternalSubmit(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['helpdesk.service'].create({'name': 'Jaringan'})
        self.category = self.env['helpdesk.category'].create({'name': 'Internet'})
        self.location = self.env['helpdesk.location'].create({'name': 'Kantor Pusat'})
        self.q1 = self.env.ref('it_helpdesk_v2.helpdesk_priority_answer_q1_1', raise_if_not_found=False) or self.env.ref('it_helpdesk.helpdesk_priority_answer_q1_1')
        self.q2 = self.env.ref('it_helpdesk_v2.helpdesk_priority_answer_q2_1', raise_if_not_found=False) or self.env.ref('it_helpdesk.helpdesk_priority_answer_q2_1')
        self.q3 = self.env.ref('it_helpdesk_v2.helpdesk_priority_answer_q3_1', raise_if_not_found=False) or self.env.ref('it_helpdesk.helpdesk_priority_answer_q3_1')
        self.q4 = self.env.ref('it_helpdesk_v2.helpdesk_priority_answer_q4_1', raise_if_not_found=False) or self.env.ref('it_helpdesk.helpdesk_priority_answer_q4_1')
        self.q5 = self.env.ref('it_helpdesk_v2.helpdesk_priority_answer_q5_1', raise_if_not_found=False) or self.env.ref('it_helpdesk.helpdesk_priority_answer_q5_1')
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
            'q1_answer_id': self.q1.id,
            'q2_answer_id': self.q2.id,
            'q3_answer_id': self.q3.id,
            'q4_answer_id': self.q4.id,
            'q5_answer_id': self.q5.id,
            'expected_result': 'Bisa konek internet wifi',
            'excel_link': 'https://example.com/kendala',
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
            'q1_answer_id': self.q1.id,
            'q2_answer_id': self.q2.id,
            'q3_answer_id': self.q3.id,
            'q4_answer_id': self.q4.id,
            'q5_answer_id': self.q5.id,
            'expected_result': 'Password SAP di-reset',
            'excel_link': 'https://example.com/kendala',
        })
        ticket.action_publish()
        self.assertEqual(ticket.state, 'open')

    def test_create_and_publish_with_dash_for_expected_result_and_link(self):
        ticket = self.env['helpdesk.ticket'].sudo().create({
            'requester_id': self.outsider.id,
            'email': self.outsider.email,
            'phone': '0812345678',
            'title': 'Test strip kendala',
            'service_id': self.service.id,
            'category_id': self.category.id,
            'location_id': self.location.id,
            'q1_answer_id': self.q1.id,
            'q2_answer_id': self.q2.id,
            'q3_answer_id': self.q3.id,
            'q4_answer_id': self.q4.id,
            'q5_answer_id': self.q5.id,
            'expected_result': '-',
            'excel_link': '-',
        })
        ticket.action_publish()
        self.assertEqual(ticket.state, 'open')
        self.assertEqual(ticket.expected_result, '-')
        self.assertEqual(ticket.excel_link, '-')
