from __future__ import annotations

from ..config import MappingConfig
from .base import BaseMapper
from .ml_mapper import MLMapper
from .rule_based import RuleBasedMapper


class MapperRegistry:
    @classmethod
    def create(cls, config: MappingConfig, config_dir: str = "config") -> BaseMapper:
        if config.type == "rule_based":
            return RuleBasedMapper(config.preset, config_dir)
        elif config.type == "ml":
            return MLMapper(config.ml_model_path)
        else:
            raise ValueError(
                f"Unknown mapper type: {config.type}. Available: rule_based, ml"
            )
