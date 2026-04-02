import asyncio

import pytest

from data_to_midi.config import RandomWalkConfig
from data_to_midi.sources.random_walk import RandomWalkSource


class TestRandomWalkSource:
    @pytest.mark.asyncio
    async def test_yields_samples(self):
        config = RandomWalkConfig(tick_interval_sec=0.01, initial_price=100.0)
        source = RandomWalkSource(config)
        await source.start()

        samples = []
        count = 0
        async for sample in source.stream():
            samples.append(sample)
            count += 1
            if count >= 5:
                await source.stop()
                break

        assert len(samples) == 5

    @pytest.mark.asyncio
    async def test_sample_has_required_fields(self):
        config = RandomWalkConfig(tick_interval_sec=0.01)
        source = RandomWalkSource(config)
        await source.start()

        async for sample in source.stream():
            assert "price" in sample.values
            assert "volume" in sample.values
            assert "change" in sample.values
            assert sample.timestamp > 0
            await source.stop()
            break

    @pytest.mark.asyncio
    async def test_price_stays_positive(self):
        config = RandomWalkConfig(tick_interval_sec=0.001, volatility=0.1)
        source = RandomWalkSource(config)
        await source.start()

        count = 0
        async for sample in source.stream():
            assert sample.values["price"] > 0
            count += 1
            if count >= 100:
                await source.stop()
                break


class TestSourceRegistry:
    def test_create_random_walk(self):
        from data_to_midi.config import SourceConfig
        from data_to_midi.sources.registry import SourceRegistry

        config = SourceConfig(type="random_walk")
        source = SourceRegistry.create(config)
        assert isinstance(source, RandomWalkSource)

    def test_unknown_source_raises(self):
        from data_to_midi.config import SourceConfig
        from data_to_midi.sources.registry import SourceRegistry

        config = SourceConfig(type="nonexistent")
        with pytest.raises(ValueError):
            SourceRegistry.create(config)
