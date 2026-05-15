import numpy as np
from augmentation.transforms import add_jitter, spatial_scaling, time_shift

AUGMENTATION_VARIANTS = [
    ("aug_jitter_soft",  ["jitter_soft"]),
    ("aug_jitter_hard",  ["jitter_hard"]),
    ("aug_scale_down",   ["scale_down"]),
    ("aug_scale_up",     ["scale_up"]),
    ("aug_shift",        ["shift"]),
    ("aug_jitter_scale", ["jitter_mid", "scale_mid"]),
    ("aug_jitter_shift", ["jitter_mid", "shift"]),
    ("aug_scale_shift",  ["scale_mid", "shift"]),
    ("aug_full",         ["jitter_mid", "scale_mid", "shift"]),
]

_TRANSFORM_REGISTRY = {
    "jitter_soft": lambda s: add_jitter(s, sigma=0.003),
    "jitter_mid":  lambda s: add_jitter(s, sigma=0.005),
    "jitter_hard": lambda s: add_jitter(s, sigma=0.007),
    "scale_down":  lambda s: spatial_scaling(s, low=0.88, high=0.97),
    "scale_mid":   lambda s: spatial_scaling(s, low=0.90, high=1.10),
    "scale_up":    lambda s: spatial_scaling(s, low=1.03, high=1.12),
    "shift":       lambda s: time_shift(s, max_shift=3),
}


def apply_variant(sequence: np.ndarray, transform_names: list) -> np.ndarray:
    augmented = sequence.copy()
    for name in transform_names:
        augmented = _TRANSFORM_REGISTRY[name](augmented)
    return augmented
