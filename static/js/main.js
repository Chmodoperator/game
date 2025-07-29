// Nova Terra: Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI elements
    initializeUI();
    
    // Start auto-refresh timers
    startAutoRefresh();
    
    // Initialize server time display
    updateServerTime();
    setInterval(updateServerTime, 1000);
});

function initializeUI() {
    // Initialize any interactive elements
    initializeForms();
    initializeButtons();
    initializeTooltips();
}

function initializeForms() {
    // Handle API form submissions
    const buildForm = document.getElementById('build-form');
    if (buildForm) {
        buildForm.addEventListener('submit', handleBuildSubmit);
    }

    const researchForm = document.getElementById('research-form');
    if (researchForm) {
        researchForm.addEventListener('submit', handleResearchSubmit);
    }

    const attackForm = document.getElementById('attack-form');
    if (attackForm) {
        attackForm.addEventListener('submit', handleAttackSubmit);
    }

    const messageForm = document.getElementById('message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', handleMessageSubmit);
    }
}

function initializeButtons() {
    // Quick action buttons
    document.querySelectorAll('.quick-build').forEach(button => {
        button.addEventListener('click', handleQuickBuild);
    });

    document.querySelectorAll('.quick-research').forEach(button => {
        button.addEventListener('click', handleQuickResearch);
    });

    document.querySelectorAll('.join-alliance').forEach(button => {
        button.addEventListener('click', handleJoinAlliance);
    });
}

function initializeTooltips() {
    // Add hover tooltips for game elements
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

// API Functions

async function apiCall(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (result.success) {
            showNotification(result.message, 'success');
            // Refresh page data
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showNotification(result.error || 'An error occurred', 'error');
        }

        return result;
    } catch (error) {
        console.error('API call failed:', error);
        showNotification('Network error occurred', 'error');
        return null;
    }
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// Form Handlers

async function handleBuildSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        building_type: formData.get('building_type'),
        territory_id: formData.get('territory_id')
    };

    await apiCall('/game/api/build/', data);
}

async function handleResearchSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        research_type: formData.get('research_type')
    };

    await apiCall('/game/api/research/', data);
}

async function handleAttackSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const selectedArmies = Array.from(formData.getAll('army_ids'));
    
    const data = {
        x: parseInt(formData.get('target_x')),
        y: parseInt(formData.get('target_y')),
        army_ids: selectedArmies
    };

    const result = await apiCall('/game/api/attack/', data);
    if (result && result.success) {
        showBattleResult(result.result);
    }
}

async function handleMessageSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        receiver_id: formData.get('receiver_id'),
        subject: formData.get('subject'),
        content: formData.get('content'),
        message_type: formData.get('message_type') || 'diplomatic'
    };

    await apiCall('/game/api/send-message/', data);
}

// Quick Action Handlers

async function handleQuickBuild(event) {
    const button = event.target;
    const buildingType = button.dataset.buildingType;
    const territoryId = button.dataset.territoryId;

    if (!buildingType || !territoryId) {
        showNotification('Invalid building data', 'error');
        return;
    }

    const data = {
        building_type: buildingType,
        territory_id: territoryId
    };

    button.disabled = true;
    button.textContent = 'Building...';

    await apiCall('/game/api/build/', data);
}

async function handleQuickResearch(event) {
    const button = event.target;
    const researchType = button.dataset.researchType;

    if (!researchType) {
        showNotification('Invalid research data', 'error');
        return;
    }

    const data = {
        research_type: researchType
    };

    button.disabled = true;
    button.textContent = 'Researching...';

    await apiCall('/game/api/research/', data);
}

async function handleJoinAlliance(event) {
    const button = event.target;
    const allianceId = button.dataset.allianceId;

    if (!allianceId) {
        showNotification('Invalid alliance data', 'error');
        return;
    }

    const data = {
        alliance_id: allianceId
    };

    await apiCall('/game/api/join-alliance/', data);
}

// UI Functions

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Add styling
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border: 1px solid currentColor;
        background-color: rgba(0, 0, 0, 0.9);
        color: inherit;
        font-family: inherit;
        z-index: 1000;
        max-width: 300px;
        word-wrap: break-word;
    `;

    // Set color based on type
    switch (type) {
        case 'success':
            notification.style.color = '#44ff44';
            break;
        case 'error':
            notification.style.color = '#ff4444';
            break;
        case 'warning':
            notification.style.color = '#ffaa44';
            break;
        default:
            notification.style.color = '#00aaff';
    }

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);

    // Click to dismiss
    notification.addEventListener('click', () => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    });
}

function showBattleResult(result) {
    // Modal disabled - just log the result instead
    console.log('Battle Result:', result);
    
    // Show a simple notification instead of modal
    showNotification(`Battle ${result.result} - Your losses: ${result.attacker_losses}% | Enemy losses: ${result.defender_losses}%`, 'info');
    
    // Original modal code commented out to prevent popup
    /*
    const modal = document.createElement('div');
    modal.className = 'battle-result-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Battle Result</h3>
            <p>Outcome: ${result.result}</p>
            <p>Your losses: ${result.attacker_losses}%</p>
            <p>Enemy losses: ${result.defender_losses}%</p>
            <button onclick="this.closest('.battle-result-modal').remove()">Close</button>
        </div>
    `;

    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;

    modal.querySelector('.modal-content').style.cssText = `
        border: 2px solid currentColor;
        padding: 30px;
        background-color: inherit;
        color: inherit;
        font-family: inherit;
        text-align: center;
        min-width: 300px;
    `;

    document.body.appendChild(modal);
    */
}

