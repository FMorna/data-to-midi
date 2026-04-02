import numpy as np
import pytest

from data_to_midi.mapping.musical_params import MusicalEvent
from data_to_midi.perception.features import FeatureVector
from data_to_midi.sources.base import SourceSample


@pytest.fixture
def sample_source_sample():
    return SourceSample(
        timestamp=1000.0,
        values={"price": 100.0, "volume": 5000.0, "change": 0.5},
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_feature_vector():
    return FeatureVector(
        timestamp=1000.0,
        change_rate=0.3,
        periodicity=0.5,
        intensity=0.6,
        direction=0.2,
        volatility=0.4,
        density=0.5,
    )


@pytest.fixture
def sample_musical_event():
    return MusicalEvent(
        pitch_hint=0.5,
        velocity=0.6,
        duration_hint=0.5,
        density_hint=0.3,
        register_hint=0.5,
        urgency=0.4,
    )


@pytest.fixture
def rising_prices():
    """A linearly increasing price series."""
    return np.linspace(100, 110, 50)


@pytest.fixture
def volatile_prices():
    """A highly volatile price series."""
    np.random.seed(42)
    base = np.ones(50) * 100
    noise = np.random.randn(50) * 5
    return base + noise


@pytest.fixture
def flat_prices():
    """A flat price series."""
    return np.ones(50) * 100.0
