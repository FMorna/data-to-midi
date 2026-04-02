/**
 * controls.js — Interactive control panel wired to WebSocket commands
 */

const Controls = (() => {
    let isRunning = true;
    let isMuted = false;
    let eventsBound = false;

    const startStopBtn = document.getElementById('btn-start-stop');
    const muteBtn = document.getElementById('btn-mute');
    const sourceSelect = document.getElementById('ctrl-source');
    const mapperSelect = document.getElementById('ctrl-mapper');
    const bpmSlider = document.getElementById('ctrl-bpm');
    const bpmDisplay = document.getElementById('bpm-display');
    const keySelect = document.getElementById('ctrl-key');
    const scaleSelect = document.getElementById('ctrl-scale');
    const soundModeSelect = document.getElementById('ctrl-sound-mode');

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

        if (state) {
            syncState(state);
        }

        if (!eventsBound) {
            bindEvents();
            eventsBound = true;
        }
    }

    function syncState(state) {
        if (!state) return;
        sourceSelect.value = state.source || 'random_walk';
        mapperSelect.value = state.mapper || 'rule_based';
        keySelect.value = state.key || 'C';
        scaleSelect.value = state.scale || 'major';
        soundModeSelect.value = state.sound_mode || 'ambient';
        isRunning = state.running !== false;
        updateStartStopBtn();

        // Populate symbol inputs if symbols provided
        if (state.symbols && state.symbols.length > 0) {
            for (let i = 0; i < 3; i++) {
                const input = document.getElementById(`symbol-${i + 1}`);
                if (input) {
                    input.value = state.symbols[i] || '';
                }
            }
        }
    }

    function bindEvents() {
        // Start/Stop
        startStopBtn.addEventListener('click', () => {
            startStopBtn.disabled = true;
            startStopBtn.textContent = isRunning ? 'Stopping...' : 'Starting...';
            App.sendCommand(isRunning ? 'stop' : 'start');
            setTimeout(() => { startStopBtn.disabled = false; }, 2000);
        });

        // Mute toggle
        muteBtn.addEventListener('click', () => {
            isMuted = !isMuted;
            updateMuteBtn();
            App.sendCommand(isMuted ? 'mute' : 'unmute');
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

        // Sound mode
        soundModeSelect.addEventListener('change', () => {
            App.sendCommand('set_sound_mode', soundModeSelect.value);
            // Rebuild instrument selectors for new mode
            Instruments.build(soundModeSelect.value);
        });

        // Apply symbols
        const applyBtn = document.getElementById('btn-apply-symbols');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                const symbols = [1, 2, 3]
                    .map(i => {
                        const el = document.getElementById(`symbol-${i}`);
                        return el ? el.value.trim().toUpperCase() : '';
                    })
                    .filter(Boolean);
                if (symbols.length > 0) {
                    applyBtn.textContent = 'Applying...';
                    applyBtn.disabled = true;
                    App.sendCommand('set_symbols', symbols);
                    // Reset stock chart for new symbols
                    StockChart.init(symbols, null);
                    setTimeout(() => {
                        applyBtn.textContent = 'Apply';
                        applyBtn.disabled = false;
                    }, 3000);
                }
            });
        }
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

    function updateMuteBtn() {
        if (isMuted) {
            muteBtn.textContent = 'Unmute';
            muteBtn.className = 'btn btn-muted';
        } else {
            muteBtn.textContent = 'Mute';
            muteBtn.className = 'btn';
        }
    }

    return { init, syncState };
})();
