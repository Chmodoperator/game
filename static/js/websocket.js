// Nova Terra WebSocket Client

class NovaSocket {
    constructor(empireId, username) {
        this.empireId = empireId;
        this.username = username;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${this.empireId}/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.handleReconnect();
        }
    }

    setupEventHandlers() {
        this.socket.onopen = (event) => {
            console.log('Connected to Nova Terra game server');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('CONNECTED', 'success');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('Disconnected from game server');
            this.showConnectionStatus('DISCONNECTED', 'error');
            this.handleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('ERROR', 'error');
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'game_state':
                this.updateGameState(data);
                break;
            case 'map_data':
                this.updateMap(data);
                break;
            case 'resource_update':
                this.updateResources(data);
                break;
            case 'battle_notification':
                this.showBattleNotification(data);
                break;
            case 'message':
                this.showMessage(data.content);
                break;
            case 'error':
                this.showError(data.message);
                break;
            case 'pong':
                // Handle ping response
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateGameState(data) {
        const empire = data.empire;
        
        // Update status bar
        const statusBar = document.querySelector('.status-bar');
        if (statusBar) {
            const statusLeft = statusBar.querySelector('.status-left');
            const statusRight = statusBar.querySelector('.status-right');
            
            if (statusLeft) {
                statusLeft.textContent = `Empire: ${empire.name} | Power: ${empire.power_level} | Rank: #${empire.rank || 'N/A'}`;
            }
            
            if (statusRight) {
                statusRight.textContent = `Energy: ${empire.energy} | Minerals: ${empire.minerals} | Food: ${empire.food}`;
            }
        }

        // Update dashboard if on dashboard page
        if (window.location.pathname.includes('game/')) {
            this.updateDashboardData(data);
        }
    }

    updateMap(data) {
        const mapContainer = document.getElementById('world-map');
        if (mapContainer) {
            this.renderMap(data.map, data.center_x, data.center_y);
        }
    }

    renderMap(mapData, centerX, centerY) {
        const mapContainer = document.getElementById('world-map');
        if (!mapContainer) return;

        let mapHtml = '';
        for (let row of mapData) {
            let rowHtml = '';
            for (let cell of row) {
                const symbol = cell.symbol;
                const color = cell.color;
                const title = `(${cell.x}, ${cell.y}) - ${cell.terrain} - Owner: ${cell.owner || 'Unclaimed'}`;
                
                rowHtml += `<span class="map-cell" 
                    style="color: ${color}" 
                    title="${title}"
                    onclick="selectMapCell(${cell.x}, ${cell.y})">${symbol}</span>`;
            }
            mapHtml += rowHtml + '\n';
        }
        
        mapContainer.innerHTML = mapHtml;
    }

    updateResources(data) {
        // Update resource displays
        this.updateGameState(data);
    }

    showBattleNotification(data) {
        const notification = `
┌─ BATTLE ALERT ──────────────────────────────────────────────────────────────┐
│ ${data.message}
│ Result: ${data.result}
└─────────────────────────────────────────────────────────────────────────────┘`;
        
        this.showMessage(notification, 'warning');
    }

    showMessage(content, type = 'info') {
        const output = document.getElementById('command-output');
        if (output) {
            const timestamp = new Date().toLocaleTimeString();
            output.textContent += `[${timestamp}] ${content}\n`;
            output.scrollTop = output.scrollHeight;
        }

        // Also show as toast notification
        this.showToast(content, type);
    }

    showError(message) {
        this.showMessage(`ERROR: ${message}`, 'error');
    }

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    showConnectionStatus(status, type) {
        const footer = document.querySelector('.terminal-footer .footer-right');
        if (footer) {
            const statusText = footer.querySelector('#connection-status') || 
                              document.createElement('span');
            statusText.id = 'connection-status';
            statusText.textContent = ` | Status: ${status}`;
            statusText.className = `connection-${type}`;
            
            if (!footer.querySelector('#connection-status')) {
                footer.appendChild(statusText);
            }
        }
    }

    sendCommand(command) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'command',
                command: command
            }));
        } else {
            this.showError('Not connected to game server');
        }
    }

    sendMapRequest(x, y) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'get_map',
                x: x,
                y: y
            }));
        }
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
            
            console.log(`Reconnecting in ${delay/1000} seconds... (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
            this.showConnectionStatus('FAILED', 'error');
        }
    }

    updateDashboardData(data) {
        // Update buildings list
        const buildingsList = document.getElementById('buildings-list');
        if (buildingsList && data.buildings) {
            let buildingsHtml = '';
            data.buildings.forEach(building => {
                const status = building.upgrading ? ' (UPGRADING)' : '';
                buildingsHtml += `${building.type} Lv.${building.level} @ ${building.territory}${status}\n`;
            });
            buildingsList.textContent = buildingsHtml || 'No buildings constructed.';
        }

        // Update research list
        const researchList = document.getElementById('research-list');
        if (researchList && data.research) {
            let researchHtml = '';
            data.research.forEach(research => {
                const status = research.researching ? ' (RESEARCHING)' : '';
                researchHtml += `${research.type} Lv.${research.level}${status}\n`;
            });
            researchList.textContent = researchHtml || 'No research completed.';
        }

        // Update territories list
        const territoriesList = document.getElementById('territories-list');
        if (territoriesList && data.territories) {
            let territoriesHtml = '';
            data.territories.forEach(territory => {
                territoriesHtml += `Territory (${territory[0]}, ${territory[1]})\n`;
            });
            territoriesList.textContent = territoriesHtml || 'No territories controlled.';
        }
    }

    // Keep connection alive
    startPingPong() {
        setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000); // Ping every 30 seconds
    }
}

// Global variables
let gameSocket;

// Initialize WebSocket connection when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (typeof empireId !== 'undefined' && typeof username !== 'undefined') {
        gameSocket = new NovaSocket(empireId, username);
        gameSocket.startPingPong();
    }
});

// Global functions for map interaction
function selectMapCell(x, y) {
    console.log(`Selected cell: (${x}, ${y})`);
    
    // Show cell info
    const info = `Selected territory: (${x}, ${y})`;
    if (gameSocket) {
        gameSocket.showMessage(info);
    }
    
    // Store selected coordinates for actions
    window.selectedX = x;
    window.selectedY = y;
}

// Command input handling
document.addEventListener('DOMContentLoaded', function() {
    const commandInput = document.getElementById('command-input');
    if (commandInput) {
        commandInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const command = this.value.trim();
                if (command && gameSocket) {
                    gameSocket.sendCommand(command);
                    this.value = '';
                }
            }
        });
    }
}); 