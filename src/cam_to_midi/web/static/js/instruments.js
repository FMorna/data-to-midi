/**
 * instruments.js — Instrument selection per channel, adapts to sound mode
 */

const Instruments = (() => {
    // Curated General MIDI instruments grouped by category
    const GM_INSTRUMENTS = [
        // Pianos
        { program: 0, name: 'Acoustic Grand Piano', category: 'Piano' },
        { program: 1, name: 'Bright Acoustic Piano', category: 'Piano' },
        { program: 4, name: 'Electric Piano 1', category: 'Piano' },
        { program: 5, name: 'Electric Piano 2', category: 'Piano' },
        { program: 7, name: 'Clavinet', category: 'Piano' },
        // Chromatic Percussion
        { program: 8, name: 'Celesta', category: 'Chromatic' },
        { program: 10, name: 'Music Box', category: 'Chromatic' },
        { program: 11, name: 'Vibraphone', category: 'Chromatic' },
        { program: 12, name: 'Marimba', category: 'Chromatic' },
        // Organ
        { program: 16, name: 'Drawbar Organ', category: 'Organ' },
        { program: 19, name: 'Church Organ', category: 'Organ' },
        // Guitar
        { program: 24, name: 'Nylon Guitar', category: 'Guitar' },
        { program: 25, name: 'Steel Guitar', category: 'Guitar' },
        { program: 26, name: 'Jazz Guitar', category: 'Guitar' },
        { program: 27, name: 'Clean Electric Guitar', category: 'Guitar' },
        // Bass
        { program: 32, name: 'Acoustic Bass', category: 'Bass' },
        { program: 33, name: 'Finger Bass', category: 'Bass' },
        { program: 34, name: 'Pick Bass', category: 'Bass' },
        { program: 35, name: 'Fretless Bass', category: 'Bass' },
        { program: 38, name: 'Synth Bass 1', category: 'Bass' },
        { program: 39, name: 'Synth Bass 2', category: 'Bass' },
        // Strings
        { program: 40, name: 'Violin', category: 'Strings' },
        { program: 42, name: 'Cello', category: 'Strings' },
        { program: 44, name: 'Tremolo Strings', category: 'Strings' },
        { program: 45, name: 'Pizzicato Strings', category: 'Strings' },
        { program: 46, name: 'Orchestral Harp', category: 'Strings' },
        { program: 48, name: 'String Ensemble 1', category: 'Strings' },
        { program: 49, name: 'String Ensemble 2', category: 'Strings' },
        { program: 50, name: 'Synth Strings 1', category: 'Strings' },
        { program: 51, name: 'Synth Strings 2', category: 'Strings' },
        // Choir
        { program: 52, name: 'Choir Aahs', category: 'Choir' },
        { program: 53, name: 'Voice Oohs', category: 'Choir' },
        { program: 54, name: 'Synth Voice', category: 'Choir' },
        // Brass
        { program: 56, name: 'Trumpet', category: 'Brass' },
        { program: 61, name: 'Brass Section', category: 'Brass' },
        { program: 62, name: 'Synth Brass 1', category: 'Brass' },
        // Reed / Woodwind
        { program: 64, name: 'Soprano Sax', category: 'Woodwind' },
        { program: 65, name: 'Alto Sax', category: 'Woodwind' },
        { program: 66, name: 'Tenor Sax', category: 'Woodwind' },
        { program: 68, name: 'Oboe', category: 'Woodwind' },
        { program: 71, name: 'Clarinet', category: 'Woodwind' },
        { program: 73, name: 'Flute', category: 'Woodwind' },
        // Synth Lead
        { program: 80, name: 'Square Lead', category: 'Synth Lead' },
        { program: 81, name: 'Saw Lead', category: 'Synth Lead' },
        { program: 82, name: 'Calliope Lead', category: 'Synth Lead' },
        { program: 84, name: 'Charang Lead', category: 'Synth Lead' },
        // Synth Pad
        { program: 88, name: 'New Age Pad', category: 'Synth Pad' },
        { program: 89, name: 'Warm Pad', category: 'Synth Pad' },
        { program: 90, name: 'Polysynth Pad', category: 'Synth Pad' },
        { program: 91, name: 'Choir Pad', category: 'Synth Pad' },
        { program: 92, name: 'Bowed Pad', category: 'Synth Pad' },
        { program: 93, name: 'Metallic Pad', category: 'Synth Pad' },
        { program: 94, name: 'Halo Pad', category: 'Synth Pad' },
        { program: 95, name: 'Sweep Pad', category: 'Synth Pad' },
        // Synth FX
        { program: 96, name: 'Rain', category: 'Synth FX' },
        { program: 98, name: 'Crystal', category: 'Synth FX' },
        { program: 99, name: 'Atmosphere', category: 'Synth FX' },
        { program: 100, name: 'Brightness', category: 'Synth FX' },
        { program: 101, name: 'Goblins', category: 'Synth FX' },
    ];

    // Channel layouts per sound mode
    const MODE_CHANNELS = {
        ambient: [
            { key: 'ch0', label: 'Symbol 1', defaultProgram: 89 },
            { key: 'ch1', label: 'Symbol 2', defaultProgram: 51 },
            { key: 'ch2', label: 'Symbol 3', defaultProgram: 39 },
            { key: 'ch3', label: 'Atmosphere', defaultProgram: 92 },
        ],
        chord: [
            { key: 'ch0', label: 'Chord Pad', defaultProgram: 89 },
            { key: 'ch1', label: 'Bass', defaultProgram: 39 },
            { key: 'ch2', label: 'Atmosphere', defaultProgram: 92 },
        ],
        standard: [
            { key: 'ch0', label: 'Melody', defaultProgram: 0 },
            { key: 'ch1', label: 'Bass', defaultProgram: 32 },
            { key: 'ch2', label: 'Pad', defaultProgram: 48 },
        ],
    };

    const container = document.getElementById('instrument-selectors');
    let currentMode = 'ambient';
    let currentPrograms = {}; // { ch0: 89, ch1: 51, ... }

    function _buildSelect(channelDef) {
        const wrapper = document.createElement('div');
        wrapper.className = 'instrument-row';

        const label = document.createElement('label');
        label.textContent = channelDef.label;
        label.className = 'instrument-label';

        const select = document.createElement('select');
        select.className = 'instrument-select';
        select.dataset.channel = channelDef.key;

        // Group by category
        let lastCat = '';
        let optgroup = null;
        GM_INSTRUMENTS.forEach(inst => {
            if (inst.category !== lastCat) {
                optgroup = document.createElement('optgroup');
                optgroup.label = inst.category;
                select.appendChild(optgroup);
                lastCat = inst.category;
            }
            const opt = document.createElement('option');
            opt.value = inst.program;
            opt.textContent = inst.name;
            optgroup.appendChild(opt);
        });

        // Set current value
        const prog = currentPrograms[channelDef.key] ?? channelDef.defaultProgram;
        select.value = prog;

        select.addEventListener('change', () => {
            const ch = parseInt(channelDef.key.replace('ch', ''), 10);
            const program = parseInt(select.value, 10);
            currentPrograms[channelDef.key] = program;
            App.sendCommand('set_instrument', { channel: ch, program: program });
        });

        wrapper.appendChild(label);
        wrapper.appendChild(select);
        return wrapper;
    }

    function build(mode) {
        if (!container) return;
        currentMode = mode || 'ambient';
        const channels = MODE_CHANNELS[currentMode] || MODE_CHANNELS.ambient;

        container.innerHTML = '';
        channels.forEach(chDef => {
            container.appendChild(_buildSelect(chDef));
        });
    }

    function syncFromState(instruments) {
        // instruments: { ch0: program, ch1: program, ... } from server
        if (!instruments) return;
        currentPrograms = { ...currentPrograms, ...instruments };

        // Update select values if they exist
        for (const [key, prog] of Object.entries(instruments)) {
            const sel = container?.querySelector(`select[data-channel="${key}"]`);
            if (sel) sel.value = prog;
        }
    }

    function getPrograms() {
        return { ...currentPrograms };
    }

    return { build, syncFromState, getPrograms, GM_INSTRUMENTS, MODE_CHANNELS };
})();
