// Machine Management
function saveMachine() {
    const name = document.getElementById('machineName').value.trim();
    const type = document.getElementById('machineType').value === 'true';

    if (!name) {
        alert('Le nom de la machine est requis');
        return;
    }

    fetch('/api/machines', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            status: 'operational',
            type: type
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hideModal('addMachineModal');
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la création de la machine');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de la machine');
    });
}

function editMachine(id) {
    fetch(`/api/machines/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const machine = data.machine;
            document.getElementById('machineName').value = machine.name;
            document.getElementById('machineType').value = machine.type ? 'true' : 'false';

            // Update modal for edit mode
            document.querySelector('#addMachineModal .modal-title').textContent = 'Modifier la machine';
            const saveButton = document.getElementById('machineSaveButton');
            saveButton.textContent = 'Mettre à jour';
            saveButton.setAttribute('data-action', 'save-machine-edit');
            saveButton.setAttribute('data-id', id);
            
            showModal('addMachineModal');
        } else {
            alert(data.message || 'Erreur lors de la récupération des détails de la machine');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la récupération des détails de la machine');
    });
}

function updateMachine(id) {
    const name = document.getElementById('machineName').value;
    const status = document.getElementById('machineStatus').value;
    const type = document.getElementById('machineType').value === 'true';  // Convert string to boolean

    if (!name) {
        alert('Veuillez entrer un nom de machine');
        return;
    }

    fetch(`/api/machines/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, status, type })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Machine mise à jour avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la mise à jour de la machine');
    });
}

function deleteMachine(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cette machine ?')) {
        fetch(`/api/machines/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Machine supprimée avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de la machine');
        });
    }
}

// Operator Management
function saveOperator() {
    const name = document.getElementById('operatorName').value.trim();
    const arabicName = document.getElementById('operatorArabicName').value.trim();
    const status = document.getElementById('operatorStatus').value;

    if (!name || !arabicName) {
        alert('Le nom et le nom arabe sont requis');
        return;
    }

    fetch('/api/operators', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            arabic_name: arabicName,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hideModal('addOperatorModal');
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la création de l\'opérateur');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de l\'opérateur');
    });
}

function editOperator(id) {
    fetch(`/api/operators/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const operator = data.operator;
            document.getElementById('editOperatorId').value = operator.id;
            document.getElementById('editOperatorName').value = operator.name;
            document.getElementById('editOperatorArabicName').value = operator.arabic_name;
            document.getElementById('editOperatorStatus').value = operator.status;
            
            showModal('editOperatorModal');
        } else {
            alert(data.message || 'Erreur lors de la récupération des détails de l\'opérateur');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la récupération des détails de l\'opérateur');
    });
}

function updateOperator(id) {
    const name = document.getElementById('operatorName').value;
    const arabic_name = document.getElementById('operatorArabicName').value;
    const status = document.getElementById('operatorStatus').value;

    if (!name || !arabic_name) {
        alert('Veuillez entrer le nom et le nom arabe de l\'opérateur');
        return;
    }

    fetch(`/api/operators/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, arabic_name, status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Opérateur mis à jour avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la mise à jour de l\'opérateur');
    });
}

function saveOperatorEdit() {
    const arabicName = document.getElementById('editOperatorArabicName').value.trim();
    if (!arabicName) {
        alert('Le nom arabe est requis');
        return;
    }
    
    const id = document.getElementById('editOperatorId').value;
    const data = {
        name: document.getElementById('editOperatorName').value,
        arabic_name: arabicName,
        status: document.getElementById('editOperatorStatus').value
    };

    fetch(`/api/operators/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Failed to update operator');
        }
    })
    .catch(error => {
        console.error('Error updating operator:', error);
        alert('Error updating operator');
    });
}

