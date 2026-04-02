from data_to_midi.config import AppConfig, load_config, load_mapping_preset


class TestLoadConfig:
    def test_default_config_loads(self):
        config = load_config("config/default.yaml")
        assert isinstance(config, AppConfig)
        assert config.source.type == "random_walk"
        assert config.engine.bpm == 120
        assert config.engine.key == "C"

    def test_missing_config_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, AppConfig)
        assert config.source.type == "random_walk"

    def test_channels_loaded(self):
        config = load_config("config/default.yaml")
        assert "melody" in config.engine.channels
        assert config.engine.channels["melody"].channel == 0


class TestLoadMappingPreset:
    def test_stock_basic_loads(self):
        preset = load_mapping_preset("stock_basic", "config")
        assert "pitch_hint" in preset
        assert "velocity" in preset
        assert preset["pitch_hint"]["source"] == "direction"
