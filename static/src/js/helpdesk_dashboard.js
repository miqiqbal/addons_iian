odoo.define('it_helpdesk_v2.AnalyticsDashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var AnalyticsDashboard = AbstractAction.extend({
        template: 'it_helpdesk_v2.AnalyticsDashboard',
        jsLibs: ['/web/static/lib/Chart/Chart.js'],
        events: {
            'click #btn_apply_filter': '_onFilterClick',
            'click #btn_reset_filter': '_onResetFilterClick',
            'click #btn_refresh, #dashboard_refresh_btn_footer': '_onRefreshClick',
            'click .o_kpi_clickable_card': '_onKPICardClick',
            'click .o_ticket_row_click': '_onTicketRowClick',
            'click .o_heatmap_cell': '_onHeatmapCellClick',
            'click .o_trend_period_btn': '_onTrendPeriodChange',
            'click #btn_export_excel': '_onExportExcel',
            'click #btn_export_pdf': '_onExportPDF',
            'click #btn_print': '_onPrint',
        },

        init: function (parent, context) {
            this._super.apply(this, arguments);
            this.data = {};
            this.chartInstances = [];
            this.activeTrendPeriod = 'week';
            this.currentFilters = {};
            this._pendingRenderTimeout = null;
        },

        willStart: function () {
            var self = this;
            return this._super().then(function () {
                return self._fetchDashboardData();
            });
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._scheduleRenderCharts(function () {
                    self._renderCharts();
                });
            });
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            var self = this;
            self._scheduleRenderCharts(function () {
                self._renderCharts();
            });
        },

        on_detach_callback: function () {
            this._super.apply(this, arguments);
            this._clearPendingRenderTimeout();
        },

        destroy: function () {
            this._clearPendingRenderTimeout();
            this._destroyCharts();
            this._super.apply(this, arguments);
        },

        _clearPendingRenderTimeout: function () {
            if (this._pendingRenderTimeout) {
                clearTimeout(this._pendingRenderTimeout);
                this._pendingRenderTimeout = null;
            }
        },

        // Menunda render Chart.js dan membatalkan timer sebelumnya yang belum
        // sempat jalan (mis. widget di-detach saat navigasi ke record lain),
        // supaya callback tidak memanipulasi DOM setelah action berpindah
        // (penyebab "insertBefore: not a child of this node" pada patch OWL).
        _scheduleRenderCharts: function (fn) {
            var self = this;
            this._clearPendingRenderTimeout();
            this._pendingRenderTimeout = setTimeout(function () {
                self._pendingRenderTimeout = null;
                fn();
            }, 150);
        },

        _fetchDashboardData: function (filters) {
            filters = filters || this.currentFilters || {};
            var self = this;
            return this._rpc({
                model: 'helpdesk.dashboard.kpi',
                method: 'get_dashboard_analytics_data',
                args: [
                    filters.date_period || 'all',
                    filters.location_id || 'all',
                    filters.service_id || 'all',
                    filters.category_id || 'all',
                    filters.priority || 'all',
                    filters.engineer_id || 'all'
                ],
            }).then(function (result) {
                self.data = result;
            });
        },

        _restoreFilterValues: function (filters) {
            if (!filters) return;
            if (filters.date_period) this.$('#filter_date_period').val(filters.date_period);
            if (filters.location_id) this.$('#filter_department').val(filters.location_id);
            if (filters.service_id) this.$('#filter_service').val(filters.service_id);
            if (filters.category_id) this.$('#filter_category').val(filters.category_id);
            if (filters.priority) this.$('#filter_priority').val(filters.priority);
            if (filters.engineer_id) this.$('#filter_engineer').val(filters.engineer_id);
        },

        _onFilterClick: function () {
            var self = this;
            var filters = {
                date_period: this.$('#filter_date_period').val() || 'all',
                location_id: this.$('#filter_department').val() || 'all',
                service_id: this.$('#filter_service').val() || 'all',
                category_id: this.$('#filter_category').val() || 'all',
                priority: this.$('#filter_priority').val() || 'all',
                engineer_id: this.$('#filter_engineer').val() || 'all'
            };
            this.currentFilters = filters;
            this._fetchDashboardData(filters).then(function () {
                self.renderElement();
                self._scheduleRenderCharts(function () {
                    self._renderCharts();
                    self._restoreFilterValues(filters);
                    self._updateCardClickState();
                });
            });
        },

        _onResetFilterClick: function () {
            var self = this;
            var filters = {
                date_period: 'all',
                location_id: 'all',
                service_id: 'all',
                category_id: 'all',
                priority: 'all',
                engineer_id: 'all'
            };
            this.currentFilters = filters;
            this._fetchDashboardData(filters).then(function () {
                self.renderElement();
                self._scheduleRenderCharts(function () {
                    self._renderCharts();
                    self._restoreFilterValues(filters);
                    self._updateCardClickState();
                });
            });
        },

        _onRefreshClick: function () {
            var self = this;
            this._fetchDashboardData(this.currentFilters).then(function () {
                self.renderElement();
                self._scheduleRenderCharts(function () {
                    self._renderCharts();
                    self._restoreFilterValues(self.currentFilters);
                    self._updateCardClickState();
                });
            });
        },

        _onTrendPeriodChange: function (ev) {
            var $btn = $(ev.currentTarget);
            var period = $btn.data('period');
            if (period) {
                this.activeTrendPeriod = period;
                this.$('.o_trend_period_btn').css({'background-color': '#6c757d', 'border-color': '#6c757d'}).removeClass('active');
                $btn.css({'background-color': '#714B67', 'border-color': '#714B67'}).addClass('active');
                this._renderCharts();
            }
        },

        _isDashboardFiltered: function () {
            var filters = this.currentFilters || {};
            return (
                (filters.location_id && filters.location_id !== 'all') ||
                (filters.service_id && filters.service_id !== 'all') ||
                (filters.category_id && filters.category_id !== 'all') ||
                (filters.priority && filters.priority !== 'all') ||
                (filters.engineer_id && filters.engineer_id !== 'all')
            );
        },

        _updateCardClickState: function () {
            if (this._isDashboardFiltered()) {
                this.$('.o_kpi_card').css({
                    'cursor': 'default',
                    'opacity': '0.95'
                }).attr('title', 'Filter sedang aktif (klik kartu dinonaktifkan)');
            } else {
                this.$('.o_kpi_card').css({
                    'cursor': 'pointer',
                    'opacity': '1.0'
                }).attr('title', 'Klik untuk melihat detail');
            }
        },

        _onKPICardClick: function (ev) {
            if (this._isDashboardFiltered()) {
                // Saat dashboard difilter, klik kartu KPI dinonaktifkan
                return;
            }

            var self = this;
            var actionType = $(ev.currentTarget).data('action-type');

            setTimeout(function () {
                if (actionType === 'services') {
                    self.do_action('it_helpdesk_v2.action_helpdesk_service_dashboard');
                } else if (actionType === 'categories') {
                    self.do_action('it_helpdesk_v2.action_helpdesk_category_dashboard');
                } else if (actionType === 'departments') {
                    self.do_action('it_helpdesk_v2.action_helpdesk_location_dashboard');
                } else if (actionType === 'priorities') {
                    self.do_action('it_helpdesk_v2.action_helpdesk_sla_dashboard');
                } else if (actionType === 'status') {
                    self.do_action('it_helpdesk_v2.action_helpdesk_ticket', {
                        context: {'search_default_group_state': 1}
                    });
                } else {
                    self.do_action('it_helpdesk_v2.action_helpdesk_ticket');
                }
            }, 0);
        },

        _onTicketRowClick: function (ev) {
            var self = this;
            var ticketId = $(ev.currentTarget).data('ticket-id');
            if (ticketId) {
                // do_action ditunda ke tick berikutnya supaya OWL (ActionContainer)
                // selesai dulu memproses patch/render yang sedang berjalan. Memanggilnya
                // synchronous di sini bentrok dengan fiber OWL yang masih aktif dan
                // menyebabkan "insertBefore: not a child of this node" saat berpindah view.
                setTimeout(function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'helpdesk.ticket',
                        res_id: ticketId,
                        views: [[false, 'form']],
                        target: 'current',
                    });
                }, 0);
            }
        },

        _onHeatmapCellClick: function () {
            var self = this;
            setTimeout(function () {
                self.do_action({
                    name: "Daftar Tiket / Case",
                    type: 'ir.actions.act_window',
                    res_model: 'helpdesk.ticket',
                    views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
                    target: 'current',
                });
            }, 0);
        },

        _onExportExcel: function () {
            window.print();
        },

        _onExportPDF: function () {
            window.print();
        },

        _onPrint: function () {
            window.print();
        },

        _destroyCharts: function () {
            if (this.chartInstances) {
                this.chartInstances.forEach(function (chart) {
                    try {
                        if (chart && typeof chart.destroy === 'function') {
                            chart.destroy();
                        }
                    } catch (e) {}
                });
            }
            this.chartInstances = [];
        },

        _renderCharts: function () {
            this._destroyCharts();

            var ChartConstructor = window.Chart || (typeof Chart !== 'undefined' ? Chart : null);
            if (!ChartConstructor) {
                return;
            }

            // 1. Ticket By Service Donut Chart
            try {
                var servCanvas = this.$('#chart_ticket_by_service')[0];
                if (servCanvas) {
                    var servLabels = (this.data.service_data || []).map(function (d) { return d.name + ' (' + d.pct + '%)'; });
                    var servValues = (this.data.service_data || []).map(function (d) { return d.count; });
                    var c1 = new ChartConstructor(servCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: servLabels,
                            datasets: [{
                                data: servValues,
                                backgroundColor: ['#714B67', '#00CFE8', '#FF9F43', '#28C76F', '#EA5455', '#7367F0', '#64748b']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'right', labels: { boxWidth: 10, fontSize: 10 } }
                        }
                    });
                    this.chartInstances.push(c1);
                }
            } catch (e) { console.error(e); }

            // 2. Ticket By Category Donut Chart
            try {
                var catCanvas = this.$('#chart_ticket_by_category')[0];
                if (catCanvas) {
                    var catLabels = (this.data.cat_data || []).map(function (d) { return d.name + ' (' + d.pct + '%)'; });
                    var catValues = (this.data.cat_data || []).map(function (d) { return d.count; });
                    var c2 = new ChartConstructor(catCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: catLabels,
                            datasets: [{
                                data: catValues,
                                backgroundColor: ['#EA5455', '#714B67', '#28C76F', '#FF9F43', '#00CFE8']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'right', labels: { boxWidth: 10, fontSize: 10 } }
                        }
                    });
                    this.chartInstances.push(c2);
                }
            } catch (e) { console.error(e); }

            // 3. Ticket By Priority Donut Chart
            try {
                var prioCanvas = this.$('#chart_ticket_by_priority')[0];
                if (prioCanvas) {
                    var prioLabels = (this.data.prio_data || []).map(function (d) { return d.name + ' (' + d.pct + '%)'; });
                    var prioValues = (this.data.prio_data || []).map(function (d) { return d.count; });
                    var c3 = new ChartConstructor(prioCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: prioLabels,
                            datasets: [{
                                data: prioValues,
                                backgroundColor: ['#EA5455', '#FF9F43', '#00CFE8', '#28C76F']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'right', labels: { boxWidth: 10, fontSize: 10 } }
                        }
                    });
                    this.chartInstances.push(c3);
                }
            } catch (e) { console.error(e); }

            // 4. Ticket By Location Horizontal Bar
            try {
                var locCanvas = this.$('#chart_ticket_by_location')[0];
                if (locCanvas) {
                    var locLabels = (this.data.loc_data || []).map(function (d) { return d.name; });
                    var locValues = (this.data.loc_data || []).map(function (d) { return d.count; });
                    var c4 = new ChartConstructor(locCanvas, {
                        type: 'horizontalBar',
                        data: {
                            labels: locLabels,
                            datasets: [{
                                label: 'Jumlah Tiket',
                                data: locValues,
                                backgroundColor: '#714B67'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { display: false },
                            scales: { xAxes: [{ ticks: { beginAtZero: true } }] }
                        }
                    });
                    this.chartInstances.push(c4);
                }
            } catch (e) { console.error(e); }

            // 5. Ticket By Status Donut Chart
            try {
                var stCanvas = this.$('#chart_ticket_by_status')[0];
                if (stCanvas) {
                    var stLabels = (this.data.status_data || []).map(function (d) { return d.label + ' (' + d.pct + '%)'; });
                    var stValues = (this.data.status_data || []).map(function (d) { return d.count; });
                    var c5 = new ChartConstructor(stCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: stLabels,
                            datasets: [{
                                data: stValues,
                                backgroundColor: ['#714B67', '#FF9F43', '#00CFE8', '#28C76F', '#64748b', '#EA5455']
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'right', labels: { boxWidth: 10, fontSize: 10 } }
                        }
                    });
                    this.chartInstances.push(c5);
                }
            } catch (e) { console.error(e); }

            // 6. Trend Line Chart (Dynamic Period Switching: Hari, Minggu, Bulan, Tahun)
            try {
                var trendCanvas = this.$('#chart_ticket_trend')[0];
                if (trendCanvas) {
                    var mode = this.activeTrendPeriod || 'week';
                    var tData = (this.data.trend_data_by_period && this.data.trend_data_by_period[mode]) || this.data.periods || [];
                    var tLabels = tData.map(function (p) { return p.label; });
                    var totalVals = tData.map(function (p) { return p.total; });
                    var resVals = tData.map(function (p) { return p.resolved; });
                    var closeVals = tData.map(function (p) { return p.closed; });

                    var c6 = new ChartConstructor(trendCanvas, {
                        type: 'line',
                        data: {
                            labels: tLabels,
                            datasets: [
                                { label: 'Total Ticket', data: totalVals, borderColor: '#714B67', backgroundColor: 'rgba(113, 75, 103, 0.08)', fill: true, tension: 0.4 },
                                { label: 'Resolved', data: resVals, borderColor: '#28C76F', backgroundColor: 'transparent', fill: false, tension: 0.4 },
                                { label: 'Closed', data: closeVals, borderColor: '#00CFE8', backgroundColor: 'transparent', fill: false, tension: 0.4 }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            legend: { position: 'top', labels: { boxWidth: 10, fontSize: 10 } },
                            scales: { yAxes: [{ ticks: { beginAtZero: true } }] }
                        }
                    });
                    this.chartInstances.push(c6);
                }
            } catch (e) { console.error(e); }
        }
    });

    core.action_registry.add('helpdesk_analytics_dashboard', AnalyticsDashboard);

    return AnalyticsDashboard;
});
