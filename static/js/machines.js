// Global variable to store available postes
let availablePostes = [];

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
            // Add keydown event listener to handle Enter key
            form.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const saveButton = document.getElementById('machineSaveButton');
                    if (saveButton) {
                        const action = saveButton.getAttribute('data-action');
                        const id = saveButton.getAttribute('data-id');
                        if (action === 'save-machine-edit' && id) {
                            updateMachine(id);
                        } else if (action === 'save-machine') {
                            saveMachine();
                        }
                    }
                }
            });
        }
    });

    // Initialize modals
    const modals = {
        addMachine: new bootstrap.Modal(document.getElementById('addMachineModal')),
        editMachine: new bootstrap.Modal(document.getElementById('editMachineModal')),
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
                        typeSelect.value = '0';
                    }

                    // Reset machine poste to regular machine
                    const posteSelect = form.querySelector('#machinePoste');
                    if (posteSelect) {
                        posteSelect.value = '';
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

    // Fetch and render machines from API
    fetch('/api/machines')
        .then(response => response.json())
        .then(data => {
            if (data.success && Array.isArray(data.machines)) {
                renderMachinesTable(data.machines);
            }
        });
});

// Function to fetch all available postes from the API
async function fetchPostes() {
    try {
        const response = await fetch('/api/postes');
        const data = await response.json();
        if (data.success) {
            availablePostes = data.postes;
            populatePosteDropdowns();
        }
    } catch (error) {
        console.error('Error fetching postes:', error);
    }
}

// Function to populate poste dropdowns
function populatePosteDropdowns() {
    const dropdowns = [
        document.getElementById('machinePoste'),
        document.getElementById('editMachinePoste')
    ];

    dropdowns.forEach(dropdown => {
        if (!dropdown) return;
        
        // Clear existing options except the first one
        while (dropdown.children.length > 1) {
            dropdown.removeChild(dropdown.lastChild);
        }

        // Add poste options
        availablePostes.forEach(poste => {
            const option = document.createElement('option');
            option.value = poste.id;
            option.textContent = poste.name;
            dropdown.appendChild(option);
        });
    });
}

function saveMachine() {
    const name = document.getElementById('machineName').value.trim();
    const status = document.getElementById('machineStatus').value;
    const type = document.getElementById('machineType').value; // 0 or 1
    const poste_id = document.getElementById('machinePoste').value;

    console.log('name:', name, 'poste_id:', poste_id, 'type:', type);

    if (!name || !poste_id) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    fetch('/api/machines', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            status: status,
            type: type, // 0 or 1
            poste_id: parseInt(poste_id)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Erreur: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de la machine');
    });
}

function updateMachine() {
    const id = document.getElementById('editMachineId').value;
    const name = document.getElementById('editMachineName').value.trim();
    const type = document.getElementById('editMachineType').value; // 0 or 1
    const poste_id = document.getElementById('editMachinePoste').value;

    console.log('name:', name, 'poste_id:', poste_id, 'type:', type);

    if (!name || !poste_id) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    fetch(`/api/machines/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            type: type, // 0 or 1
            poste_id: parseInt(poste_id)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Erreur: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la mise à jour de la machine');
    });
}

function markMachineFixed(id) {
    if (!id) {
        alert('ID de machine non spécifié.');
        return;
    }

    if (confirm('Voulez-vous vraiment marquer cette machine comme fonctionnelle ?')) {
        fetch(`/api/machines/${id}/mark-fixed`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Erreur: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erreur lors de la mise à jour de la machine');
        });
    }
}

function deleteMachine(id) {
    if (!id) {
        alert('ID de machine non spécifié.');
        return;
    }

    if (confirm('Voulez-vous vraiment supprimer cette machine ? Cette action est irréversible.')) {
        fetch(`/api/machines/${id}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Erreur: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erreur lors de la suppression de la machine');
        });
    }
}

function saveNonFunctioningMachine() {
    const name = document.getElementById('nonFunctioningMachineName').value.trim();
    const status = 'non-functioning'; // Always 'non-functioning' for this form
    const type = parseInt(document.getElementById('nonFunctioningMachineType').value, 10); // 0 or 1
    const poste_id = document.getElementById('nonFunctioningMachinePoste').value;

    console.log('name:', name, 'poste_id:', poste_id, 'type:', type);

    if (!name || !poste_id) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    fetch('/api/non-functioning-machines', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            status: status,
            type: type, // 0 or 1
            poste_id: parseInt(poste_id)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Erreur: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de la machine non fonctionnelle');
    });
}

function editMachine(id) {
    if (!id) {
        alert('ID de machine non spécifié.');
        return;
    }

    fetch(`/api/machines/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('editMachineId').value = data.machine.id;
                document.getElementById('editMachineName').value = data.machine.name;
                document.getElementById('editMachineType').value = data.machine.type ? '1' : '0';
                document.getElementById('editMachinePoste').value = data.machine.poste_id;
                if (document.getElementById('editMachineStatus')) {
                    document.getElementById('editMachineStatus').value = data.machine.status;
                }
                new bootstrap.Modal(document.getElementById('editMachineModal')).show();
            } else {
                alert('Erreur: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erreur lors de la récupération de la machine');
        });
}

function filterMachines() {
    const searchTerm = document.getElementById('machineSearch').value.toLowerCase();
    const machines = document.querySelectorAll('.machine-row');
    machines.forEach(machine => {
        const name = machine.querySelector('.machine-name').textContent.toLowerCase();
        if (name.includes(searchTerm)) {
            machine.style.display = '';
        } else {
            machine.style.display = 'none';
        }
    });
}

function filterNonFunctioningMachines() {
    const searchTerm = document.getElementById('nonFunctioningMachineSearch').value.toLowerCase();
    const nonFunctioningMachines = document.querySelectorAll('.non-functioning-machine-row');
    nonFunctioningMachines.forEach(machine => {
        const name = machine.querySelector('.non-functioning-machine-name').textContent.toLowerCase();
        if (name.includes(searchTerm)) {
            machine.style.display = '';
        } else {
            machine.style.display = 'none';
        }
    });
}

function renderMachinesTable(machines) {
    const tbody = document.getElementById('machinesBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    machines.forEach(machine => {
        const tr = document.createElement('tr');
        tr.classList.add('machine-row');
        tr.innerHTML = `
            <td class="machine-name">${machine.name}</td>
            <td>
                <span class="badge bg-${machine.status === 'operational' ? 'success' : machine.status === 'maintenance' ? 'light' : 'danger'}">
                    ${machine.status}
                </span>
            </td>
            <td>${machine.type ? 'Service' : 'Machine'}</td>
            <td>
                ${machine.poste_name ? `${machine.poste_name.charAt(0).toUpperCase() + machine.poste_name.slice(1)}` : `<span class='text-dark'>-</span>`}
            </td>
            <td>
                <button class="btn btn-sm btn-light" data-action="edit-machine" data-id="${machine.id}">
                    <i class='bx bx-edit-alt'></i>
                </button>
                <button class="btn btn-sm btn-danger" data-action="delete-machine" data-id="${machine.id}">
                    <i class='bx bx-x'></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}