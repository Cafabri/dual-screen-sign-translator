import sys
import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import config
from augmentation.file_utils import count_all_npy_files
from augmentation.pipeline import augment_class_folder


def main():
    initial_count = count_all_npy_files(config.FEATURES_DIR)
    print(f"[Augment] Initial .npy count : {initial_count}\n")

    for class_name in sorted(os.listdir(config.FEATURES_DIR)):
        class_dir = os.path.join(config.FEATURES_DIR, class_name)
        if not os.path.isdir(class_dir):
            continue
        print(f"[Augment] Processing class: {class_name}")
        augment_class_folder(class_dir, class_name)

    final_count = count_all_npy_files(config.FEATURES_DIR)
    print(f"\n[Augment] Done.")
    print(f"[Augment] Initial files : {initial_count}")
    print(f"[Augment] Final files   : {final_count}")
    print(f"[Augment] New samples   : {final_count - initial_count}")


if __name__ == "__main__":
    main()
