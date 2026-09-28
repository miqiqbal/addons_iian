from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestSLA(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.start = datetime(2026, 7, 20, 9, 0, 0)  # Senin 09:00
        self.sla_p1 = self.env.ref('it_helpdesk.helpdesk_sla_p1')
        self.sla_p2 = self.env.ref('it_helpdesk.helpdesk_sla_p2')
        self.sla_p3 = self.env.ref('it_helpdesk.helpdesk_sla_p3')
        self.sla_p4 = self.env.ref('it_helpdesk.helpdesk_sla_p4')

    def test_response_deadline_minute_unit(self):
        # P1: response 15 menit
        deadline = self.sla_p1.get_deadline(self.start)
        self.assertEqual(deadline, self.start + timedelta(minutes=15))

    def test_resolution_deadline_hour_unit(self):
        # P1: resolution 4 jam (kalender biasa, bukan jam kerja)
        deadline = self.sla_p1.get_resolution_deadline(self.start)
        self.assertEqual(deadline, self.start + timedelta(hours=4))

    def test_response_deadline_minute_unit_p2(self):
        deadline = self.sla_p2.get_deadline(self.start)
        self.assertEqual(deadline, self.start + timedelta(minutes=30))

    def test_resolution_deadline_working_hour_unit(self):
        # P2: resolution 8 jam kerja -> harus lewat resource.calendar, bukan timedelta mentah
        deadline = self.sla_p2.get_resolution_deadline(self.start)
        self.assertGreater(deadline, self.start)

    def test_response_deadline_working_hour_unit(self):
        # P3: response 4 jam kerja
        deadline = self.sla_p3.get_deadline(self.start)
        self.assertGreater(deadline, self.start)

    def test_resolution_deadline_working_day_unit(self):
        # P3: resolution 3 hari kerja
        deadline = self.sla_p3.get_resolution_deadline(self.start)
        self.assertGreater(deadline, self.start)
        self.assertGreaterEqual((deadline - self.start).days, 2)

    def test_response_deadline_working_day_unit(self):
        # P4: response 1 hari kerja
        deadline = self.sla_p4.get_deadline(self.start)
        self.assertGreater(deadline, self.start)

    def test_priority_unique_constraint(self):
        with self.assertRaises(Exception):
            self.env['helpdesk.sla'].create({
                'priority': '1',
                'response_time_value': 1,
                'response_time_unit': 'minute',
                'resolution_time_value': 1,
                'resolution_time_unit': 'hour',
            })

    def test_priority_matrix_unique_constraint(self):
        with self.assertRaises(Exception):
            self.env['helpdesk.priority.matrix'].create({
                'impact_level': 'tinggi',
                'urgency_level': 'tinggi',
                'priority': '1',
            })
