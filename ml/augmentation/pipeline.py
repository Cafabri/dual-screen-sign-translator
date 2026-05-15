import os
import numpy as np
from augmentation.file_utils import list_original_files
from augmentation.variants import AUGMENTATION_VARIANTS, apply_variant


def augment_class_folder(class_dir: str, class_name: str):
    for original_filename in list_original_files(class_dir):
        sequence = np.load(os.path.join(class_dir, original_filename))
        stem = original_filename.replace(".npy", "")

        for suffix, transforms in AUGMENTATION_VARIANTS:
            output_path = os.path.join(class_dir, f"{stem}_{suffix}.npy")
            if os.path.exists(output_path):
                continue
            np.save(output_path, apply_variant(sequence, transforms))

        print(f"  [+] {class_name}/{original_filename} → {len(AUGMENTATION_VARIANTS)} variants generated")
