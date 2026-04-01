/**
 * pianoroll.js — Canvas-based scrolling note visualization
 */

const PianoRoll = (() => {
    const canvas = document.getElementById('pianoroll-canvas');
    const ctx = canvas.getContext('2d');

    // Note buffer: rolling history
    const MAX_COLUMNS = 200;
    const noteColumns = []; // Array of arrays of note objects

    // MIDI range to display
    const NOTE_MIN = 30;
    const NOTE_MAX = 100;
    const NOTE_RANGE = NOTE_MAX - NOTE_MIN;

    // Channel colors
    const CHANNEL_COLORS = {
        0: { r: 74, g: 158, b: 255 },   // melody — blue
        1: { r: 68, g: 255, b: 136 },   // bass — green
        2: { r: 170, g: 102, b: 255 },  // pad — purple
        9: { r: 255, g: 136, b: 68 },   // drums — orange
    };

    function addNotes(notes) {
        if (!notes || notes.length === 0) {
            noteColumns.push([]);
        } else {
            noteColumns.push(notes.map(n => ({
                note: n.note,
                channel: n.channel,
                velocity: n.velocity,
            })));
        }

        // Trim to max
        while (noteColumns.length > MAX_COLUMNS) {
            noteColumns.shift();
        }
    }

    function draw() {
        // Resize canvas to container
        const rect = canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const w = rect.width - 40; // account for padding
        const h = rect.height - 50;

        if (w <= 0 || h <= 0) return;

        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.scale(dpr, dpr);

        // Clear
        ctx.fillStyle = '#1e1e2e';
        ctx.fillRect(0, 0, w, h);

        // Draw guide lines for octaves
        ctx.strokeStyle = '#2a2a3a';
        ctx.lineWidth = 0.5;
        for (let note = NOTE_MIN; note <= NOTE_MAX; note += 12) {
            const y = h - ((note - NOTE_MIN) / NOTE_RANGE) * h;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Draw notes
        if (noteColumns.length === 0) return;

        const colWidth = w / MAX_COLUMNS;
        const noteHeight = Math.max(3, h / NOTE_RANGE * 1.5);

        for (let i = 0; i < noteColumns.length; i++) {
            const col = noteColumns[i];
            const x = i * colWidth;
            const age = 1 - (noteColumns.length - 1 - i) / MAX_COLUMNS;
            const alpha = 0.3 + age * 0.7;

            for (const n of col) {
                if (n.note < NOTE_MIN || n.note > NOTE_MAX) continue;

                const y = h - ((n.note - NOTE_MIN) / NOTE_RANGE) * h - noteHeight / 2;
                const color = CHANNEL_COLORS[n.channel] || CHANNEL_COLORS[0];
                const velScale = n.velocity / 127;

                ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha * velScale})`;
                ctx.shadowColor = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha * 0.5})`;
                ctx.shadowBlur = 4;

                ctx.beginPath();
                ctx.roundRect(x, y, Math.max(colWidth - 1, 2), noteHeight, 2);
                ctx.fill();
            }
        }
        ctx.shadowBlur = 0;

        // Draw channel labels
        ctx.font = '10px monospace';
        ctx.fillStyle = '#555568';
        ctx.fillText('C2', 4, h - ((36 - NOTE_MIN) / NOTE_RANGE) * h - 2);
        ctx.fillText('C3', 4, h - ((48 - NOTE_MIN) / NOTE_RANGE) * h - 2);
        ctx.fillText('C4', 4, h - ((60 - NOTE_MIN) / NOTE_RANGE) * h - 2);
        ctx.fillText('C5', 4, h - ((72 - NOTE_MIN) / NOTE_RANGE) * h - 2);
        ctx.fillText('C6', 4, h - ((84 - NOTE_MIN) / NOTE_RANGE) * h - 2);
    }

    function reset() {
        noteColumns.length = 0;
    }

    return { addNotes, draw, reset };
})();
