$(document).ready(function() {
    // --- Setup for DataTables ---
    var englishLanguage = {
        "sEmptyTable":     "No data available in table",
        "sInfo":           "Showing _START_ to _END_ of _TOTAL_ entries",
        "sInfoEmpty":      "Showing 0 to 0 of 0 entries",
        "sInfoFiltered":   "(filtered from _MAX_ total entries)",
        "sInfoPostFix":    "",
        "sInfoThousands":  ",",
        "sLengthMenu":     "Show _MENU_ entries",
        "sLoadingRecords": "Loading...",
        "sProcessing":     "Processing...",
        "sSearch":         "Search:",
        "sZeroRecords":    "No matching records found",
        "oPaginate": { "sFirst": "First", "sLast": "Last", "sNext": "Next", "sPrevious": "Previous" },
        "oAria": { "sSortAscending": ": activate to sort column ascending", "sSortDescending": ": activate to sort column descending" }
    };

    // Only initialize DataTable if the table exists (i.e., user has permission)
    if ($('#users-table').length) {
        $('#users-table').DataTable({
            language: englishLanguage,
            columns: [
                null, // Full Name
                null, // Email
                null, // Team
                { "orderable": false, "searchable": false }, // Roles
                { "orderable": true, "searchable": false }, // CT Status (sortable by data-order, not searchable)
                null, // Initial Training Level
                { "orderable": false, "searchable": false }  // Actions
            ]
        });
    }
    if ($('#skills-table').length) {
        $('#skills-table').DataTable({ language: englishLanguage });
    }
    if ($('#teams-table').length) {
        $('#teams-table').DataTable({ language: englishLanguage });
    }

    // --- MODAL INITIALIZATION ---
    window.userModal = null;
    if (document.getElementById('user-edit-modal')) {
        window.userModal = new bootstrap.Modal(document.getElementById('user-edit-modal'));
    }
    window.skillModal = null;
    if (document.getElementById('skill-edit-modal')) {
        window.skillModal = new bootstrap.Modal(document.getElementById('skill-edit-modal'));
    }
    window.teamAddModal = null;
    if (document.getElementById('team-add-modal')) {
        window.teamAddModal = new bootstrap.Modal(document.getElementById('team-add-modal'));
    }
    window.teamEditModal = null;
    if (document.getElementById('team-edit-modal')) {
        window.teamEditModal = new bootstrap.Modal(document.getElementById('team-edit-modal'));
    }
    window.addUsersToTeamModal = null;
    if (document.getElementById('add-users-to-team-modal')) {
        window.addUsersToTeamModal = new bootstrap.Modal(document.getElementById('add-users-to-team-modal'));
    }

    // Initialize actionModal
    window.actionModal = null;
    if (document.getElementById('action-modal')) {
        window.actionModal = new bootstrap.Modal(document.getElementById('action-modal'));

        // Destroy Select2 instances when the modal is hidden to prevent conflicts
        $('#action-modal').on('hide.bs.modal', function (e) {
            if (document.activeElement === this.querySelector('.btn-close')) {
                document.activeElement.blur();
            }

            $('.select2-hidden-accessible').each(function() {
                if ($(this).data('select2')) {
                    $(this).select2('destroy');
                }
            });

            if (window.activeElement) { // Use window.activeElement as it's global
                window.activeElement.focus();
                window.activeElement = null;
            } else {
                document.body.focus();
            }
        });
    }

    // --- Training History Chart ---
    var ctx = document.getElementById('trainingHistoryChart');
    if (ctx) {
        // Destroy existing chart instance if it exists
        if (Chart.getChart(ctx)) {
            Chart.getChart(ctx).destroy();
        }

        // trainingChartData is passed from the Flask template
        var trainingChart = new Chart(ctx, {
            type: 'bar',
            data: trainingChartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Heures de formation par an'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    },
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Heures'
                        }
                    }
                },
                onClick: function(event, elements) {
                    if (elements.length > 0) {
                        var clickedElement = elements[0];
                        var year = trainingChart.data.labels[clickedElement.index];
                        filterTrainingTableByYear(year);
                    } else {
                        resetTrainingTableFilter();
                    }
                }
            }
        });

        var currentFilteredYear = null;

        function filterTrainingTableByYear(year) {
            var table = $('#training-details-table').DataTable();
            if (currentFilteredYear === year) {
                // If the same year is clicked again, reset filter
                table.column(0).search('').draw();
                currentFilteredYear = null;
            } else {
                table.column(0).search(year).draw();
                currentFilteredYear = year;
            }
        }

        function resetTrainingTableFilter() {
            var table = $('#training-details-table').DataTable();
            table.column(0).search('').draw();
            currentFilteredYear = null;
        }
    }

    // Initialize training-details-table DataTable
    if ($('#training-details-table').length) {
        // Destroy existing DataTable instance if it exists
        if ($.fn.DataTable.isDataTable('#training-details-table')) {
            $('#training-details-table').DataTable().destroy();
        }
        $('#training-details-table').DataTable({
            language: frenchLanguage,
            order: [[0, 'desc']] // Order by year descending by default
        });
    }



});
