"""Verify imports from the deployable Python bundle, without falling back to src/."""
import shutil
import subprocess
import sys
from pathlib import Path


def test_serverless_bundle_includes_worker_health_dependency(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo / "src/neopulse", tmp_path / "src/neopulse", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo / "web/reference", tmp_path / "web/reference")
    script = tmp_path / "tools/prepare_web_python.py"
    script.parent.mkdir()
    shutil.copyfile(repo / "tools/prepare_web_python.py", script)
    subprocess.run([sys.executable, str(script)], check=True, capture_output=True)
    bundle = tmp_path / "web/serverpkg"
    result = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from neopulse.analytics.telegram_cloud import run, _health; "
         "from neopulse.analytics import health; "
         "assert health.recorder_issue(None, 0) is None; "
         "print(health.__file__)", str(bundle)],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )
    assert Path(result.stdout.strip()).is_relative_to(bundle)