function deleteOperator(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet opérateur ?')) {
        fetch(`/api/operators/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Opérateur supprimé avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de l\'opérateur');
        });
    }
}

// Non-Functioning Machines Management
function saveNonFunctioningMachine() {
    const machineId = document.getElementById('machineSelect').value;
    const issue = document.getElementById('issueDescription').value;
    const reportedDate = document.getElementById('reportedDate').value;
    const reportedTime = document.getElementById('reportedTime').value;

    if (!machineId || !issue || !reportedDate || !reportedTime) {
        alert('Veuillez remplir tous les champs requis (Machine, Problème, Date de signalement et Heure de signalement)');
        return;
    }

    const reportedAt = `${reportedDate} ${reportedTime}`;

    if (new Date(reportedAt) > new Date()) {
        alert('La date et l\'heure de signalement ne peuvent pas être dans le futur');
        return;
    }


    fetch('/api/non_functioning_machines', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            machine_id: machineId,
            issue: issue,
            reported_date: reportedAt
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Machine non fonctionnelle ajoutée avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de l\'ajout de la machine non fonctionnelle');
    });
}

function markMachineFixed(id) {
    // Show a modal to select the fixed date and time
    const modalHtml = `
        <div class="modal fade" id="markFixedModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Marquer la machine comme réparée</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="markFixedForm">
                            <div class="mb-3">
                                <label for="fixedDate" class="form-label">Date de réparation</label>
                                <input type="date" class="form-control" id="fixedDate" required>
                            </div>
                            <div class="mb-3">
                                <label for="fixedTime" class="form-label">Heure de réparation</label>
                                <input type="time" class="form-control" id="fixedTime" required>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-primary" onclick="submitMarkFixed(${id})">Enregistrer</button>
                    </div>
                </div>
            </div>
        </div>`;

    // Append the modal to the body and show it
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('markFixedModal'));
    modal.show();

    // Remove the modal from the DOM after it's hidden
    document.getElementById('markFixedModal').addEventListener('hidden.bs.modal', function () {
        document.getElementById('markFixedModal').remove();
    });
}

function submitMarkFixed(id) {
    const fixedDate = document.getElementById('fixedDate').value;
    const fixedTime = document.getElementById('fixedTime').value;

    if (!fixedDate || !fixedTime) {
        alert('Veuillez sélectionner la date et l\'heure');
        return;
    }

    // Combine date and time into a proper format
    const fixedDateTime = `${fixedDate} ${fixedTime}`;

    // Get the reported date from the table row
    const row = document.querySelector(`tr[data-machine-id="${id}"]`);
    const reportedDateStr = row.querySelector('td:nth-child(3)').textContent.trim();
    const reportedDate = new Date(reportedDateStr);
    const fixedDateObj = new Date(fixedDateTime);

    // Compare dates
    if (fixedDateObj <= reportedDate) {
        alert('La date de réparation doit être postérieure à la date de signalement');
        return;
    }

    fetch(`/api/non_functioning_machines/${id}/fix`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fixed_date: fixedDateTime })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Machine marquée comme réparée avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la marque de la machine comme réparée');
    });
}

// Articles Management
function saveArticle() {
    const name = document.getElementById('articleName').value.trim();
    const abbreviation = document.getElementById('articleAbbreviation').value.trim();
    const description = document.getElementById('articleDescription').value.trim();
    
    if (!name) {
        alert('Le nom de l\'article est requis');
        return;
    }

    fetch('/api/articles', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, abbreviation, description })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la création de l\'article');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de l\'article');
    });
}

function saveArticleEdit() {
    const id = document.getElementById('editArticleId').value;
    const name = document.getElementById('editArticleName').value.trim();
    const abbreviation = document.getElementById('editArticleAbbreviation').value.trim();
    const description = document.getElementById('editArticleDescription').value.trim();
    
    if (!name) {
        alert('Le nom de l\'article est requis');
        return;
    }

    fetch(`/api/articles/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, abbreviation, description })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la mise à jour de l\'article');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la mise à jour de l\'article');
    });
}

function deleteArticle(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet article ?')) {
        fetch(`/api/articles/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Article supprimé avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de l\'article');
        });
    }
}

function editArticle(id) {
    fetch(`/api/articles/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Échec de la récupération des détails de l\'article');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const article = data.article; // Correctly access the article object
                document.getElementById('editArticleId').value = article.id;
                document.getElementById('editArticleName').value = article.name;
                document.getElementById('editArticleAbbreviation').value = article.abbreviation;
                document.getElementById('editArticleDescription').value = article.description;
                new bootstrap.Modal(document.getElementById('editArticleModal')).show();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur lors de la récupération des détails de l\'article :', error);
            alert('Erreur lors de la récupération des détails de l\'article');
        });
}

