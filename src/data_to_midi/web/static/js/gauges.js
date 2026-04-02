/**
 * gauges.js — Feature vector and musical event bar gauges
 */

const Gauges = (() => {
    const FEATURE_COLORS = {
        change_rate: '#4a9eff',
        direction: '#00d4aa',
        intensity: '#ff8844',
        volatility: '#ff4466',
        periodicity: '#aa66ff',
        density: '#ffcc44',
    };

    function update(features, musicalEvent) {
        // Update perception gauges
        for (const [key, value] of Object.entries(features)) {
            updateGauge(key, value, key === 'change_rate' || key === 'direction');
        }

        // Update musical event gauges
        if (musicalEvent) {
            updateUnipolarGauge('pitch_hint', musicalEvent.pitch_hint);
            updateUnipolarGauge('evt-velocity', musicalEvent.velocity);
            updateUnipolarGauge('duration_hint', musicalEvent.duration_hint);
            updateUnipolarGauge('density_hint', musicalEvent.density_hint);
            updateUnipolarGauge('register_hint', musicalEvent.register_hint);
            updateUnipolarGauge('urgency', musicalEvent.urgency);
        }
    }

    function updateGauge(key, value, bipolar) {
        if (bipolar) {
            updateBipolarGauge(key, value);
        } else {
            updateUnipolarGauge(key, value);
        }
    }

    function updateUnipolarGauge(key, value) {
        const fill = document.getElementById(`gauge-${key}`);
        const valEl = document.getElementById(`val-${key}`);
        if (!fill) return;

        const pct = Math.max(0, Math.min(100, value * 100));
        fill.style.width = `${pct}%`;
        fill.style.left = '0';

        if (valEl) {
            valEl.textContent = value.toFixed(2);
        }
    }

    function updateBipolarGauge(key, value) {
        const fill = document.getElementById(`gauge-${key}`);
        const valEl = document.getElementById(`val-${key}`);
        if (!fill) return;

        // value is in [-1, 1]
        // Map to position and width from center (50%)
        const normalized = Math.max(-1, Math.min(1, value));
        const pct = Math.abs(normalized) * 50;

        if (normalized >= 0) {
            fill.style.left = '50%';
            fill.style.width = `${pct}%`;
            fill.className = 'gauge-fill';
            fill.style.background = '#00d4aa';
        } else {
            fill.style.left = `${50 - pct}%`;
            fill.style.width = `${pct}%`;
            fill.className = 'gauge-fill negative';
            fill.style.background = '#ff4466';
        }

        if (valEl) {
            valEl.textContent = (normalized >= 0 ? '+' : '') + normalized.toFixed(2);
        }
    }

    function reset() {
        document.querySelectorAll('.gauge-fill').forEach(el => {
            el.style.width = '0%';
        });
        document.querySelectorAll('.gauge-value').forEach(el => {
            el.textContent = '0.00';
        });
    }

    return { update, reset };
})();
