/**
 * MapLibre GL JS integration for TerraFusion Platform
 */

// Global map instance
let map = null;
let mapLoaded = false;
let activeLayers = [];

/**
 * Initialize the map
 * @param {string} containerId - The ID of the container element
 * @param {object} options - Additional options
 */
function initializeMap(containerId, options = {}) {
    // Default options
    const defaultOptions = {
        center: [-95.7129, 37.0902],  // Default to US center
        zoom: 4,
        style: '/api/tiles/styles/default',
        container: containerId
    };
    
    // Merge options
    const mapOptions = { ...defaultOptions, ...options };
    
    // Check if MapLibre GL JS is loaded
    if (!maplibregl) {
        console.error('MapLibre GL JS not loaded');
        showErrorMessage('Map library failed to load. Please refresh the page.');
        return;
    }
    
    try {
        // Create the map
        map = new maplibregl.Map(mapOptions);
        
        // Add navigation controls
        map.addControl(new maplibregl.NavigationControl(), 'top-right');
        map.addControl(new maplibregl.ScaleControl(), 'bottom-left');
        
        // Add geolocation control
        map.addControl(
            new maplibregl.GeolocateControl({
                positionOptions: {
                    enableHighAccuracy: true
                },
                trackUserLocation: true
            }),
            'top-right'
        );
        
        // Handle map events
        map.on('load', () => {
            mapLoaded = true;
            console.log('Map loaded');
            document.dispatchEvent(new Event('map:loaded'));
        });
        
        map.on('error', (e) => {
            console.error('Map error:', e);
            showErrorMessage(`Map error: ${e.error.message || 'Unknown error'}`);
        });
        
        return map;
    } catch (error) {
        console.error('Error initializing map:', error);
        showErrorMessage(`Failed to initialize map: ${error.message}`);
        return null;
    }
}

/**
 * Load and display GeoJSON data on the map
 * @param {string} url - URL to fetch GeoJSON data
 * @param {object} options - Layer options
 */
function loadGeoJSONLayer(url, options = {}) {
    if (!map || !mapLoaded) {
        console.error('Map not initialized');
        return;
    }
    
    // Default options
    const defaultOptions = {
        id: `layer-${Date.now()}`,
        type: 'fill',
        paint: {
            'fill-color': '#088',
            'fill-opacity': 0.8
        },
        layout: {},
        filter: null
    };
    
    // Merge options
    const layerOptions = { ...defaultOptions, ...options };
    
    try {
        // Add source if it doesn't exist
        const sourceId = `source-${layerOptions.id}`;
        if (!map.getSource(sourceId)) {
            map.addSource(sourceId, {
                type: 'geojson',
                data: url
            });
        }
        
        // Add layer
        const layerConfig = {
            id: layerOptions.id,
            type: layerOptions.type,
            source: sourceId,
            paint: layerOptions.paint,
            layout: layerOptions.layout
        };
        
        // Add filter if provided
        if (layerOptions.filter) {
            layerConfig.filter = layerOptions.filter;
        }
        
        // Remove layer if it already exists
        if (map.getLayer(layerOptions.id)) {
            map.removeLayer(layerOptions.id);
        }
        
        map.addLayer(layerConfig);
        
        // Add to active layers
        activeLayers.push(layerOptions.id);
        
        // Add hover effect for interactive layers
        if (layerOptions.interactive !== false) {
            map.on('mouseenter', layerOptions.id, () => {
                map.getCanvas().style.cursor = 'pointer';
            });
            
            map.on('mouseleave', layerOptions.id, () => {
                map.getCanvas().style.cursor = '';
            });
            
            // Add click handler for feature details
            map.on('click', layerOptions.id, (e) => {
                const features = map.queryRenderedFeatures(e.point, { layers: [layerOptions.id] });
                if (features.length > 0) {
                    showFeatureDetails(features[0]);
                }
            });
        }
        
        return layerOptions.id;
    } catch (error) {
        console.error('Error loading GeoJSON layer:', error);
        showErrorMessage(`Failed to load map layer: ${error.message}`);
        return null;
    }
}

