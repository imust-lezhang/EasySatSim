import json
from dataclasses import dataclass

import numpy as np

from cases.case2.experiment.data.cifar10_data import get_dataset_targets
from cases.case2.experiment.data.cifar10_data import resolve_case2_path


@dataclass
class UserDataPartition:
    user_id: int
    indices: list
    primary_classes: tuple
    class_counts: dict


@dataclass
class UserDataPartitions:
    mode: str
    seed: int
    samples_per_user: int
    user_number: int
    partitions: list

    def as_index_lists(self):
        return [partition.indices for partition in self.partitions]


def create_user_partitions(dataset, user_number, samples_per_user,
                           mode="non_iid", seed=0,
                           primary_classes_per_user=2,
                           dominant_fraction=0.8,
                           with_replacement=True):
    targets = get_dataset_targets(dataset)
    if len(targets) == 0:
        raise ValueError("Cannot create user partitions from an empty dataset.")

    normalized_mode = str(mode).strip().lower().replace("-", "_")
    if normalized_mode == "iid":
        partitions = create_iid_partitions(
            targets=targets,
            user_number=user_number,
            samples_per_user=samples_per_user,
            seed=seed,
            with_replacement=with_replacement,
        )
    elif normalized_mode in ("non_iid", "noniid"):
        partitions = create_non_iid_partitions(
            targets=targets,
            user_number=user_number,
            samples_per_user=samples_per_user,
            seed=seed,
            primary_classes_per_user=primary_classes_per_user,
            dominant_fraction=dominant_fraction,
            with_replacement=with_replacement,
        )
        normalized_mode = "non_iid"
    else:
        raise ValueError(f"Unsupported partition mode: {mode!r}")

    return UserDataPartitions(
        mode=normalized_mode,
        seed=seed,
        samples_per_user=samples_per_user,
        user_number=user_number,
        partitions=partitions,
    )


def create_iid_partitions(targets, user_number, samples_per_user, seed,
                          with_replacement=True):
    rng = np.random.default_rng(seed)
    all_indices = np.arange(len(targets), dtype=np.int64)
    partitions = []

    if not with_replacement and user_number * samples_per_user > len(all_indices):
        raise ValueError(
            "IID partition without replacement is impossible because the "
            "requested sample count exceeds the available training samples."
        )

    if with_replacement:
        for user_id in range(user_number):
            indices = rng.choice(all_indices, size=samples_per_user, replace=True)
            partitions.append(build_user_partition(user_id, indices, (), targets))
        return partitions

    shuffled_indices = rng.permutation(all_indices)
    for user_id in range(user_number):
        start = user_id * samples_per_user
        end = start + samples_per_user
        indices = shuffled_indices[start:end]
        partitions.append(build_user_partition(user_id, indices, (), targets))
    return partitions


def create_non_iid_partitions(targets, user_number, samples_per_user, seed,
                              primary_classes_per_user=2,
                              dominant_fraction=0.8,
                              with_replacement=True):
    if not 0.0 <= dominant_fraction <= 1.0:
        raise ValueError("dominant_fraction must be between 0 and 1.")
    if primary_classes_per_user < 1:
        raise ValueError("primary_classes_per_user must be at least 1.")

    rng = np.random.default_rng(seed)
    classes = sorted(set(int(target) for target in targets))
    class_to_indices = build_class_to_indices(targets=targets, classes=classes)
    all_indices = np.arange(len(targets), dtype=np.int64)
    dominant_count = int(round(samples_per_user * dominant_fraction))
    background_count = samples_per_user - dominant_count
    partitions = []

    for user_id in range(user_number):
        primary_classes = tuple(
            classes[(user_id + offset) % len(classes)]
            for offset in range(primary_classes_per_user)
        )
        selected_indices = []
        for class_id, count in zip(
                primary_classes,
                split_counts(dominant_count, len(primary_classes))):
            selected_indices.extend(sample_indices(
                rng=rng,
                candidates=class_to_indices[class_id],
                count=count,
                with_replacement=with_replacement,
            ))

        selected_indices.extend(sample_indices(
            rng=rng,
            candidates=all_indices,
            count=background_count,
            with_replacement=True,
        ))
        rng.shuffle(selected_indices)
        partitions.append(build_user_partition(
            user_id=user_id,
            indices=selected_indices,
            primary_classes=primary_classes,
            targets=targets,
        ))
    return partitions


