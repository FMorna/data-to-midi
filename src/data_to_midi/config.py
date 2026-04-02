from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class StockConfig:
    symbols: list[str] = field(default_factory=lambda: ["NOS.LS", "EDP.LS", "BRISA.LS"])
    provider: str = "yfinance"
    poll_interval_sec: float = 5.0


@dataclass
class RandomWalkConfig:
    tick_interval_sec: float = 0.2
    volatility: float = 0.02
    initial_price: float = 100.0


@dataclass
class SourceConfig:
    type: str = "random_walk"
    stock: StockConfig = field(default_factory=StockConfig)
    random_walk: RandomWalkConfig = field(default_factory=RandomWalkConfig)


@dataclass
class PerceptionConfig:
    window_size: int = 50


@dataclass
class MappingConfig:
    type: str = "rule_based"
    preset: str = "stock_basic"
    ml_model_path: str = "models/default.joblib"


@dataclass
class ChannelConfig:
    channel: int = 0
    program: int = 0


@dataclass
class EngineConfig:
    bpm: int = 120
    key: str = "C"
    scale: str = "major"
    time_signature: list[int] = field(default_factory=lambda: [4, 4])
    auto_key_change: bool = True
    mode: str = "standard"  # "standard" or "ambient_stock"
    velocity_range: list[int] = field(default_factory=lambda: [30, 120])
    channels: dict[str, ChannelConfig] = field(default_factory=lambda: {
        "melody": ChannelConfig(0, 0),
        "bass": ChannelConfig(1, 32),
        "pad": ChannelConfig(2, 48),
        "drums": ChannelConfig(9, 0),
    })


@dataclass
class SynthConfig:
    backend: str = "fluidsynth"
    soundfont: str = "soundfonts/FluidR3_GM.sf2"
    gain: float = 0.8


@dataclass
class UIConfig:
    show_dashboard: bool = True


@dataclass
class AppConfig:
    source: SourceConfig = field(default_factory=SourceConfig)
    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    mapping: MappingConfig = field(default_factory=MappingConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    synth: SynthConfig = field(default_factory=SynthConfig)
    ui: UIConfig = field(default_factory=UIConfig)


# Map of field type name (as string) -> actual dataclass type for nested building
_NESTED_TYPES = {
    "SourceConfig": SourceConfig,
    "StockConfig": StockConfig,
    "RandomWalkConfig": RandomWalkConfig,
    "PerceptionConfig": PerceptionConfig,
    "MappingConfig": MappingConfig,
    "EngineConfig": EngineConfig,
    "SynthConfig": SynthConfig,
    "UIConfig": UIConfig,
    "ChannelConfig": ChannelConfig,
}


def _build_dataclass(cls, data: dict):
    """Recursively build a dataclass from a dict, ignoring unknown keys."""
    if data is None:
        return cls()
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(cls)}
    filtered = {}
    for k, v in data.items():
        if k not in field_names:
            continue
        f = next(f for f in dataclasses.fields(cls) if f.name == k)
        # Resolve the type name (string due to __future__ annotations)
        type_name = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", "")
        nested_cls = _NESTED_TYPES.get(type_name)
        if nested_cls is not None and isinstance(v, dict):
            filtered[k] = _build_dataclass(nested_cls, v)
        elif "ChannelConfig" in str(type_name) and isinstance(v, dict):
            # Handle dict[str, ChannelConfig]
            filtered[k] = {
                name: ChannelConfig(**ch) if isinstance(ch, dict) else ch
                for name, ch in v.items()
            }
        else:
            filtered[k] = v
    return cls(**filtered)


def load_config(path: str | Path) -> AppConfig:
    """Load application config from a YAML file."""
    path = Path(path)
    if not path.exists():
        return AppConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return _build_dataclass(AppConfig, data)


def load_mapping_preset(preset_name: str, config_dir: str | Path = "config") -> dict:
    """Load a mapping preset YAML file."""
    path = Path(config_dir) / "mappings" / f"{preset_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Mapping preset not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def load_scales_config(config_dir: str | Path = "config") -> dict:
    """Load scales and music theory definitions."""
    path = Path(config_dir) / "scales.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scales config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)
