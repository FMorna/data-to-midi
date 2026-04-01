/**
 * app.js — WebSocket client, message routing, state management
 */

const App = (() => {
    let ws = null;
    let reconnectDelay = 1000;
    let state = { running: true };
    let lastTick = null;

    const statusEl = document.getElementById('connection-status');

    function connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${location.host}/ws`);

        ws.onopen = () => {
            statusEl.textContent = 'connected';
            statusEl.className = 'status connected';
            reconnectDelay = 1000;
        };

        ws.onclose = () => {
            statusEl.textContent = 'disconnected';
            statusEl.className = 'status disconnected';
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
        };

        ws.onerror = () => {
            ws.close();
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };
    }

    function handleMessage(data) {
        if (data.type === 'init') {
            state = data.state;
            Controls.init(data.options, data.state);
            Gauges.reset();
            PianoRoll.reset();
        } else if (data.type === 'tick') {
            lastTick = data;
            state = { ...state, ...data.state };
        } else if (data.type === 'state') {
            // Immediate state update (from stop/start commands)
            state = { ...state, ...data.state };
            Controls.syncState(data.state);
            updateState(data.state, []);
        }
    }

    function sendCommand(cmd, value) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ cmd, value }));
        }
    }

    // Render loop — throttled to ~20fps via requestAnimationFrame
    function renderLoop() {
        if (lastTick) {
            Gauges.update(lastTick.features, lastTick.musical_event);
            PianoRoll.addNotes(lastTick.notes);
            updateState(lastTick.state, lastTick.notes);
            lastTick = null;
        }
        PianoRoll.draw();
        requestAnimationFrame(renderLoop);
    }

    function updateState(s, notes) {
        if (!s) return;
        document.getElementById('state-bpm').textContent = s.bpm;
        document.getElementById('state-key').textContent = s.key;
        document.getElementById('state-scale').textContent = s.scale;
        document.getElementById('state-bar').textContent = s.bar;
        document.getElementById('state-beat').textContent = s.beat + 1; // 1-indexed for display

        // Active notes
        const display = document.getElementById('note-display');
        display.innerHTML = '';
        if (notes && notes.length > 0) {
            notes.forEach(n => {
                const chip = document.createElement('span');
                chip.className = `note-chip ch${n.channel}`;
                chip.textContent = n.name;
                display.appendChild(chip);
            });
        }
    }

    // Boot
    function init() {
        connect();
        requestAnimationFrame(renderLoop);
    }

    return { init, sendCommand, getState: () => state };
})();

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', App.init);
