import numpy as np


def add_jitter(sequence: np.ndarray, sigma: float) -> np.ndarray:
    noise = np.random.normal(loc=0.0, scale=sigma, size=sequence.shape)
    return (sequence + noise).astype(np.float32)


def spatial_scaling(sequence: np.ndarray, low: float, high: float) -> np.ndarray:
    scale_factor = np.random.uniform(low, high)
    return (sequence * scale_factor).astype(np.float32)


def time_shift(sequence: np.ndarray, max_shift: int = 3) -> np.ndarray:
    shift = np.random.randint(-max_shift, max_shift + 1)
    if shift == 0:
        return sequence

    shifted = np.roll(sequence, shift, axis=0)

    # Zero-fill the frames exposed by the roll (not real landmark data)
    if shift > 0:
        shifted[:shift] = 0.0
    else:
        shifted[shift:] = 0.0

    return shifted.astype(np.float32)