// Production Management
function deleteProduction(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet enregistrement de production ?')) {
        fetch(`/api/production/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Enregistrement de production supprimé avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de l\'enregistrement de production');
        });
    }
}

function saveProduction() {
    const machineSelect = document.getElementById('productionMachine');
    const machineId = machineSelect.value;
    const startDate = document.getElementById('productionStartDate').value;
    const endDate = document.getElementById('productionEndDate').value;
    
    if (!machineId || !startDate) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    const data = {
        machine_id: machineId,
        start_date: startDate,
        end_date: endDate || null
    };

    // Add article data only if it's not a service machine
    const selectedOption = machineSelect.options[machineSelect.selectedIndex];
    const isService = selectedOption.getAttribute('data-type') === 'true';
    
    if (!isService) {
        const articleId = document.getElementById('productionArticle').value;
        const quantity = document.getElementById('productionQuantity').value;
        
        data.article_id = articleId;
        data.quantity = quantity;
    }

    fetch('/api/production', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la création de la production');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de la production');
    });
}

function saveProductionEdit() {
    const id = document.getElementById('editProductionId').value;
    const machineSelect = document.getElementById('editProductionMachine');
    const machineId = machineSelect.value;
    const startDate = document.getElementById('editProductionStartDate').value;
    const endDate = document.getElementById('editProductionEndDate').value;
    
    if (!machineId || !startDate) {
        alert('Veuillez remplir tous les champs obligatoires');
            return;
    }

    const data = {
        machine_id: machineId,
        start_date: startDate,
        end_date: endDate || null
    };

    // Add article data only if it's not a service machine
    const selectedOption = machineSelect.options[machineSelect.selectedIndex];
    const isService = selectedOption.getAttribute('data-type') === 'true';
    
    if (!isService) {
        const articleId = document.getElementById('editProductionArticle').value;
        const quantity = document.getElementById('editProductionQuantity').value;
        
        data.article_id = articleId;
        data.quantity = quantity;
    }

    fetch(`/api/production/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la mise à jour de la production');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la mise à jour de la production');
    });
}

function editProduction(id) {
    fetch(`/api/production/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Échec de la récupération des détails de la production');
            }
            return response.json();
        })
        .then(production => {
            document.getElementById('editProductionId').value = production.id;
            
            // Ensure the machine is properly selected in the dropdown
            const machineSelect = document.getElementById('editProductionMachine');
            
            // Check if the machine exists in the dropdown
            let machineExists = false;
            for (let i = 0; i < machineSelect.options.length; i++) {
                if (machineSelect.options[i].value == production.machine_id) {
                    machineExists = true;
                    break;
                }
            }
            
            // If machine doesn't exist in dropdown, add it
            if (!machineExists && production.machine_name) {
                const option = document.createElement('option');
                option.value = production.machine_id;
                option.textContent = production.machine_name;
                machineSelect.appendChild(option);
            }
            
            // Now set the value
            machineSelect.value = production.machine_id;
            
            document.getElementById('editProductionArticle').value = production.article_id;
            document.getElementById('editProductionQuantity').value = production.quantity;
            
            // Format start date to YYYY-MM-DD if it exists
            if (production.start_date) {
                // If the date is already in YYYY-MM-DD format, use it directly
                // Otherwise, convert it to that format
                if (/^\d{4}-\d{2}-\d{2}$/.test(production.start_date)) {
                    document.getElementById('editProductionStartDate').value = production.start_date;
                } else {
                    // Parse the date and format it as YYYY-MM-DD
                    const startDate = new Date(production.start_date);
                    const formattedStartDate = startDate.toISOString().split('T')[0];
                    document.getElementById('editProductionStartDate').value = formattedStartDate;
                }
            } else {
                document.getElementById('editProductionStartDate').value = '';
            }
            
            // Format end date to YYYY-MM-DD if it exists
            if (production.end_date) {
                // If the date is already in YYYY-MM-DD format, use it directly
                // Otherwise, convert it to that format
                if (/^\d{4}-\d{2}-\d{2}$/.test(production.end_date)) {
                    document.getElementById('editProductionEndDate').value = production.end_date;
                } else {
                    // Parse the date and format it as YYYY-MM-DD
                    const endDate = new Date(production.end_date);
                    const formattedEndDate = endDate.toISOString().split('T')[0];
                    document.getElementById('editProductionEndDate').value = formattedEndDate;
                }
            } else {
                document.getElementById('editProductionEndDate').value = '';
            }
            
            document.getElementById('editProductionStatus').value = production.status;
            new bootstrap.Modal(document.getElementById('editProductionModal')).show();

        })
        .catch(error => {
            console.error('Erreur lors de la récupération des détails de la production :', error);
            alert('Erreur lors de la récupération des détails de la production');
        });
}

// Shifts Management
function deleteShift(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce shift ?')) {
        fetch(`/api/shifts/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Shift supprimé avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression du shift');
        });
    }
}

