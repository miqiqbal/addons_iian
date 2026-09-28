from odoo import SUPERUSER_ID, api

DASHBOARD_ARCH = """<form string="Helpdesk Dashboard">
    <board style="2-2">
        <column>
            <action name="%(kpi)d" string="Helpdesk KPI"/>
            <action name="%(priority)d" string="Tiket by Priority (Pie Chart)"/>
            <action name="%(type)d" string="Tiket by Type (Pie Chart)"/>
        </column>
        <column>
            <action name="%(department)d" string="Tiket by Departemen (Bar Chart)"/>
            <action name="%(service)d" string="Tiket by Service (Bar Chart)"/>
            <action name="%(category)d" string="Tiket by Category (Bar Chart)"/>
        </column>
    </board>
</form>"""


def post_init_hook(cr, registry):
    """Mengisi arch board.board Helpdesk Dashboard dan mengupdate menu Knowledge Base."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    dash_menu = env.ref('it_helpdesk_v2.menu_it_helpdesk_dashboard', raise_if_not_found=False)
    dash_action = env.ref('it_helpdesk_v2.action_helpdesk_analytics_dashboard', raise_if_not_found=False)
    if dash_menu and dash_action:
        dash_menu.sudo().write({'action': 'ir.actions.client,%d' % dash_action.id})

    menu = env.ref('it_helpdesk_v2.menu_it_helpdesk_knowledge_base', raise_if_not_found=False)
    action = env.ref('it_helpdesk_v2.action_helpdesk_knowledge', raise_if_not_found=False)
    if menu and action:
        menu.sudo().write({'action': 'ir.actions.act_window,%d' % action.id})

    view = env.ref('it_helpdesk_v2.view_helpdesk_dashboard_board', raise_if_not_found=False)
    if not view:
        return
    actions = {
        'kpi': env.ref('it_helpdesk_v2.action_helpdesk_dashboard_kpi').id,
        'priority': env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_priority').id,
        'department': env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_department').id,
        'service': env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_service').id,
        'category': env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_category').id,
        'type': env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_status').id if env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_status', raise_if_not_found=False) else env.ref('it_helpdesk_v2.action_helpdesk_ticket_graph_type').id,
    }
    # Force all helpdesk.ticket record rules to [(1, '=', 1)] for full engineer access
    rules = env['ir.rule'].search([('model_id.model', '=', 'helpdesk.ticket')])
    for rule in rules:
        rule.sudo().write({'domain_force': '[(1, "=", 1)]'})
    env['ir.rule'].clear_caches()

    view.write({'arch': DASHBOARD_ARCH % actions})
