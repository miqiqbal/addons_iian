odoo.define('it_helpdesk_v2.helpdesk_form_control', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var session = require('web.session');

    FormController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            this._applyEditButtonRule();
        },

        updateButtons: function () {
            this._super.apply(this, arguments);
            this._applyEditButtonRule();
        },

        _updateControlPanel: function () {
            this._super.apply(this, arguments);
            this._applyEditButtonRule();
        },

        _applyEditButtonRule: function () {
            var self = this;
            if (!this.model || !this.handle) {
                return;
            }
            var record = this.model.get(this.handle);
            if (!record || !record.model) {
                return;
            }
            var targetModels = ['helpdesk.ticket', 'helpdesk.change.request'];
            if (targetModels.indexOf(record.model) === -1) {
                return;
            }

            var data = record.data || {};
            var state = data.state;

            // Check user group: agent, it manager, or admin
            session.user_has_group('it_helpdesk_v2.group_helpdesk_agent').then(function (isAgent) {
                session.user_has_group('it_helpdesk_v2.group_helpdesk_it_manager').then(function (isITMgr) {
                    session.user_has_group('it_helpdesk_v2.group_helpdesk_manager').then(function (isAdmin) {
                        var hasSpecialAccess = isAgent || isITMgr || isAdmin || session.is_admin;
                        
                        // Hide Edit button if user is regular Employee and state is not 'draft'
                        var shouldHideEdit = !hasSpecialAccess && Boolean(state && state !== 'draft');

                        var hideOrShow = function () {
                            var editBtns = $('.o_control_panel .o_form_button_edit, .o_cp_buttons .o_form_button_edit, .o_form_button_edit');
                            if (self.$buttons) {
                                editBtns = editBtns.add(self.$buttons.find('.o_form_button_edit'));
                            }
                            if (shouldHideEdit) {
                                editBtns.addClass('d-none').attr('style', 'display: none !important; visibility: hidden !important;');
                            } else {
                                editBtns.removeClass('d-none').attr('style', '');
                            }
                        };

                        hideOrShow();
                        setTimeout(hideOrShow, 50);
                        setTimeout(hideOrShow, 200);
                        setTimeout(hideOrShow, 500);
                    });
                });
            });
        }
    });
});
