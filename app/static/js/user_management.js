$(document).ready(function() {
    // --- User Management ---
    var editingUserRow = null;

    // Handle modal opening for ADDING a user
    $('#add-user-btn').on('click', function() {
        var addUrl = add_user_url;
        editingUserRow = null;

        fetch(addUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#user-edit-modal-label').text('Créer un Utilisateur');
            $('#user-edit-modal .modal-body').html(`<form id="modal-user-form" action="${addUrl}" method="post" novalidate>${html}</form>`);
            if (window.userModal) window.userModal.show();
        })
        .catch(error => { console.error('Error loading user form:', error); alert('Erreur lors du chargement du formulaire.'); });
    });

    // Handle modal opening for EDITING a user
    $('#users-table').on('click', '.edit-user-btn', function() {
        var button = $(this);
        var editUrl = button.data('edit-url');
        editingUserRow = button.closest('tr');
        
        fetch(editUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#user-edit-modal-label').text('Éditer l\'Utilisateur');
            $('#user-edit-modal .modal-body').html(`<form id="modal-user-form" action="${editUrl}" method="post" novalidate>${html}</form>`);
            if (window.userModal) window.userModal.show();
        })
        .catch(error => { console.error('Error loading user form:', error); alert('Erreur lors du chargement du formulaire.'); });
    });

    // Handle SAVE button click in the user modal
    $('#save-user-changes-btn').on('click', () => $('#modal-user-form').submit());

    // Handle the user form SUBMISSION via AJAX
    $('#user-edit-modal').on('submit', '#modal-user-form', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var formData = new FormData(this);
        var csrfToken = $('meta[name=csrf-token]').attr('content');

        fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken } })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                var user = data.user;
                var table = $('#users-table').DataTable();
                var teamsHtml = user.teams && user.teams.length > 0 ? user.teams.map(name => `<span class="badge bg-secondary">${name}</span>`).join(' ') : 'Aucune';
                var rolesHtml = (user.is_admin ? '<span class="badge bg-primary">Admin</span> ' : '') +
                                (user.teams_as_lead && user.teams_as_lead.length > 0 ? user.teams_as_lead.map(name => `<span class="badge bg-info">Lead: ${name}</span>`).join(' ') : '');
                
                var summary = user.continuous_training_summary;
                var color = 'success';
                if (!summary.is_compliant) {
                    color = 'danger';
                } else if (!summary.is_live_ratio_compliant || summary.is_at_risk_next_year) {
                    color = 'warning';
                }
                var statusFcHtml = `<span class="badge bg-${color}" data-bs-toggle="tooltip" data-bs-placement="top" title="Total Hours: ${summary.total_hours_6_years.toFixed(2)} / ${summary.required_hours.toFixed(2)}. Live Ratio: ${(summary.live_ratio * 100).toFixed(0)}%"><i class="fas fa-info-circle"></i></span>`;

                var statusFcHtml = `<span style="display:none;">${summary.total_hours_6_years}</span>` +
                                 `<span class="badge bg-${color}" data-bs-toggle="tooltip" data-bs-placement="top" title="Total Hours: ${summary.total_hours_6_years.toFixed(2)} / ${summary.required_hours.toFixed(2)}. Live Ratio: ${(summary.live_ratio * 100).toFixed(0)}%"><i class="fas fa-info-circle"></i></span>`;

                var actionsHtml = `<button class="btn btn-sm btn-warning edit-user-btn" data-edit-url="/admin/users/edit/${user.id}" title="Éditer"><i class="fa fa-edit"></i></button> ` +
                                  `<button class="btn btn-sm btn-danger delete-user-btn" data-user-id="${user.id}" data-delete-url="/admin/users/delete/${user.id}" title="Supprimer"><i class="fa fa-trash"></i></button> ` +
                                  `<a href="/profile/${user.id}/booklet.pdf" target="_blank" class="btn btn-sm btn-secondary" title="Générer PDF"><i class="fa fa-file-pdf"></i></a>`;
                
                var rowData = [user.full_name, user.email, teamsHtml, rolesHtml, statusFcHtml, actionsHtml];

                if (editingUserRow) {
                    table.row(editingUserRow).data(rowData).draw();
                } else {
                    var newNode = table.row.add(rowData).draw().node();
                    $(newNode).attr('id', 'user-row-' + user.id);
                }
                
                if (window.userModal) window.userModal.hide();

            } else {
                if (data.form_html) { form.html(data.form_html); } 
                else { alert(data.message || 'Erreur lors de la sauvegarde.'); }
            }
        })
        .catch(error => { console.error('Error:', error); alert('Une erreur réseau est survenue.'); });
    });

    // Handle AJAX deletion for users
    $('#users-table').on('click', '.delete-user-btn', function() {
        var button = $(this);
        var userId = button.data('user-id');
        var deleteUrl = button.data('delete-url');
        var csrfToken = $('meta[name=csrf-token]').attr('content');

        if (confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
            fetch(deleteUrl, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken } })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    $('#users-table').DataTable().row('#user-row-' + userId).remove().draw();
                } else { alert('Erreur: ' + (data.message || 'Inconnue.')); }
            })
            .catch(error => { console.error('Error:', error); alert('Une erreur réseau est survenue.'); });
        }
    });

    // --- Import Modals ---
    $('#import-users-modal').on('show.bs.modal', function () {
        fetch(import_export_users_url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => { $(this).find('.modal-body').html(html); })
        .catch(error => { console.error('Error loading import form:', error); });
    });
});
