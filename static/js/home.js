// Search functionality for each section
document.addEventListener('DOMContentLoaded', function() {
    // Initialize article fields visibility
    toggleArticleFields();
    toggleEditArticleFields();
    
    // Machine search
    const machineSearch = document.getElementById('machineSearch');
    machineSearch.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = document.querySelectorAll('#machinesBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const name = row.querySelector('td:first-child').textContent.toLowerCase();
            const isVisible = name.includes(searchText);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) hasVisibleRows = true;
        });
        
        document.getElementById('noMachinesFound').style.display = hasVisibleRows ? 'none' : 'block';
    });

    // Operator search
    const operatorSearch = document.getElementById('operatorSearch');
    operatorSearch.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = document.querySelectorAll('#operatorsBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const id = row.querySelector('td:first-child').textContent.toLowerCase();
            const name = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const arabicName = row.querySelector('td:nth-child(3)').textContent;
            const isVisible = id.includes(searchText) || 
                            name.includes(searchText) || 
                            arabicName.includes(searchText);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) hasVisibleRows = true;
        });
        
        document.getElementById('noOperatorsFound').style.display = hasVisibleRows ? 'none' : 'block';
    });

    // Non-functioning machine search
    const nonFunctioningMachineSearch = document.getElementById('nonFunctioningMachineSearch');
    nonFunctioningMachineSearch.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = document.querySelectorAll('#nonFunctioningMachinesBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const name = row.querySelector('td:first-child').textContent.toLowerCase();
            const issue = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const isVisible = name.includes(searchText) || issue.includes(searchText);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) hasVisibleRows = true;
        });
        
        document.getElementById('noNonFunctioningMachinesFound').style.display = hasVisibleRows ? 'none' : 'block';
    });

    // Absence search
    const absenceSearch = document.getElementById('absenceSearch');
    absenceSearch.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = document.querySelectorAll('#absencesBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const operatorName = row.querySelector('td:first-child').textContent.toLowerCase();
            const reason = row.querySelector('td:last-child').textContent.toLowerCase();
            const isVisible = operatorName.includes(searchText) || reason.includes(searchText);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) hasVisibleRows = true;
        });
        
        document.getElementById('noAbsencesFound').style.display = hasVisibleRows ? 'none' : 'block';
    });

    // Article search
    const articleSearch = document.getElementById('articleSearch');
    articleSearch.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = document.querySelectorAll('#articlesBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const name = row.querySelector('td:first-child').textContent.toLowerCase();
            const description = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const isVisible = name.includes(searchText) || description.includes(searchText);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) hasVisibleRows = true;
        });
        
        document.getElementById('noArticlesFound').style.display = hasVisibleRows ? 'none' : 'block';
    });

    // Production search
    const productionSearch = document.getElementById('productionSearch');
    productionSearch.addEventListener('input', function() {
        filterProduction();
    });

    // Add event listeners for date inputs
    document.getElementById('startDateSearch').addEventListener('change', filterProduction);
    document.getElementById('endDateSearch').addEventListener('change', filterProduction);
});

//Production search
function toggleDateSearch() {
    const dateInputs = document.getElementById('dateSearchInputs');
    const isChecked = document.getElementById('dateSearchToggle').checked;
    dateInputs.style.display = isChecked ? 'block' : 'none';
    
    if (!isChecked) {
        clearDateSearch();
    }
}

function clearDateSearch() {
    document.getElementById('startDateSearch').value = '';
    document.getElementById('endDateSearch').value = '';
    filterProduction();
}

function filterProduction() {
    const searchText = document.getElementById('productionSearch').value.toLowerCase();
    const startDate = document.getElementById('startDateSearch').value;
    const endDate = document.getElementById('endDateSearch').value;
    const isDateSearchEnabled = document.getElementById('dateSearchToggle').checked;
        const rows = document.querySelectorAll('#productionBody tr');
        let hasVisibleRows = false;
        
        rows.forEach(row => {
            const machineName = row.querySelector('td:first-child').textContent.toLowerCase();
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

// Function to toggle article and quantity fields based on machine type
function toggleArticleFields() {
    const machineSelect = document.getElementById('productionMachine');
    const articleFields = document.querySelectorAll('.article-field');
    
    if (machineSelect.selectedIndex > 0) {
        const selectedOption = machineSelect.options[machineSelect.selectedIndex];
        const machineType = selectedOption.getAttribute('data-type') === 'true'; // true = Service
        
        articleFields.forEach(field => {
            field.style.display = machineType ? 'none' : 'block';
        });
        
        // If machine is a service, clear article and quantity values
        if (machineType) {
            document.getElementById('productionArticle').value = '';
            document.getElementById('productionQuantity').value = '';
        }
    } else {
        // Show fields by default when no machine is selected
        articleFields.forEach(field => {
            field.style.display = 'block';
        });
    }
}

// Function to toggle article and quantity fields in edit modal
function toggleEditArticleFields() {
    const machineSelect = document.getElementById('editProductionMachine');
    const articleFields = document.querySelectorAll('.edit-article-field');
    
    if (machineSelect.selectedIndex > 0) {
        const selectedOption = machineSelect.options[machineSelect.selectedIndex];
        const machineType = selectedOption.getAttribute('data-type') === 'true'; // true = Service
        
        articleFields.forEach(field => {
            field.style.display = machineType ? 'none' : 'block';
        });
        
        // If machine is a service, clear article and quantity values
        if (machineType) {
            document.getElementById('editProductionArticle').value = '';
            document.getElementById('editProductionQuantity').value = '';
        }
    } else {
        // Show fields by default when no machine is selected
        articleFields.forEach(field => {
            field.style.display = 'block';
        });
    }
}
