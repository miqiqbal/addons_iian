from odoo import fields, models, tools

from .helpdesk_ticket import CUSTOMER_RATING_SELECTION, STATE_SELECTION, TICKET_PRIORITY_SELECTION


class HelpdeskTicketReport(models.Model):
    _name = 'helpdesk.ticket.report'
    _description = 'Helpdesk Ticket Report'
    _auto = False
    _order = 'create_date desc'

    service_id = fields.Many2one('helpdesk.service', string='Service', readonly=True)
    category_id = fields.Many2one('helpdesk.category', string='Category', readonly=True)
    priority = fields.Selection(TICKET_PRIORITY_SELECTION, readonly=True)
    state = fields.Selection(STATE_SELECTION, readonly=True)
    engineer_id = fields.Many2one('res.users', string='Engineer', readonly=True)
    sla_response_breached = fields.Boolean(readonly=True)
    sla_resolution_breached = fields.Boolean(readonly=True)
    create_date = fields.Datetime(readonly=True)
    resolved_date = fields.Datetime(readonly=True)
    closed_date = fields.Datetime(readonly=True)
    resolution_duration_hours = fields.Float(
        string='Durasi Resolusi (Jam)', readonly=True, group_operator='avg')
    customer_rating = fields.Selection(CUSTOMER_RATING_SELECTION, readonly=True)
    ticket_count = fields.Integer(string='# Tickets', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    t.id AS id,
                    t.service_id AS service_id,
                    t.category_id AS category_id,
                    t.priority AS priority,
                    t.state AS state,
                    t.engineer_id AS engineer_id,
                    t.sla_response_breached AS sla_response_breached,
                    t.sla_resolution_breached AS sla_resolution_breached,
                    t.create_date AS create_date,
                    t.resolved_date AS resolved_date,
                    t.closed_date AS closed_date,
                    t.customer_rating AS customer_rating,
                    1 AS ticket_count,
                    CASE WHEN t.resolved_date IS NOT NULL
                         THEN EXTRACT(EPOCH FROM (t.resolved_date - t.create_date)) / 3600.0
                         ELSE NULL
                    END AS resolution_duration_hours
                FROM helpdesk_ticket t
            )
        """ % self._table)
