// Camera Analyzer - Main JavaScript

// Show alert message
function showAlert(message, type = 'info') {
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.getElementById('alertArea').innerHTML = alertHTML;
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        $('.alert').alert('close');
    }, 5000);
}

// Initialize Analyzer
function initializeAnalyzer() {
    const data = {
        images_dir: document.getElementById('imagesDir').value,
        excel_file: document.getElementById('excelFile').value,
        max_workers: document.getElementById('maxWorkers').value
    };
    
    fetch('/initialize_analyzer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('✅ ' + data.message, 'success');
            $('#settingsModal').modal('hide');
        } else {
            showAlert('❌ ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('❌ Error: ' + error.message, 'danger');
    });
}

// Create New Session
function createNewSession() {
    fetch('/create_session', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('✅ New session created!', 'success');
            currentSessionId = data.session_id;
            updateSessionInfo();
            document.getElementById('endSessionBtn').disabled = false;
            refreshSessions();
            
            // Clear conversation
            document.getElementById('conversationHistory').innerHTML = `
                <div class="text-center text-muted p-5">
                    <i class="fas fa-comment-dots fa-3x mb-3"></i>
                    <h5>Start a Conversation!</h5>
                    <p>Ask your first question below.</p>
                </div>
            `;
        } else {
            showAlert('❌ Failed to create session', 'danger');
        }
    })
    .catch(error => {
        showAlert('❌ Error: ' + error.message, 'danger');
    });
}

