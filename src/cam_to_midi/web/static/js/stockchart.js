/**
 * stockchart.js — Real-time stock price chart with per-symbol colored lines
 */

const StockChart = (() => {
    const canvas = document.getElementById('stockchart-canvas');
    if (!canvas) return { init() {}, updatePrices() {}, draw() {}, reset() {} };
    const ctx = canvas.getContext('2d');

    // Per-symbol price history accumulated client-side
    let priceData = {}; // {symbol: [{ts, price}, ...]}
    let symbols = [];
    let activeSymbol = '';
    let allStale = false;
    const MAX_POINTS = 300;

    // Symbol colors matching piano roll channel colors
    const SYMBOL_COLORS = [
        { r: 74, g: 158, b: 255, hex: '#4a9eff' },   // blue — lead
        { r: 68, g: 255, b: 136, hex: '#44ff88' },   // green — pad
        { r: 170, g: 102, b: 255, hex: '#aa66ff' },  // purple — bass
    ];

    function init(syms, history) {
        symbols = syms || [];
        priceData = {};
        symbols.forEach(s => { priceData[s] = []; });

        // Load history if provided
        if (history) {
            for (const [sym, pts] of Object.entries(history)) {
                if (priceData[sym]) {
                    priceData[sym] = pts.slice(-MAX_POINTS);
                }
            }
        }
    }

    function updatePrices(prices, active, stale) {
        activeSymbol = active || '';
        allStale = !!stale;
        if (!prices) return;

        for (const [sym, data] of Object.entries(prices)) {
            if (!priceData[sym]) priceData[sym] = [];
            priceData[sym].push({ ts: data.ts, price: data.price });
            // Trim
            while (priceData[sym].length > MAX_POINTS) {
                priceData[sym].shift();
            }
        }
    }

    function draw() {
        if (!canvas.parentElement) return;
        const panel = canvas.parentElement;
        if (panel.style.display === 'none') return;

        const rect = panel.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const w = rect.width - 40;
        const h = rect.height - 50;
        if (w <= 0 || h <= 0) return;

        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.scale(dpr, dpr);

        // Background
        ctx.fillStyle = '#1e1e2e';
        ctx.fillRect(0, 0, w, h);

        if (symbols.length === 0) {
            ctx.fillStyle = '#555568';
            ctx.font = '12px monospace';
            ctx.fillText('Waiting for stock data...', w / 2 - 80, h / 2);
            return;
        }

        // Draw each symbol's price line
        const padding = { top: 10, bottom: 25, left: 5, right: 10 };
        const chartW = w - padding.left - padding.right;
        const chartH = h - padding.top - padding.bottom;

        symbols.forEach((sym, idx) => {
            const pts = priceData[sym];
            if (!pts || pts.length < 2) return;

            const color = SYMBOL_COLORS[idx] || SYMBOL_COLORS[0];
            const prices = pts.map(p => p.price);
            const minP = Math.min(...prices);
            const maxP = Math.max(...prices);
            // Minimum visible range: 0.2% of price so tiny movements are amplified
            const minRange = (maxP || 1) * 0.002;
            const range = Math.max(maxP - minP, minRange);

            ctx.beginPath();
            ctx.strokeStyle = color.hex;
            ctx.lineWidth = sym === activeSymbol ? 2.5 : 1.5;
            ctx.globalAlpha = sym === activeSymbol ? 1.0 : 0.6;

            const numPts = pts.length;
            for (let i = 0; i < numPts; i++) {
                // Span full chart width based on actual point count
                const x = padding.left + (i / Math.max(numPts - 1, 1)) * chartW;
                const mid = (minP + maxP) / 2;
                const y = padding.top + (1 - (pts[i].price - mid + range / 2) / range) * chartH;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.globalAlpha = 1.0;

            // Symbol label at the end of the line
            const lastPt = pts[pts.length - 1];
            const lastX = padding.left + ((numPts - 1) / Math.max(numPts - 1, 1)) * chartW;
            const mid = (minP + maxP) / 2;
            const lastY = padding.top + (1 - (lastPt.price - mid + range / 2) / range) * chartH;

            ctx.fillStyle = color.hex;
            ctx.font = '10px monospace';
            ctx.fillText(`${sym} $${lastPt.price.toFixed(2)}`, lastX - 70, lastY - 6);
        });

        // "Market may be closed" overlay
        if (allStale) {
            ctx.fillStyle = 'rgba(255, 204, 68, 0.7)';
            ctx.font = '11px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('Market may be closed — prices unchanged', w / 2, h - 8);
            ctx.textAlign = 'start';
        } else {
            // Time axis label
            ctx.fillStyle = '#555568';
            ctx.font = '9px monospace';
            ctx.fillText('time →', w - 50, h - 5);
        }
    }

    function reset() {
        priceData = {};
        symbols = [];
        activeSymbol = '';
    }

    return { init, updatePrices, draw, reset };
})();
