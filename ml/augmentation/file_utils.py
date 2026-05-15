import os


def is_original_file(filename: str) -> bool:
    return filename.endswith(".npy") and "_aug_" not in filename


def list_original_files(class_dir: str) -> list:
    return [f for f in os.listdir(class_dir) if is_original_file(f)]


def count_all_npy_files(features_dir: str) -> int:
    total = 0
    for entry in os.listdir(features_dir):
        class_dir = os.path.join(features_dir, entry)
        if os.path.isdir(class_dir):
            total += sum(1 for f in os.listdir(class_dir) if f.endswith(".npy"))
    return total
