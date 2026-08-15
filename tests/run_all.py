import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = PROJECT_ROOT / "tests"
ARTIFACT_DIR = TEST_ROOT / "artifacts"
STEPS = {
    index: TEST_ROOT / "diagnostics" / f"step_{index:02d}_{name}.py"
    for index, name in (
        (0, "environment"),
        (1, "dependencies"),
        (2, "configuration"),
        (3, "qt_application"),
        (4, "qt_window"),
        (5, "vispy_backend"),
        (6, "opengl_canvas"),
        (7, "pyqtgraph"),
        (8, "dashboard"),
        (9, "control_window"),
        (10, "live_refresh"),
        (11, "short_simulation"),
    )
}


def main():
    parser = argparse.ArgumentParser(
        description="Run EasySatSim stepwise diagnostics and regression tests."
    )
    parser.add_argument(
        "--mode",
        choices=("offscreen", "live"),
        default="live",
        help=(
            "Visualization mode. Defaults to live so direct IDE execution tests the "
            "desktop Qt/OpenGL path; use offscreen explicitly for CI or headless systems."
        ),
    )
    parser.add_argument("--from-step", type=int, choices=range(0, 12), default=0)
    parser.add_argument("--only-step", type=int, choices=range(0, 12))
    parser.add_argument("--skip-unit", action="store_true")
    parser.add_argument("--skip-integration", action="store_true")
    parser.add_argument("--timeout", type=int, default=45, help="Timeout per diagnostic step.")
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    selected = [args.only_step] if args.only_step is not None else list(range(args.from_step, 12))
    results = []
    print(f"EasySatSim diagnostics: mode={args.mode}, steps={selected}")
    for step in selected:
        results.append(run_diagnostic(step, args.mode, args.timeout))

    if args.only_step is None and not args.skip_unit:
        results.append(run_test_group("unit", "tests.unit.test_core", timeout=90, mode=args.mode))
    if args.only_step is None and not args.skip_integration:
        results.append(
            run_test_group("integration", "tests.integration.test_integrations", timeout=120, mode=args.mode)
        )

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": args.mode,
        "python": sys.version,
        "executable": sys.executable,
        "results": results,
        "summary": summarize(results),
    }
    report["run_passed"] = report["summary"]["FAIL"] == 0
    report["live_release_gate_passed"] = (
        args.mode == "live"
        and report["summary"]["FAIL"] == 0
        and report["summary"]["SKIP"] == 0
    )
    json_path = ARTIFACT_DIR / f"diagnostics_{args.mode}_{timestamp}.json"
    md_path = ARTIFACT_DIR / f"diagnostics_{args.mode}_{timestamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    print("\n" + summary_table(results))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    if args.mode == "live" and report["summary"]["SKIP"]:
        print("Live release gate failed: live diagnostics must contain no skipped steps.")
    passed = report["live_release_gate_passed"] if args.mode == "live" else report["run_passed"]
    raise SystemExit(0 if passed else 1)


def run_diagnostic(step, mode, timeout):
    script = STEPS[step]
    environment = child_environment(mode)
    print(f"\n[Step {step:02d}] {script.stem}")
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "step": step,
            "name": script.stem,
            "status": "FAIL",
            "summary": f"Timed out after {timeout} seconds.",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    payload = parse_payload(completed.stdout)
    status = "SKIP" if completed.returncode == 77 else "PASS" if completed.returncode == 0 else "FAIL"
    result = {
        "step": step,
        "name": script.stem,
        "status": payload.get("status", status),
        "summary": payload.get("summary", "Diagnostic completed." if not completed.returncode else "Failed."),
        "details": payload.get("details", {}),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    print(f"[{result['status']}] {result['summary']}")
    if result["status"] == "FAIL" and completed.stderr:
        print(completed.stderr[-2000:])
    return result


def run_test_group(name, module, timeout, mode):
    print(f"\n[{name.title()} tests] {module}")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", module],
            cwd=PROJECT_ROOT,
            env=child_environment(mode),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        status = "PASS" if completed.returncode == 0 else "FAIL"
        summary = f"{name.title()} test suite passed." if not completed.returncode else f"{name.title()} test suite failed."
        print(f"[{status}] {summary}")
        return {
            "step": name,
            "name": f"{name}_tests",
            "status": status,
            "summary": summary,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "step": name,
            "name": f"{name}_tests",
            "status": "FAIL",
            "summary": f"Timed out after {timeout} seconds.",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def child_environment(mode):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONUNBUFFERED"] = "1"
    environment["EASYSATSIM_TEST_MODE"] = mode
    environment["EASYSATSIM_CONFIG_ROOT"] = str(TEST_ROOT / "fixtures" / "small_config")
    if mode == "offscreen":
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment.setdefault("QT_OPENGL", "software")
    else:
        environment.pop("QT_QPA_PLATFORM", None)
    return environment


def parse_payload(stdout):
    marker = "EASYSATSIM_DIAGNOSTIC="
    for line in reversed(stdout.splitlines()):
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):])
            except json.JSONDecodeError:
                return {}
    return {}


def summarize(results):
    totals = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for result in results:
        totals[result["status"]] = totals.get(result["status"], 0) + 1
    return totals


def summary_table(results):
    lines = ["Result summary", "=" * 78]
    for result in results:
        lines.append(f"{str(result['step']):>11}  {result['status']:<5}  {result['summary']}")
    totals = summarize(results)
    lines.append("-" * 78)
    lines.append(f"PASS={totals['PASS']} FAIL={totals['FAIL']} SKIP={totals['SKIP']}")
    return "\n".join(lines)


def markdown_report(report):
    lines = [
        "# EasySatSim Diagnostic Report",
        "",
        f"- Created: `{report['created_at']}`",
        f"- Mode: `{report['mode']}`",
        f"- Python: `{report['executable']}`",
        f"- Summary: `{report['summary']}`",
        f"- Diagnostic run passed: `{report['run_passed']}`",
        f"- Live release gate passed: `{report['live_release_gate_passed']}`",
        "",
        "| Step | Status | Result |",
        "|---:|---|---|",
    ]
    for result in report["results"]:
        summary = result["summary"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {result['step']} | {result['status']} | {summary} |")
    lines.extend(["", "## Failure details", ""])
    failures = [result for result in report["results"] if result["status"] == "FAIL"]
    if not failures:
        lines.append("No failures.")
    for result in failures:
        lines.extend([
            f"### {result['name']}",
            "",
            "```text",
            (result.get("stderr") or result.get("stdout") or json.dumps(result.get("details", {}), indent=2))[-8000:],
            "```",
            "",
        ])
    evidence = {
        str(result["step"]): result.get("details", {})
        for result in report["results"]
        if result["step"] in (0, 1, 5, 6)
    }
    lines.extend([
        "",
        "## Visualization environment evidence",
        "",
        "```json",
        json.dumps(evidence, indent=2, ensure_ascii=False, default=str),
        "```",
        "",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
