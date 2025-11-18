$(document).ready(function() {
    // --- Team Management ---
    // Handle modal opening for ADDING a team
    $('#add-team-btn').on('click', function() {
        var addUrl = add_team_url;
        fetch(addUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#team-add-modal-label').text('Create Team');
            $('#team-add-modal .modal-body').html(`<form id="modal-team-form" action="${addUrl}" method="post" novalidate>${html}</form>`);
            if (window.teamAddModal) window.teamAddModal.show();
        })
        .catch(error => { console.error('Error loading team form:', error); alert('Error loading form.'); });
    });

    // Handle form submission from the team add modal
    $('#team-add-modal').on('submit', '#modal-team-form', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var formData = new FormData(this);
        fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': form.find('input[name=csrf_token]').val() } })
        .then(response => response.json())
        .then(data => {
            if (data.success) { location.reload(); } 
            else {
                if (data.form_html) { form.html(data.form_html); } 
                else { alert(data.message || 'Error during creation.'); }
            }
        })
        .catch(error => { console.error('Error:', error); alert('A network error has occurred.'); });
    });
    $('#submit-team-form-btn').on('click', () => $('#modal-team-form').submit());

    // Handle modal opening for EDITING a team
    $('#teams-table').on('click', '.btn-warning[title="Edit"]', function(e) {
        e.preventDefault();
        var editUrl = $(this).attr('href');

        fetch(editUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#team-edit-modal-label').text('Edit Team');
            $('#team-edit-modal .modal-body').html(`<form id="modal-team-edit-form" action="${editUrl}" method="post" novalidate>${html}</form>`);
            if (window.teamEditModal) window.teamEditModal.show();
        })
        .catch(error => { console.error('Error loading team edit form:', error); alert('Error loading form.'); });
    });

    // Handle form submission from the team edit modal
    $('#team-edit-modal').on('submit', '#modal-team-edit-form', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var formData = new FormData(this);
        fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': form.find('input[name=csrf_token]').val() } })
        .then(response => response.json())
        .then(data => {
            if (data.success) { location.reload(); }
            else {
                if (data.form_html) { form.html(data.form_html); } 
                else { alert(data.message || 'Error during update.'); }
            }
        })
        .catch(error => { console.error('Error:', error); alert('A network error has occurred.'); });
    });
    $('#submit-team-edit-form-btn').on('click', () => $('#modal-team-edit-form').submit());

    // Handle AJAX deletion for teams
    $('#teams-table').on('submit', 'form[action*="delete_team"]', function(e) {
        e.preventDefault();
        var form = $(this);
        if (confirm('Are you sure you want to delete this team?')) {
            fetch(form.attr('action'), { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': form.find('input[name=csrf_token]').val() } })
            .then(response => response.json())
            .then(data => {
                if (data.success) { location.reload(); } 
                else { alert('Error: ' + (data.message || 'Unknown.')); }
            })
            .catch(error => { console.error('Error:', error); alert('A network error has occurred.'); });
        }
    });
    // This makes the button trigger the form submission, which is then caught by the handler above.
    $('#teams-table').on('click', '.btn-danger[title="Delete"]', function(e) {
        e.preventDefault();
        $(this).closest('form').submit();
    });

    // Handle modal opening for ADDING USERS to a team
    $('#teams-table').on('click', '.add-user-to-team-btn', function() {
        var teamId = $(this).data('team-id');
        var teamName = $(this).data('team-name');
        var addUsersUrl = `/admin/team/${teamId}/add_users`;

        fetch(addUsersUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#add-users-to-team-modal-label').text(`Add users to ${teamName}`);
            $('#add-users-to-team-modal .modal-body').html(html);
            if (window.addUsersToTeamModal) window.addUsersToTeamModal.show();
        })
        .catch(error => { console.error('Error loading add users form:', error); alert('Error loading form.'); });
    });

    // Handle form submission for adding users to a team
    $('#add-users-to-team-modal').on('submit', '#add-users-to-team-form', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var formData = new FormData(this);
        fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': form.find('input[name=csrf_token]').val() } })
        .then(response => response.json())
        .then(data => {
            if (data.success) { location.reload(); } 
            else {
                if (data.form_html) { form.html(data.form_html); } 
                else { alert(data.message || 'Error during addition.'); }
            }
        })
        .catch(error => { console.error('Error:', error); alert('A network error has occurred.'); });
    });
    $('#submit-add-users-to-team-form-btn').on('click', () => $('#add-users-to-team-form').submit());
});
