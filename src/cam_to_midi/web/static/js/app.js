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
            setStockMode(state.source === 'stock');

            // Init stock chart with history if available
            if (state.source === 'stock' && data.price_history) {
                StockChart.init(state.symbols || [], data.price_history);
            }
        } else if (data.type === 'tick') {
            lastTick = data;
            state = { ...state, ...data.state };
        } else if (data.type === 'state') {
            state = { ...state, ...data.state };
            Controls.syncState(data.state);
            updateState(data.state, []);
            setStockMode(state.source === 'stock');
        }
    }

    function sendCommand(cmd, value) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ cmd, value }));
        }
    }

    function setStockMode(isStock) {
        const body = document.body;
        const chartPanel = document.getElementById('stockchart-panel');
        const eventPanel = document.getElementById('event-panel');
        const symbolControls = document.getElementById('symbol-controls');
        const soundModeControls = document.getElementById('sound-mode-controls');
        const instrumentControls = document.getElementById('instrument-controls');

        if (isStock) {
            body.classList.add('stock-mode');
            chartPanel.style.display = '';
            eventPanel.style.display = 'none';
            symbolControls.style.display = '';
            soundModeControls.style.display = '';
            instrumentControls.style.display = '';
            Instruments.build(state.sound_mode || 'ambient');
            if (state.instruments) Instruments.syncFromState(state.instruments);
            if (!StockChart._initialized) {
                StockChart.init(state.symbols || [], null);
                StockChart._initialized = true;
            }
        } else {
            body.classList.remove('stock-mode');
            chartPanel.style.display = 'none';
            eventPanel.style.display = '';
            symbolControls.style.display = 'none';
            soundModeControls.style.display = 'none';
            instrumentControls.style.display = '';
            Instruments.build('standard');
            if (state.instruments) Instruments.syncFromState(state.instruments);
        }
    }

    // Render loop
    function renderLoop() {
        if (lastTick) {
            Gauges.update(lastTick.features, lastTick.musical_event);
            PianoRoll.addNotes(lastTick.notes);
            updateState(lastTick.state, lastTick.notes);

            // Route stock price data to chart
            if (lastTick.prices) {
                StockChart.updatePrices(lastTick.prices, lastTick.active_symbol, lastTick.all_stale);
            }

            lastTick = null;
        }
        PianoRoll.draw();
        StockChart.draw();
        requestAnimationFrame(renderLoop);
    }

    function updateState(s, notes) {
        if (!s) return;
        document.getElementById('state-bpm').textContent = s.bpm;
        document.getElementById('state-key').textContent = s.key;
        document.getElementById('state-scale').textContent = s.scale;
        document.getElementById('state-bar').textContent = s.bar;
        document.getElementById('state-beat').textContent = s.beat + 1;

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

    function init() {
        connect();
        requestAnimationFrame(renderLoop);
    }

    return { init, sendCommand, getState: () => state };
})();

document.addEventListener('DOMContentLoaded', App.init);
