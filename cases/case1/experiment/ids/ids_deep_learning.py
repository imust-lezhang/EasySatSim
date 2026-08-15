import os
import random
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import Conv1D, Dense, Embedding, GlobalMaxPooling1D, Input
from tensorflow.keras.models import Sequential
from tensorflow.keras.models import load_model as keras_load_model

from cases.case1.experiment.data.normal_payload_library import normal_payload_library
from cases.case1.experiment.data.test_dataset import test_benign_payloads
from cases.case1.experiment.data.test_dataset import test_malicious_payloads


tf.get_logger().setLevel("ERROR")

MAX_SEQUENCE_LENGTH = 128
VOCABULARY_SIZE = 257
RANDOM_SEED = 20260801
DEFAULT_THRESHOLD = 0.9
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = EXPERIMENT_ROOT / "models" / "dl_ids_model.keras"
_MODEL_CACHE = {}


TRAINING_BASE_ATTACK_PATTERNS = [
    "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\x99\xb0\x0b\xcd\x80",
    "\x31\xc0\x31\xdb\xb0\x30\xc1\xe0\x08\xc1\xe8\x10\x40\x50\xcd\x80\x31\xd2\x52\x68\x6e\x2f\x73\x68",
    "\xdb\xc0\xd9\x74\x24\xf4\x5b\x53\x59\x49\x49\x49\x49\x43\x43\x43\x43\x43\x43\x37\x51\x5a\x6a\x41",
    "\x31\xdb\xf7\xe3\xb0\x66\x43\x52\x53\x6a\x02\x89\xe1\xcd\x80\x97\x5b\x52\x66\x68\x11\x5c\x66\x53",
    "\xda\xc3\xb8\x12\xcb\x81\x7c\xd9\x74\x24\xf4\x5b\x2b\xc9\xb1\x56\x83\xc3\x04\x31\x43\x14\x03\x43",
]


def encode_payload(payload, max_sequence_length=MAX_SEQUENCE_LENGTH):
    sequence = [min(ord(char), 255) + 1 for char in payload[:max_sequence_length]]
    if len(sequence) < max_sequence_length:
        sequence.extend([0] * (max_sequence_length - len(sequence)))
    return sequence


def generate_training_malicious_payloads(sample_count=600, seed=RANDOM_SEED):
    rng = random.Random(seed)
    payloads = []
    templates = [
        "case1_malicious_payload family=packed_loader target=port22 intent=unauthorized_command stage=encoded variant={index}",
        "case1_malicious_payload family=credential_dropper target=port22 marker=credential marker=persistence variant={index}",
        "case1_malicious_payload family=staged_port22_probe target=port22 marker=loader marker=callback variant={index}",
    ]

    for index in range(sample_count):
        if index % 4 == 0:
            base_code = rng.choice(TRAINING_BASE_ATTACK_PATTERNS)
            payload = base_code + "\x90" * rng.randint(1, 5) + f" train_variant_{index}"
        elif index % 4 == 1:
            base_code = rng.choice(TRAINING_BASE_ATTACK_PATTERNS)
            payload = "\x90" * rng.randint(1, 5) + base_code + f" train_variant_{index}"
        elif index % 4 == 2:
            base_code = rng.choice(TRAINING_BASE_ATTACK_PATTERNS)
            payload = base_code + f" encoded_stage_{index} target_port22"
        else:
            payload = templates[index % len(templates)].format(index=index)
        payloads.append(payload)
    return payloads


def build_training_data():
    test_payloads = set(test_malicious_payloads) | set(test_benign_payloads)
    malicious_payloads = [
        payload for payload in generate_training_malicious_payloads()
        if payload not in test_payloads
    ]
    normal_payloads = [
        payload for payload in normal_payload_library
        if payload not in test_payloads
    ]

    samples = malicious_payloads + normal_payloads
    labels = [1] * len(malicious_payloads) + [0] * len(normal_payloads)

    rng = random.Random(RANDOM_SEED)
    combined = list(zip(samples, labels))
    rng.shuffle(combined)
    samples, labels = zip(*combined)

    x = np.array([encode_payload(sample) for sample in samples], dtype=np.int32)
    y = np.array(labels, dtype=np.float32)
    return x, y


def train_model(epochs=8, batch_size=32):
    tf.keras.utils.set_random_seed(RANDOM_SEED)
    x_train, y_train = build_training_data()
    model = Sequential([
        Input(shape=(MAX_SEQUENCE_LENGTH,)),
        Embedding(input_dim=VOCABULARY_SIZE, output_dim=16),
        Conv1D(filters=32, kernel_size=5, activation="relu"),
        GlobalMaxPooling1D(),
        Dense(16, activation="relu"),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(x_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0)
    return model


def save_model(model, model_path=DEFAULT_MODEL_PATH):
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    return model_path


def train_and_save_model(model_path=DEFAULT_MODEL_PATH, epochs=8, batch_size=32):
    model = train_model(epochs=epochs, batch_size=batch_size)
    save_model(model=model, model_path=model_path)
    return model


def load_trained_model(model_path=DEFAULT_MODEL_PATH):
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"DL IDS model was not found: {model_path}. "
            "Run: python -m cases.case1.experiment.ids.train_ids_deep_learning"
        )
    return keras_load_model(str(model_path), compile=False)


def get_runtime_model(model_path=DEFAULT_MODEL_PATH):
    model_path = Path(model_path).resolve()
    cache_key = str(model_path)
    if cache_key not in _MODEL_CACHE:
        _MODEL_CACHE[cache_key] = load_trained_model(model_path)
    return _MODEL_CACHE[cache_key]


def predict_score(code, model):
    x = np.array([encode_payload(code)], dtype=np.int32)
    prediction = model.predict(x, verbose=0)
    return float(prediction[0][0])


def detect(code, model=None, threshold=DEFAULT_THRESHOLD):
    if model is None:
        model = get_runtime_model()
    score = predict_score(code, model)
    return score >= threshold, score
