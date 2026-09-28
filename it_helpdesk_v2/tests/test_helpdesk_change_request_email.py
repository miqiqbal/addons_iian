from odoo.tests import common


class TestHelpdeskChangeRequestEmail(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.dept_manager = self.env['res.users'].create({
            'name': 'Dept Manager Test',
            'login': 'dept.manager.test@example.com',
            'email': 'dept.manager.test@example.com',
        })
        self.it_manager = self.env['res.users'].create({
            'name': 'IT Manager Test',
            'login': 'it.manager.test@example.com',
            'email': 'it.manager.test@example.com',
        })

    def _create_cr(self, **extra_vals):
        vals = {
            'request_identification': 'Perlu tambahan field di form X',
            'category': 'form',
        }
        vals.update(extra_vals)
        return self.env['helpdesk.change.request'].create(vals)

    def test_publish_with_dept_manager_moves_to_dept_approval(self):
        cr = self._create_cr(dept_manager_id=self.dept_manager.id)
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_approval')
        self.assertTrue(cr.code)

    def test_publish_without_dept_manager_does_not_raise(self):
        cr = self._create_cr()
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_approval')

    def test_approve_dept_moves_to_it_approval(self):
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id, manager_it_id=self.it_manager.id)
        cr.action_publish()
        cr.action_approve_dept()
        self.assertEqual(cr.state, 'it_approval')

    def test_reject_does_not_raise_without_requester_email(self):
        cr = self._create_cr()
        cr.created_by = False
        cr.action_reject()
        self.assertEqual(cr.state, 'rejected')

    def test_done_moves_state(self):
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id, manager_it_id=self.it_manager.id)
        cr.action_publish()
        cr.action_approve_dept()
        cr.action_approve_it()
        cr.action_done()
        self.assertEqual(cr.state, 'done')
