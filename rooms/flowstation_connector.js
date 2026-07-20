// FlowStation Connector — FC_FLOW WebSocket bridge
// Connects UI panels to FlowStation-v1.1.0-FC_FLOW.py backend

const WS_URL = 'ws://localhost:8081';
let ws = null;

function connectFlowStation() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => console.log('[FC_FLOW] Connected to FlowStation mesh');
    ws.onmessage = (e) => handleMeshEvent(JSON.parse(e.data));
    ws.onclose = () => setTimeout(connectFlowStation, 3000);
    ws.onerror = (e) => console.error('[FC_FLOW] WebSocket error', e);
}

function handleMeshEvent(data) {
    console.log('[FC_FLOW] Mesh event:', data);
}

function sendCommand(cmd, payload = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: cmd, ...payload }));
    }
}

document.addEventListener('DOMContentLoaded', connectFlowStation);
