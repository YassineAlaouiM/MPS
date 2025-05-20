document.addEventListener('DOMContentLoaded', function() {
            // Handle all data-action buttons
            document.addEventListener('click', function(e) {
                const button = e.target.closest('[data-action]');
                if (!button) return;

                const action = button.getAttribute('data-action');
                const id = button.getAttribute('data-id');

                switch (action) {
                    case 'edit-operator':
                        editOperator(id);
                        break;
                    case 'delete-operator':
                        deleteOperator(id);
                        break;
                    case 'edit-absence':
                        editAbsence(id);
                        break;
                    case 'delete-absence':
                        deleteAbsence(id);
                        break;
                    case 'save-operator':
                        saveOperator();
                        break;
                    case 'save-operator-edit':
                        saveOperatorEdit();
                        break;
                    case 'save-absence':
                        saveAbsence();
                        break;
                    case 'save-absence-edit':
                        saveAbsenceEdit();
                        break;
                }
            });

            // Add search functionality
            const operatorSearchInput = document.getElementById('operatorSearch');
            if (operatorSearchInput) {
                operatorSearchInput.addEventListener('input', filterOperators);
            }

            const absenceSearchInput = document.getElementById('absenceSearch');
            if (absenceSearchInput) {
                absenceSearchInput.addEventListener('input', filterAbsences);
            }

            // Add form submission handlers
            ['addOperatorForm', 'editOperatorForm', 'addAbsenceForm', 'editAbsenceForm'].forEach(formId => {
                const form = document.getElementById(formId);
                if (form) {
                    form.addEventListener('submit', function(e) {
                        e.preventDefault();
                        const action = this.getAttribute('data-form-action');
                        if (action) {
                            window[action]();
                        }
                    });
                }
            });

            // Initialize modals
            const modals = {
                addOperator: new bootstrap.Modal(document.getElementById('addOperatorModal')),
                editOperator: new bootstrap.Modal(document.getElementById('editOperatorModal')),
                addAbsence: new bootstrap.Modal(document.getElementById('addAbsenceModal')),
                editAbsence: new bootstrap.Modal(document.getElementById('editAbsenceModal'))
            };

            // Add modal cleanup on hide
            Object.entries(modals).forEach(([key, modal]) => {
                if (modal && modal._element) {
                    modal._element.addEventListener('hidden.bs.modal', function() {
                        const form = this.querySelector('form');
                        if (form) {
                            form.reset();
                        }
                    });
                }
            });
        });