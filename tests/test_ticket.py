from datetime import timedelta

from odoo import fields
from odoo.tests import common


class TestTicket(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['helpdesk.service'].create({'name': 'Test Service'})
        self.q1 = self.env.ref('it_helpdesk.helpdesk_priority_answer_q1_1')  # score 5
        self.q2 = self.env.ref('it_helpdesk.helpdesk_priority_answer_q2_1')  # score 5
        self.q3 = self.env.ref('it_helpdesk.helpdesk_priority_answer_q3_1')  # score 5
        self.q4 = self.env.ref('it_helpdesk.helpdesk_priority_answer_q4_1')  # score 5
        self.q5 = self.env.ref('it_helpdesk.helpdesk_priority_answer_q5_1')  # score 5

    def _create_ticket(self, ticket_type='incident', **overrides):
        vals = {
            'title': 'Test Ticket',
            'ticket_type': ticket_type,
            'service_id': self.service.id,
            'description': '<p>desc</p>',
            'q1_answer_id': self.q1.id,
            'q2_answer_id': self.q2.id,
            'q3_answer_id': self.q3.id,
            'q4_answer_id': self.q4.id,
            'q5_answer_id': self.q5.id,
        }
        vals.update(overrides)
        return self.env['helpdesk.ticket'].create(vals)

    def test_sequence_naming_incident(self):
        ticket = self._create_ticket(ticket_type='incident')
        self.assertTrue(ticket.name.startswith('INC-'))

    def test_sequence_naming_service_request(self):
        ticket = self._create_ticket(ticket_type='service_request')
        self.assertTrue(ticket.name.startswith('SR-'))

    def test_impact_urgency_score_and_priority(self):
        # semua jawaban skor 5, weight default 1
        # impact_score = 5+5+5=15 (>=12 -> tinggi), urgency_score = 5+5=10 (>=8 -> tinggi)
        ticket = self._create_ticket()
        self.assertEqual(ticket.impact_score, 15)
        self.assertEqual(ticket.urgency_score, 10)
        self.assertEqual(ticket.impact_level, 'tinggi')
        self.assertEqual(ticket.urgency_level, 'tinggi')
        self.assertEqual(ticket.priority, '1')
        self.assertEqual(ticket.sla_id.label, 'Critical')

    def test_low_score_priority(self):
        ticket = self._create_ticket(
            q1_answer_id=self.env.ref('it_helpdesk.helpdesk_priority_answer_q1_5').id,
            q2_answer_id=self.env.ref('it_helpdesk.helpdesk_priority_answer_q2_5').id,
            q3_answer_id=self.env.ref('it_helpdesk.helpdesk_priority_answer_q3_8').id,
            q4_answer_id=self.env.ref('it_helpdesk.helpdesk_priority_answer_q4_5').id,
            q5_answer_id=self.env.ref('it_helpdesk.helpdesk_priority_answer_q5_5').id,
        )
        # impact_score=3 -> rendah, urgency_score=2 -> rendah -> matrix RENDAH+RENDAH -> P4
        self.assertEqual(ticket.impact_level, 'rendah')
        self.assertEqual(ticket.urgency_level, 'rendah')
        self.assertEqual(ticket.priority, '4')
        self.assertEqual(ticket.sla_id.label, 'Low')

    def test_sla_deadline_computed(self):
        ticket = self._create_ticket()
        self.assertTrue(ticket.sla_response_deadline)
        self.assertTrue(ticket.sla_resolution_deadline)
        self.assertGreater(ticket.sla_response_deadline, ticket.created_date)

    def test_sla_response_breach_when_overdue(self):
        past = fields.Datetime.now() - timedelta(hours=2)
        ticket = self._create_ticket(created_date=past)
        # P1: SLA response 15 menit, dibuat 2 jam lalu, belum direspon -> harus breached
        self.assertEqual(ticket.priority, '1')
        self.assertTrue(ticket.sla_response_breached)

    def test_sla_response_not_breached_when_responded_in_time(self):
        past = fields.Datetime.now() - timedelta(hours=2)
        ticket = self._create_ticket(created_date=past)
        ticket.first_response_date = past + timedelta(minutes=5)
        self.assertFalse(ticket.sla_response_breached)

    def test_action_assign_requires_engineer(self):
        ticket = self._create_ticket()
        with self.assertRaises(Exception):
            ticket.action_assign()

    def test_action_assign_sets_state_and_first_response(self):
        ticket = self._create_ticket(engineer_id=self.env.ref('base.user_admin').id)
        self.assertFalse(ticket.first_response_date)
        ticket.action_assign()
        self.assertEqual(ticket.state, 'assigned')
        self.assertTrue(ticket.first_response_date)

    def test_full_state_flow(self):
        ticket = self._create_ticket(engineer_id=self.env.ref('base.user_admin').id)
        ticket.action_assign()
        ticket.action_start_progress()
        self.assertEqual(ticket.state, 'in_progress')
        self.assertEqual(ticket.progress_percent, 50.0)
        ticket.action_set_pending()
        self.assertEqual(ticket.state, 'pending')
        ticket.action_resolve()
        self.assertEqual(ticket.state, 'resolved')
        self.assertTrue(ticket.resolved_date)
        ticket.action_close()
        self.assertEqual(ticket.state, 'closed')
        self.assertTrue(ticket.closed_date)
        self.assertEqual(ticket.progress_percent, 100.0)

    def test_action_cancel(self):
        ticket = self._create_ticket()
        ticket.action_cancel()
        self.assertEqual(ticket.state, 'cancelled')

    def test_category_subcategory_relation(self):
        category = self.env['helpdesk.category'].create(
            {'name': 'Test Category', 'service_id': self.service.id})
        subcategory = self.env['helpdesk.subcategory'].create(
            {'name': 'Test Subcategory', 'category_id': category.id})
        ticket = self._create_ticket(category_id=category.id, subcategory_id=subcategory.id)
        self.assertEqual(ticket.category_id, category)
        self.assertEqual(ticket.subcategory_id, subcategory)
