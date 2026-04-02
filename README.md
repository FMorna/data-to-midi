# data_to_midi

Turn live data streams into real-time MIDI music. Stock market prices drive ambient, harmonious compositions where each company becomes a musical voice.

## How it works

A 5-stage pipeline transforms raw data into music:

```
Data Source -> Perception -> Mapping -> Music Engine -> Synth
```

- **Source**: Live stock prices (via yfinance) or synthetic random walk data
- **Perception**: Sliding-window feature extraction (change rate, volatility, direction, intensity, periodicity, density)
- **Mapping**: Rule-based or ML translation of features into musical parameters
- **Engine**: Three sound modes for stock data:
  - **Ambient** -- each stock symbol drives a separate drone/pad instrument
  - **Chord** -- all symbols fuse into unified 3-note chords
  - **Standard** -- piano/bass/strings arrangement
- **Synth**: FluidSynth with General MIDI SoundFont, self-contained audio output

## Features

- Real-time web dashboard with perception gauges, piano roll, and stock price chart
- Up to 3 stock symbols tracked simultaneously, each contributing to the music
- Per-channel instrument selection from 70+ curated General MIDI instruments
- Live controls: BPM, key, scale, source, mapper, sound mode, mute
- Music anchored in real market data -- price movements drive pitch, volatility drives rhythm
- Notes avoid repetition (same note sustains rather than re-triggering)
- Chord progressions adapt to market mood (rising, falling, volatile, calm)

## Quick start

```bash
# Install
pip install -e ".[all]"

# System dependency (macOS)
brew install fluidsynth

# Download a GM SoundFont into soundfonts/ (e.g., GeneralUser_GS.sf2)

# Launch
python -m data_to_midi web
# Open http://127.0.0.1:8080
```

## Web UI controls

- **Source**: Switch between Random Walk (synthetic) and Stock Market (live)
- **Symbols**: Choose up to 3 stock ticker symbols (e.g., NOS.LS, EDP.LS, BRISA.LS)
- **Sound Mode**: Ambient (drone/pad), Chord (unified harmony), Standard (piano/bass)
- **Instruments**: Change the GM instrument for each channel in real-time
- **Key/Scale**: Set musical key and scale (auto chord progressions adapt)
- **BPM**: Adjust tempo (engine also drifts slightly based on market urgency)
- **Mute**: Silence audio while keeping the data feed and visualizations active

## Testing

```bash
python -m pytest tests/ -v
```

## License

MIT
