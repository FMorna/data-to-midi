"""FastAPI WebSocket server bridging the pipeline to a web frontend."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from ..config import AppConfig, EngineConfig, ChannelConfig, load_config, load_mapping_preset
from ..engine.engine import MusicEngine
from ..engine.theory import NOTE_MAP, SCALES
from ..mapping.musical_params import MusicalEvent
from ..mapping.registry import MapperRegistry
from ..perception.features import FeatureVector
from ..perception.multi_symbol import MultiSymbolPerceptor
from ..perception.windowed import WindowedPerceptor
from ..pipeline import Pipeline
from ..sources.registry import SourceRegistry

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_name(note: int) -> str:
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


def _make_chord_engine(config: AppConfig, symbols: list):
    """Create a ChordStockEngine configured for the given symbols."""
    from ..engine.ambient_engine import ChordStockEngine
    engine_cfg = EngineConfig(
        bpm=75,
        key=config.engine.key,
        scale="dorian" if config.engine.scale == "major" else config.engine.scale,
        time_signature=config.engine.time_signature,
        auto_key_change=config.engine.auto_key_change,
        mode="chord_stock",
        velocity_range=[25, 65],
        channels={
            "chord": ChannelConfig(0, 89),       # Warm Pad — unified chord
            "bass": ChannelConfig(1, 39),         # Synth Bass — root note
            "atmosphere": ChannelConfig(2, 92),   # Spacey Pad — wash
        },
    )
    return ChordStockEngine(engine_cfg, symbols)


def _make_stock_engine(config: AppConfig, symbols: list):
    """Create an AmbientStockEngine configured for the given symbols."""
    from ..engine.ambient_engine import AmbientStockEngine
    engine_cfg = EngineConfig(
        bpm=75,
        key=config.engine.key,
        scale="dorian" if config.engine.scale == "major" else config.engine.scale,
        time_signature=config.engine.time_signature,
        auto_key_change=config.engine.auto_key_change,
        mode="ambient_stock",
        velocity_range=[25, 70],
        channels={
            "pad": ChannelConfig(0, 89),         # Warm Pad — sustained, lush
            "strings": ChannelConfig(1, 51),      # Synth Strings — wide, evolving
            "bass": ChannelConfig(2, 39),          # Synth Bass — deep foundation
            "atmosphere": ChannelConfig(3, 92),    # Spacey Pad — background wash
        },
    )
    return AmbientStockEngine(engine_cfg, symbols)


class WebBridge:
    """Bridges the pipeline event callback to WebSocket clients."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._queue = None
        self._clients: set = set()
        self._running = False
        self._muted = False
        self._pipeline_task = None

        # Synth — shared across pipeline restarts
        try:
            from ..synth.registry import SynthRegistry
            self.synth = SynthRegistry.create(config.synth)
            self.synth.start()
            print(f"  Audio: {config.synth.backend} with {config.synth.soundfont}")
        except Exception as e:
            print(f"  Synth unavailable ({e}), running silent.")
            self.synth = _NullSynth()

        # Pipeline components — will be built in _start_pipeline
        self.source = None
        self.perceptor = None
        self.mapper = None
        self.engine = None
        self.pipeline = None
        self._sound_mode = "ambient"  # "ambient" or "standard" (stock mode only)

    def _is_stock_mode(self) -> bool:
        return self.config.source.type == "stock"

    def _get_symbols(self) -> list:
        return self.config.source.stock.symbols[:3]

    def on_pipeline_event(
        self, features: FeatureVector, event: MusicalEvent, messages: list
    ) -> None:
        """Sync callback from pipeline — serializes data and enqueues."""
        notes = []
        for msg in messages:
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append({
                    "channel": msg.channel,
                    "note": msg.note,
                    "velocity": msg.velocity,
                    "name": _midi_to_name(msg.note),
                })

        payload = {
            "type": "tick",
            "ts": time.time(),
            "features": {
                "change_rate": round(features.change_rate, 3),
                "periodicity": round(features.periodicity, 3),
                "intensity": round(features.intensity, 3),
                "direction": round(features.direction, 3),
                "volatility": round(features.volatility, 3),
                "density": round(features.density, 3),
            },
            "musical_event": {
                "pitch_hint": round(event.pitch_hint, 3),
                "velocity": round(event.velocity, 3),
                "duration_hint": round(event.duration_hint, 3),
                "density_hint": round(event.density_hint, 3),
                "register_hint": round(event.register_hint, 3),
                "urgency": round(event.urgency, 3),
            },
            "notes": notes,
            "state": self._get_state(),
            "active_symbol": features.symbol or "",
        }

        # Add price data if in stock mode
        if isinstance(self.perceptor, MultiSymbolPerceptor):
            latest = self.perceptor.get_latest_prices()
            payload["prices"] = {
                sym: {"ts": round(ts, 3), "price": round(price, 2)}
                for sym, (ts, price) in latest.items()
            }
            # Detect if all symbols are reporting stale (unchanged) prices
            if self.source and hasattr(self.source, '_stale_counts'):
                all_stale = all(
                    self.source._stale_counts.get(s, 0) > 5
                    for s in self.perceptor.symbols
                )
                payload["all_stale"] = all_stale

        if self._queue is None:
            return
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def _get_instruments(self) -> dict:
        """Return current instrument programs as {ch0: program, ch1: program, ...}."""
        if self.engine is None:
            return {}
        result = {}
        for name, cfg in self.engine.channels.items():
            result[f"ch{cfg.channel}"] = cfg.program
        return result

    def _get_state(self) -> dict:
        if self.engine is None:
            return {
                "bpm": self.config.engine.bpm,
                "key": self.config.engine.key,
                "scale": self.config.engine.scale,
                "bar": 0, "beat": 0,
                "source": self.config.source.type,
                "mapper": self.config.mapping.type,
                "running": self._running,
                "symbols": self._get_symbols() if self._is_stock_mode() else [],
                "sound_mode": self._sound_mode,
                "muted": self._muted,
                "instruments": self._get_instruments(),
            }
        seq = self.engine.sequencer
        return {
            "bpm": round(seq.bpm, 1),
            "key": self.engine.root,
            "scale": self.engine.scale,
            "bar": seq.current_bar,
            "beat": seq.current_beat,
            "source": self.config.source.type,
            "mapper": self.config.mapping.type,
            "running": self._running,
            "symbols": self._get_symbols() if self._is_stock_mode() else [],
            "sound_mode": self._sound_mode,
            "instruments": self._get_instruments(),
        }

    def get_init_message(self) -> dict:
        msg = {
            "type": "init",
            "state": self._get_state(),
            "options": {
                "keys": list(NOTE_MAP.keys()),
                "scales": list(SCALES.keys()),
                "sources": ["random_walk", "stock"],
                "mappers": ["rule_based", "ml"],
            },
        }
        # Send full price history on connect so chart populates immediately
        if isinstance(self.perceptor, MultiSymbolPerceptor):
            history = self.perceptor.get_price_history()
            msg["price_history"] = {
                sym: [{"ts": round(ts, 3), "price": round(p, 2)} for ts, p in pts]
                for sym, pts in history.items()
            }
        return msg

    def ensure_queue(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=100)

    async def broadcast_loop(self) -> None:
        self.ensure_queue()
        while True:
            payload = await self._queue.get()
            data = json.dumps(payload)
            disconnected = set()
            for ws in self._clients:
                try:
                    await ws.send_text(data)
                except Exception:
                    disconnected.add(ws)
            self._clients -= disconnected

    async def handle_command(self, data: dict) -> None:
        cmd = data.get("cmd")
        value = data.get("value")

        if cmd == "set_bpm":
            bpm = int(value)
            if self.engine:
                self.engine.config.bpm = bpm
                self.engine.set_tempo(bpm)

        elif cmd == "set_key":
            if self.engine:
                self.engine.set_key(str(value), self.engine.scale)
                self.engine.root = str(value)

        elif cmd == "set_scale":
            if self.engine:
                self.engine.set_key(self.engine.root, str(value))
                self.engine.scale = str(value)

        elif cmd == "set_instrument":
            # value is {channel: int, program: int}
            ch = int(value.get("channel", 0))
            prog = int(value.get("program", 0))
            # Send program_change to synth immediately
            from ..engine.midi_out import program_change
            self.synth.send(program_change(ch, prog))
            # Update the engine's channel config so it persists
            if self.engine:
                for name, cfg in self.engine.channels.items():
                    if cfg.channel == ch:
                        cfg.program = prog
                        break
            await self._send_state_update()

        elif cmd == "set_mapper":
            self.config.mapping.type = str(value)
            new_mapper = MapperRegistry.create(self.config.mapping)
            self.mapper = new_mapper
            if self.pipeline:
                self.pipeline.mapper = new_mapper

        elif cmd == "set_source":
            await self._swap_source(str(value))
            await self._send_state_update()

        elif cmd == "set_symbols":
            # value is a list of symbol strings
            symbols = [s.upper().strip() for s in value if s.strip()][:3]
            if symbols:
                self.config.source.stock.symbols = symbols
                if self._is_stock_mode():
                    await self._swap_source("stock")
                await self._send_state_update()

        elif cmd == "set_sound_mode":
            mode = str(value)
            if mode in ("ambient", "standard", "chord") and mode != self._sound_mode:
                self._sound_mode = mode
                if self._is_stock_mode() and self._running:
                    await self._hot_swap_engine()
                await self._send_state_update()

        elif cmd == "mute":
            self._muted = True
            if self.pipeline:
                self.pipeline.muted = True
            # Silence all channels immediately
            from ..engine.midi_out import all_notes_off
            for ch in range(16):
                self.synth.send(all_notes_off(ch))
            await self._send_state_update()

        elif cmd == "unmute":
            self._muted = False
            if self.pipeline:
                self.pipeline.muted = False
            # Re-send program changes so instruments are ready
            if self.engine:
                from ..engine.midi_out import setup_channels
                for msg in setup_channels(self.engine.channels):
                    self.synth.send(msg)
            await self._send_state_update()

        elif cmd == "stop":
            await self._stop_pipeline()
            await self._send_state_update()

        elif cmd == "start":
            await self._start_pipeline()
            await self._send_state_update()

    async def _send_state_update(self) -> None:
        payload = json.dumps({"type": "state", "state": self._get_state()})
        disconnected = set()
        for ws in self._clients:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.add(ws)
        self._clients -= disconnected

    async def _start_pipeline(self) -> None:
        if self._running:
            return
        self.ensure_queue()
        self._running = True

        # Create source
        self.source = SourceRegistry.create(self.config.source)

        # Create perceptor + engine based on mode
        if self._is_stock_mode():
            symbols = self._get_symbols()
            # Use smaller window for stock — each symbol only gets 1 sample per poll
            from ..config import PerceptionConfig
            stock_perception = PerceptionConfig(window_size=10)
            self.perceptor = MultiSymbolPerceptor(stock_perception, symbols)

            if self._sound_mode == "ambient":
                self.engine = _make_stock_engine(self.config, symbols)
                self.config.mapping.preset = "stock_ambient"
            elif self._sound_mode == "chord":
                self.engine = _make_chord_engine(self.config, symbols)
                self.config.mapping.preset = "stock_ambient"
            else:
                # Standard mode: use the regular MusicEngine with stock data
                self.engine = MusicEngine(self.config.engine)
                self.config.mapping.preset = "stock_basic"

            self.mapper = MapperRegistry.create(self.config.mapping)
        else:
            self.perceptor = WindowedPerceptor(self.config.perception)
            # Reuse engine if it's already a standard MusicEngine, else create fresh
            if not isinstance(self.engine, MusicEngine):
                self.engine = MusicEngine(self.config.engine)
            # Always ensure mapper matches config preset
            self.config.mapping.preset = self.config.mapping.preset or "stock_basic"
            self.mapper = MapperRegistry.create(self.config.mapping)

        self.pipeline = Pipeline(
            self.source, self.perceptor, self.mapper, self.engine, self.synth
        )
        self.pipeline.set_event_callback(self.on_pipeline_event)
        await self.source.start()
        self._pipeline_task = asyncio.create_task(self._run_pipeline())

    async def _stop_pipeline(self) -> None:
        if not self._running:
            return
        self._running = False
        if self.source:
            await self.source.stop()
        if self._pipeline_task:
            self._pipeline_task.cancel()
            try:
                await self._pipeline_task
            except asyncio.CancelledError:
                pass
            self._pipeline_task = None
        # Silence all channels
        from ..engine.midi_out import all_notes_off
        for ch in range(16):
            self.synth.send(all_notes_off(ch))
        # Drain queue
        if self._queue:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def _hot_swap_engine(self) -> None:
        """Swap engine and mapper in-place without restarting the source/perceptor."""
        from ..engine.midi_out import all_notes_off, setup_channels

        # Silence current notes
        for ch in range(16):
            self.synth.send(all_notes_off(ch))

        # Build new engine + mapper based on current sound mode
        symbols = self._get_symbols()
        if self._sound_mode == "ambient":
            self.engine = _make_stock_engine(self.config, symbols)
            self.config.mapping.preset = "stock_ambient"
        elif self._sound_mode == "chord":
            self.engine = _make_chord_engine(self.config, symbols)
            self.config.mapping.preset = "stock_ambient"
        else:
            self.engine = MusicEngine(self.config.engine)
            self.config.mapping.preset = "stock_basic"
        self.mapper = MapperRegistry.create(self.config.mapping)

        # Send program_change messages to set up new instruments
        for msg in setup_channels(self.engine.channels):
            self.synth.send(msg)

        # Update the live pipeline references
        if self.pipeline:
            self.pipeline.engine = self.engine
            self.pipeline.mapper = self.mapper

    async def _swap_source(self, source_type: str) -> None:
        was_running = self._running
        await self._stop_pipeline()
        self.config.source.type = source_type
        # Reset mapper to default preset when switching away from stock
        if source_type != "stock":
            self.config.mapping.preset = "stock_basic"
            self.mapper = MapperRegistry.create(self.config.mapping)
        if was_running:
            await self._start_pipeline()

    async def _run_pipeline(self) -> None:
        try:
            await self.pipeline.run()
        except asyncio.CancelledError:
            pass


class _NullSynth:
    def start(self): ...
    def stop(self): ...
    def send(self, msg): ...
    def set_instrument(self, ch, prog): ...


def run_web(config: AppConfig, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the web UI server."""
    from contextlib import asynccontextmanager

    import uvicorn
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    bridge = WebBridge(config)
    static_dir = Path(__file__).parent.parent / "web" / "static"

    @asynccontextmanager
    async def lifespan(app):
        asyncio.create_task(bridge.broadcast_loop())
        await bridge._start_pipeline()
        yield
        await bridge._stop_pipeline()
        bridge.synth.stop()

    app = FastAPI(title="cam_to_midi", lifespan=lifespan)

    @app.get("/")
    async def index():
        return HTMLResponse((static_dir / "index.html").read_text())

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        bridge._clients.add(ws)
        try:
            await ws.send_text(json.dumps(bridge.get_init_message()))
            while True:
                data = await ws.receive_text()
                try:
                    cmd = json.loads(data)
                    await bridge.handle_command(cmd)
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            bridge._clients.discard(ws)
        except Exception:
            bridge._clients.discard(ws)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    print(f"\n  cam_to_midi web UI: http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