/**
 * Create a buffer around a point or feature
 * @param {array|object} geometry - Point coordinates [lng, lat] or GeoJSON feature
 * @param {number} distance - Buffer distance in meters
 * @param {object} options - Layer options for the buffer
 */
async function createBuffer(geometry, distance, options = {}) {
    if (!map || !mapLoaded) {
        console.error('Map not initialized');
        return;
    }
    
    try {
        let geometryString = '';
        
        // Convert input to expected format
        if (Array.isArray(geometry)) {
            // Point coordinates
            geometryString = `POINT(${geometry[0]} ${geometry[1]})`;
        } else if (geometry.geometry) {
            // GeoJSON feature
            geometryString = JSON.stringify(geometry.geometry);
        } else {
            throw new Error('Invalid geometry format');
        }
        
        // Call API to create buffer
        const response = await fetch(`/api/ai/analyze?analysis_type=buffer&geometry=${encodeURIComponent(geometryString)}&distance=${distance}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Default options for buffer layer
        const defaultOptions = {
            id: `buffer-${Date.now()}`,
            type: 'fill',
            paint: {
                'fill-color': '#f28cb1',
                'fill-opacity': 0.4,
                'fill-outline-color': '#f28cb1'
            }
        };
        
        // Merge options
        const layerOptions = { ...defaultOptions, ...options };
        
        // Add buffer to map
        const sourceId = `source-${layerOptions.id}`;
        map.addSource(sourceId, {
            type: 'geojson',
            data: data.result
        });
        
        map.addLayer({
            id: layerOptions.id,
            type: layerOptions.type,
            source: sourceId,
            paint: layerOptions.paint
        });
        
        // Add to active layers
        activeLayers.push(layerOptions.id);
        
        // Fit map to buffer (with padding)
        const bufferBounds = getBoundsFromGeoJSON(data.result);
        if (bufferBounds) {
            map.fitBounds(bufferBounds, { padding: 50 });
        }
        
        return layerOptions.id;
    } catch (error) {
        console.error('Error creating buffer:', error);
        showErrorMessage(`Failed to create buffer: ${error.message}`);
        return null;
    }
}

/**
 * Get bounds from GeoJSON data
 * @param {object} geojson - GeoJSON object
 * @returns {array} Bounds as [[minLng, minLat], [maxLng, maxLat]]
 */
function getBoundsFromGeoJSON(geojson) {
    if (!geojson) return null;
    
    let minLng = 180;
    let minLat = 90;
    let maxLng = -180;
    let maxLat = -90;
    
    function processCoordinates(coords, geomType) {
        if (geomType === 'Point') {
            minLng = Math.min(minLng, coords[0]);
            maxLng = Math.max(maxLng, coords[0]);
            minLat = Math.min(minLat, coords[1]);
            maxLat = Math.max(maxLat, coords[1]);
        } else if (geomType === 'LineString' || geomType === 'MultiPoint') {
            coords.forEach(coord => {
                minLng = Math.min(minLng, coord[0]);
                maxLng = Math.max(maxLng, coord[0]);
                minLat = Math.min(minLat, coord[1]);
                maxLat = Math.max(maxLat, coord[1]);
            });
        } else if (geomType === 'Polygon' || geomType === 'MultiLineString') {
            coords.forEach(line => {
                line.forEach(coord => {
                    minLng = Math.min(minLng, coord[0]);
                    maxLng = Math.max(maxLng, coord[0]);
                    minLat = Math.min(minLat, coord[1]);
                    maxLat = Math.max(maxLat, coord[1]);
                });
            });
        } else if (geomType === 'MultiPolygon') {
            coords.forEach(poly => {
                poly.forEach(line => {
                    line.forEach(coord => {
                        minLng = Math.min(minLng, coord[0]);
                        maxLng = Math.max(maxLng, coord[0]);
                        minLat = Math.min(minLat, coord[1]);
                        maxLat = Math.max(maxLat, coord[1]);
                    });
                });
            });
        }
    }
    
    // Process feature collection
    if (geojson.type === 'FeatureCollection') {
        geojson.features.forEach(feature => {
            processCoordinates(feature.geometry.coordinates, feature.geometry.type);
        });
    } 
    // Process single feature
    else if (geojson.type === 'Feature') {
        processCoordinates(geojson.geometry.coordinates, geojson.geometry.type);
    }
    // Process geometry
    else {
        processCoordinates(geojson.coordinates, geojson.type);
    }
    
    if (minLng === 180 || minLat === 90 || maxLng === -180 || maxLat === -90) {
        return null;
    }
    
    return [[minLng, minLat], [maxLng, maxLat]];
}

/**
 * Remove a layer and its source from the map
 * @param {string} layerId - ID of the layer to remove
 */
function removeLayer(layerId) {
    if (!map || !mapLoaded) {
        console.error('Map not initialized');
        return;
    }
    
    try {
        // Check if layer exists
        if (map.getLayer(layerId)) {
            // Get source ID
            const sourceId = map.getLayer(layerId).source;
            
            // Remove layer
            map.removeLayer(layerId);
            
            // Remove source if it exists
            if (sourceId && map.getSource(sourceId)) {
                map.removeSource(sourceId);
            }
            
            // Remove from active layers
            const index = activeLayers.indexOf(layerId);
            if (index > -1) {
                activeLayers.splice(index, 1);
            }
            
            console.log(`Removed layer: ${layerId}`);
        } else {
            console.warn(`Layer not found: ${layerId}`);
        }
    } catch (error) {
        console.error('Error removing layer:', error);
    }
}

/**
 * Clear all data layers from the map
 */
function clearLayers() {
    if (!map || !mapLoaded) {
        console.error('Map not initialized');
        return;
    }
    
    try {
        // Make a copy of the array since we'll be modifying it
        const layersToRemove = [...activeLayers];
        
        // Remove each layer
        layersToRemove.forEach(layerId => {
            removeLayer(layerId);
        });
        
        console.log('Cleared all layers');
    } catch (error) {
        console.error('Error clearing layers:', error);
    }
}

/**
 * Show a popup with feature details
 * @param {object} feature - GeoJSON feature
 */
function showFeatureDetails(feature) {
    if (!map || !feature) return;
    
    try {
        // Get feature center
        const coordinates = getCenterFromFeature(feature);
        if (!coordinates) return;
        
        // Create popup content
        const properties = feature.properties || {};
        let content = '<div class="feature-popup">';
        content += `<h5>${properties.name || 'Feature Details'}</h5>`;
        content += '<table class="table table-sm">';
        
        // Add properties
        for (const [key, value] of Object.entries(properties)) {
            // Skip internal or complex properties
            if (key === 'id' || key === 'name' || typeof value === 'object') continue;
            
            content += `<tr><th>${key}</th><td>${value}</td></tr>`;
        }
        
        content += '</table>';
        
        // Add actions
        content += '<div class="popup-actions mt-2">';
        content += `<button class="btn btn-sm btn-primary me-2" onclick="createBuffer([${coordinates[0]}, ${coordinates[1]}], 1000)">Buffer (1km)</button>`;
        content += `<button class="btn btn-sm btn-outline-secondary" onclick="submitCorrection('${properties.id}')">Submit Correction</button>`;
        content += '</div>';
        content += '</div>';
        
        // Create and add popup
        new maplibregl.Popup()
            .setLngLat(coordinates)
            .setHTML(content)
            .addTo(map);
    } catch (error) {
        console.error('Error showing feature details:', error);
    }
}

/**
 * Get center coordinates from a feature
 * @param {object} feature - GeoJSON feature
 * @returns {array} [lng, lat] coordinates
 */
function getCenterFromFeature(feature) {
    if (!feature || !feature.geometry) return null;
    
    const type = feature.geometry.type;
    const coords = feature.geometry.coordinates;
    
    if (type === 'Point') {
        return coords;
    } else if (type === 'LineString') {
        // Return midpoint of line
        const midIndex = Math.floor(coords.length / 2);
        return coords[midIndex];
    } else if (type === 'Polygon') {
        // Use the first exterior ring for center calculation
        const exterior = coords[0];
        const bounds = getBoundsFromCoordinates(exterior);
        return [
            (bounds[0][0] + bounds[1][0]) / 2,
            (bounds[0][1] + bounds[1][1]) / 2
        ];
    } else {
        // For other geometry types, try to get centroid
        return getCentroid(feature.geometry);
    }
}

/**
 * Get bounds from coordinates array
 * @param {array} coordinates - Array of [lng, lat] coordinates
 * @returns {array} Bounds as [[minLng, minLat], [maxLng, maxLat]]
 */
function getBoundsFromCoordinates(coordinates) {
    if (!coordinates || !coordinates.length) return null;
    
    let minLng = 180;
    let minLat = 90;
    let maxLng = -180;
    let maxLat = -90;
    
    coordinates.forEach(coord => {
        minLng = Math.min(minLng, coord[0]);
        maxLng = Math.max(maxLng, coord[0]);
        minLat = Math.min(minLat, coord[1]);
        maxLat = Math.max(maxLat, coord[1]);
    });
    
    return [[minLng, minLat], [maxLng, maxLat]];
}

/**
 * Calculate centroid of a geometry
 * @param {object} geometry - GeoJSON geometry
 * @returns {array} [lng, lat] coordinates
 */
function getCentroid(geometry) {
    if (!geometry) return null;
    
    const type = geometry.type;
    const coords = geometry.coordinates;
    
    if (type === 'Point') {
        return coords;
    } else if (type === 'LineString') {
        // Simple center of line
        let sumX = 0;
        let sumY = 0;
        
        coords.forEach(coord => {
            sumX += coord[0];
            sumY += coord[1];
        });
        
        return [sumX / coords.length, sumY / coords.length];
    } else if (type === 'Polygon') {
        // Calculate centroid of polygon
        const exterior = coords[0];
        let sumX = 0;
        let sumY = 0;
        
        exterior.forEach(coord => {
            sumX += coord[0];
            sumY += coord[1];
        });
        
        return [sumX / exterior.length, sumY / exterior.length];
    } else {
        // For complex geometries, use first coordinate
        if (type === 'MultiPoint') {
            return coords[0];
        } else if (type === 'MultiLineString') {
            return coords[0][0];
        } else if (type === 'MultiPolygon') {
            return coords[0][0][0];
        }
    }
    
    return null;
}

/**
 * Handle map search
 * @param {string} query - Search query
 */
async function searchLocation(query) {
    if (!query) return;
    
    try {
        // For simplicity, this uses a mock geocoding response
        // In production, this would use a real geocoding service
        
        console.log(`Searching for: ${query}`);
        showInfoMessage(`Searching for: ${query}...`);
        
        // Simulate API call with timeout
        setTimeout(() => {
            // Fly to a default location for demo purposes
            map.flyTo({
                center: [-95.7129, 37.0902],
                zoom: 12,
                essential: true
            });
            
            // Show success message
            showSuccessMessage(`Found location: ${query}`);
        }, 1000);
    } catch (error) {
        console.error('Error searching location:', error);
        showErrorMessage(`Search failed: ${error.message}`);
    }
}

/**
 * Get authentication token from localStorage
 * @returns {string} Authentication token
 */
function getAuthToken() {
    return localStorage.getItem('auth_token') || '';
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

/**
 * Submit a correction for a feature
 * @param {string} featureId - ID of the feature to correct
 */
function submitCorrection(featureId) {
    // Redirect to the audit page with feature ID
    window.location.href = `/audit?feature_id=${featureId}`;
}
