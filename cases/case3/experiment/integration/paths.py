from pathlib import Path
from pathlib import PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CASE3_ROOT = PROJECT_ROOT / "cases" / "case3"
CASE3_MARKER = "cases/case3/"


def resolve_project_path(path):
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    return _require_project_path((PROJECT_ROOT / path).resolve())


def to_project_relative_path(path):
    """Serialize a project file without recording a machine-specific prefix."""
    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = _require_project_path(path.resolve())
    return resolved.relative_to(PROJECT_ROOT).as_posix()


def resolve_recorded_path(path, reference_path=None):
    """Resolve new relative paths and rebase legacy Case 3 absolute paths."""
    del reference_path  # Reserved for future metadata-relative formats.
    text = str(path)
    candidate = Path(text)
    if not candidate.is_absolute() and not _looks_like_windows_absolute(text):
        return _require_project_path((PROJECT_ROOT / candidate).resolve())

    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            return _require_project_path(resolved)
        except ValueError:
            pass

    suffix = _case3_suffix(text)
    if suffix is None:
        raise ValueError(
            "Recorded Case 3 path is outside the current project and cannot be "
            f"rebased: {path}"
        )
    return _require_project_path((PROJECT_ROOT / suffix).resolve())


def normalize_recorded_path(path, reference_path=None):
    return to_project_relative_path(
        resolve_recorded_path(path, reference_path=reference_path)
    )


def _case3_suffix(path):
    normalized = str(path).replace("\\", "/")
    index = normalized.lower().find(CASE3_MARKER)
    if index < 0:
        return None
    return PurePosixPath(normalized[index:])


def _looks_like_windows_absolute(path):
    text = str(path)
    return len(text) >= 3 and text[1] == ":" and text[2] in ("\\", "/")


def _require_project_path(path):
    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path is outside the EasySatSim project: {path}") from exc
    return path
