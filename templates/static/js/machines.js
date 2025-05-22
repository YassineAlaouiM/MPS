document.addEventListener('DOMContentLoaded', function() {
            // Handle all data-action buttons
            document.addEventListener('click', function(e) {
                const button = e.target.closest('[data-action]');
                if (!button) return;

                const action = button.getAttribute('data-action');
                const id = button.getAttribute('data-id');

                switch (action) {
                    case 'edit-machine':
                        editMachine(id);
                        break;
                    case 'delete-machine':
                        deleteMachine(id);
                        break;
                    case 'mark-fixed':
                        markMachineFixed(id);
                        break;
                    case 'save-machine-edit':
                        updateMachine(id);
                        break;
                    case 'save-non-functioning':
                        saveNonFunctioningMachine();
                        break;
                }
            });

            // Add search functionality
            const machineSearchInput = document.getElementById('machineSearch');
            if (machineSearchInput) {
                machineSearchInput.addEventListener('input', filterMachines);
            }

            const nonFunctioningSearchInput = document.getElementById('nonFunctioningMachineSearch');
            if (nonFunctioningSearchInput) {
                nonFunctioningSearchInput.addEventListener('input', filterNonFunctioningMachines);
            }

            // Add form submission handlers
            ['addMachineForm', 'addNonFunctioningMachineForm'].forEach(formId => {
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
                addMachine: new bootstrap.Modal(document.getElementById('addMachineModal')),
                addNonFunctioning: new bootstrap.Modal(document.getElementById('addNonFunctioningMachineModal'))
            };

            // Add modal cleanup on hide
            Object.entries(modals).forEach(([key, modal]) => {
                if (modal && modal._element) {
                    modal._element.addEventListener('hidden.bs.modal', function() {
                        const form = this.querySelector('form');
                        if (form) {
                            form.reset();
                            // Reset machine status to operational
                            const statusSelect = form.querySelector('#machineStatus');
                            if (statusSelect) {
                                statusSelect.value = 'operational';
                            }
                            // Reset machine type to regular machine
                            const typeSelect = form.querySelector('#machineType');
                            if (typeSelect) {
                                typeSelect.value = 'false';
                            }
                        }
                        // Reset modal title and button if it's the machine modal
                        if (this.id === 'addMachineModal') {
                            this.querySelector('.modal-title').textContent = 'Ajouter une machine';
                            const saveButton = this.querySelector('.btn-primary');
                            saveButton.textContent = 'Enregistrer';
                            saveButton.setAttribute('data-action', 'save-machine');
                        }
                    });
                }
            });
        });