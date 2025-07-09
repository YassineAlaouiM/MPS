// History Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality
    initializeSearch();
    
    // Initialize filter functionality
    initializeFilter();
    
    // Initialize save today history functionality
    initializeSaveTodayHistory();
    
    // Initialize date range functionality
    initializeDateRange();
    
    // Add smooth scrolling for better UX
    addSmoothScrolling();
});

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('historySearch');
    if (!searchInput) return;
  
    searchInput.addEventListener('input', function() {
      const searchTerm = this.value.toLowerCase().trim();
      const historyEntries = document.querySelectorAll('.history-entry');
  
      historyEntries.forEach(entry => {
        const machineCards = entry.querySelectorAll('.machine-card');
        let hasMatch = false;
  
        machineCards.forEach(card => {
          const cardText = card.textContent.toLowerCase();
  
          if (searchTerm && cardText.includes(searchTerm)) {
            card.style.display = 'block';
            hasMatch = true;
          } else if (searchTerm) {
            card.style.display = 'none';
          } else {
            card.style.display = 'block';
          }
        });
  
        // Show/hide the entire entry based on whether any of its cards match
        if (searchTerm) {
          entry.style.display = hasMatch ? 'block' : 'none';
        } else {
          entry.style.display = 'block';
        }
      });
  
      updateEmptyStateMessage();
    });
  }
  
  // Helper to escape special regex characters in search term
  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  
  // Stub for your empty state message update function
  function updateEmptyStateMessage() {
    const historyEntries = document.querySelectorAll('.history-entry');
    const emptyState = document.getElementById('emptyStateMessage'); // Assume this exists
    const anyVisible = Array.from(historyEntries).some(entry => entry.style.display !== 'none');
  
    if (emptyState) {
      emptyState.style.display = anyVisible ? 'none' : 'block';
    }
  }
  

// Filter functionality
function initializeFilter() {
    const dateFilter = document.getElementById('dateFilter');
    if (!dateFilter) return;
    
    dateFilter.addEventListener('change', function() {
        const selectedDate = this.value;
        const historyEntries = document.querySelectorAll('.history-entry');
        
        historyEntries.forEach(entry => {
            const entryDate = entry.getAttribute('data-date');
            // FIX: Show all entries if 'all' is selected
            if (selectedDate === 'all' || !selectedDate) {
                entry.style.display = 'block';
                entry.classList.remove('hidden');
            } else if (entryDate === selectedDate) {
                entry.style.display = 'block';
                entry.classList.remove('hidden');
            } else {
                entry.style.display = 'none';
                entry.classList.add('hidden');
            }
        });
        
        // Show/hide empty state message
        updateEmptyStateMessage();
    });
}

// Save today's history functionality
function initializeSaveTodayHistory() {
    const saveButtons = [
        document.getElementById('saveTodayHistory'),
        document.getElementById('saveTodayHistoryEmpty')
    ];
    
    saveButtons.forEach(button => {
        if (button) {
            button.addEventListener('click', saveTodayHistory);
        }
    });
}

// Save today's history
async function saveTodayHistory() {
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    try {
        // Show loading modal
        loadingModal.show();
        
        // Disable save buttons
        const saveButtons = document.querySelectorAll('#saveTodayHistory, #saveTodayHistoryEmpty');
        saveButtons.forEach(button => {
            if (button) button.disabled = true;
        });
        
        // Make API call
        const response = await fetch('/api/save_today_history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success message
            showNotification('Succès!', result.message, 'success');
            
            // Reload page to show new data
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            // Show error message
            showNotification('Erreur!', result.message, 'error');
        }
        
    } catch (error) {
        console.error('Error saving today\'s history:', error);
        showNotification('Erreur!', 'Une erreur est survenue lors de la sauvegarde.', 'error');
    } finally {
        // Hide loading modal
        loadingModal.hide();
        
        // Re-enable save buttons
        const saveButtons = document.querySelectorAll('#saveTodayHistory, #saveTodayHistoryEmpty');
        saveButtons.forEach(button => {
            if (button) button.disabled = false;
        });
    }
}

// Escape regex special characters
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Update empty state message
function updateEmptyStateMessage() {
    const visibleEntries = document.querySelectorAll('.history-entry:not([style*="display: none"])');
    const emptyState = document.querySelector('.empty-state');
    const timeline = document.querySelector('.timeline');
    
    if (visibleEntries.length === 0 && timeline) {
        if (emptyState) {
            emptyState.style.display = 'block';
        }
        timeline.style.display = 'none';
    } else {
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        if (timeline) {
            timeline.style.display = 'block';
        }
    }
}

// Show notification
function showNotification(title, message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    notification.innerHTML = `
        <strong>${title}</strong><br>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Date range functionality
function initializeDateRange() {
    // Set default date range if not already set
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    if (startDate && !startDate.value) {
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        startDate.value = thirtyDaysAgo.toISOString().split('T')[0];
    }
    
    if (endDate && !endDate.value) {
        const today = new Date();
        endDate.value = today.toISOString().split('T')[0];
    }
}

function filterByDateRange() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        showNotification('Erreur', 'Veuillez sélectionner une plage de dates', 'error');
        return;
    }
    
    if (startDate > endDate) {
        showNotification('Erreur', 'La date de début doit être antérieure à la date de fin', 'error');
        return;
    }
    
    // Redirect to history page with date range parameters
    const url = new URL(window.location);
    url.searchParams.set('start_date', startDate);
    url.searchParams.set('end_date', endDate);
    window.location.href = url.toString();
}

// Date picker functionality
function showDatePicker() {
    const datePickerModal = new bootstrap.Modal(document.getElementById('datePickerModal'));
    const saveDateInput = document.getElementById('saveDate');
    
    // Set default date to today
    const today = new Date();
    saveDateInput.value = today.toISOString().split('T')[0];
    
    datePickerModal.show();
}

function saveDateHistory() {
    const saveDate = document.getElementById('saveDate').value;
    
    if (!saveDate) {
        showNotification('Erreur', 'Veuillez sélectionner une date', 'error');
        return;
    }
    
    // Show loading modal
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    const datePickerModal = bootstrap.Modal.getInstance(document.getElementById('datePickerModal'));
    
    loadingModal.show();
    datePickerModal.hide();
    
    fetch('/api/save_daily_history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ date: saveDate })
    })
    .then(response => response.json())
    .then(data => {
        loadingModal.hide();
        if (data.success) {
            showNotification('Succès', data.message, 'success');
            // Reload page to show updated history
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification('Erreur', data.message, 'error');
        }
    })
    .catch(error => {
        loadingModal.hide();
        console.error('Error:', error);
        showNotification('Erreur', 'Une erreur est survenue lors de la sauvegarde', 'error');
    });
}

// Add smooth scrolling
function addSmoothScrolling() {
    // Smooth scroll to top when clicking on date headers
    const dateHeaders = document.querySelectorAll('.history-date');
    dateHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const entry = this.closest('.history-entry');
            if (entry) {
                entry.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
        });
        
        // Add cursor pointer to indicate clickable
        header.style.cursor = 'pointer';
        header.title = 'Cliquer pour faire défiler vers cette date';
    });
}

// Export functions for potential external use
window.HistoryPage = {
    saveTodayHistory,
    showNotification,
    updateEmptyStateMessage
}; 
