import os
import numpy as np


def build_class_map(features_dir: str) -> dict:
    class_names = sorted(os.listdir(features_dir))
    return {name: index for index, name in enumerate(class_names)}


def load_sequences_and_labels(features_dir: str, class_map: dict):
    sequences = []
    labels = []

    for class_name, class_index in class_map.items():
        class_dir = os.path.join(features_dir, class_name)
        for filename in os.listdir(class_dir):
            if not filename.endswith(".npy"):
                continue
            sequence = np.load(os.path.join(class_dir, filename))
            sequences.append(sequence)
            labels.append(class_index)

    return np.array(sequences, dtype=np.float32), np.array(labels, dtype=np.int32)
