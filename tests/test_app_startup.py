import os
import subprocess
import sys
from pathlib import Path


def test_app_starts_with_sqlalchemy_instrumentation(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'startup.db'}"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n"
            "with TestClient(app) as client:\n"
            "    assert client.get('/docs').status_code == 200\n",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
    )