// Absences Management
function saveAbsence() {
    const operatorSelect = document.getElementById('operatorSelect');
    const operatorId = operatorSelect ? operatorSelect.value : null;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reason = document.getElementById('absenceReason').value;
    
    if (!operatorId || !startDate || !endDate || !reason) {
        alert('Veuillez remplir tous les champs');
        return;
    }

    if (startDate > endDate) {
        alert('La date de début doit être antérieure à la date de fin');
        return;
    }
    
    fetch('/api/absences', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            operator_id: operatorId,
            start_date: startDate,
            end_date: endDate,
            reason: reason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Absence ajoutée avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de l\'ajout de l\'absence');
    });
}

function editAbsence(id) {
    // Fetch absence details and populate the edit modal
    fetch(`/api/absences/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur lors de la récupération des détails de l\'absence');
            }
            return response.json();
        })
        .then(data => {
            const absence = data.absence || data; // Handle both response formats
            if (!absence) {
                throw new Error('Données d\'absence non trouvées');
            }

            document.getElementById('editAbsenceId').value = absence.id;
            document.getElementById('editOperatorSelect').value = absence.operator_id;
            
            // Format dates to YYYY-MM-DD
            if (absence.start_date) {
                const startDate = new Date(absence.start_date);
                document.getElementById('editStartDate').value = startDate.toISOString().split('T')[0];
            }
            if (absence.end_date) {
                const endDate = new Date(absence.end_date);
                document.getElementById('editEndDate').value = endDate.toISOString().split('T')[0];
            }
            
            document.getElementById('editAbsenceReason').value = absence.reason;
            
            // Show the modal
            new bootstrap.Modal(document.getElementById('editAbsenceModal')).show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert(error.message || 'Erreur lors de la récupération des détails de l\'absence');
        });
}

function saveAbsenceEdit() {
    const id = document.getElementById('editAbsenceId').value;
    if (!id) {
        alert('ID d\'absence non trouvé');
        return;
    }

    const operatorId = document.getElementById('editOperatorSelect').value;
    const startDate = document.getElementById('editStartDate').value;
    const endDate = document.getElementById('editEndDate').value;
    const reason = document.getElementById('editAbsenceReason').value;

    // Validate all required fields
    if (!operatorId || !startDate || !endDate || !reason) {
        alert('Veuillez remplir tous les champs requis');
        return;
    }

    // Validate dates
    if (new Date(endDate) < new Date(startDate)) {
        alert('La date de fin doit être postérieure à la date de début');
        return;
    }

    const data = {
        operator_id: operatorId,
        start_date: startDate,
        end_date: endDate,
        reason: reason
    };

    fetch(`/api/absences/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erreur lors de la mise à jour de l\'absence');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Absence mise à jour avec succès');
            location.reload();
        } else {
            throw new Error(data.message || 'Erreur lors de la mise à jour de l\'absence');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || 'Erreur lors de la mise à jour de l\'absence');
    });
}

function deleteAbsence(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cette absence ?')) {
        fetch(`/api/absences/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Absence supprimée avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de l\'absence');
        });
    }
}

// Schedule Management
function assignOperator(machineId, shiftId, weekNumber, year) {
    const operatorSelect = document.getElementById(`operator-select-${machineId}-${shiftId}`);
    const operatorId = operatorSelect ? operatorSelect.value : null;

    if (!operatorId) {
        alert('Veuillez sélectionner un opérateur');
        return;
    }

    fetch('/api/schedule', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            machine_id: machineId,
            operator_id: operatorId,
            shift_id: shiftId,
            week_number: weekNumber,
            year: year
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Opérateur assigné avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de l\'assignation de l\'opérateur');
    });
}

function removeAssignment(assignmentId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cette assignation ?')) {
        fetch(`/api/schedule/${assignmentId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Assignation supprimée avec succès');
                location.reload();
            } else {
                alert('Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur :', error);
            alert('Erreur lors de la suppression de l\'assignation');
        });
    }
}

