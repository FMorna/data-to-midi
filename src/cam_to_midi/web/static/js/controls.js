/**
 * controls.js — Interactive control panel wired to WebSocket commands
 */

const Controls = (() => {
    let isRunning = true;
    let eventsbound = false;

    const startStopBtn = document.getElementById('btn-start-stop');
    const sourceSelect = document.getElementById('ctrl-source');
    const mapperSelect = document.getElementById('ctrl-mapper');
    const bpmSlider = document.getElementById('ctrl-bpm');
    const bpmDisplay = document.getElementById('bpm-display');
    const keySelect = document.getElementById('ctrl-key');
    const scaleSelect = document.getElementById('ctrl-scale');

    // Debounce helper
    let bpmTimeout = null;

    function init(options, state) {
        // Populate key dropdown
        keySelect.innerHTML = '';
        (options.keys || []).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            keySelect.appendChild(opt);
        });

        // Populate scale dropdown
        scaleSelect.innerHTML = '';
        (options.scales || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s.replace(/_/g, ' ');
            scaleSelect.appendChild(opt);
        });

        // Set current values
        if (state) {
            syncState(state);
        }

        if (!eventsbound) {
            bindEvents();
            eventsbound = true;
        }
    }

    function syncState(state) {
        if (!state) return;
        sourceSelect.value = state.source || 'random_walk';
        mapperSelect.value = state.mapper || 'rule_based';
        keySelect.value = state.key || 'C';
        scaleSelect.value = state.scale || 'major';
        isRunning = state.running !== false;
        updateStartStopBtn();
    }

    function bindEvents() {
        // Start/Stop — send command, server confirms via state message
        startStopBtn.addEventListener('click', () => {
            startStopBtn.disabled = true;
            startStopBtn.textContent = isRunning ? 'Stopping...' : 'Starting...';
            App.sendCommand(isRunning ? 'stop' : 'start');
            // Button updates when server sends state confirmation
            setTimeout(() => { startStopBtn.disabled = false; }, 2000);
        });

        // Source
        sourceSelect.addEventListener('change', () => {
            App.sendCommand('set_source', sourceSelect.value);
        });

        // Mapper
        mapperSelect.addEventListener('change', () => {
            App.sendCommand('set_mapper', mapperSelect.value);
        });

        // BPM — debounced
        bpmSlider.addEventListener('input', () => {
            bpmDisplay.textContent = bpmSlider.value;
            clearTimeout(bpmTimeout);
            bpmTimeout = setTimeout(() => {
                App.sendCommand('set_bpm', parseInt(bpmSlider.value));
            }, 150);
        });

        // Key
        keySelect.addEventListener('change', () => {
            App.sendCommand('set_key', keySelect.value);
        });

        // Scale
        scaleSelect.addEventListener('change', () => {
            App.sendCommand('set_scale', scaleSelect.value);
        });
    }

    function updateStartStopBtn() {
        startStopBtn.disabled = false;
        if (isRunning) {
            startStopBtn.textContent = 'Stop';
            startStopBtn.className = 'btn btn-danger';
        } else {
            startStopBtn.textContent = 'Start';
            startStopBtn.className = 'btn btn-primary';
        }
    }

    return { init, syncState };
})();
