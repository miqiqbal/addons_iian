odoo.define('it_helpdesk_v2.DrilldownList', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var DrilldownListRenderer = ListRenderer.extend({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click tbody tr': '_onCustomRowClick',
        }),
        _onCustomRowClick: function (ev) {
            var $tr = $(ev.currentTarget);
            var id = $tr.data('id');
            if (id) {
                this.trigger_up('open_record', { id: id, target: ev.target });
            }
        }
    });

    var DrilldownListController = ListController.extend({
        custom_events: _.extend({}, ListController.prototype.custom_events, {
            open_record: '_onOpenRecord',
        }),
        _onOpenRecord: function (ev) {
            ev.stopPropagation();
            var recordId = ev.data.id;
            var record = this.model.get(recordId);
            if (record && record.data) {
                var modelName = this.modelName;
                var resId = record.data.id;
                var domain = [];
                var context = {};

                if (modelName === 'helpdesk.service') {
                    domain = [['service_id', '=', resId]];
                    context = {'default_service_id': resId};
                } else if (modelName === 'helpdesk.category') {
                    domain = [['category_id', '=', resId]];
                    context = {'default_category_id': resId};
                } else if (modelName === 'helpdesk.location') {
                    domain = [['location_id', '=', resId]];
                    context = {'default_location_id': resId};
                } else if (modelName === 'helpdesk.sla') {
                    domain = [['priority', '=', record.data.priority]];
                    context = {'default_priority': record.data.priority};
                }

                if (domain.length > 0) {
                    this.do_action('it_helpdesk_v2.action_helpdesk_ticket', {
                        domain: domain,
                        context: context
                    });
                }
            }
        }
    });

    var DrilldownListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: DrilldownListController,
            Renderer: DrilldownListRenderer,
        }),
    });

    viewRegistry.add('helpdesk_drilldown_list', DrilldownListView);

    return DrilldownListView;
});
