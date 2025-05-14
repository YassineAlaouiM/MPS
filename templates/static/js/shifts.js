let currentShiftId = null;

document.getElementById('shift-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const name = document.getElementById('shift-name').value;
    const startTime = document.getElementById('start-time').value;
    const endTime = document.getElementById('end-time').value;
    
    if (!name || !startTime || !endTime) {
        alert('Veuillez remplir tous les champs');
        return;
    }
    
    const url = currentShiftId ? `/api/shifts/${currentShiftId}` : '/api/shifts';
    const method = currentShiftId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            start_time: startTime,
            end_time: endTime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(currentShiftId ? 'Shift mis à jour avec succès' : 'Shift créé avec succès');
            location.reload();
        } else {
            alert('Erreur: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur ' + (currentShiftId ? 'de mise à jour' : 'de création') + ' du Shift');
    });
});

function editShift(shiftId) {
    currentShiftId = shiftId;
    const row = document.querySelector(`tr[data-shift-id="${shiftId}"]`);
    
    document.getElementById('form-title').textContent = 'Modifier le Shift';
    document.getElementById('submit-button').textContent = 'Mettre à jour le Shift';
    
    // Set form values
    document.getElementById('shift-name').value = row.cells[0].textContent;
    document.getElementById('start-time').value = row.cells[1].textContent;
    document.getElementById('end-time').value = row.cells[2].textContent;
}

function deleteShift(shiftId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce Shift?')) {
        fetch(`/api/shifts/${shiftId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Shift supprimé avec succès');
                location.reload();
            } else {
                alert('Erreur: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur de suppression du Shift');
        });
    }
}