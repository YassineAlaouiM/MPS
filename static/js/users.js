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

            // Utility to handle enabling/disabling permission dropdowns
            function setupPagePermissionHandlers(prefix = '') {
                const pages = ['machines', 'operators', 'production', 'schedule', 'rest_days', 'history'];
                pages.forEach(page => {
                    const checkbox = document.getElementById(`${prefix}page_${page}`);
                    const select = document.getElementById(`${prefix}perm_${page}`);
                    if (!checkbox || !select) return;
                    checkbox.addEventListener('change', function() {
                        select.disabled = !checkbox.checked;
                    });
                });
            }

            // Call for both add and edit modals
            setupPagePermissionHandlers('');
            setupPagePermissionHandlers('edit_');

            // Collect accessible_pages array for backend
            function collectAccessiblePages(prefix = '') {
                const pages = ['machines', 'operators', 'production', 'schedule', 'rest_days', 'history'];
                const result = [];
                pages.forEach(page => {
                    const checkbox = document.getElementById(`${prefix}page_${page}`);
                    const select = document.getElementById(`${prefix}perm_${page}`);
                    if (checkbox && checkbox.checked) {
                        result.push({
                            page_name: page,
                            can_edit: select.value === 'edit'
                        });
                    }
                });
                return result;
            }

            // Save user (add)
            window.saveUser = function() {
                const username = document.getElementById('username').value;
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const role = document.getElementById('role').value;
                const accessible_pages = collectAccessiblePages();
                fetch('/api/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, email, password, role, accessible_pages })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) location.reload();
                    else alert(data.message || 'Erreur lors de la création de l\'utilisateur');
                });
            }

            // Save user (edit)
            window.saveUserEdit = function() {
                const id = document.getElementById('editUserId').value;
                const username = document.getElementById('editUsername').value;
                const email = document.getElementById('editEmail').value;
                const password = document.getElementById('editPassword').value;
                const role = document.getElementById('editRole').value;
                const accessible_pages = collectAccessiblePages('edit_');
                const payload = { username, email, role, accessible_pages };
                if (password) payload.password = password;
                fetch(`/api/users/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) location.reload();
                    else alert(data.message || 'Erreur lors de la modification de l\'utilisateur');
                });
            }

            // Pre-fill edit modal with user data
            window.editUser = function(id) {
                fetch(`/api/users/${id}`)
                    .then(res => res.json())
                    .then(data => {
                        if (!data.success) return alert('Utilisateur non trouvé');
                        const user = data.user;
                        document.getElementById('editUserId').value = user.id;
                        document.getElementById('editUsername').value = user.username;
                        document.getElementById('editEmail').value = user.email;
                        document.getElementById('editRole').value = user.role;
                        // Reset checkboxes and dropdowns
                        ['machines', 'operators', 'production', 'schedule', 'rest_days', 'history'].forEach(page => {
                            const cb = document.getElementById(`edit_page_${page}`);
                            const sel = document.getElementById(`edit_perm_${page}`);
                            cb.checked = false;
                            sel.disabled = true;
                            sel.value = 'edit';
                        });
                        // Set accessible pages
                        if (user.accessible_pages) {
                            Object.entries(user.accessible_pages).forEach(([page, can_edit]) => {
                                const cb = document.getElementById(`edit_page_${page}`);
                                const sel = document.getElementById(`edit_perm_${page}`);
                                if (cb && sel) {
                                    cb.checked = true;
                                    sel.disabled = false;
                                    sel.value = can_edit ? 'edit' : 'read';
                                }
                            });
                        }
                        // Show modal
                        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
                        modal.show();
                    });
            }
        });