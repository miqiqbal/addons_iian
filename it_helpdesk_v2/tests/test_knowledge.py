import base64
from odoo.tests import common
from odoo.exceptions import UserError


class TestHelpdeskKnowledge(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['helpdesk.service'].create({'name': 'IT Service Test'})
        self.category = self.env['helpdesk.category'].create({
            'name': 'Hardware Test',
            'service_id': self.service.id,
        })
        self.subcategory = self.env['helpdesk.subcategory'].create({
            'name': 'Printer Test',
            'category_id': self.category.id,
        })
        self.mgr_group = self.env.ref('it_helpdesk_v2.group_helpdesk_manager', raise_if_not_found=False)
        self.it_mgr_group = self.env.ref('it_helpdesk_v2.group_helpdesk_it_manager', raise_if_not_found=False)
        self.agent_group = self.env.ref('it_helpdesk_v2.group_helpdesk_agent', raise_if_not_found=False)
        self.user_group = self.env.ref('it_helpdesk_v2.group_helpdesk_user', raise_if_not_found=False)

    def test_create_knowledge_auto_hierarchy(self):
        # Create with only subcategory -> should auto-fill category and service
        kb = self.env['helpdesk.knowledge'].create({
            'name': 'Cara Memperbaiki Printer Paper Jam',
            'subcategory_id': self.subcategory.id,
            'summary': 'Kertas macet di dalam roller printer',
            'content': '<p>Tarik kertas perlahan ke arah luar.</p>',
            'solution_type': 'text',
        })
        self.assertEqual(kb.category_id, self.category)
        self.assertEqual(kb.service_id, self.service)
        self.assertEqual(kb.problem, 'Cara Memperbaiki Printer Paper Jam')

    def test_create_knowledge_file_mode_with_attachment(self):
        # Admin creates KB with solution_type='file' and attachment, without typing manual content
        attachment = self.env['ir.attachment'].create({
            'name': 'SOP_Printer_Paper_Jam.pdf',
            'type': 'binary',
            'datas': base64.b64encode(b'PDF CONTENT GUIDE'),
        })
        kb = self.env['helpdesk.knowledge'].create({
            'name': 'SOP Penanganan Printer Paper Jam',
            'subcategory_id': self.subcategory.id,
            'solution_type': 'file',
            'attachment_ids': [(6, 0, [attachment.id])],
        })
        self.assertEqual(kb.solution_type, 'file')
        self.assertTrue('lampiran' in kb.content.lower(), 'Default text should be generated for file mode')
        self.assertEqual(attachment.res_model, 'helpdesk.knowledge')
        self.assertEqual(attachment.res_id, kb.id)

    def test_onchange_hierarchy(self):
        kb = self.env['helpdesk.knowledge'].new({
            'name': 'Panduan Baru',
        })
        kb.subcategory_id = self.subcategory
        kb._onchange_subcategory_id()
        self.assertEqual(kb.category_id, self.category)
        self.assertEqual(kb.service_id, self.service)

    def test_security_it_manager_and_agent_read_only(self):
        # IT Manager (Read Only)
        it_manager_user = self.env['res.users'].create({
            'name': 'Test IT Manager',
            'login': 'it_mgr_test_kb',
            'groups_id': [(6, 0, [self.it_mgr_group.id])] if self.it_mgr_group else [],
        })
        # Regular Employee (Read Only)
        employee_user = self.env['res.users'].create({
            'name': 'Test Employee User',
            'login': 'employee_test_kb',
            'groups_id': [(6, 0, [self.user_group.id])] if self.user_group else [],
        })
        # IT Admin (Full Access)
        admin_user = self.env['res.users'].create({
            'name': 'Test IT Admin',
            'login': 'admin_test_kb',
            'groups_id': [(6, 0, [self.mgr_group.id])] if self.mgr_group else [],
        })

        # 1. Non-admin users cannot create
        with self.assertRaises(UserError):
            self.env['helpdesk.knowledge'].with_user(it_manager_user).create({
                'name': 'Test Blocked Create IT Mgr',
                'subcategory_id': self.subcategory.id,
            })
        with self.assertRaises(UserError):
            self.env['helpdesk.knowledge'].with_user(employee_user).create({
                'name': 'Test Blocked Create Employee',
                'subcategory_id': self.subcategory.id,
            })

        # 2. IT Admin can create
        kb = self.env['helpdesk.knowledge'].with_user(admin_user).create({
            'name': 'Panduan Keamanan Dibuat Admin',
            'subcategory_id': self.subcategory.id,
        })
        self.assertTrue(kb.id)

        # 3. Non-admin cannot write
        with self.assertRaises(UserError):
            kb.with_user(it_manager_user).write({'name': 'Updated by IT Manager'})
        with self.assertRaises(UserError):
            kb.with_user(employee_user).write({'name': 'Updated by Employee'})

        # 4. IT Admin can write
        kb.with_user(admin_user).write({'name': 'Updated by IT Admin'})
        self.assertEqual(kb.name, 'Updated by IT Admin')

        # 5. Non-admin cannot unlink
        with self.assertRaises(UserError):
            kb.with_user(it_manager_user).unlink()
        with self.assertRaises(UserError):
            kb.with_user(employee_user).unlink()

        # 6. IT Admin can unlink
        kb_id = kb.id
        kb.with_user(admin_user).unlink()
        self.assertFalse(self.env['helpdesk.knowledge'].browse(kb_id).exists())