def build_class_to_indices(targets, classes):
    class_to_indices = {}
    target_array = np.asarray(targets, dtype=np.int64)
    for class_id in classes:
        class_indices = np.where(target_array == class_id)[0]
        if len(class_indices) == 0:
            raise ValueError(f"Class {class_id} has no samples.")
        class_to_indices[class_id] = class_indices
    return class_to_indices


def sample_indices(rng, candidates, count, with_replacement):
    if count <= 0:
        return []
    if not with_replacement and count > len(candidates):
        raise ValueError("Requested more samples than available candidates.")
    return [
        int(index)
        for index in rng.choice(candidates, size=count, replace=with_replacement)
    ]


def split_counts(total_count, bucket_number):
    base_count = total_count // bucket_number
    remainder = total_count % bucket_number
    return [
        base_count + (1 if bucket_index < remainder else 0)
        for bucket_index in range(bucket_number)
    ]


def build_user_partition(user_id, indices, primary_classes, targets):
    class_counts = {}
    for index in indices:
        class_id = int(targets[int(index)])
        class_counts[class_id] = class_counts.get(class_id, 0) + 1
    return UserDataPartition(
        user_id=int(user_id),
        indices=[int(index) for index in indices],
        primary_classes=tuple(int(class_id) for class_id in primary_classes),
        class_counts=class_counts,
    )


def summarize_partitions(user_partitions):
    total_class_counts = {}
    for partition in user_partitions.partitions:
        for class_id, count in partition.class_counts.items():
            total_class_counts[class_id] = total_class_counts.get(class_id, 0) + count

    return {
        "mode": user_partitions.mode,
        "seed": user_partitions.seed,
        "user_number": user_partitions.user_number,
        "samples_per_user": user_partitions.samples_per_user,
        "total_assigned_samples": (
            user_partitions.user_number * user_partitions.samples_per_user
        ),
        "total_class_counts": total_class_counts,
        "first_user_primary_classes": (
            user_partitions.partitions[0].primary_classes
            if user_partitions.partitions else ()
        ),
        "first_user_class_counts": (
            user_partitions.partitions[0].class_counts
            if user_partitions.partitions else {}
        ),
    }


def save_user_partitions(user_partitions, file_path):
    resolved_path = resolve_case2_path(file_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_path, mode="w", encoding="utf-8") as file:
        json.dump(user_partitions_to_dict(user_partitions), file, indent=2)
    return resolved_path


def load_user_partitions(file_path):
    resolved_path = resolve_case2_path(file_path)
    with open(resolved_path, mode="r", encoding="utf-8") as file:
        data = json.load(file)
    return user_partitions_from_dict(data)


def user_partitions_to_dict(user_partitions):
    return {
        "mode": user_partitions.mode,
        "seed": user_partitions.seed,
        "samples_per_user": user_partitions.samples_per_user,
        "user_number": user_partitions.user_number,
        "partitions": [
            {
                "user_id": partition.user_id,
                "indices": partition.indices,
                "primary_classes": list(partition.primary_classes),
                "class_counts": {
                    str(class_id): count
                    for class_id, count in partition.class_counts.items()
                },
            }
            for partition in user_partitions.partitions
        ],
    }


def user_partitions_from_dict(data):
    partitions = []
    for partition_data in data["partitions"]:
        partitions.append(UserDataPartition(
            user_id=int(partition_data["user_id"]),
            indices=[int(index) for index in partition_data["indices"]],
            primary_classes=tuple(
                int(class_id) for class_id in partition_data["primary_classes"]
            ),
            class_counts={
                int(class_id): int(count)
                for class_id, count in partition_data["class_counts"].items()
            },
        ))
    return UserDataPartitions(
        mode=data["mode"],
        seed=int(data["seed"]),
        samples_per_user=int(data["samples_per_user"]),
        user_number=int(data["user_number"]),
        partitions=partitions,
    )


def build_case2_user_partitions(dataset):
    from configuration import simulation_config as cg

    return create_user_partitions(
        dataset=dataset,
        user_number=cg.USER_NUMBER,
        samples_per_user=cg.FL_LOCAL_SAMPLE_COUNT,
        mode=cg.FL_DATA_PARTITION_MODE,
        seed=cg.CASE_RANDOM_SEED,
        primary_classes_per_user=cg.FL_PRIMARY_CLASSES_PER_USER,
        dominant_fraction=cg.FL_NON_IID_DOMINANT_FRACTION,
        with_replacement=cg.FL_PARTITION_WITH_REPLACEMENT,
    )
