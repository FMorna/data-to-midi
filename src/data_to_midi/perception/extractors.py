from __future__ import annotations

"""Feature extraction functions operating on a numpy array of prices.

Each function returns a normalized value. All inputs are assumed to be
a 1D array from a sliding window of sufficient length.
"""

import numpy as np


def extract_change_rate(prices: np.ndarray) -> float:
    """Speed of change, normalized by rolling std. Returns [-1, 1]."""
    if len(prices) < 2:
        return 0.0
    diff = np.diff(prices)
    recent_diff = diff[-1]
    std = np.std(diff)
    if std < 1e-10:
        return 0.0
    return float(np.clip(recent_diff / (3 * std), -1.0, 1.0))


def extract_periodicity(prices: np.ndarray) -> float:
    """Rhythmic regularity via autocorrelation peak strength. Returns [0, 1]."""
    if len(prices) < 4:
        return 0.0
    # Detrend
    detrended = prices - np.linspace(prices[0], prices[-1], len(prices))
    # Normalize
    norm = np.std(detrended)
    if norm < 1e-10:
        return 0.0
    detrended = detrended / norm

    # Autocorrelation via numpy
    n = len(detrended)
    autocorr = np.correlate(detrended, detrended, mode="full")
    autocorr = autocorr[n - 1 :]  # Keep positive lags only
    autocorr = autocorr / autocorr[0]  # Normalize

    # Find the strongest peak after lag 2 (skip trivial peaks at 0,1)
    if len(autocorr) < 4:
        return 0.0
    peak = np.max(autocorr[2:])
    return float(np.clip(peak, 0.0, 1.0))


def extract_intensity(prices: np.ndarray) -> float:
    """Magnitude/energy as absolute z-score of current value. Returns [0, 1]."""
    if len(prices) < 2:
        return 0.0
    mean = np.mean(prices)
    std = np.std(prices)
    if std < 1e-10:
        return 0.0
    z = abs(prices[-1] - mean) / std
    # Map z-score to [0, 1]: z=0 -> 0, z>=3 -> 1
    return float(np.clip(z / 3.0, 0.0, 1.0))


def extract_direction(prices: np.ndarray) -> float:
    """Trend direction via linear regression slope. Returns [-1, 1]."""
    if len(prices) < 2:
        return 0.0
    x = np.arange(len(prices), dtype=float)
    # Simple linear regression
    x_mean = np.mean(x)
    y_mean = np.mean(prices)
    slope = np.sum((x - x_mean) * (prices - y_mean)) / np.sum((x - x_mean) ** 2)

    # Normalize slope by price std
    std = np.std(prices)
    if std < 1e-10:
        return 0.0
    normalized = slope * len(prices) / std
    return float(np.clip(normalized / 3.0, -1.0, 1.0))


def extract_volatility(prices: np.ndarray) -> float:
    """Coefficient of variation (std/mean). Returns [0, 1]."""
    if len(prices) < 2:
        return 0.0
    mean = np.mean(prices)
    if abs(mean) < 1e-10:
        return 0.0
    cv = np.std(prices) / abs(mean)
    # Typical stock CV in a short window is 0-0.05, map to [0, 1]
    return float(np.clip(cv / 0.05, 0.0, 1.0))


def extract_density(prices: np.ndarray) -> float:
    """Direction-change frequency (choppiness). Returns [0, 1]."""
    if len(prices) < 3:
        return 0.0
    diff = np.diff(prices)
    # Count sign changes
    signs = np.sign(diff)
    sign_changes = np.sum(signs[1:] != signs[:-1])
    max_changes = len(diff) - 1
    if max_changes <= 0:
        return 0.0
    return float(sign_changes / max_changes)
