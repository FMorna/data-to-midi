import numpy as np

from cam_to_midi.perception.extractors import (
    extract_change_rate,
    extract_density,
    extract_direction,
    extract_intensity,
    extract_periodicity,
    extract_volatility,
)
from cam_to_midi.perception.windowed import WindowedPerceptor
from cam_to_midi.sources.base import SourceSample


class TestExtractors:
    def test_direction_rising(self, rising_prices):
        d = extract_direction(rising_prices)
        assert d > 0.5, f"Expected positive direction for rising prices, got {d}"

    def test_direction_falling(self, rising_prices):
        falling = rising_prices[::-1]
        d = extract_direction(falling)
        assert d < -0.5, f"Expected negative direction for falling prices, got {d}"

    def test_direction_flat(self, flat_prices):
        d = extract_direction(flat_prices)
        assert abs(d) < 0.1, f"Expected near-zero direction for flat prices, got {d}"

    def test_volatility_high(self, volatile_prices):
        v = extract_volatility(volatile_prices)
        assert v > 0.3, f"Expected high volatility, got {v}"

    def test_volatility_low(self, flat_prices):
        v = extract_volatility(flat_prices)
        assert v < 0.01, f"Expected near-zero volatility for flat prices, got {v}"

    def test_density_choppy(self):
        # Alternating up/down
        prices = np.array([100, 101, 99, 101, 99, 101, 99, 101, 99, 101])
        d = extract_density(prices)
        assert d > 0.7, f"Expected high density for choppy prices, got {d}"

    def test_density_smooth(self, rising_prices):
        d = extract_density(rising_prices)
        assert d < 0.3, f"Expected low density for smooth rise, got {d}"

    def test_intensity_normal(self, rising_prices):
        i = extract_intensity(rising_prices)
        assert 0 <= i <= 1

    def test_change_rate_bounds(self, volatile_prices):
        cr = extract_change_rate(volatile_prices)
        assert -1 <= cr <= 1

    def test_periodicity_bounds(self, volatile_prices):
        p = extract_periodicity(volatile_prices)
        assert 0 <= p <= 1


class TestWindowedPerceptor:
    def test_returns_none_until_window_full(self):
        from cam_to_midi.config import PerceptionConfig

        config = PerceptionConfig(window_size=5)
        perceptor = WindowedPerceptor(config)

        for i in range(4):
            result = perceptor.update(
                SourceSample(timestamp=float(i), values={"price": 100.0 + i})
            )
            assert result is None

        result = perceptor.update(
            SourceSample(timestamp=5.0, values={"price": 105.0})
        )
        assert result is not None

    def test_feature_vector_fields(self):
        from cam_to_midi.config import PerceptionConfig

        config = PerceptionConfig(window_size=5)
        perceptor = WindowedPerceptor(config)

        for i in range(5):
            result = perceptor.update(
                SourceSample(timestamp=float(i), values={"price": 100.0 + i * 2})
            )

        assert result is not None
        assert hasattr(result, "change_rate")
        assert hasattr(result, "direction")
        assert hasattr(result, "volatility")

    def test_reset(self):
        from cam_to_midi.config import PerceptionConfig

        config = PerceptionConfig(window_size=5)
        perceptor = WindowedPerceptor(config)

        for i in range(5):
            perceptor.update(
                SourceSample(timestamp=float(i), values={"price": 100.0})
            )

        perceptor.reset()
        result = perceptor.update(
            SourceSample(timestamp=10.0, values={"price": 100.0})
        )
        assert result is None  # Window not full after reset
