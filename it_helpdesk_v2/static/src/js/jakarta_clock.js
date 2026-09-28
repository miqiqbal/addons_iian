odoo.define('it_helpdesk_v2.JakartaClock', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var SystrayMenu = require('web.SystrayMenu');

    var JakartaClock = Widget.extend({
        tagName: 'li',
        className: 'o_jakarta_clock_item d-none d-md-flex align-items-center mr-3 px-2 py-1 rounded',
        start: function () {
            var self = this;
            this.$el.css({
                'background': 'rgba(255, 255, 255, 0.12)',
                'border': '1px solid rgba(255, 255, 255, 0.2)',
                'font-size': '12px',
                'color': '#ffffff'
            });
            this._updateClock();
            this._interval = setInterval(function () {
                self._updateClock();
            }, 1000);
            return this._super.apply(this, arguments);
        },
        _updateClock: function () {
            var now = new Date();
            var options = {
                timeZone: 'Asia/Jakarta',
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            };
            var formattedDate = '';
            try {
                var formatter = new Intl.DateTimeFormat('id-ID', options);
                formattedDate = formatter.format(now) + ' WIB';
            } catch (e) {
                formattedDate = now.toLocaleTimeString() + ' WIB';
            }
            this.$el.html('<i class="fa fa-clock-o mr-2" style="color: #28a745; font-size: 14px;"/> <span style="font-weight: 600; letter-spacing: 0.3px;">' + formattedDate + '</span>');
        },
        destroy: function () {
            if (this._interval) {
                clearInterval(this._interval);
            }
            this._super.apply(this, arguments);
        }
    });

    SystrayMenu.Items.push(JakartaClock);

    return JakartaClock;
});
