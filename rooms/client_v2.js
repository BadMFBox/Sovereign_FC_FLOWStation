let ws;
let wsReconnectTimer;

function connectWebSocket() {
    ws = new WebSocket('ws://' + window.location.hostname + ':8081');
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('ws-status').textContent = '● LIVE';
        document.getElementById('ws-status').style.color = '#00ff00';
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Parse error:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        document.getElementById('ws-status').textContent = '● RECONNECTING';
        document.getElementById('ws-status').style.color = '#ff0000';
        wsReconnectTimer = setTimeout(connectWebSocket, 2000);
    };
}

function handleWebSocketMessage(data) {
    if (data.event === 'CYCLE') {
        updateElement('gear', data.payload.gear);
        updateElement('health', `${data.payload.health}/50`);
        updateElement('cycles', data.payload.cycle);
        updateElement('mode', data.payload.mode || 'NORMAL');
        updateElement('rate', data.payload.rate || 0);
        updateElement('pressure', data.payload.pressure || 0.5);
    } else if (data.event === 'ROOM_UPDATE') {
        updateRoomList(data.payload);
    } else if (data.event === 'AI_MESSAGE') {
        addAIMessage(data.payload);
    } else if (data.event === 'TERMINAL_OUTPUT') {
        addTerminalOutput(data.payload);
    }
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function updateRoomList(rooms) {
    const roomList = document.getElementById('room-list');
    if (!roomList) return;
    
    roomList.innerHTML = '';
    let count = 0;
    for (const [name, status] of Object.entries(rooms)) {
        const color = status === 'HEALTHY' ? '#00ff00' : '#ff0000';
        roomList.innerHTML += `<div style="color: ${color}; margin: 3px 0;">▸ ${name}: ${status}</div>`;
        if (status === 'HEALTHY') count++;
    }
    updateElement('room-count', count);
}

function addAIMessage(msg) {
    const feed = document.getElementById('ai-feed');
    if (!feed) return;
    
    const div = document.createElement('div');
    div.className = 'ai-msg';
    div.textContent = `🤖 ${msg}`;
    feed.appendChild(div);
    feed.scrollTop = feed.scrollHeight;
}

function addTerminalOutput(output) {
    const terminal = document.getElementById('terminal-output');
    if (!terminal) return;
    
    const div = document.createElement('div');
    div.className = 'terminal-output';
    div.textContent = output;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function sendCommand(cmd, params = {}) {
    addTerminalOutput(`> ${cmd} ${JSON.stringify(params)}`);
    
    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, params: params })
    }).then(r => r.json()).then(data => {
        addTerminalOutput(`✓ ${cmd}: ${JSON.stringify(data)}`);
    }).catch(err => {
        addTerminalOutput(`✗ ${cmd} failed: ${err}`);
    });
}

// Terminal input handler
document.addEventListener('DOMContentLoaded', () => {
    const termInput = document.getElementById('terminal-input');
    if (termInput) {
        termInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const cmd = e.target.value.trim();
                if (cmd) {
                    addTerminalOutput(`$ ${cmd}`);
                    sendCommand(cmd);
                    e.target.value = '';
                }
            }
        });
    }
    
    const aiInput = document.getElementById('ai-input');
    if (aiInput) {
        aiInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const msg = e.target.value.trim();
                if (msg) {
                    addAIMessage(`You: ${msg}`);
                    // TODO: Send to AI backend
                    e.target.value = '';
                }
            }
        });
    }
});

// Initialize
connectWebSocket();

// Fetch initial state
fetch('/state').then(r => r.json()).then(data => {
    if (data.turf && data.turf.rooms) {
        updateRoomList(data.turf.rooms);
    }
}).catch(err => console.error('State fetch failed:', err));
