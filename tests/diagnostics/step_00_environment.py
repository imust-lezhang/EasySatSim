import os
import platform
import json
import struct
import subprocess
import sys

from tests.diagnostics.common import mode, run_step


def windows_video_controllers():
    """Return Windows display-adapter evidence without making it a prerequisite."""
    if platform.system() != "Windows":
        return {"status": "not-applicable", "controllers": []}
    queries = (
        (
            "Win32_VideoController",
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,DriverVersion,AdapterCompatibility,VideoProcessor | "
            "ConvertTo-Json -Compress",
        ),
        (
            "Windows display-driver registry",
            "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Video' "
            "-Recurse -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Property -contains 'DriverDesc' } | "
            "ForEach-Object { Get-ItemProperty $_.PSPath | "
            "Select-Object DriverDesc,DriverVersion,ProviderName } | "
            "ConvertTo-Json -Compress",
        ),
    )
    reasons = []
    for source, command in queries:
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = completed.stdout.strip().lstrip("\ufeff")
            if completed.returncode or not output:
                reason = (
                    f"query unavailable (exit code {completed.returncode})"
                    if completed.returncode
                    else "no adapter data returned"
                )
                reasons.append(f"{source}: {reason}")
                continue
            parsed = json.loads(output)
            controllers = parsed if isinstance(parsed, list) else [parsed]
            unique = []
            fingerprints = set()
            for controller in controllers:
                fingerprint = json.dumps(controller, sort_keys=True, ensure_ascii=False)
                if fingerprint not in fingerprints:
                    fingerprints.add(fingerprint)
                    unique.append(controller)
            return {
                "status": "recorded",
                "source": source,
                "controllers": unique,
                "fallback_reasons": reasons,
            }
        except Exception as exc:
            reasons.append(f"{source}: {type(exc).__name__}: {exc}")
    return {"status": "unavailable", "controllers": [], "reasons": reasons}


def check():
    displays = {
        key: os.environ.get(key)
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM", "QT_OPENGL")
    }
    return {
        "summary": "Python and operating-system environment recorded.",
        "python": sys.version,
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
        "architecture_bits": struct.calcsize("P") * 8,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "test_mode": mode(),
        "display_environment": displays,
        "video_controllers": windows_video_controllers(),
    }


if __name__ == "__main__":
    run_step(0, check)
