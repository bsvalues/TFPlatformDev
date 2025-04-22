/**
 * UI functionality for TerraFusion Platform
 */

// Document ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    // Check authentication status
    checkAuthStatus();
    
    // Register event handlers
    registerEventHandlers();
});

/**
 * Register event handlers for UI elements
 */
function registerEventHandlers() {
    // Login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Search form
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
    
    // Data sync form
    const syncForm = document.getElementById('sync-form');
    if (syncForm) {
        syncForm.addEventListener('submit', handleDataSync);
    }
    
    // Correction form
    const correctionForm = document.getElementById('correction-form');
    if (correctionForm) {
        correctionForm.addEventListener('submit', handleCorrectionSubmit);
    }
    
    // Natural language query form
    const queryForm = document.getElementById('nlq-form');
    if (queryForm) {
        queryForm.addEventListener('submit', handleNaturalLanguageQuery);
    }
    
    // Map layer toggle buttons
    const layerToggles = document.querySelectorAll('.layer-toggle');
    layerToggles.forEach(toggle => {
        toggle.addEventListener('change', handleLayerToggle);
    });
}

/**
 * Check authentication status
 */
async function checkAuthStatus() {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Token is valid
                updateUIForAuthenticatedUser();
                
                // Get user info
                const userResponse = await fetch('/api/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    updateUserInfo(userData);
                }
            } else {
                // Token is invalid
                localStorage.removeItem('auth_token');
                updateUIForUnauthenticatedUser();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            localStorage.removeItem('auth_token');
            updateUIForUnauthenticatedUser();
        }
    } else {
        updateUIForUnauthenticatedUser();
    }
}

/**
 * Update UI for authenticated user
 */
function updateUIForAuthenticatedUser() {
    // Show authenticated elements
    document.querySelectorAll('.auth-required').forEach(el => {
        el.classList.remove('d-none');
    });
    
    // Hide unauthenticated elements
    document.querySelectorAll('.auth-not-required').forEach(el => {
        el.classList.add('d-none');
    });
}

/**
 * Update UI for unauthenticated user
 */
function updateUIForUnauthenticatedUser() {
    // Hide authenticated elements
    document.querySelectorAll('.auth-required').forEach(el => {
        el.classList.add('d-none');
    });
    
    // Show unauthenticated elements
    document.querySelectorAll('.auth-not-required').forEach(el => {
        el.classList.remove('d-none');
    });
}

/**
 * Update user info in the UI
 * @param {object} userData - User data
 */
function updateUserInfo(userData) {
    const userNameElement = document.getElementById('user-name');
    if (userNameElement) {
        userNameElement.textContent = userData.username;
    }
    
    const userEmailElement = document.getElementById('user-email');
    if (userEmailElement && userData.email) {
        userEmailElement.textContent = userData.email;
    }
    
    // Update admin-only elements
    if (userData.is_superuser) {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.classList.remove('d-none');
        });
    }
}

/**
 * Handle login form submission
 * @param {Event} event - Form submit event
 */
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showErrorMessage('Please enter both username and password');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('auth_token', data.access_token);
            
            showSuccessMessage('Login successful');
            
            // Redirect to home page or refresh
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            const errorData = await response.json();
            showErrorMessage(`Login failed: ${errorData.detail || 'Invalid credentials'}`);
        }
    } catch (error) {
        console.error('Login error:', error);
        showErrorMessage(`Login failed: ${error.message}`);
    }
}

/**
 * Handle logout
 */
function handleLogout() {
    localStorage.removeItem('auth_token');
    showSuccessMessage('Logout successful');
    
    // Update UI
    updateUIForUnauthenticatedUser();
    
    // Redirect to login page
    setTimeout(() => {
        window.location.href = '/';
    }, 1000);
}

/**
 * Handle search form submission
 * @param {Event} event - Form submit event
 */
function handleSearch(event) {
    event.preventDefault();
    
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;
    
    const query = searchInput.value.trim();
    if (!query) return;
    
    // If map is available, search on map
    if (typeof searchLocation === 'function') {
        searchLocation(query);
    }
}

/**
 * Handle data sync form submission
 * @param {Event} event - Form submit event
 */