function updateAssignment(assignmentId, machineId, operatorId, shiftId) {
    fetch(`/api/schedule/${assignmentId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            machine_id: machineId,
            operator_id: operatorId,
            shift_id: shiftId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Assignation mise à jour avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la mise à jour de l\'assignation');
    });
}

// Helper function to get week number (ISO 8601)
Date.prototype.getWeek = function() {
    // Create a copy of this date object
    const target = new Date(this.valueOf());

    // ISO week date weeks start on Monday, so correct the day number
    const dayNr = (this.getDay() + 6) % 7;

    // Set the target to the Thursday of this week so the
    // target date is in the right year
    target.setDate(target.getDate() - dayNr + 3);

    // ISO 8601 states that week 1 is the week with January 4th in it
    const jan4 = new Date(target.getFullYear(), 0, 4);
    
    // Number of days between target date and january 4th
    const dayDiff = (target - jan4) / 86400000;

    // Calculate week number: Week 1 + number of weeks between target and jan4
    const weekNr = 1 + Math.ceil((dayDiff - 3 + (jan4.getDay() + 6) % 7) / 7);

    return weekNr;
};

// Helper function to get the last week number of a year (53/52week a year) (ISO 8601)
function getLastWeekOfYear(year) {
    // Get Dec 31 of the year
    const dec31 = new Date(year, 11, 31);
    // Get its week number
    let weekNum = dec31.getWeek();
    
    // Special handling: if Dec 31 is in week 1, we need to find the last week of the previous year
    if (weekNum === 1) {
        // Try Dec 28 which is always in the last week
        const dec28 = new Date(year, 11, 28);
        weekNum = dec28.getWeek();
    }
    
    return weekNum;
}

// Helper function to validate week number
function isValidWeek(week, year) {
    if (week < 1) return false;
    const lastWeek = getLastWeekOfYear(year);
    return week <= lastWeek;
}

// Helper function to get current week and year
function getCurrentWeekYear() {
    const today = new Date();
    const week = today.getWeek();
    let year = today.getFullYear();
    
    // Handle edge case where current week might belong to previous/next year
    if (week === 1 && today.getMonth() === 11) {
        // Week 1 in December belongs to next year
        year++;
    } else if (week >= 52 && today.getMonth() === 0) {
        // Week 52/53 in January belongs to previous year
        year--;
    }
    
    return { week, year };
}

//Schedule Operator Selection
function updateOperatorDropdowns() {
    // Get all operator dropdowns
    const dropdowns = document.querySelectorAll('.operator-select');

    // Get all currently selected operators
    const selectedOperators = new Set();
    dropdowns.forEach(dropdown => {
        if (dropdown.value) {
            selectedOperators.add(dropdown.value);
        }
    });

    // Update each dropdown
    dropdowns.forEach(dropdown => {
        const currentValue = dropdown.value;
        const options = Array.from(dropdown.querySelectorAll('option'));

        // Clear the dropdown
        dropdown.innerHTML = '';

        // Ensure the default option is always on top and only once
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Sélectionner un opérateur';
        dropdown.appendChild(defaultOption);

        // Separate enabled and disabled options
        const enabledOptions = [];
        const disabledOptions = [];

        options.forEach(option => {
            if (option.value && selectedOperators.has(option.value) && option.value !== currentValue) {
                disabledOptions.push(option);
            } else if (option.value) {
                enabledOptions.push(option);
            }
        });

        // Sort enabled options to maintain default order
        enabledOptions.sort((a, b) => a.textContent.localeCompare(b.textContent));

        // Append enabled options first
        enabledOptions.forEach(option => {
            option.disabled = false;
            option.style.color = 'black';
            dropdown.appendChild(option);
        });

        // Append disabled options at the bottom
        disabledOptions.forEach(option => {
            option.disabled = true;
            option.style.color = '#b3b3b3';
            dropdown.appendChild(option);
        });

        // Restore the current selection
        if (currentValue) {
            dropdown.value = currentValue;
        }
    });
}
// Add event listeners for modal show events
document.addEventListener('DOMContentLoaded', function() {
    // Machine modal reset
    document.getElementById('addMachineModal').addEventListener('show.bs.modal', function() {
        // Only reset if we're not in edit mode (check if button text is not 'Update')
        if (document.querySelector('#addMachineModal .btn-primary').textContent !== 'Mettre à jour') {
            document.getElementById('machineName').value = '';
            document.getElementById('machineStatus').value = 'operational';
            document.getElementById('machineType').value = 'false';
            document.querySelector('#addMachineModal .modal-title').textContent = 'Ajouter une machine';
            document.querySelector('#addMachineModal .btn-primary').textContent = 'Enregistrer';
            document.querySelector('#addMachineModal .btn-primary').onclick = saveMachine;
        }
    });

    // Operator modal reset
    document.getElementById('addOperatorModal').addEventListener('show.bs.modal', function() {
        // Only reset if we're not in edit mode (check if button text is not 'Update')
        if (document.querySelector('#addOperatorModal .btn-primary').textContent !== 'Mettre à jour') {
            document.getElementById('operatorName').value = '';
            document.getElementById('operatorArabicName').value = '';
            document.getElementById('operatorStatus').value = 'active';
            document.querySelector('#addOperatorModal .modal-title').textContent = 'Ajouter un opérateur';
            document.querySelector('#addOperatorModal .btn-primary').textContent = 'Enregistrer';
            document.querySelector('#addOperatorModal .btn-primary').onclick = saveOperator;
        }
    });

    // Non-Functioning Machine modal reset
    document.getElementById('addNonFunctioningMachineModal').addEventListener('show.bs.modal', function() {
        document.getElementById('machineSelect').value = '';
        document.getElementById('issueDescription').value = '';
        document.getElementById('reportedDate').value = '';
        document.getElementById('reportedTime').value = '';
    });

    // Absence modal reset
    document.getElementById('addAbsenceModal').addEventListener('show.bs.modal', function() {
        document.getElementById('operatorSelect').value = '';
        document.getElementById('startDate').value = '';
        document.getElementById('endDate').value = '';
        document.getElementById('absenceReason').value = '';
    });

    // Production modal reset
    document.getElementById('addProductionModal').addEventListener('show.bs.modal', function() {
        document.getElementById('productionMachine').value = '';
        document.getElementById('productionArticle').value = '';
        document.getElementById('productionQuantity').value = '';
        document.getElementById('productionStartDate').value = '';
        document.getElementById('productionEndDate').value = '';
        // Reset article fields visibility
        const articleFields = document.querySelectorAll('.article-field');
        articleFields.forEach(field => {
            field.style.display = 'none';
        });
    });

    // Article modal reset
    document.getElementById('addArticleModal').addEventListener('show.bs.modal', function() {
        document.getElementById('articleName').value = '';
        document.getElementById('articleAbbreviation').value = '';
        document.getElementById('articleDescription').value = '';
    });

    // Add this to the modal cleanup code in the DOMContentLoaded event listener
    document.getElementById('addMachineModal').addEventListener('hidden.bs.modal', function() {
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
        // Reset modal title and button
        this.querySelector('.modal-title').textContent = 'Ajouter une machine';
        const saveButton = document.getElementById('machineSaveButton');
        saveButton.textContent = 'Enregistrer';
        saveButton.setAttribute('data-action', 'save-machine');
        saveButton.removeAttribute('data-id');
    });
});

// Production filtering
function filterProduction() {
    const searchText = document.getElementById('productionSearch').value.toLowerCase();
    const startDate = document.getElementById('startDateSearch').value;
    const endDate = document.getElementById('endDateSearch').value;
    const isDateSearchEnabled = document.getElementById('dateSearchToggle').checked;
    
    const rows = document.querySelectorAll('#productionBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const machineName = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const articleName = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        const rowStartDate = row.querySelector('td:nth-child(5)').textContent;
        const rowEndDate = row.querySelector('td:nth-child(6)').textContent;
        
        let matchesText = machineName.includes(searchText) || articleName.includes(searchText);
        let matchesDate = true;

        if (isDateSearchEnabled && (startDate || endDate)) {
            if (startDate && endDate) {
                matchesDate = (rowStartDate >= startDate && (rowEndDate === '-' || rowEndDate <= endDate));
            } else if (startDate) {
                matchesDate = (rowStartDate >= startDate);
            } else if (endDate) {
                matchesDate = (rowEndDate === '-' || rowEndDate <= endDate);
            }
        }

        const isVisible = matchesText && matchesDate;
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noProductionFound').style.display = hasVisibleRows ? 'none' : 'block';
}

// Article filtering
function filterArticles() {
    const searchText = document.getElementById('articleSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#articlesBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const name = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const abbreviation = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const description = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        
        const isVisible = name.includes(searchText) || abbreviation.includes(searchText) || description.includes(searchText);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noArticlesFound').style.display = hasVisibleRows ? 'none' : 'block';
}

// Toggle date search fields
function toggleDateSearch() {
    const dateInputs = document.getElementById('dateSearchInputs');
    const isChecked = document.getElementById('dateSearchToggle').checked;
    dateInputs.style.display = isChecked ? 'block' : 'none';
    if (!isChecked) {
        document.getElementById('startDateSearch').value = '';
        document.getElementById('endDateSearch').value = '';
        filterProduction();
    }
}

// Clear date search
function clearDateSearch() {
    document.getElementById('startDateSearch').value = '';
    document.getElementById('endDateSearch').value = '';
    filterProduction();
}

// Toggle article fields based on machine type
function toggleArticleFields() {
    const machineSelect = document.getElementById('productionMachine');
    const articleFields = document.querySelectorAll('.article-field');
    
    if (machineSelect && machineSelect.selectedIndex > 0) {
        const selectedOption = machineSelect.options[machineSelect.selectedIndex];
        const isService = selectedOption.getAttribute('data-type') === 'true';
        
        articleFields.forEach(field => {
            field.style.display = isService ? 'none' : 'block';
            const input = field.querySelector('select, input');
            if (input) {
                input.required = !isService;
            }
        });
    }
}

// Toggle article fields in edit form
function toggleEditArticleFields() {
    const machineSelect = document.getElementById('editProductionMachine');
    const articleFields = document.querySelectorAll('.edit-article-field');
    
    if (machineSelect && machineSelect.selectedIndex > 0) {
        const selectedOption = machineSelect.options[machineSelect.selectedIndex];
        const isService = selectedOption.getAttribute('data-type') === 'true';
        
        articleFields.forEach(field => {
            field.style.display = isService ? 'none' : 'block';
            const input = field.querySelector('select, input');
            if (input) {
                input.required = !isService;
            }
        });
    }
}

// Machine filtering
function filterMachines() {
    const searchText = document.getElementById('machineSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#machinesBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const name = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const status = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const type = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        
        const isVisible = name.includes(searchText) || status.includes(searchText) || type.includes(searchText);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noMachinesFound').style.display = hasVisibleRows ? 'none' : 'block';
}

function filterNonFunctioningMachines() {
    const searchText = document.getElementById('nonFunctioningMachineSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#nonFunctioningMachinesBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const name = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const issue = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        
        const isVisible = name.includes(searchText) || issue.includes(searchText);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noNonFunctioningMachinesFound').style.display = hasVisibleRows ? 'none' : 'block';
}

// Operator filtering
function filterOperators() {
    const searchText = document.getElementById('operatorSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#operatorsBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const id = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const name = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const arabicName = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        const status = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
        
        const isVisible = id.includes(searchText) || 
                         name.includes(searchText) || 
                         arabicName.includes(searchText) || 
                         status.includes(searchText);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noOperatorsFound').style.display = hasVisibleRows ? 'none' : 'block';
}

function filterAbsences() {
    const searchText = document.getElementById('absenceSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#absencesBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const operator = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const reason = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
        
        const isVisible = operator.includes(searchText) || reason.includes(searchText);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noAbsencesFound').style.display = hasVisibleRows ? 'none' : 'block';
}

// Modal Management
function showModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement) {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

// User Management
function saveUser() {
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const role = document.getElementById('role').value;

    // Get selected pages
    const accessiblePages = [];
    ['machines', 'operators', 'production', 'schedule'].forEach(page => {
        const checkbox = document.getElementById(`page_${page}`);
        if (checkbox && checkbox.checked) {
            accessiblePages.push(page);
        }
    });

    // Validate form
    if (!username || !email || !password || !confirmPassword) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    if (password !== confirmPassword) {
        alert('Les mots de passe ne correspondent pas');
        return;
    }

    if (accessiblePages.length === 0 && role !== 'admin') {
        alert('Veuillez sélectionner au moins une page accessible');
        return;
    }

    const data = {
        username: username,
        email: email,
        password: password,
        role: role,
        accessible_pages: accessiblePages
    };

    fetch('/api/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hideModal('addUserModal');
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la création de l\'utilisateur');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la création de l\'utilisateur');
    });
}

function editUser(id) {
    // Reset form and checkboxes first
    const form = document.getElementById('editUserForm');
    if (form) {
        form.reset();
        // Reset all checkboxes
        ['machines', 'operators', 'production', 'schedule'].forEach(page => {
            const checkbox = document.getElementById(`edit_page_${page}`);
            if (checkbox) {
                checkbox.checked = false;
            }
        });
    }

    fetch(`/api/users/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const user = data.user;
            document.getElementById('editUserId').value = user.id;
            document.getElementById('editUsername').value = user.username;
            document.getElementById('editEmail').value = user.email;
            document.getElementById('editRole').value = user.role;
            
            // Clear password fields
            document.getElementById('editPassword').value = '';
            document.getElementById('editConfirmPassword').value = '';

            // Set accessible pages
            if (Array.isArray(user.accessible_pages)) {
                user.accessible_pages.forEach(page => {
                    const checkbox = document.getElementById(`edit_page_${page}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }

            showModal('editUserModal');
        } else {
            alert(data.message || 'Erreur lors de la récupération des détails de l\'utilisateur');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la récupération des détails de l\'utilisateur');
    });
}

function saveUserEdit() {
    const id = document.getElementById('editUserId').value;
    const username = document.getElementById('editUsername').value.trim();
    const email = document.getElementById('editEmail').value.trim();
    const password = document.getElementById('editPassword').value;
    const confirmPassword = document.getElementById('editConfirmPassword').value;
    const role = document.getElementById('editRole').value;

    // Get selected pages
    const accessiblePages = [];
    ['machines', 'operators', 'production', 'schedule'].forEach(page => {
        const checkbox = document.getElementById(`edit_page_${page}`);
        if (checkbox && checkbox.checked) {
            accessiblePages.push(page);
        }
    });

    // Validate form
    if (!username || !email) {
        alert('Veuillez remplir tous les champs obligatoires');
        return;
    }

    if (password && password !== confirmPassword) {
        alert('Les mots de passe ne correspondent pas');
        return;
    }

    if (accessiblePages.length === 0 && role !== 'admin') {
        alert('Veuillez sélectionner au moins une page accessible');
        return;
    }

    const data = {
        username: username,
        email: email,
        role: role,
        accessible_pages: accessiblePages
    };

    // Only include password if it's being changed
    if (password) {
        data.password = password;
    }

    fetch(`/api/users/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hideModal('editUserModal');
            location.reload();
        } else {
            alert(data.message || 'Erreur lors de la mise à jour de l\'utilisateur');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de la mise à jour de l\'utilisateur');
    });
}

function deleteUser(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
        fetch(`/api/users/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert(data.message || 'Erreur lors de la suppression de l\'utilisateur');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erreur lors de la suppression de l\'utilisateur');
        });
    }
}

function filterUsers() {
    const searchText = document.getElementById('userSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#usersBody tr');
    let hasVisibleRows = false;
    
    rows.forEach(row => {
        const username = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const email = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const role = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        const pages = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
        
        const isVisible = username.includes(searchText) || 
                         email.includes(searchText) || 
                         role.includes(searchText) ||
                         pages.includes(searchText);
        
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) hasVisibleRows = true;
    });
    
    document.getElementById('noUsersFound').style.display = hasVisibleRows ? 'none' : 'block';
}