function showTooltip(event) {
    const element = event.target;
    const tooltipText = element.dataset.tooltip;

    if (!tooltipText) return;

    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.cssText = `
        position: absolute;
        background-color: rgba(0, 0, 0, 0.9);
        color: inherit;
        padding: 5px 10px;
        border: 1px solid currentColor;
        font-family: inherit;
        font-size: 12px;
        z-index: 1000;
        max-width: 200px;
        word-wrap: break-word;
    `;

    document.body.appendChild(tooltip);

    // Position tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + 'px';
    tooltip.style.top = (rect.bottom + 5) + 'px';

    element._tooltip = tooltip;
}

function hideTooltip(event) {
    const element = event.target;
    if (element._tooltip) {
        element._tooltip.remove();
        delete element._tooltip;
    }
}

// Auto-refresh functions

function startAutoRefresh() {
    // Refresh resource displays every 30 seconds
    setInterval(refreshResources, 30000);
    
    // Refresh building/research progress every 10 seconds
    setInterval(refreshProgress, 10000);
}

async function refreshResources() {
    // This would normally be handled by WebSocket, but as fallback
    if (!gameSocket || gameSocket.socket.readyState !== WebSocket.OPEN) {
        // Only refresh if WebSocket is not working
        try {
            const response = await fetch('/game/api/generate-resources/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                }
            });
            const data = await response.json();
            
            if (data.success) {
                updateResourceDisplay(data);
            }
        } catch (error) {
            console.log('Resource refresh failed:', error);
        }
    }
}

function refreshProgress() {
    // Update progress bars for buildings and research
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(updateProgressBar);
}

function updateProgressBar(progressBar) {
    const startTime = parseInt(progressBar.dataset.startTime);
    const endTime = parseInt(progressBar.dataset.endTime);
    
    if (!startTime || !endTime) return;

    const now = Date.now();
    const progress = Math.min(100, ((now - startTime) / (endTime - startTime)) * 100);
    
    progressBar.style.width = progress + '%';
    
    if (progress >= 100) {
        progressBar.textContent = 'COMPLETE';
        progressBar.style.backgroundColor = '#44ff44';
    } else {
        const remaining = Math.ceil((endTime - now) / 1000);
        progressBar.textContent = `${Math.round(progress)}% (${remaining}s)`;
    }
}

function updateResourceDisplay(empire) {
    const statusRight = document.querySelector('.status-bar .status-right');
    if (statusRight) {
        statusRight.textContent = `Energy: ${empire.energy} | Minerals: ${empire.minerals} | Food: ${empire.food}`;
    }
}

function updateServerTime() {
    const timeElement = document.getElementById('server-time');
    if (timeElement) {
        timeElement.textContent = new Date().toLocaleTimeString();
    }
}

// Map functions

function centerMapOn(x, y) {
    const url = new URL(window.location);
    url.searchParams.set('x', x);
    url.searchParams.set('y', y);
    window.location.href = url.toString();
}

function quickAttack(x, y) {
    window.selectedX = x;
    window.selectedY = y;
    
    // Log instead of showing modal
    console.log(`Attack target selected: (${x}, ${y})`);
    
    // Don't try to show attack modal - just log the selection
    // const attackModal = document.getElementById('attack-modal');
    // if (attackModal) {
    //     attackModal.style.display = 'block';
    //     
    //     // Fill in coordinates
    //     const xInput = attackModal.querySelector('input[name="target_x"]');
    //     const yInput = attackModal.querySelector('input[name="target_y"]');
    //     
    //     if (xInput) xInput.value = x;
    //     if (yInput) yInput.value = y;
    // }
}

// Command line interface

function executeCommand(command) {
    if (gameSocket) {
        gameSocket.sendCommand(command);
    } else {
        showNotification('Game connection not available', 'error');
    }
}

// Color theme switching

function switchTheme(theme) {
    document.body.className = `theme-${theme}`;
    
    // Save preference
    fetch('/accounts/api/update-theme/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({theme: theme})
    });
}

// Keyboard shortcuts

document.addEventListener('keydown', function(event) {
    // Only handle shortcuts when not in input fields
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    switch (event.key) {
        case 'h':
            executeCommand('help');
            break;
        case 's':
            executeCommand('status');
            break;
        case 'm':
            window.location.href = '/game/map/';
            break;
        case 'b':
            window.location.href = '/game/buildings/';
            break;
        case 'r':
            window.location.href = '/game/research/';
            break;
        case 'd':
            window.location.href = '/game/';
            break;
        case 'Escape':
            // Close any open modals
            document.querySelectorAll('.modal, .battle-result-modal').forEach(modal => {
                modal.remove();
            });
            break;
    }
});

// Chat functionality

function sendChatMessage(chatType, allianceId = null) {
    const input = document.getElementById('chat-input');
    if (!input || !input.value.trim()) return;

    const message = input.value.trim();
    input.value = '';

    // This would connect to chat WebSocket
    if (chatType === 'global') {
        // Send to global chat
        console.log('Sending global message:', message);
    } else if (chatType === 'alliance' && allianceId) {
        // Send to alliance chat
        console.log('Sending alliance message:', message, 'to alliance', allianceId);
    }
}

// Utility functions

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// Export functions for global use
window.NovaGame = {
    executeCommand,
    switchTheme,
    centerMapOn,
    quickAttack,
    sendChatMessage,
    showNotification,
    formatNumber,
    formatTime
}; 