"""
Export modelo_dualsign.keras → TF.js format (model.json + weight shards).

tensorflowjs/__init__.py always triggers tf_saved_model_conversion_v2, which
imports two packages that break in this venv:
  - tensorflow_decision_forests: gencode requires protobuf 6.x, runtime is 5.29.6
  - tensorflow_hub: uses pkg_resources which is absent from this venv
Mocking both in sys.modules before any tensorflowjs import intercepts them at
module-load time; the actual Keras→TFJS conversion path never calls either one.
"""
import sys
from unittest.mock import MagicMock

sys.modules["tensorflow_decision_forests"] = MagicMock()
sys.modules["tensorflow_hub"] = MagicMock()

import os
import tensorflow as tf
from tensorflowjs.converters.keras_h5_conversion import save_keras_model

MODEL_PATH = "artifacts/modelo_dualsign.keras"
OUTPUT_DIR = "artifacts/tfjs_export"

print("Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)
print(f"  Input : {model.input_shape}")
print(f"  Output: {model.output_shape}")
print(f"  Params: {model.count_params():,}")

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"\nExporting to {OUTPUT_DIR}/...")
save_keras_model(model, OUTPUT_DIR)

# keras_h5_conversion serializes the topology with Keras 3 snake_case keys,
# but TF.js expects camelCase for these specific layer config fields.
_SNAKE_TO_CAMEL = {
    "batch_shape":           "batchInputShape",
    "return_sequences":      "returnSequences",
    "use_bias":              "useBias",
    "recurrent_activation":  "recurrentActivation",
    "unit_forget_bias":      "unitForgetBias",
    "recurrent_dropout":     "recurrentDropout",
}

import json

model_json_path = os.path.join(OUTPUT_DIR, "model.json")
with open(model_json_path) as f:
    raw = f.read()

for snake, camel in _SNAKE_TO_CAMEL.items():
    raw = raw.replace(f'"{snake}"', f'"{camel}"')

with open(model_json_path, "w") as f:
    f.write(raw)

print("Patched model.json: snake_case keys → camelCase for TF.js compatibility.")
print("Done.")
