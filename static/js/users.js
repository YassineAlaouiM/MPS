document.addEventListener('DOMContentLoaded', function() {
            // Handle all data-action buttons
            document.addEventListener('click', function(e) {
                const button = e.target.closest('[data-action]');
                if (!button) return;

                const action = button.getAttribute('data-action');
                const id = button.getAttribute('data-id');

                switch (action) {
                    case 'edit-user':
                        editUser(id);
                        break;
                    case 'delete-user':
                        deleteUser(id);
                        break;
                    case 'save-user':
                        saveUser();
                        break;
                    case 'save-user-edit':
                        saveUserEdit();
                        break;
                }
            });

            // Add search functionality
            const userSearchInput = document.getElementById('userSearch');
            if (userSearchInput) {
                userSearchInput.addEventListener('input', filterUsers);
            }

            // Add form submission handlers
            ['addUserForm', 'editUserForm'].forEach(formId => {
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
                addUser: new bootstrap.Modal(document.getElementById('addUserModal')),
                editUser: new bootstrap.Modal(document.getElementById('editUserModal'))
            };

            // Add modal cleanup on hide
            Object.entries(modals).forEach(([key, modal]) => {
                if (modal && modal._element) {
                    modal._element.addEventListener('hidden.bs.modal', function() {
                        const form = this.querySelector('form');
                        if (form) {
                            form.reset();
                            // Reset password fields
                            const passwordFields = form.querySelectorAll('input[type="password"]');
                            passwordFields.forEach(field => field.value = '');
                        }
                    });
                }
            });
        });