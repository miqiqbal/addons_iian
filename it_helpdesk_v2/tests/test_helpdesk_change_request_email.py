from datetime import date
from odoo.exceptions import UserError
from odoo.tests import common


class TestHelpdeskChangeRequestEmail(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept_manager = cls.env['res.users'].create({
            'name': 'Dept Manager Test',
            'login': 'dept.manager.test@example.com',
            'email': 'dept.manager.test@example.com',
        })
        cls.kadept_user = cls.env['res.users'].create({
            'name': 'Kadept Test',
            'login': 'kadept.test@example.com',
            'email': 'kadept.test@example.com',
        })
        cls.bpo_kadept_user = cls.env['res.users'].create({
            'name': 'BPO Kadept Test',
            'login': 'bpo.kadept.test@example.com',
            'email': 'bpo.kadept.test@example.com',
        })
        cls.it_manager = cls.env['res.users'].create({
            'name': 'IT Manager Test',
            'login': 'it.manager.test@example.com',
            'email': 'it.manager.test@example.com',
        })
        cls.kadept_it_user = cls.env['res.users'].create({
            'name': 'Kadept IT Test',
            'login': 'kadept.it.test@example.com',
            'email': 'kadept.it.test@example.com',
        })
        cls.engineer_user = cls.env['res.users'].create({
            'name': 'Engineer Test',
            'login': 'engineer.test@example.com',
            'email': 'engineer.test@example.com',
        })
        cls.cr_type = cls.env['helpdesk.cr.type'].create({'name': 'Enhancement'})
        cls.service = cls.env['helpdesk.service'].create({'name': 'ERP'})
        cls.category = cls.env['helpdesk.category'].create({'name': 'Finance', 'service_id': cls.service.id})
        cls.subcategory = cls.env['helpdesk.subcategory'].create({'name': 'Invoice', 'category_id': cls.category.id})
        cls.target_dept = cls.env['hr.department'].create({'name': 'Departemen Keuangan'})
        cls.attachment = cls.env['ir.attachment'].create({'name': 'doc.pdf', 'datas': 'dGVzdA=='})

    def _create_cr(self, **extra_vals):
        vals = {
            'request_identification': 'Perlu tambahan field di form X',
            'cr_type_id': self.cr_type.id,
            'category_id': self.category.id,
            'subcategory_id': self.subcategory.id,
            'target_department_id': self.target_dept.id,
            'impact_on': 'development',
            'attachment_ids': [(6, 0, [self.attachment.id])],
        }
        vals.update(extra_vals)
        return self.env['helpdesk.change.request'].create(vals)

    def test_publish_with_dept_manager_moves_to_dept_mgr_approval(self):
        cr = self._create_cr(dept_manager_id=self.dept_manager.id)
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_mgr_approval')
        self.assertTrue(cr.code)

    def test_publish_without_dept_manager_does_not_raise(self):
        cr = self._create_cr()
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_mgr_approval')

    def test_approve_flow_standard(self):
        dept_other = self.env['hr.department'].create({'name': 'Departemen Keuangan'})
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id,
            kadept_manager_id=self.kadept_user.id,
            target_department_id=dept_other.id,
            bpo_kadept_manager_id=self.bpo_kadept_user.id,
            manager_it_id=self.it_manager.id,
            kadept_it_manager_id=self.kadept_it_user.id,
            engineer_id=self.engineer_user.id,
            estimated_completion_date=date.today(),
        )
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_mgr_approval')

        cr.with_user(self.dept_manager).action_approve_dept_mgr()
        self.assertEqual(cr.state, 'kadept_approval')

        cr.with_user(self.kadept_user).action_approve_kadept()
        self.assertEqual(cr.state, 'bpo_approval')

        cr.with_user(self.bpo_kadept_user).action_approve_bpo()
        self.assertEqual(cr.state, 'it_mgr_review')

        cr.with_user(self.it_manager).action_review_it_mgr()
        self.assertEqual(cr.state, 'it_kadept_approval')

        cr.with_user(self.kadept_it_user).action_approve_it_kadept()
        self.assertEqual(cr.state, 'in_progress')

        cr.action_done()
        self.assertEqual(cr.state, 'done')

    def test_approve_flow_bypass_bpo_for_it_dept(self):
        dept_it = self.env['hr.department'].create({'name': 'Departemen Sistem, TI & Digitalisasi'})
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id,
            kadept_manager_id=self.kadept_user.id,
            target_department_id=dept_it.id,
            manager_it_id=self.it_manager.id,
            kadept_it_manager_id=self.kadept_it_user.id,
            engineer_id=self.engineer_user.id,
            estimated_completion_date=date.today(),
        )
        cr.action_publish()
        self.assertEqual(cr.state, 'dept_mgr_approval')

        cr.with_user(self.dept_manager).action_approve_dept_mgr()
        self.assertEqual(cr.state, 'kadept_approval')

        # Since target dept is IT, it should directly jump to it_mgr_review
        cr.with_user(self.kadept_user).action_approve_kadept()
        self.assertEqual(cr.state, 'it_mgr_review')

    def test_reject_does_not_raise_without_requester_email(self):
        dept_other = self.env['hr.department'].create({'name': 'Departemen Keuangan'})
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id,
            kadept_manager_id=self.kadept_user.id,
            target_department_id=dept_other.id,
        )
        cr.created_by = False
        cr.action_publish()
        wizard = self.env['helpdesk.cr.reject.wizard'].create({
            'cr_id': cr.id,
            'reason': 'Alasan penolakan pengujian',
        })
        wizard.action_confirm_reject()
        self.assertEqual(cr.state, 'draft')
        self.assertEqual(cr.rejection_reason, 'Alasan penolakan pengujian')

    def test_dept_manager_cannot_done_or_start_progress_cr(self):
        dept_it = self.env['hr.department'].create({'name': 'Departemen Sistem, TI & Digitalisasi'})
        cr = self._create_cr(
            dept_manager_id=self.dept_manager.id,
            target_department_id=dept_it.id,
        )
        cr.action_publish()
        cr.state = 'in_progress'
        with self.assertRaises(UserError):
            cr.with_user(self.dept_manager).action_done()
        with self.assertRaises(UserError):
            cr.with_user(self.dept_manager).action_start_progress()
