"""FastAPI WebSocket server bridging the pipeline to a web frontend."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from ..config import AppConfig, load_config
from ..engine.engine import MusicEngine
from ..engine.theory import NOTE_MAP, SCALES
from ..mapping.musical_params import MusicalEvent
from ..mapping.registry import MapperRegistry
from ..perception.features import FeatureVector
from ..perception.windowed import WindowedPerceptor
from ..pipeline import Pipeline
from ..sources.registry import SourceRegistry

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_name(note: int) -> str:
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


class WebBridge:
    """Bridges the pipeline event callback to WebSocket clients."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._queue = None  # Created lazily on the running event loop
        self._clients: set = set()
        self._running = False

        # Pipeline components (mutable for hot-swapping)
        self.source = SourceRegistry.create(config.source)
        self.perceptor = WindowedPerceptor(config.perception)
        self.mapper = MapperRegistry.create(config.mapping)
        self.engine = MusicEngine(config.engine)

        # Try real synth for audio output, fall back to silent
        try:
            from ..synth.registry import SynthRegistry
            self.synth = SynthRegistry.create(config.synth)
            self.synth.start()
            print(f"  Audio: {config.synth.backend} with {config.synth.soundfont}")
        except Exception as e:
            print(f"  Synth unavailable ({e}), running silent.")
            self.synth = _NullSynth()

        self.pipeline = Pipeline(
            self.source, self.perceptor, self.mapper, self.engine, self.synth
        )
        self.pipeline.set_event_callback(self.on_pipeline_event)

        self._pipeline_task = None

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
        }
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

    def _get_state(self) -> dict:
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
        }

    def get_init_message(self) -> dict:
        return {
            "type": "init",
            "state": self._get_state(),
            "options": {
                "keys": list(NOTE_MAP.keys()),
                "scales": list(SCALES.keys()),
                "sources": ["random_walk", "stock"],
                "mappers": ["rule_based", "ml"],
            },
        }

    def ensure_queue(self) -> None:
        """Create the queue on the running event loop."""
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=100)

    async def broadcast_loop(self) -> None:
        """Continuously read from queue and broadcast to all clients."""
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
            self.engine.config.bpm = bpm
            self.engine.set_tempo(bpm)

        elif cmd == "set_key":
            self.engine.set_key(str(value), self.engine.scale)
            self.engine.root = str(value)

        elif cmd == "set_scale":
            self.engine.set_key(self.engine.root, str(value))
            self.engine.scale = str(value)

        elif cmd == "set_mapper":
            self.config.mapping.type = str(value)
            new_mapper = MapperRegistry.create(self.config.mapping)
            self.mapper = new_mapper
            self.pipeline.mapper = new_mapper

        elif cmd == "set_source":
            await self._swap_source(str(value))
            await self._send_state_update()

        elif cmd == "stop":
            await self._stop_pipeline()
            await self._send_state_update()

        elif cmd == "start":
            await self._start_pipeline()
            await self._send_state_update()

    async def _send_state_update(self) -> None:
        """Push a state update to all clients immediately (for stop/start feedback)."""
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
        self.source = SourceRegistry.create(self.config.source)
        self.perceptor = WindowedPerceptor(self.config.perception)
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
        await self.source.stop()
        if self._pipeline_task:
            self._pipeline_task.cancel()
            try:
                await self._pipeline_task
            except asyncio.CancelledError:
                pass
            self._pipeline_task = None
        # Silence all channels — send all-notes-off CC 123
        from ..engine.midi_out import all_notes_off
        for ch in range(16):
            self.synth.send(all_notes_off(ch))
        # Drain the queue so stale ticks don't replay on restart
        if self._queue:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def _swap_source(self, source_type: str) -> None:
        was_running = self._running
        await self._stop_pipeline()
        self.config.source.type = source_type
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
