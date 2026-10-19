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
        self.agent_group = self.env.ref('it_helpdesk_v2.group_helpdesk_agent', raise_if_not_found=False)

    def test_create_knowledge_auto_hierarchy(self):
        # Create with only subcategory -> should auto-fill category and service
        kb = self.env['helpdesk.knowledge'].create({
            'name': 'Cara Memperbaiki Printer Paper Jam',
            'subcategory_id': self.subcategory.id,
            'summary': 'Kertas macet di dalam roller printer',
            'content': '<p>Tarik kertas perlahan ke arah luar.</p>',
        })
        self.assertEqual(kb.category_id, self.category)
        self.assertEqual(kb.service_id, self.service)
        self.assertEqual(kb.problem, 'Cara Memperbaiki Printer Paper Jam')

    def test_onchange_hierarchy(self):
        kb = self.env['helpdesk.knowledge'].new({
            'name': 'Panduan Baru',
        })
        kb.subcategory_id = self.subcategory
        kb._onchange_subcategory_id()
        self.assertEqual(kb.category_id, self.category)
        self.assertEqual(kb.service_id, self.service)

    def test_delete_security(self):
        # User without manager group should not be allowed to unlink
        user_test = self.env['res.users'].create({
            'name': 'Regular Agent',
            'login': 'agent_test_kb',
            'groups_id': [(6, 0, [self.agent_group.id])] if self.agent_group else [],
        })
        kb = self.env['helpdesk.knowledge'].create({
            'name': 'Panduan Keamanan',
            'subcategory_id': self.subcategory.id,
        })
        with self.assertRaises(UserError):
            kb.with_user(user_test).unlink()
