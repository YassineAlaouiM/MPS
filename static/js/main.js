// Machine Management
function saveMachine() {
    const name = document.getElementById('machineName').value;
    const status = document.getElementById('machineStatus').value;
    const type = document.getElementById('machineType').value === 'true';  // Convert string to boolean

    if (!name) {
        alert('Veuillez entrer un nom de machine');
        return;
    }

    fetch('/api/machines', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, status, type })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Machine créée avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la création de la machine');
    });
}

function editMachine(id) {
    // Get machine details
    fetch(`/api/machines/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const machine = data.machine;
            // Populate the modal form
            document.getElementById('machineName').value = machine.name;
            document.getElementById('machineStatus').value = machine.status;
            document.getElementById('machineType').value = machine.type ? 'true' : 'false';

            // Change modal title and button
            document.querySelector('#addMachineModal .modal-title').textContent = 'Modifier la machine';
            document.querySelector('#addMachineModal .btn-primary').textContent = 'Mettre à jour';
            document.querySelector('#addMachineModal .btn-primary').onclick = () => updateMachine(id);

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('addMachineModal'));
            modal.show();

            // Add event listener to reset form when modal is hidden
            document.getElementById('addMachineModal').addEventListener('hidden.bs.modal', function () {
                document.getElementById('machineName').value = '';
                document.getElementById('machineStatus').value = 'operational';
                document.getElementById('machineType').value = 'false';
                document.querySelector('#addMachineModal .modal-title').textContent = 'Ajouter une machine';
                document.querySelector('#addMachineModal .btn-primary').textContent = 'Enregistrer';
                document.querySelector('#addMachineModal .btn-primary').onclick = saveMachine;
            }, { once: true });
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors du chargement des détails de la machine');
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
    const id = document.getElementById('operatorId').value;
    const name = document.getElementById('operatorName').value;
    const arabic_name = document.getElementById('operatorArabicName').value;
    const status = document.getElementById('operatorStatus').value;

    if (!id || !name || !arabic_name) {
        alert('Veuillez entrer l\'ID et le nom de l\'opérateur');
        return;
    }

    fetch('/api/operators', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id, name, arabic_name, status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Opérateur créé avec succès');
            location.reload();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors de la création de l\'opérateur');
    });
}

function editOperator(id) {
    // Get operator details
    fetch(`/api/operators/${id}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const operator = data.operator;
            // Populate the modal form
            document.getElementById('operatorId').value = operator.id;
            document.getElementById('operatorName').value = operator.name;
            document.getElementById('operatorArabicName').value = operator.arabic_name;
            document.getElementById('operatorStatus').value = operator.status;

            // Change modal title and button
            document.querySelector('#addOperatorModal .modal-title').textContent = 'Modifier l\'opérateur';
            document.querySelector('#addOperatorModal .btn-primary').textContent = 'Mettre à jour';
            document.querySelector('#addOperatorModal .btn-primary').onclick = () => updateOperator(id);

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('addOperatorModal'));
            modal.show();

            // Add event listener to reset form when modal is hidden
            document.getElementById('addOperatorModal').addEventListener('hidden.bs.modal', function () {
                document.getElementById('operatorId').value = '';
                document.getElementById('operatorName').value = '';
                document.getElementById('operatorArabicName').value = '';
                document.getElementById('operatorStatus').value = 'active';
                document.querySelector('#addOperatorModal .modal-title').textContent = 'Ajouter un opérateur';
                document.querySelector('#addOperatorModal .btn-primary').textContent = 'Enregistrer';
                document.querySelector('#addOperatorModal .btn-primary').onclick = saveOperator;
            }, { once: true });
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur :', error);
        alert('Erreur lors du chargement des détails de l\'opérateur');
    });
}

function updateOperator(id) {
    const operatorId = document.getElementById('operatorId').value;
    const name = document.getElementById('operatorName').value;
    const arabic_name = document.getElementById('operatorArabicName').value;
    const status = document.getElementById('operatorStatus').value;

    if (!operatorId || !name || !arabic_name) {
        alert('Veuillez entrer l\'ID et le nom de l\'opérateur');
        return;
    }

    fetch(`/api/operators/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: operatorId, name, arabic_name, status })
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

// Schedule Management
function assignOperator(machineId, shiftId, weekNumber, year) {
    const operatorId = document.getElementById(`operator-select-${machineId}-${shiftId}`).value;
    
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

// Helper function to get the last week number of a year (ISO 8601)
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

function previousWeek() {
    const currentUrl = new URL(window.location.href);
    const current = getCurrentWeekYear();
    let week = parseInt(currentUrl.searchParams.get('week')) || current.week;
    let year = parseInt(currentUrl.searchParams.get('year')) || current.year;
    
    // Validate current week/year
    if (!isValidWeek(week, year)) {
        week = current.week;
        year = current.year;
    }
    
    // Calculate previous week
    if (week === 1) {
        year--;
        week = getLastWeekOfYear(year);
    } else {
        week--;
    }
    
    // Double-check the result is valid
    if (!isValidWeek(week, year)) {
        console.error('Invalid week calculation', { week, year });
        return;
    }
    
    currentUrl.searchParams.set('week', week);
    currentUrl.searchParams.set('year', year);
    window.location.href = currentUrl.toString();
}

function nextWeek() {
    const currentUrl = new URL(window.location.href);
    const current = getCurrentWeekYear();
    let week = parseInt(currentUrl.searchParams.get('week')) || current.week;
    let year = parseInt(currentUrl.searchParams.get('year')) || current.year;
    
    // Validate current week/year
    if (!isValidWeek(week, year)) {
        week = current.week;
        year = current.year;
    }
    
    // Calculate next week
    const lastWeek = getLastWeekOfYear(year);
    if (week === lastWeek) {
        week = 1;
        year++;
    } else {
        week++;
    }
    
    // Double-check the result is valid
    if (!isValidWeek(week, year)) {
        console.error('Invalid week calculation', { week, year });
        return;
    }
    
    currentUrl.searchParams.set('week', week);
    currentUrl.searchParams.set('year', year);
    window.location.href = currentUrl.toString();
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

    console.log('Fixed Date:', fixedDate); // Debug log
    console.log('Fixed Time:', fixedTime); // Debug log

    if (!fixedDate || !fixedTime) {
        alert('Veuillez sélectionner la date et l\'heure');
        return;
    }

    // Combine date and time into a proper format
    const fixedDateTime = `${fixedDate} ${fixedTime}`;
    console.log('Fixed DateTime:', fixedDateTime); // Debug log

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
    const operatorId = document.getElementById('operatorSelect').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reason = document.getElementById('absenceReason').value;
    
    if (!operatorId || !startDate || !endDate || !reason) {
        alert('Veuillez remplir tous les champs');
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
            document.getElementById('operatorStatus').value = 'active';
            document.querySelector('#addOperatorModal .modal-title').textContent = 'Ajouter un opérateur';
            document.querySelector('#addOperatorModal .btn-primary').textContent = 'Enregistrer';
            document.querySelector('#addOperatorModal .btn-primary').onclick = saveOperator;
        }
    });
});

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