// Load Session
function loadSession(sessionId) {
    fetch(`/get_session/${sessionId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentSessionId = sessionId;
            updateSessionInfo();
            renderConversation(data.session.conversation.queries);
            showAlert('✅ Session loaded successfully!', 'success');
            
            // Update active state in sidebar
            document.querySelectorAll('.session-item').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelector(`[data-session-id="${sessionId}"]`).classList.add('active');
        } else {
            showAlert('❌ Failed to load session', 'danger');
        }
    })
    .catch(error => {
        showAlert('❌ Error: ' + error.message, 'danger');
    });
}

// Send Query with Real-Time Streaming
function sendQuery() {
    const query = document.getElementById('queryInput').value.trim();
    const useBatch = document.getElementById('batchMode').checked;
    
    if (!query) {
        showAlert('⚠️ Please enter a query', 'warning');
        return;
    }
    
    if (!currentSessionId) {
        showAlert('⚠️ Please create a session first', 'warning');
        return;
    }
    
    // Show loading
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('sendBtn').disabled = true;
    
    // Add user message immediately
    addUserMessage(query);
    
    // Add progress log container
    addProgressLog();
    
    // Use Server-Sent Events for streaming
    const eventSource = new EventSource(`/analyze_stream?query=${encodeURIComponent(query)}`);
    
    let finalResults = null;
    let matchedResults = [];
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'start':
                    addProgressLogItem('🚀 ' + data.data.message);
                    break;
                
                case 'log':
                    addProgressLogItem(data.data.message);
                    break;
                
                case 'query_analysis':
                    addProgressLogItem('✅ ' + data.data.message);
                    break;
                
                case 'progress':
                    updateProgressBar(data.data.current, data.data.total);
                    break;
                
                case 'match':
                    // Show matched result immediately!
                    addProgressLogItem(data.data.message);
                    matchedResults.push(data.data.result);
                    
                    // Add match card immediately
                    addMatchCard(data.data.result);
                    break;
                
                case 'complete':
                    // Analysis complete
                    finalResults = data.data;
                    addProgressLogItem('🎉 Analysis complete!');
                    
                    // Close event source
                    eventSource.close();
                    
                    // Hide loading
                    document.getElementById('loadingSpinner').style.display = 'none';
                    document.getElementById('sendBtn').disabled = false;
                    
                    // Remove progress log after a delay
                    setTimeout(() => {
                        removeProgressLog();
                        
                        // Add final AI message with all results
                        addAIMessage(finalResults);
                        showAlert('✅ Analysis complete!', 'success');
                        document.getElementById('queryInput').value = '';
                        updateSessionInfo();
                    }, 2000);
                    break;
                
                case 'error':
                    addProgressLogItem('❌ ' + data.data.message);
                    eventSource.close();
                    document.getElementById('loadingSpinner').style.display = 'none';
                    document.getElementById('sendBtn').disabled = false;
                    showAlert('❌ Error: ' + data.data.message, 'danger');
                    break;
            }
        } catch (e) {
            console.error('Error parsing SSE data:', e);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        eventSource.close();
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('sendBtn').disabled = false;
        removeProgressLog();
        showAlert('❌ Connection error', 'danger');
    };
}

// Add progress log container with progress bar
function addProgressLog() {
    const progressHTML = `
        <div id="progressLogContainer" class="message ai-message">
            <div class="message-header">
                <i class="fas fa-cog fa-spin"></i> Processing
                <span class="message-time">Live</span>
            </div>
            <div class="progress-log-box">
                <div class="progress-log-header">
                    📊 Analysis Progress
                    <span id="progressPercent" class="badge bg-light text-dark ms-2">0%</span>
                </div>
                <div class="progress mb-2" style="height: 8px;">
                    <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
                         role="progressbar" style="width: 0%"></div>
                </div>
                <div id="progressLogContent" class="progress-log-content"></div>
            </div>
        </div>
        <div id="liveMatchesContainer"></div>
    `;
    
    const historyDiv = document.getElementById('conversationHistory');
    historyDiv.insertAdjacentHTML('beforeend', progressHTML);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

// Add progress log item (real-time)
function addProgressLogItem(message) {
    const progressContent = document.getElementById('progressLogContent');
    if (progressContent) {
        const item = document.createElement('div');
        item.className = 'progress-log-item';
        item.textContent = message;
        progressContent.appendChild(item);
        progressContent.scrollTop = progressContent.scrollHeight;
        
        // Scroll main chat to bottom
        const historyDiv = document.getElementById('conversationHistory');
        historyDiv.scrollTop = historyDiv.scrollHeight;
    }
}

// Update progress bar
function updateProgressBar(current, total) {
    const percent = Math.round((current / total) * 100);
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
    }
    
    if (progressPercent) {
        progressPercent.textContent = `${current}/${total} (${percent}%)`;
    }
}

// Add match card immediately
function addMatchCard(result) {
    const container = document.getElementById('liveMatchesContainer');
    if (!container) return;
    
    const cardHTML = `
        <div class="message ai-message live-match-card" style="animation: slideInRight 0.3s ease-out;">
            <div class="message-header">
                <i class="fas fa-check-circle text-success"></i> Match Found!
            </div>
            <div class="card border-success">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <img src="/get_image/${encodeURIComponent(result.filename)}" 
                                 class="img-fluid rounded" 
                                 alt="${escapeHtml(result.location_name)}"
                                 style="max-height: 150px; object-fit: cover;"
                                 onerror="this.src='https://via.placeholder.com/150?text=Image+Not+Found'">
                        </div>
                        <div class="col-md-8">
                            <h6 class="card-title text-success">
                                <i class="fas fa-map-marker-alt"></i> ${escapeHtml(result.location_name)}
                            </h6>
                            <p class="card-text small mb-1">
                                <strong>📍 District:</strong> ${escapeHtml(result.new_district)}<br>
                                <strong>🏘️ Mandal:</strong> ${escapeHtml(result.mandal)}<br>
                                <strong>📹 Camera IP:</strong> ${escapeHtml(result.camera_ip)}<br>
                                <strong>📊 Count:</strong> ${result.count}<br>
                                <strong>✅ Confidence:</strong> ${escapeHtml(result.confidence)}
                            </p>
                            <p class="card-text small text-muted">
                                ${escapeHtml(result.description)}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', cardHTML);
    
    // Scroll to show the new match
    const historyDiv = document.getElementById('conversationHistory');
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

// Remove progress log and live matches
function removeProgressLog() {
    const progressContainer = document.getElementById('progressLogContainer');
    if (progressContainer) {
        progressContainer.remove();
    }
    
    const matchesContainer = document.getElementById('liveMatchesContainer');
    if (matchesContainer) {
        matchesContainer.remove();
    }
}

// Simulate progress updates
let progressSimulator = null;
function simulateProgress() {
    const progressMessages = [
        "📷 Processing image 1/20...",
        "✅ Found match at location...",
        "📷 Processing image 5/20...",
        "✅ Found match at location...",
        "📷 Processing image 10/20...",
        "✅ Found match at location...",
        "📷 Processing image 15/20...",
        "📷 Processing image 20/20...",
        "📝 Generating comprehensive report...",
        "🎯 Finalizing results..."
    ];
    
    let index = 0;
    progressSimulator = setInterval(() => {
        const progressContent = document.getElementById('progressLogContent');
        if (progressContent && index < progressMessages.length) {
            progressContent.innerHTML += `<div class="progress-log-item">${progressMessages[index]}</div>`;
            progressContent.scrollTop = progressContent.scrollHeight;
            index++;
        } else {
            clearInterval(progressSimulator);
        }
    }, 800);
}

// Add user message to conversation
function addUserMessage(query) {
    const timestamp = new Date().toLocaleString();
    const messageHTML = `
        <div class="message user-message">
            <div class="message-header">
                <i class="fas fa-user"></i> You
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-body">${escapeHtml(query)}</div>
        </div>
    `;
    
    const historyDiv = document.getElementById('conversationHistory');
    if (historyDiv.querySelector('.text-muted')) {
        historyDiv.innerHTML = '';
    }
    historyDiv.insertAdjacentHTML('beforeend', messageHTML);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

// Add AI message to conversation
function addAIMessage(results) {
    const timestamp = new Date().toLocaleString();
    const isContextual = results.is_contextual || false;
    const badge = isContextual ? 
        '<span class="badge bg-info">🔗 Contextual</span>' : 
        '<span class="badge bg-primary">🔍 Full Analysis</span>';
    
    const detailsId = `details-new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Get matched images
    const matchedResults = (results.detailed_results || []).filter(r => r.match);
    
    // Build matched images HTML
    let matchedImagesHTML = '';
    if (matchedResults.length > 0) {
        matchedImagesHTML = `
            <div class="mb-4">
                <h6>📸 Matched Images</h6>
                <p class="text-muted small mb-2">Showing ${matchedResults.length} matched images</p>
                <div class="row g-3">
        `;
        
        matchedResults.forEach(result => {
            const filename = result.filename || result.image_name || '';
            const locationName = result.location_name || 'Unknown';
            const cameraIp = result.camera_ip || 'Unknown';
            const count = result.count || 'N/A';
            
            matchedImagesHTML += `
                <div class="col-md-4">
                    <div class="card image-card clickable-image" 
                         onclick="showImageFullscreen('/get_image/${encodeURIComponent(filename)}', '${escapeHtml(locationName)}', '${escapeHtml(cameraIp)}', '${count}')"
                         style="cursor: pointer;">
                        <img src="/get_image/${encodeURIComponent(filename)}" 
                             class="card-img-top" 
                             alt="${escapeHtml(locationName)}"
                             loading="lazy"
                             onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'p-3 text-center bg-light\\' style=\\'height:200px; display:flex; flex-direction:column; justify-content:center;\\'><i class=\\'fas fa-image fa-3x text-muted mb-2\\'></i><p class=\\'small text-muted mb-1\\'><strong>${escapeHtml(locationName).substring(0,30)}</strong></p><p class=\\'small text-muted mb-0\\'>📹 ${escapeHtml(cameraIp)}</p><p class=\\'small text-danger mb-0\\'>⚠️ Image: ${escapeHtml(filename)}</p></div>';">
                        <div class="card-body p-2">
                            <p class="mb-1 small"><strong>${escapeHtml(locationName).substring(0, 30)}</strong></p>
                            <p class="mb-0 text-muted small">📹 ${escapeHtml(cameraIp)}</p>
                            <p class="mb-0 text-muted small">📊 Count: ${count}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        matchedImagesHTML += '</div></div>';
    }
    
    // Extract key findings from final answer
    const finalAnswer = results.final_answer || '';
    let keyFindings = '';
    const keyFindingsMatch = finalAnswer.match(/Key Findings:([\s\S]*?)(?:Detailed Analysis|Conclusion|$)/);
    if (keyFindingsMatch && keyFindingsMatch[1]) {
        keyFindings = keyFindingsMatch[1].trim();
    }
    
    const messageHTML = `
        <div class="message ai-message">
            <div class="message-header">
                <i class="fas fa-robot"></i> AI Assistant
                ${badge}
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-body">
                <strong>Analyzed ${results.total_images} images, found ${results.matches_found} matches</strong>
            </div>
            
            <button class="btn btn-sm btn-primary mt-3" 
                    type="button" 
                    data-bs-toggle="collapse" 
                    data-bs-target="#${detailsId}">
                <i class="fas fa-eye"></i> View Details
            </button>
            
            <div class="collapse mt-3" id="${detailsId}">
                <div class="card details-card">
                    <div class="card-body">
                        <!-- Statistics -->
                        <div class="stats-grid mb-4">
                            <div class="stat-card-sm bg-gradient-primary">
                                <div class="stat-value">${results.total_images}</div>
                                <div class="stat-label">Images</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-success">
                                <div class="stat-value">${results.matches_found}</div>
                                <div class="stat-label">Matches</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-warning">
                                <div class="stat-value">${results.unique_locations}</div>
                                <div class="stat-label">Locations</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-info">
                                <div class="stat-value">${Math.round((results.matches_found / results.total_images) * 100)}%</div>
                                <div class="stat-label">Match Rate</div>
                            </div>
                        </div>
                        
                        <!-- Matched Images -->
                        ${matchedImagesHTML}
                        
                        <!-- Key Findings -->
                        ${keyFindings ? `
                        <div class="mb-4">
                            <h6>🎯 Key Findings</h6>
                            <div class="key-findings-box">
                                <pre class="mb-0">${escapeHtml(keyFindings)}</pre>
                            </div>
                        </div>
                        ` : ''}
                        
                        <!-- Full Answer -->
                        <div>
                            <h6>📋 Full Answer</h6>
                            <div class="full-answer-box">
                                <div class="full-answer-content">${formatFullAnswer(finalAnswer)}</div>
                            </div>
                        </div>
                        
                        <!-- Map (if available) -->
                        <div id="map-container-${detailsId}" class="mt-4"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const historyDiv = document.getElementById('conversationHistory');
    historyDiv.insertAdjacentHTML('beforeend', messageHTML);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    
    // Check if we need to create a map
    if (results.detailed_results && results.detailed_results.length > 0) {
        checkAndCreateMap(results, `map-container-${detailsId}`);
    }
}

// Render conversation
function renderConversation(queries) {
    const historyDiv = document.getElementById('conversationHistory');
    
    if (!queries || queries.length === 0) {
        historyDiv.innerHTML = `
            <div class="text-center text-muted p-5">
                <i class="fas fa-comment-dots fa-3x mb-3"></i>
                <h5>Start a Conversation!</h5>
                <p>Ask your first question below.</p>
            </div>
        `;
        return;
    }
    
    historyDiv.innerHTML = '';
    
    console.log(`Rendering ${queries.length} queries...`);
    
    queries.forEach((query, index) => {
        console.log(`Query ${index + 1}:`, query.user_query);
        
        // Add user message
        const timestamp = query.timestamp || new Date().toLocaleString();
        const userMessageHTML = `
            <div class="message user-message">
                <div class="message-header">
                    <i class="fas fa-user"></i> You
                    <span class="message-time">${timestamp}</span>
                </div>
                <div class="message-body">${escapeHtml(query.user_query)}</div>
            </div>
        `;
        historyDiv.insertAdjacentHTML('beforeend', userMessageHTML);
        
        // Add AI message with results
        if (query.results) {
            addAIMessageFromHistory(query.results, timestamp, index);
        }
    });
    
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

// Add AI message from history (preserves data)
function addAIMessageFromHistory(results, timestamp, index) {
    const isContextual = results.is_contextual || false;
    const badge = isContextual ? 
        '<span class="badge bg-info">🔗 Contextual</span>' : 
        '<span class="badge bg-primary">🔍 Full Analysis</span>';
    
    const detailsId = `details-history-${index}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Get matched images
    const matchedResults = (results.detailed_results || []).filter(r => r.match);
    
    // Build matched images HTML
    let matchedImagesHTML = '';
    if (matchedResults.length > 0) {
        matchedImagesHTML = `
            <div class="mb-4">
                <h6>📸 Matched Images</h6>
                <p class="text-muted small mb-2">Showing ${matchedResults.length} matched images</p>
                <div class="row g-3">
        `;
        
        matchedResults.forEach(result => {
            const filename = result.filename || result.image_name || '';
            const locationName = result.location_name || 'Unknown';
            const cameraIp = result.camera_ip || 'Unknown';
            const count = result.count || 'N/A';
            
            matchedImagesHTML += `
                <div class="col-md-4">
                    <div class="card image-card clickable-image" 
                         onclick="showImageFullscreen('/get_image/${encodeURIComponent(filename)}', '${escapeHtml(locationName)}', '${escapeHtml(cameraIp)}', '${count}')"
                         style="cursor: pointer;">
                        <img src="/get_image/${encodeURIComponent(filename)}" 
                             class="card-img-top" 
                             alt="${escapeHtml(locationName)}"
                             loading="lazy"
                             onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'p-3 text-center bg-light\\' style=\\'height:200px; display:flex; flex-direction:column; justify-content:center;\\'><i class=\\'fas fa-image fa-3x text-muted mb-2\\'></i><p class=\\'small text-muted mb-1\\'><strong>${escapeHtml(locationName).substring(0,30)}</strong></p><p class=\\'small text-muted mb-0\\'>📹 ${escapeHtml(cameraIp)}</p></div>';">
                        <div class="card-body p-2">
                            <p class="mb-1 small"><strong>${escapeHtml(locationName).substring(0, 30)}</strong></p>
                            <p class="mb-0 text-muted small">📹 ${escapeHtml(cameraIp)}</p>
                            <p class="mb-0 text-muted small">📊 Count: ${count}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        matchedImagesHTML += '</div></div>';
    }
    
    // Extract key findings
    const finalAnswer = results.final_answer || '';
    let keyFindings = '';
    const keyFindingsMatch = finalAnswer.match(/Key Findings:([\s\S]*?)(?:Detailed Analysis|Conclusion|$)/);
    if (keyFindingsMatch && keyFindingsMatch[1]) {
        keyFindings = keyFindingsMatch[1].trim();
    }
    
    const messageHTML = `
        <div class="message ai-message">
            <div class="message-header">
                <i class="fas fa-robot"></i> AI Assistant
                ${badge}
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-body">
                <strong>Analyzed ${results.total_images || 0} images, found ${results.matches_found || 0} matches</strong>
            </div>
            
            <button class="btn btn-sm btn-primary mt-3" 
                    type="button" 
                    data-bs-toggle="collapse" 
                    data-bs-target="#${detailsId}">
                <i class="fas fa-eye"></i> View Details
            </button>
            
            <div class="collapse mt-3" id="${detailsId}">
                <div class="card details-card">
                    <div class="card-body">
                        <!-- Statistics -->
                        <div class="stats-grid mb-4">
                            <div class="stat-card-sm bg-gradient-primary">
                                <div class="stat-value">${results.total_images || 0}</div>
                                <div class="stat-label">Images</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-success">
                                <div class="stat-value">${results.matches_found || 0}</div>
                                <div class="stat-label">Matches</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-warning">
                                <div class="stat-value">${results.unique_locations || 0}</div>
                                <div class="stat-label">Locations</div>
                            </div>
                            <div class="stat-card-sm bg-gradient-info">
                                <div class="stat-value">${results.total_images ? Math.round((results.matches_found / results.total_images) * 100) : 0}%</div>
                                <div class="stat-label">Match Rate</div>
                            </div>
                        </div>
                        
                        <!-- Matched Images -->
                        ${matchedImagesHTML}
                        
                        <!-- Key Findings -->
                        ${keyFindings ? `
                        <div class="mb-4">
                            <h6>🎯 Key Findings</h6>
                            <div class="key-findings-box">
                                <pre class="mb-0">${escapeHtml(keyFindings)}</pre>
                            </div>
                        </div>
                        ` : ''}
                        
                        <!-- Full Answer -->
                        <div>
                            <h6>📋 Full Answer</h6>
                            <div class="full-answer-box">
                                <div class="full-answer-content">${formatFullAnswer(finalAnswer)}</div>
                            </div>
                        </div>
                        
                        <!-- Map (if available) -->
                        <div id="map-container-${detailsId}" class="mt-4"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const historyDiv = document.getElementById('conversationHistory');
    historyDiv.insertAdjacentHTML('beforeend', messageHTML);
    
    // Check if we need to create a map
    if (results.detailed_results && results.detailed_results.length > 0) {
        checkAndCreateMap(results, `map-container-${detailsId}`);
    }
}

// Update session info
function updateSessionInfo() {
    if (currentSessionId) {
        fetch(`/get_session/${currentSessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('currentSessionInfo').style.display = 'block';
                document.getElementById('sessionTitle').textContent = data.session.info.title;
                document.getElementById('sessionQueryCount').textContent = data.session.info.query_count;
            }
        });
    }
}

// Refresh sessions list
function refreshSessions() {
    fetch('/get_sessions')
    .then(response => response.json())
    .then(data => {
        const sessionsDiv = document.getElementById('sessionsList');
        
        if (data.sessions.length === 0) {
            sessionsDiv.innerHTML = `
                <div class="text-center text-muted p-3">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>No sessions yet</p>
                </div>
            `;
            return;
        }
        
        sessionsDiv.innerHTML = '';
        data.sessions.forEach(sess => {
            const sessionHTML = `
                <a href="#" class="list-group-item list-group-item-action session-item ${sess.session_id === currentSessionId ? 'active' : ''}" 
                   data-session-id="${sess.session_id}"
                   onclick="loadSession('${sess.session_id}')">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${sess.title.substring(0, 30)}...</h6>
                        <small>${sess.last_updated.substring(0, 10)}</small>
                    </div>
                    <small class="text-muted">
                        💬 ${sess.query_count} queries
                    </small>
                </a>
            `;
            sessionsDiv.insertAdjacentHTML('beforeend', sessionHTML);
        });
    });
}

// End current session
function endCurrentSession() {
    if (confirm('Are you sure you want to end the current session?')) {
        currentSessionId = null;
        document.getElementById('currentSessionInfo').style.display = 'none';
        document.getElementById('endSessionBtn').disabled = true;
        document.getElementById('conversationHistory').innerHTML = `
            <div class="text-center text-muted p-5">
                <i class="fas fa-comment-dots fa-3x mb-3"></i>
                <h5>Start a Conversation!</h5>
                <p>Create a session and ask your first question below.</p>
            </div>
        `;
        showAlert('Session ended', 'info');
        
        // Remove active state from all sessions
        document.querySelectorAll('.session-item').forEach(el => {
            el.classList.remove('active');
        });
    }
}

// Check and create map if locations have coordinates
function checkAndCreateMap(results, containerId) {
    const detailed_results = results.detailed_results || [];
    const locationsWithCoords = [];
    
    detailed_results.forEach(result => {
        const lat = parseFloat(result.latitude);
        const lon = parseFloat(result.longitude);
        
        if (!isNaN(lat) && !isNaN(lon) && lat !== 0 && lon !== 0) {
            locationsWithCoords.push({
                lat: lat,
                lon: lon,
                name: result.location_name || 'Unknown',
                ip: result.camera_ip || 'Unknown',
                district: result.new_district || 'Unknown',
                mandal: result.mandal || 'Unknown',
                match: result.match || false,
                count: result.count || 'N/A'
            });
        }
    });
    
    if (locationsWithCoords.length > 0) {
        createLeafletMap(locationsWithCoords, containerId);
    }
}

// Google Maps ready flag
window.googleMapsReady = false;
window.pendingMaps = [];

// Check if API key exists
if (!window.GOOGLE_MAPS_API_KEY || window.GOOGLE_MAPS_API_KEY === "") {
    console.error('❌ Google Maps API key not found! Please add GOOGLE_MAPS_API_KEY to your .env file');
    console.log('📝 Steps to fix:');
    console.log('   1. Get API key from: https://console.cloud.google.com/');
    console.log('   2. Add to .env file: GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE');
    console.log('   3. Restart Flask server');
}

// Initialize Google Maps callback
window.initGoogleMaps = function() {
    window.googleMapsReady = true;
    console.log('✅ Google Maps API loaded successfully!');
    
    // Create any pending maps
    if (window.pendingMaps.length > 0) {
        console.log(`📍 Creating ${window.pendingMaps.length} pending map(s)...`);
        window.pendingMaps.forEach(config => {
            createGoogleMap(config.locations, config.containerId);
        });
        window.pendingMaps = [];
    }
};

// Timeout check - if Google Maps doesn't load in 10 seconds, show error
setTimeout(() => {
    if (!window.googleMapsReady && window.pendingMaps.length > 0) {
        console.error('❌ Google Maps failed to load after 10 seconds');
        console.error('⚠️ Possible issues:');
        console.error('   1. Missing or invalid API key');
        console.error('   2. API key restrictions blocking localhost');
        console.error('   3. Internet connection issue');
        console.error('   4. Maps JavaScript API not enabled in Google Cloud Console');
        
        // Show user-friendly error in the map containers
        window.pendingMaps.forEach(config => {
            const container = document.getElementById(config.containerId);
            if (container) {
                container.innerHTML = `
                    <div class="alert alert-warning" role="alert">
                        <h5 class="alert-heading">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Map Could Not Load
                        </h5>
                        <p class="mb-2">Google Maps API is not available. Please check:</p>
                        <ol class="mb-2">
                            <li>Is <code>GOOGLE_MAPS_API_KEY</code> set in your <code>.env</code> file?</li>
                            <li>Is the API key valid?</li>
                            <li>Is "Maps JavaScript API" enabled in Google Cloud Console?</li>
                            <li>Are there any API key restrictions blocking localhost?</li>
                        </ol>
                        <p class="mb-0">
                            <small>Check browser console (F12) for detailed error messages.</small>
                        </p>
                    </div>
                `;
            }
        });
        window.pendingMaps = [];
    }
}, 10000);

// Create Google Map with WOW styling
function createGoogleMap(locations, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Check if Google Maps is loaded
    if (!window.googleMapsReady || typeof google === 'undefined') {
        console.log('⏳ Google Maps not ready yet, queueing map creation...');
        window.pendingMaps.push({ locations, containerId });
        return;
    }
    
    // Add map HTML with beautiful header
    container.innerHTML = `
        <div class="google-map-container">
            <div class="map-header">
                <h6 class="mb-0">
                    <i class="fas fa-map-marked-alt me-2"></i>
                    📍 Location Map
                </h6>
                <span class="badge bg-primary">${locations.length} Locations</span>
            </div>
            <div id="${containerId}-map" class="google-map-canvas"></div>
            <div class="map-footer">
                <span class="map-legend-item">
                    <span class="legend-dot" style="background: #10b981;"></span> Match
                </span>
                <span class="map-legend-item">
                    <span class="legend-dot" style="background: #6b7280;"></span> No Match
                </span>
                <span class="map-legend-item">
                    <i class="fas fa-hand-pointer me-1"></i> Click markers for details
                </span>
            </div>
        </div>
    `;
    
    // Calculate center
    const avgLat = locations.reduce((sum, loc) => sum + loc.lat, 0) / locations.length;
    const avgLon = locations.reduce((sum, loc) => sum + loc.lon, 0) / locations.length;
    
    // Initialize map with custom styling
    setTimeout(() => {
        const mapOptions = {
            center: { lat: avgLat, lng: avgLon },
            zoom: 11,
            styles: [
                {
                    featureType: "all",
                    elementType: "geometry",
                    stylers: [{ color: "#f5f5f5" }]
                },
                {
                    featureType: "all",
                    elementType: "labels.text.fill",
                    stylers: [{ color: "#616161" }]
                },
                {
                    featureType: "all",
                    elementType: "labels.text.stroke",
                    stylers: [{ color: "#f5f5f5" }]
                },
                {
                    featureType: "poi.park",
                    elementType: "geometry",
                    stylers: [{ color: "#c8e6c9" }]
                },
                {
                    featureType: "poi.park",
                    elementType: "labels.text.fill",
                    stylers: [{ color: "#689f38" }]
                },
                {
                    featureType: "road",
                    elementType: "geometry",
                    stylers: [{ color: "#ffffff" }]
                },
                {
                    featureType: "road.highway",
                    elementType: "geometry",
                    stylers: [{ color: "#ffd93d" }]
                },
                {
                    featureType: "water",
                    elementType: "geometry",
                    stylers: [{ color: "#64b5f6" }]
                },
                {
                    featureType: "water",
                    elementType: "labels.text.fill",
                    stylers: [{ color: "#1976d2" }]
                }
            ],
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
                mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain']
            },
            streetViewControl: true,
            fullscreenControl: true,
            zoomControl: true,
            zoomControlOptions: {
                position: google.maps.ControlPosition.RIGHT_CENTER
            }
        };
        
        const map = new google.maps.Map(document.getElementById(`${containerId}-map`), mapOptions);
        
        // Create bounds for auto-fitting
        const bounds = new google.maps.LatLngBounds();
        
        // Add markers with custom styling
        locations.forEach((loc, idx) => {
            const position = { lat: loc.lat, lng: loc.lon };
            
            // Create custom marker icon (SVG)
            const markerColor = loc.match ? '#10b981' : '#6b7280';
            const svgMarker = {
                path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
                fillColor: markerColor,
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2,
                scale: 2,
                anchor: new google.maps.Point(12, 24),
                labelOrigin: new google.maps.Point(12, 9)
            };
            
            const marker = new google.maps.Marker({
                position: position,
                map: map,
                icon: svgMarker,
                label: {
                    text: String(idx + 1),
                    color: '#ffffff',
                    fontSize: '12px',
                    fontWeight: 'bold'
                },
                title: loc.name,
                animation: google.maps.Animation.DROP
            });
            
            // Create info window with beautiful styling
            const infoContent = `
                <div class="map-info-window">
                    <h6 class="info-title">${escapeHtml(loc.name)}</h6>
                    <div class="info-content">
                        <div class="info-row">
                            <span class="info-icon">📍</span>
                            <div>
                                <div class="info-label">District</div>
                                <div class="info-value">${escapeHtml(loc.district)}</div>
                            </div>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">🏘️</span>
                            <div>
                                <div class="info-label">Mandal</div>
                                <div class="info-value">${escapeHtml(loc.mandal)}</div>
                            </div>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📹</span>
                            <div>
                                <div class="info-label">Camera IP</div>
                                <div class="info-value">${escapeHtml(loc.ip)}</div>
                            </div>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📊</span>
                            <div>
                                <div class="info-label">Count</div>
                                <div class="info-value">${loc.count}</div>
                            </div>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">${loc.match ? '✅' : '❌'}</span>
                            <div>
                                <div class="info-label">Match Status</div>
                                <div class="info-value ${loc.match ? 'text-success' : 'text-muted'}">
                                    ${loc.match ? 'Matched' : 'No Match'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const infoWindow = new google.maps.InfoWindow({
                content: infoContent,
                maxWidth: 300
            });
            
            marker.addListener('click', () => {
                infoWindow.open(map, marker);
            });
            
            // Extend bounds
            bounds.extend(position);
        });
        
        // Fit map to show all markers
        if (locations.length > 1) {
            map.fitBounds(bounds);
            
            // Adjust zoom if too close
            google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
                if (map.getZoom() > 15) {
                    map.setZoom(15);
                }
            });
        }
    }, 100);
}

// Alias for compatibility
function createLeafletMap(locations, containerId) {
    createGoogleMap(locations, containerId);
}

// Format full answer text to HTML
function formatFullAnswer(text) {
    if (!text) return '';
    
    // Split by major sections
    const lines = text.split('\n');
    let html = '';
    let inList = false;
    let listItems = [];
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // Skip empty lines
        if (!line) {
            if (inList) {
                html += formatList(listItems);
                listItems = [];
                inList = false;
            }
            html += '<div class="my-2"></div>';
            continue;
        }
        
        // Check for horizontal rules
        if (line.match(/^[-=]{3,}$/)) {
            if (inList) {
                html += formatList(listItems);
                listItems = [];
                inList = false;
            }
            html += '<hr class="my-3">';
            continue;
        }
        
        // Check for main headings (Introduction, Summary, Conclusion, etc.)
        if (line.match(/^(Introduction|Summary|Conclusion|Key Observations|Locations|Details?|Analysis)/i) && !line.includes(':')) {
            if (inList) {
                html += formatList(listItems);
                listItems = [];
                inList = false;
            }
            html += `<h2 class="report-heading">${escapeHtml(line)}</h2>`;
            continue;
        }
        
        // Check for numbered headings (1., 2., etc.)
        const numberedHeading = line.match(/^(\d+)\.\s+(.+)$/);
        if (numberedHeading && !inList) {
            html += `<h3 class="report-subheading"><span class="badge bg-primary me-2">${numberedHeading[1]}</span>${escapeHtml(numberedHeading[2])}</h3>`;
            continue;
        }
        
        // Check for bullet points or location details
        if (line.startsWith('-') || line.startsWith('•')) {
            inList = true;
            listItems.push(line.substring(1).trim());
            continue;
        }
        
        // Regular paragraph
        if (inList) {
            html += formatList(listItems);
            listItems = [];
            inList = false;
        }
        
        // Format bold text
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        html += `<p class="report-text">${escapeHtml(line).replace(/&lt;strong&gt;/g, '<strong>').replace(/&lt;\/strong&gt;/g, '</strong>')}</p>`;
    }
    
    // Close any remaining list
    if (inList) {
        html += formatList(listItems);
    }
    
    return html;
}

// Helper function to format lists
function formatList(items) {
    if (items.length === 0) return '';
    
    let html = '<ul class="report-list">';
    items.forEach(item => {
        // Format bold within list items
        item = item.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html += `<li>${escapeHtml(item).replace(/&lt;strong&gt;/g, '<strong>').replace(/&lt;\/strong&gt;/g, '</strong>')}</li>`;
    });
    html += '</ul>';
    return html;
}

// Show image in fullscreen modal
function showImageFullscreen(imageSrc, locationName, cameraIp, count) {
    document.getElementById('modalImage').src = imageSrc;
    document.getElementById('imageModalTitle').textContent = locationName;
    document.getElementById('imageModalInfo').innerHTML = `
        <strong>📍 Location:</strong> ${locationName}<br>
        <strong>📹 Camera IP:</strong> ${cameraIp}<br>
        <strong>📊 Count:</strong> ${count}
    `;
    
    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    modal.show();
}

// Utility function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enter key to send
document.addEventListener('DOMContentLoaded', function() {
    const queryInput = document.getElementById('queryInput');
    if (queryInput) {
        queryInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                sendQuery();
            }
        });
    }
    
    // Load example queries
    document.querySelectorAll('.example-query').forEach(el => {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('queryInput').value = this.dataset.query;
        });
    });
});

