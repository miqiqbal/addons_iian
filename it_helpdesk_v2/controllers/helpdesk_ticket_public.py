from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request


class HelpdeskTicketPublicController(http.Controller):

    @http.route(['/helpdesk/submit'], type='http', auth='user', website=True, sitemap=False)
    def helpdesk_submit_form(self, **kwargs):
        values = self._get_form_values()
        return request.render('it_helpdesk_v2.website_helpdesk_submit_page', values)

    @http.route(
        ['/helpdesk/submit/send'], type='http', auth='user', website=True,
        methods=['POST'], csrf=True)
    def helpdesk_submit_send(self, **post):
        errors = self._validate_post(post)

        if errors:
            values = self._get_form_values()
            values.update({'error': errors, 'form_data': post})
            return request.render('it_helpdesk_v2.website_helpdesk_submit_page', values)

        current_user = request.env.user
        vals = {
            'requester_id': current_user.id,
            'email': current_user.email,
            'phone': (post.get('phone') or '').strip() or current_user.phone,
            'title': (post.get('title') or '').strip(),
            'description': post.get('description') or '',
            'service_id': int(post['service_id']),
            'category_id': int(post['category_id']),
            'subcategory_id': int(post['subcategory_id']) if post.get('subcategory_id') else False,
            'location_id': int(post['location_id']),
            'q1_answer_id': int(post['q1_answer_id']),
            'q2_answer_id': int(post['q2_answer_id']),
            'q3_answer_id': int(post['q3_answer_id']),
            'q4_answer_id': int(post['q4_answer_id']),
            'q5_answer_id': int(post['q5_answer_id']),
        }

        Ticket = request.env['helpdesk.ticket'].sudo()
        ticket = Ticket.create(vals)
        try:
            ticket.action_publish()
        except UserError as e:
            values = self._get_form_values()
            values.update({
                'error': {'_general': str(e)},
                'form_data': post,
            })
            return request.render('it_helpdesk_v2.website_helpdesk_submit_page', values)

        return request.render('it_helpdesk_v2.website_helpdesk_submit_success_page', {
            'ticket': ticket,
        })

    def _get_form_values(self):
        env = request.env
        return {
            'current_user': env.user,
            'services': env['helpdesk.service'].sudo().search([]),
            'categories': env['helpdesk.category'].sudo().search([]),
            'subcategories': env['helpdesk.subcategory'].sudo().search([]),
            'locations': env['helpdesk.location'].sudo().search([]),
            'priority_questions': env['helpdesk.priority.question'].sudo().search([], order='sequence'),
        }

    def _validate_post(self, post):
        errors = {}
        if not (post.get('phone') or '').strip():
            errors['phone'] = _('Nomor Whatsapp/Telepon wajib diisi.')
        if not (post.get('title') or '').strip():
            errors['title'] = _('Judul Kendala wajib diisi.')

        errors.update(self._validate_selection(
            post, 'service_id', 'helpdesk.service', _('Service wajib dipilih.')))
        errors.update(self._validate_selection(
            post, 'category_id', 'helpdesk.category', _('Category wajib dipilih.')))
        errors.update(self._validate_selection(
            post, 'location_id', 'helpdesk.location', _('Department / Lokasi wajib dipilih.')))
        if post.get('subcategory_id'):
            errors.update(self._validate_selection(
                post, 'subcategory_id', 'helpdesk.subcategory', _('Sub Category tidak valid.')))
        for i in range(1, 6):
            key = 'q%d_answer_id' % i
            errors.update(self._validate_selection(
                post, key, 'helpdesk.priority.answer', _('Pertanyaan %d wajib dijawab.') % i))
        return errors

    def _validate_selection(self, post, field_name, model_name, required_message):
        raw = (post.get(field_name) or '').strip()
        if not raw:
            return {field_name: required_message}
        try:
            record_id = int(raw)
        except (TypeError, ValueError):
            return {field_name: _('Pilihan tidak valid.')}
        if not request.env[model_name].sudo().browse(record_id).exists():
            return {field_name: _('Pilihan tidak valid.')}
        return {}
