$(document).ready(function() {
    // --- Skill Management ---
    var editingSkillRow = null;

    // Handle modal opening for ADDING a skill
    $('#add-skill-btn').on('click', function() {
        var addUrl = add_skill_url;
        editingSkillRow = null;

        fetch(addUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#skill-edit-modal-label').text('Créer une Compétence');
            $('#skill-edit-modal .modal-body').html(`<form id="modal-skill-form" action="${addUrl}" method="post" novalidate>${html}</form>`);
            if (window.skillModal) window.skillModal.show();
        })
        .catch(error => { console.error('Error loading skill form:', error); alert('Erreur lors du chargement du formulaire.'); });
    });
    
    // Handle modal opening for EDITING a skill
    $('#skills-table').on('click', '.edit-skill-btn', function() {
        var button = $(this);
        var editUrl = button.data('edit-url');
        editingSkillRow = button.closest('tr');

        fetch(editUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            $('#skill-edit-modal-label').text('Éditer la Compétence');
            $('#skill-edit-modal .modal-body').html(`<form id="modal-skill-form" action="${editUrl}" method="post" novalidate>${html}</form>`);
            if (window.skillModal) window.skillModal.show();
        })
        .catch(error => { console.error('Error loading skill form:', error); alert('Erreur lors du chargement du formulaire.'); });
    });

    // Handle SAVE button click in the skill modal
    $('#save-skill-changes-btn').on('click', () => $('#modal-skill-form').submit());

    // Handle the skill form SUBMISSION via AJAX
    $('#skill-edit-modal').on('submit', '#modal-skill-form', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var formData = new FormData(this);
        var csrfToken = $('meta[name=csrf-token]').attr('content');

        fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken } })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                var skill = data.skill;
                var table = $('#skills-table').DataTable();
                var speciesHtml = skill.species && skill.species.length > 0 ? skill.species.map(name => `<span class="badge bg-secondary">${name}</span>`).join(' ') : 'Aucune';
                var tutorsHtml = skill.tutors && skill.tutors.length > 0 ? skill.tutors.map(name => `<span class="badge bg-dark">${name}</span>`).join(' ') : '<span class="badge bg-warning">Aucun</span>';
                var actionsHtml = `<button class="btn btn-sm btn-warning edit-skill-btn" data-edit-url="/admin/skills/edit/${skill.id}" title="Éditer"><i class="fa fa-edit"></i></button> ` +
                                  `<button class="btn btn-sm btn-danger delete-skill-btn" data-skill-id="${skill.id}" data-delete-url="/admin/skills/delete/${skill.id}" title="Supprimer"><i class="fa fa-trash"></i></button>`;
                
                var truncatedDescription = (skill.description || '').substring(0, 120) + ((skill.description || '').length > 120 ? '...' : '');
                var rowData = [skill.name, truncatedDescription, speciesHtml, tutorsHtml, actionsHtml];

                if (editingSkillRow) {
                    table.row(editingSkillRow).data(rowData).draw();
                } else {
                    var newNode = table.row.add(rowData).draw().node();
                    $(newNode).attr('id', 'skill-row-' + skill.id);
                }

                if (window.skillModal) window.skillModal.hide();
            } else {
                if (data.form_html) { form.html(data.form_html); } 
                else { alert(data.message || 'Erreur lors de la sauvegarde.'); }
            }
        })
        .catch(error => { console.error('Error:', error); alert('Une erreur réseau est survenue.'); });
    });

    // Handle AJAX deletion for skills
    $('#skills-table').on('click', '.delete-skill-btn', function() {
        var button = $(this);
        var skillId = button.data('skill-id');
        var deleteUrl = button.data('delete-url');
        var csrfToken = $('meta[name=csrf-token]').attr('content');

        if (confirm('Êtes-vous sûr de vouloir supprimer cette compétence ?')) {
            fetch(deleteUrl, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken } })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    $('#skills-table').DataTable().row('#skill-row-' + skillId).remove().draw();
                } else { alert('Erreur: ' + (data.message || 'Inconnue.')); }
            })
            .catch(error => { console.error('Error:', error); alert('Une erreur réseau est survenue.'); });
        }
    });

    // --- Import Modals ---
    $('#import-skills-modal').on('show.bs.modal', function () {
        fetch(import_export_skills_url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => { $(this).find('.modal-body').html(html); })
        .catch(error => { console.error('Error loading skill import form:', error); });
    });
});
