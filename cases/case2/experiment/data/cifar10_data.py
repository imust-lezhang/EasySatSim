from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

CIFAR10_CLASSES = (
    "plane",
    "car",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
)
CIFAR10_IMAGE_SHAPE = (3, 32, 32)
CIFAR10_IMAGE_BYTE_SIZE = (
    CIFAR10_IMAGE_SHAPE[0] * CIFAR10_IMAGE_SHAPE[1] * CIFAR10_IMAGE_SHAPE[2]
)
CIFAR10_INDEX_BYTE_SIZE = 4


@dataclass
class Case2Cifar10Datasets:
    data_root: object
    train_dataset: object
    test_dataset: object
    train_indices: list
    test_indices: list
    classes: tuple


def resolve_case2_path(file_path):
    path = Path(file_path)
    if path.is_absolute():
        return path

    text_path = str(file_path).replace("\\", "/")
    if text_path.startswith("../"):
        return (PROJECT_ROOT / "src" / path).resolve()
    return (PROJECT_ROOT / path).resolve()


def require_torchvision():
    try:
        import torch
        from torchvision import datasets, transforms
        from torch.utils.data import random_split
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Case 2 data loading requires torch and torchvision. "
            "Install them before loading CIFAR-10."
        ) from exc
    return torch, datasets, transforms, random_split


def get_cifar10_transform():
    _, _, transforms, _ = require_torchvision()
    return transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
    ])


def load_case2_cifar10(download=False, data_root=None, train_split=None,
                       test_split=None, seed=None, transform=None):
    cg = get_case2_config()
    torch, datasets, _, random_split = require_torchvision()

    if data_root is None:
        data_root = cg.CIFAR10_DATA_ROOT
    if train_split is None:
        train_split = cg.CIFAR10_TRAIN_SPLIT
    if test_split is None:
        test_split = cg.CIFAR10_TEST_SPLIT
    if seed is None:
        seed = cg.CASE_RANDOM_SEED
    if transform is None:
        transform = get_cifar10_transform()

    resolved_data_root = resolve_case2_path(data_root)
    full_dataset = datasets.CIFAR10(
        root=str(resolved_data_root),
        train=True,
        download=download,
        transform=transform,
    )

    expected_size = train_split + test_split
    if expected_size != len(full_dataset):
        raise ValueError(
            "CIFAR10_TRAIN_SPLIT + CIFAR10_TEST_SPLIT must equal the "
            f"CIFAR-10 training-set size. Got {expected_size}, "
            f"but CIFAR-10 train=True has {len(full_dataset)} samples."
        )

    generator = torch.Generator().manual_seed(seed)
    train_dataset, test_dataset = random_split(
        full_dataset,
        [train_split, test_split],
        generator=generator,
    )
    return Case2Cifar10Datasets(
        data_root=resolved_data_root,
        train_dataset=train_dataset,
        test_dataset=test_dataset,
        train_indices=list(train_dataset.indices),
        test_indices=list(test_dataset.indices),
        classes=CIFAR10_CLASSES,
    )


def get_dataset_targets(dataset):
    if hasattr(dataset, "indices") and hasattr(dataset, "dataset"):
        base_targets = get_dataset_targets(dataset.dataset)
        return [int(base_targets[index]) for index in dataset.indices]

    if hasattr(dataset, "targets"):
        return [int(target) for target in dataset.targets]

    targets = []
    for index in range(len(dataset)):
        _, target = dataset[index]
        targets.append(int(target))
    return targets


def get_cifar10_sample_payload_size(label=0,
                                    index_byte_size=CIFAR10_INDEX_BYTE_SIZE):
    label_byte_size = len(str(label).encode("utf-8"))
    return CIFAR10_IMAGE_BYTE_SIZE + label_byte_size + index_byte_size


def get_cifar10_sample_payload_summary():
    sizes = [
        get_cifar10_sample_payload_size(label=label)
        for label in range(10)
    ]
    return {
        "image_shape": CIFAR10_IMAGE_SHAPE,
        "image_byte_size": CIFAR10_IMAGE_BYTE_SIZE,
        "index_byte_size": CIFAR10_INDEX_BYTE_SIZE,
        "min_sample_payload_size": min(sizes),
        "max_sample_payload_size": max(sizes),
        "typical_sample_payload_size": sizes[0],
    }


def get_case2_config():
    from configuration import simulation_config as cg
    from src.tools.config_loader import load_configuration

    if not hasattr(cg, "LEARNING_ARCHITECTURE"):
        cg = load_configuration("cases/case2/src")
    return cg
