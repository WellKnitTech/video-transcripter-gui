from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path


def test_root_launcher_adds_src_to_sys_path_and_calls_main(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "video_transcriber_gui.py"
    src_path = repo_root / "src"
    called = False

    def fake_main() -> None:
        nonlocal called
        called = True

    fake_package = types.ModuleType("video_transcriber")
    fake_main_module = types.ModuleType("video_transcriber.main")
    fake_main_module.main = fake_main
    monkeypatch.setitem(sys.modules, "video_transcriber", fake_package)
    monkeypatch.setitem(sys.modules, "video_transcriber.main", fake_main_module)
    monkeypatch.setattr(sys, "path", [path for path in sys.path if path != str(src_path)])

    runpy.run_path(str(script_path), run_name="__main__")

    assert called
    assert sys.path[0] == str(src_path)
