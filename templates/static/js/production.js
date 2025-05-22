document.addEventListener('DOMContentLoaded', function() {
            // Handle all data-action buttons
            document.addEventListener('click', function(e) {
                const button = e.target.closest('[data-action]');
                if (!button) return;

                const action = button.getAttribute('data-action');
                const id = button.getAttribute('data-id');

                switch (action) {
                    case 'edit-production':
                        editProduction(id);
                        break;
                    case 'delete-production':
                        deleteProduction(id);
                        break;
                    case 'edit-article':
                        editArticle(id);
                        break;
                    case 'delete-article':
                        deleteArticle(id);
                        break;
                    case 'clear-date':
                        clearDateSearch();
                        break;
                    case 'save-article':
                        saveArticle();
                        break;
                    case 'save-article-edit':
                        saveArticleEdit();
                        break;
                    case 'save-production':
                        saveProduction();
                        break;
                    case 'save-production-edit':
                        saveProductionEdit();
                        break;
                }
            });

            // Add search functionality
            const productionSearchInput = document.getElementById('productionSearch');
            if (productionSearchInput) {
                productionSearchInput.addEventListener('input', filterProduction);
            }

            const articleSearchInput = document.getElementById('articleSearch');
            if (articleSearchInput) {
                articleSearchInput.addEventListener('input', filterArticles);
            }

            // Add date search toggle functionality
            const dateSearchToggle = document.getElementById('dateSearchToggle');
            if (dateSearchToggle) {
                dateSearchToggle.addEventListener('change', toggleDateSearch);
            }

            const startDateSearch = document.getElementById('startDateSearch');
            if (startDateSearch) {
                startDateSearch.addEventListener('change', filterProduction);
            }

            const endDateSearch = document.getElementById('endDateSearch');
            if (endDateSearch) {
                endDateSearch.addEventListener('change', filterProduction);
            }

            // Add machine type change handlers
            const productionMachine = document.getElementById('productionMachine');
            if (productionMachine) {
                productionMachine.addEventListener('change', toggleArticleFields);
            }

            const editProductionMachine = document.getElementById('editProductionMachine');
            if (editProductionMachine) {
                editProductionMachine.addEventListener('change', toggleEditArticleFields);
            }

            // Add form submission handlers
            ['addProductionForm', 'editProductionForm', 'addArticleForm', 'editArticleForm'].forEach(formId => {
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

            // Initialize article fields visibility
            toggleArticleFields();
            toggleEditArticleFields();

            // Initialize date search visibility
            const dateSearchInputs = document.getElementById('dateSearchInputs');
            if (dateSearchInputs) {
                dateSearchInputs.style.display = 'none';
            }

            // Initialize modals
            const modals = {
                addProduction: new bootstrap.Modal(document.getElementById('addProductionModal')),
                editProduction: new bootstrap.Modal(document.getElementById('editProductionModal')),
                addArticle: new bootstrap.Modal(document.getElementById('addArticleModal')),
                editArticle: new bootstrap.Modal(document.getElementById('editArticleModal'))
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