# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

data_to_midi observes live systems (stock market, and eventually webcam/sensors) and translates their behavioral dynamics into structured real-time MIDI music. It extracts motion, rhythm, intensity, direction, and volatility from a data stream, then maps those features to pitch, rhythm, velocity, harmony, and timbre through a 5-stage pipeline.

## Architecture

```
Source → Perception → Mapping → Music Engine → Synth
```

Each stage is independent and swappable. Data contracts between stages:
- **SourceSample** (raw timestamped values) → **FeatureVector** (6 normalized dynamics) → **MusicalEvent** (musical hints [0,1]) → **mido.Message** (MIDI) → audio

### Key modules

- `src/data_to_midi/sources/` — Pluggable data sources. `RandomWalkSource` for testing, `StockSource` for live market data. New sources subclass `BaseSource` and register in `registry.py`.
- `src/data_to_midi/perception/` — Sliding-window feature extraction. `extractors.py` contains the 6 feature functions (change_rate, periodicity, intensity, direction, volatility, density). `WindowedPerceptor` buffers samples and emits `FeatureVector`. `MultiSymbolPerceptor` routes stock samples by symbol to separate windows and tracks price history for the chart.
- `src/data_to_midi/mapping/` — Feature-to-music translation. `RuleBasedMapper` uses YAML presets from `config/mappings/`. `MLMapper` uses scikit-learn or a hand-tuned nonlinear fallback.
- `src/data_to_midi/engine/` — Musical structure enforcement. `theory.py` has scales/chords/quantization. `sequencer.py` manages beat grid and chord progressions. `engine.py` orchestrates voice leading for standard mode. `ambient_engine.py` contains `AmbientStockEngine` (per-symbol drone/pad voices) and `ChordStockEngine` (fused 3-note chord from all symbols).
- `src/data_to_midi/synth/` — Audio output. `FluidSynthBackend` (requires system FluidSynth + a .sf2 SoundFont) or `PygameSynth` fallback.
- `src/data_to_midi/pipeline.py` — The async loop wiring all stages.
- `src/data_to_midi/config.py` — YAML config loader with nested dataclass building.
- `src/data_to_midi/ui/web_server.py` — FastAPI + WebSocket server bridging the pipeline to the web frontend. `WebBridge` class queues pipeline events and broadcasts to connected clients.
- `src/data_to_midi/web/static/` — Vanilla HTML/CSS/JS frontend (no build step). `app.js` manages WebSocket, `gauges.js` renders feature bars, `pianoroll.js` draws a canvas note display, `controls.js` handles interactive controls, `stockchart.js` draws the real-time price chart, `instruments.js` manages per-channel GM instrument selection.

### Configuration

All config lives in `config/`. `default.yaml` is the main config file. Mapping presets are in `config/mappings/`. Scale/chord definitions in `config/scales.yaml`. CLI flags override YAML values.

## Build & Run Commands

```bash
# Install (editable, all optional deps)
pip install -e ".[all]"

# Install minimal (core only)
pip install -e .

# System dependency (macOS) for FluidSynth audio backend
brew install fluidsynth
# Then download a GM SoundFont into soundfonts/ (e.g., FluidR3_GM.sf2)

# Launch web UI (browser-based dashboard)
python -m data_to_midi web
# Then open http://127.0.0.1:8080

# Run with synthetic data (no API key needed, terminal mode)
python -m data_to_midi demo

# Run with stock data (defaults to NOS.LS, EDP.LS, BRISA.LS)
python -m data_to_midi stock NOS.LS EDP.LS BRISA.LS

# Override settings via CLI
python -m data_to_midi demo --bpm 90 --key Am --scale minor
python -m data_to_midi --mapper ml
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_theory.py -v

# Run a single test
python -m pytest tests/test_theory.py::TestQuantization::test_all_quantized_notes_in_scale -v

# With coverage
python -m pytest tests/ --cov=data_to_midi
```

Tests use `pytest` with `pytest-asyncio` (auto mode). No audio hardware needed — integration tests use a `CollectorSynth` that captures MIDI messages silently.

## Linting

```bash
python -m ruff check src/
python -m ruff check src/ --fix
```

## Adding a New Source

1. Create `src/data_to_midi/sources/my_source.py` subclassing `BaseSource`
2. Implement `start()`, `stop()`, and `async stream() -> AsyncIterator[SourceSample]`
3. Register it in `sources/registry.py`
4. Add config dataclass if needed in `config.py` and add to `_NESTED_TYPES`

## Adding a Mapping Preset

Create a YAML file in `config/mappings/` following the structure in `stock_basic.yaml`. Each parameter maps a feature (change_rate, periodicity, intensity, direction, volatility, density) to a musical hint via a curve (linear, exponential, step) with input/output ranges.

## Important: `from __future__ import annotations`

Do NOT use `from __future__ import annotations` in files that define FastAPI routes (e.g., `web_server.py`). It turns type annotations into strings, which breaks FastAPI's runtime parameter resolution for WebSocket and request handlers. All other source files use it for Python 3.9 compatibility.
