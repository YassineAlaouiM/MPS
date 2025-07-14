// Global variable to store available postes
let availablePostes = [];

// Function to fetch all available postes from the API
async function fetchPostes() {
    try {
        const response = await fetch('/api/postes');
        const data = await response.json();
        if (data.success) {
            availablePostes = data.postes;
            populatePostesCheckboxes();
        }
    } catch (error) {
        console.error('Error fetching postes:', error);
    }
}

// Function to populate postes checkboxes dynamically
function populatePostesCheckboxes() {
    const containers = [
        { prefix: '', container: document.getElementById('addOperatorPostesCheckboxes') },
        { prefix: 'edit', container: document.getElementById('editOperatorPostesCheckboxes') }
    ];

    containers.forEach(({ prefix, container }) => {
        if (!container) return;
        container.innerHTML = '';

        // Create two columns
        const leftCol = document.createElement('div');
        leftCol.className = 'col-6';
        const rightCol = document.createElement('div');
        rightCol.className = 'col-6';

        availablePostes.forEach((poste, idx) => {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check mb-2 ps-4';
            checkboxDiv.innerHTML = `
                <input class="form-check-input" type="checkbox" id="${prefix}Poste${poste.id}" value="${poste.id}">
                <label class="form-check-label" for="${prefix}Poste${poste.id}">${poste.name}</label>
            `;
            if (idx < 4) {
                leftCol.appendChild(checkboxDiv);
            } else {
                rightCol.appendChild(checkboxDiv);
            }
        });

        container.appendChild(leftCol);
        container.appendChild(rightCol);
    });
}

// Function to get selected postes from checkboxes (returns array of IDs)
function getSelectedPostes(prefix = '') {
    const postes = [];
    const checkboxes = document.querySelectorAll(`#${prefix}OperatorModal .form-check-input:checked`);
    checkboxes.forEach(checkbox => {
        postes.push(parseInt(checkbox.value));
    });
    return postes;
}

// Function to set postes checkboxes based on array of poste IDs
function setPostesCheckboxes(posteIds, prefix = '') {
    if (!posteIds || !Array.isArray(posteIds)) return;
    
    // Clear all checkboxes first
    const checkboxes = document.querySelectorAll(`#${prefix}OperatorModal .form-check-input`);
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Check the ones that match the poste IDs
    posteIds.forEach(posteId => {
        const checkbox = document.getElementById(`${prefix}Poste${posteId}`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });
}

// Function to clear postes checkboxes
function clearPostesCheckboxes() {
    const checkboxes = document.querySelectorAll('#addOperatorModal .form-check-input');
    checkboxes.forEach(checkbox => checkbox.checked = false);
}

// Function to clear edit postes checkboxes
function clearEditPostesCheckboxes() {
    const checkboxes = document.querySelectorAll('#editOperatorModal .form-check-input');
    checkboxes.forEach(checkbox => checkbox.checked = false);
}

document.addEventListener('DOMContentLoaded', function() {
    fetchPostes(); // <--- Add this line at the top
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
                        // Clear checkboxes and textarea
                        if (key === 'addOperator') {
                            clearPostesCheckboxes();
                            document.getElementById('otherCompetences').value = '';
                        } else if (key === 'editOperator') {
                            clearEditPostesCheckboxes();
                            document.getElementById('editOtherCompetences').value = '';
                        }
                    });
                }
            });

            // Ensure checkboxes are rendered before showing the add operator modal
            const addOperatorModal = document.getElementById('addOperatorModal');
            if (addOperatorModal) {
                addOperatorModal.addEventListener('show.bs.modal', function() {
                    populatePostesCheckboxes();
                });
            }
        });