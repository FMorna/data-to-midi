from __future__ import annotations

"""CLI entry point: python -m data_to_midi"""

import asyncio

import click

from .app import App
from .config import AppConfig, load_config


@click.group(invoke_without_command=True)
@click.option("--config", "config_path", default="config/default.yaml", help="Path to config file")
@click.option("--source", type=click.Choice(["stock", "random_walk"]), default=None)
@click.option("--mapper", type=click.Choice(["rule_based", "ml"]), default=None)
@click.option("--preset", default=None, help="Mapping preset name")
@click.option("--bpm", type=int, default=None)
@click.option("--key", default=None, help="Musical key (e.g. C, D, A)")
@click.option("--scale", default=None, help="Scale name (e.g. major, minor, pentatonic_minor)")
@click.pass_context
def cli(ctx, config_path, source, mapper, preset, bpm, key, scale):
    """data_to_midi: Turn live systems into real-time music."""
    if ctx.invoked_subcommand is not None:
        return

    cfg = load_config(config_path)
    _apply_overrides(cfg, source, mapper, preset, bpm, key, scale)

    app = App(cfg)
    asyncio.run(app.run())


@cli.command()
@click.option("--bpm", type=int, default=None)
@click.option("--key", default=None)
@click.option("--scale", default=None)
def demo(bpm, key, scale):
    """Run with synthetic random-walk data — no API key needed."""
    cfg = load_config("config/default.yaml")
    cfg.source.type = "random_walk"
    _apply_overrides(cfg, None, None, None, bpm, key, scale)

    app = App(cfg)
    asyncio.run(app.run())


@cli.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--provider", type=click.Choice(["yfinance", "finnhub"]), default="yfinance")
@click.option("--mapper", type=click.Choice(["rule_based", "ml"]), default=None)
@click.option("--bpm", type=int, default=None)
@click.option("--key", default=None)
@click.option("--scale", default=None)
def stock(symbols, provider, mapper, bpm, key, scale):
    """Run with live stock market data."""
    cfg = load_config("config/default.yaml")
    cfg.source.type = "stock"
    cfg.source.stock.symbols = list(symbols)
    cfg.source.stock.provider = provider
    _apply_overrides(cfg, None, mapper, None, bpm, key, scale)

    app = App(cfg)
    asyncio.run(app.run())


@cli.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", type=int, default=8080, help="Server port")
@click.option("--config", "config_path", default="config/default.yaml", help="Path to config file")
def web(host, port, config_path):
    """Launch the web UI in your browser."""
    cfg = load_config(config_path)
    from .ui.web_server import run_web
    run_web(cfg, host=host, port=port)


def _apply_overrides(cfg: AppConfig, source, mapper, preset, bpm, key, scale):
    if source:
        cfg.source.type = source
    if mapper:
        cfg.mapping.type = mapper
    if preset:
        cfg.mapping.preset = preset
    if bpm:
        cfg.engine.bpm = bpm
    if key:
        cfg.engine.key = key
    if scale:
        cfg.engine.scale = scale


if __name__ == "__main__":
    cli()
