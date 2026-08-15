# Case 2 CIFAR-10 Data

Case 2 uses the CIFAR-10 image-classification dataset through
`torchvision.datasets.CIFAR10`. The dataset itself is not part of the
EasySatSim source release. Only the loader and deterministic partitioning code
in this directory should be tracked by Git.

## Source and integrity

The installed torchvision loader currently obtains the Python archive from:

```text
https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
```

The archive metadata used by torchvision is:

```text
Filename: cifar-10-python.tar.gz
MD5:      c58f30108f718f92721af3b95e74349a
```

The local archive inspected for this EasySatSim release also had:

```text
SHA-256: 6d958be074577803d12ecdefd02955f39262c83c16fe9348329d7fe0b5c001ce
```

Refer to the CIFAR-10 project page and accompanying technical report for the
dataset authorship and citation. The upstream archive is a third-party research
dataset and is not relicensed by EasySatSim. Confirm its current terms before
redistributing a copy; the EasySatSim GitHub source repository does not bundle
the archive or extracted images.

## Install the Case 2 environment

Run from the EasySatSim project root:

```powershell
python -m pip install -r cases/case2/requirements.txt
```

## Automatic download

The Case 2 configuration uses:

```python
CIFAR10_DATA_ROOT = "../cases/case2/experiment/data"
CIFAR10_DOWNLOAD = True
```

On the first Case 2 run, torchvision downloads and extracts the dataset below
this directory. Both generated paths are ignored by the root `.gitignore`:

```text
cases/case2/experiment/data/cifar-10-python.tar.gz
cases/case2/experiment/data/cifar-10-batches-py/
```

Later runs reuse the local extracted data. Set `CIFAR10_DOWNLOAD = False` only
when a complete, verified local copy is already present and network access must
be disabled.

## Lightweight local check

After the data has been downloaded and extracted, verify the fixed split
without running a simulation or training a model:

```powershell
python -c "from cases.case2.experiment.data.cifar10_data import load_case2_cifar10; d=load_case2_cifar10(download=False); print(len(d.train_dataset), len(d.test_dataset))"
```

Expected output:

```text
45000 5000
```

This check also verifies torchvision's per-file CIFAR-10 integrity metadata.

## Download or permission failures

If loading fails:

1. confirm that the Case 2 requirements were installed;
2. confirm that this directory is writable;
3. remove or move only an incomplete local download after making any needed
   backup, then retry with `CIFAR10_DOWNLOAD = True`;
4. check proxy, firewall, and TLS settings if the official source is
   unreachable.

EasySatSim does not silently use a different dataset mirror. If the upstream
archive changes, record the source, checksum, and resulting experiment impact
before using it for paper results.