async function handleDataSync(event) {
    event.preventDefault();
    
    const datasetSelect = document.getElementById('dataset-select');
    if (!datasetSelect) return;
    
    const dataset = datasetSelect.value;
    const fullSync = document.getElementById('full-sync-checkbox')?.checked || false;
    
    if (!dataset) {
        showErrorMessage('Please select a dataset');
        return;
    }
    
    try {
        // Show loading state
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...`;
        
        // Call API
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`/api/etl/sync?dataset=${encodeURIComponent(dataset)}&full_sync=${fullSync}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Reset button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        if (response.ok) {
            const data = await response.json();
            
            // Show result
            showSuccessMessage(`Sync completed: ${data.message}`);
            
            // Update sync status UI
            updateSyncStatus(data);
        } else {
            const errorData = await response.json();
            showErrorMessage(`Sync failed: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Sync error:', error);
        showErrorMessage(`Sync failed: ${error.message}`);
    }
}

/**
 * Update sync status UI
 * @param {object} data - Sync result data
 */
function updateSyncStatus(data) {
    const statusContainer = document.getElementById('sync-status');
    if (!statusContainer) return;
    
    // Create status card
    let statusClass = 'success';
    if (data.status === 'partial') {
        statusClass = 'warning';
    } else if (data.status === 'failed') {
        statusClass = 'danger';
    }
    
    const statusCard = document.createElement('div');
    statusCard.className = `card mb-3 border-${statusClass}`;
    statusCard.innerHTML = `
        <div class="card-header bg-${statusClass} bg-opacity-10">
            <h5 class="card-title mb-0">Sync Result: ${data.status.toUpperCase()}</h5>
        </div>
        <div class="card-body">
            <p>${data.message}</p>
            <h6 class="mt-3">Details:</h6>
            <ul class="list-group list-group-flush">
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Records Processed
                    <span class="badge bg-primary rounded-pill">${data.details.records_processed}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Records Added
                    <span class="badge bg-success rounded-pill">${data.details.records_added}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Records Updated
                    <span class="badge bg-info rounded-pill">${data.details.records_updated}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Records Failed
                    <span class="badge bg-danger rounded-pill">${data.details.records_failed}</span>
                </li>
            </ul>
            <p class="mt-3 mb-0 text-muted small">Completed at: ${new Date().toLocaleString()}</p>
        </div>
    `;
    
    // Add to status container
    statusContainer.prepend(statusCard);
    
    // Limit to 5 status cards
    const statusCards = statusContainer.querySelectorAll('.card');
    if (statusCards.length > 5) {
        Array.from(statusCards)
            .slice(5)
            .forEach(card => card.remove());
    }
}

/**
 * Handle correction form submission
 * @param {Event} event - Form submit event
 */
async function handleCorrectionSubmit(event) {
    event.preventDefault();
    
    const featureId = document.getElementById('feature-id').value;
    const correctionType = document.getElementById('correction-type').value;
    const correctionValue = document.getElementById('correction-value').value;
    const reason = document.getElementById('correction-reason').value;
    
    if (!featureId || !correctionType || !correctionValue) {
        showErrorMessage('Please fill in all required fields');
        return;
    }
    
    try {
        // Show loading state
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...`;
        
        // Parse correction value as JSON
        let correctedValue = {};
        try {
            correctedValue = JSON.parse(correctionValue);
        } catch (e) {
            // If not valid JSON, use as string
            correctedValue = { [correctionType]: correctionValue };
        }
        
        // Call API
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`/api/audit/correction?feature_id=${encodeURIComponent(featureId)}&correction_type=${encodeURIComponent(correctionType)}&reason=${encodeURIComponent(reason || '')}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(correctedValue)
        });
        
        // Reset button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        if (response.ok) {
            const data = await response.json();
            
            // Show result
            showSuccessMessage(`Correction submitted with status: ${data.status}`);
            
            // Clear form
            event.target.reset();
            
            // Update corrections list if available
            if (typeof loadCorrections === 'function') {
                loadCorrections();
            }
        } else {
            const errorData = await response.json();
            showErrorMessage(`Submission failed: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Correction submission error:', error);
        showErrorMessage(`Submission failed: ${error.message}`);
    }
}

/**
 * Handle natural language query form submission
 * @param {Event} event - Form submit event
 */
async function handleNaturalLanguageQuery(event) {
    event.preventDefault();
    
    const queryInput = document.getElementById('nlq-input');
    if (!queryInput) return;
    
    const query = queryInput.value.trim();
    if (!query) {
        showErrorMessage('Please enter a query');
        return;
    }
    
    try {
        // Show loading state
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...`;
        
        // Call API
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`/api/ai/query?query=${encodeURIComponent(query)}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Reset button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        if (response.ok) {
            const data = await response.json();
            
            // Show result
            showQueryResult(data);
        } else {
            const errorData = await response.json();
            showErrorMessage(`Query failed: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Natural language query error:', error);
        showErrorMessage(`Query failed: ${error.message}`);
    }
}

/**
 * Show natural language query result
 * @param {object} data - Query result data
 */
function showQueryResult(data) {
    const resultContainer = document.getElementById('query-result');
    if (!resultContainer) return;
    
    // Create result card
    const resultCard = document.createElement('div');
    resultCard.className = 'card mb-3';
    resultCard.innerHTML = `
        <div class="card-header bg-primary bg-opacity-10">
            <h5 class="card-title mb-0">Query Result</h5>
        </div>
        <div class="card-body">
            <p><strong>Query:</strong> ${data.query}</p>
            <p><strong>Explanation:</strong> ${data.explanation || 'No explanation provided'}</p>
            ${data.sql_generated ? `
            <div class="mt-3">
                <h6>Generated SQL:</h6>
                <pre class="bg-dark text-light p-3 rounded"><code>${data.sql_generated}</code></pre>
            </div>
            ` : ''}
            ${data.result && data.result.features ? `
            <div class="mt-3">
                <h6>Found ${data.result.features.length} features</h6>
                <button class="btn btn-sm btn-primary" id="show-result-btn">
                    Show on Map
                </button>
            </div>
            ` : ''}
            <p class="mt-3 mb-0 text-muted small">Processed at: ${new Date().toLocaleString()}</p>
        </div>
    `;
    
    // Add to result container
    resultContainer.innerHTML = '';
    resultContainer.appendChild(resultCard);
    
    // Add event handler for show on map button
    const showResultBtn = document.getElementById('show-result-btn');
    if (showResultBtn && data.result) {
        showResultBtn.addEventListener('click', () => {
            if (typeof map !== 'undefined' && map) {
                // Add result to map
                const source = {
                    type: 'geojson',
                    data: data.result
                };
                
                // Check if source already exists
                if (map.getSource('query-result-source')) {
                    map.removeSource('query-result-source');
                }
                
                // Check if layer already exists
                if (map.getLayer('query-result-layer')) {
                    map.removeLayer('query-result-layer');
                }
                
                // Add source and layer
                map.addSource('query-result-source', source);
                map.addLayer({
                    id: 'query-result-layer',
                    type: 'fill',
                    source: 'query-result-source',
                    paint: {
                        'fill-color': '#088',
                        'fill-opacity': 0.8,
                        'fill-outline-color': '#044'
                    }
                });
                
                // Zoom to results
                const bounds = getBoundsFromGeoJSON(data.result);
                if (bounds) {
                    map.fitBounds(bounds, { padding: 50 });
                }
                
                showSuccessMessage('Query results shown on map');
            }
        });
    }
}

/**
 * Handle layer toggle change
 * @param {Event} event - Change event
 */
function handleLayerToggle(event) {
    const layerId = event.target.dataset.layerId;
    const isChecked = event.target.checked;
    
    if (!layerId || typeof map === 'undefined' || !map) return;
    
    if (isChecked) {
        // Show layer
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', 'visible');
        } else {
            // Load layer if not already loaded
            loadLayer(layerId);
        }
    } else {
        // Hide layer
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', 'none');
        }
    }
}

/**
 * Load a layer by ID
 * @param {string} layerId - Layer ID
 */
function loadLayer(layerId) {
    // This is a placeholder for actual layer loading logic
    // In a real application, this would load the layer data from the server
    
    console.log(`Loading layer: ${layerId}`);
    
    // Example layer loading
    if (typeof loadGeoJSONLayer === 'function') {
        const url = `/api/tiles/features?layer_id=${encodeURIComponent(layerId)}`;
        loadGeoJSONLayer(url, {
            id: layerId,
            type: 'fill',
            paint: {
                'fill-color': '#088',
                'fill-opacity': 0.8,
                'fill-outline-color': '#044'
            }
        });
    }
}

/**
 * Show error message in the UI
 * @param {string} message - Error message
 */
function showErrorMessage(message) {
    const messageContainer = document.getElementById('message-container');
    if (!messageContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messageContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

/**
 * Show success message in the UI
 * @param {string} message - Success message
 */
function showSuccessMessage(message) {
    const messageContainer = document.getElementById('message-container');
    if (!messageContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messageContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

/**
 * Show info message in the UI
 * @param {string} message - Info message
 */
function showInfoMessage(message) {
    const messageContainer = document.getElementById('message-container');
    if (!messageContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-info alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messageContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}
