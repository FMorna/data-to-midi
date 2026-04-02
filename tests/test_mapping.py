from data_to_midi.mapping.ml_mapper import MLMapper
from data_to_midi.mapping.rule_based import RuleBasedMapper, _apply_curve
from data_to_midi.perception.features import FeatureVector


class TestApplyCurve:
    def test_linear_identity(self):
        spec = {"curve": "linear", "input_range": [0, 1], "output_range": [0, 1]}
        assert _apply_curve(0.5, spec) == 0.5

    def test_linear_scaling(self):
        spec = {"curve": "linear", "input_range": [0, 1], "output_range": [0, 100]}
        assert _apply_curve(0.5, spec) == 50.0

    def test_invert(self):
        spec = {"curve": "linear", "input_range": [0, 1], "output_range": [0, 1], "invert": True}
        assert _apply_curve(0.0, spec) == 1.0

    def test_exponential(self):
        spec = {
            "curve": "exponential", "exponent": 2.0,
            "input_range": [0, 1], "output_range": [0, 1],
        }
        result = _apply_curve(0.5, spec)
        assert abs(result - 0.25) < 0.01  # 0.5^2 = 0.25

    def test_clamping(self):
        spec = {"curve": "linear", "input_range": [0, 1], "output_range": [0, 1]}
        assert _apply_curve(2.0, spec) == 1.0
        assert _apply_curve(-1.0, spec) == 0.0


class TestRuleBasedMapper:
    def test_output_range(self):
        mapper = RuleBasedMapper("stock_basic", "config")
        features = FeatureVector(
            timestamp=0, change_rate=0, periodicity=0.5,
            intensity=0.5, direction=0, volatility=0.5, density=0.5,
        )
        event = mapper.map(features)
        assert 0 <= event.pitch_hint <= 1
        assert 0 <= event.velocity <= 1
        assert 0 <= event.duration_hint <= 1
        assert 0 <= event.density_hint <= 1
        assert 0 <= event.urgency <= 1


class TestMLMapper:
    def test_default_transform_output_range(self):
        mapper = MLMapper()  # No model, uses default transform
        features = FeatureVector(
            timestamp=0, change_rate=0.3, periodicity=0.5,
            intensity=0.6, direction=0.2, volatility=0.4, density=0.5,
        )
        event = mapper.map(features)
        assert 0 <= event.pitch_hint <= 1
        assert 0 <= event.velocity <= 1
        assert 0 <= event.duration_hint <= 1

    def test_extreme_features(self):
        mapper = MLMapper()
        features = FeatureVector(
            timestamp=0, change_rate=1.0, periodicity=1.0,
            intensity=1.0, direction=1.0, volatility=1.0, density=1.0,
        )
        event = mapper.map(features)
        assert 0 <= event.pitch_hint <= 1
        assert 0 <= event.velocity <= 1
