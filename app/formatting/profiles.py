from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


@dataclass(frozen=True)
class FormatProfile:
    key: str
    label: str


PROFILES: list[FormatProfile] = [
    FormatProfile(key="none", label="无"),
    FormatProfile(key="thesis_standard", label="论文标准格式"),
    FormatProfile(key="a4_strict", label="A4规范格式"),
    FormatProfile(key="zhengda_cup", label="正大杯报告格式"),
]


def resolve_profile(key: str | None) -> str:
    key = (key or "").strip()
    if not key:
        return "none"
    known = {p.key for p in PROFILES}
    return key if key in known else "none"


def _apply_format_profile_inprocess(*, docx_path: str, root_dir: str, profile: str) -> None:
    profile = resolve_profile(profile)
    if profile == "none":
        return
    if profile == "zhengda_cup":
        from app.formatting.zhengda_cup import apply_zhengda_cup_profile

        apply_zhengda_cup_profile(docx_path=docx_path, root_dir=root_dir)
        return
    if profile == "a4_strict":
        from app.formatting.a4_strict import apply_a4_strict_profile

        apply_a4_strict_profile(docx_path=docx_path, root_dir=root_dir)
        return
    if profile == "thesis_standard":
        from app.formatting.thesis_standard import apply_thesis_standard_profile

        apply_thesis_standard_profile(docx_path=docx_path, root_dir=root_dir)
        return
    raise ValueError(f"Unknown format profile: {profile}")


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return float(default)
    try:
        return float(value.strip())
    except Exception:
        return float(default)


def _should_use_subprocess() -> bool:
    if os.name != "nt":
        return False
    # Default to subprocess mode on Windows to avoid blocking the Streamlit process
    # when Word COM automation hangs.
    return _env_flag("FORMAT_PROFILE_SUBPROCESS", True)


def _winword_pids() -> set[int]:
    if os.name != "nt":
        return set()
    try:
        import csv
        import io

        completed = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode != 0:
            return set()
        raw_lines = (completed.stdout or "").splitlines()
        lines = [line.strip() for line in raw_lines if line.strip() and "No tasks are running" not in line]
        if not lines:
            return set()
        pids: set[int] = set()
        for row in csv.reader(io.StringIO("\n".join(lines))):
            if len(row) < 2:
                continue
            try:
                pids.add(int(row[1]))
            except Exception:
                continue
        return pids
    except Exception:
        return set()


def _run_profile_subprocess(*, docx_path: str, root_dir: str, profile: str) -> None:
    resolved_root = str(Path(root_dir).resolve())
    resolved_docx = str(Path(docx_path).resolve())

    timeout_s = _env_float("FORMAT_PROFILE_TIMEOUT_S", 120.0)
    if timeout_s <= 0:
        timeout_s = 0.0
    kill_word_on_timeout = _env_flag("FORMAT_PROFILE_KILL_WORD_ON_TIMEOUT", True)
    pre_word_pids = _winword_pids() if kill_word_on_timeout else set()

    src = Path(resolved_docx)
    if not src.exists():
        raise FileNotFoundError(resolved_docx)

    # Apply formatting on a temporary copy first; only replace the original on success
    # to avoid corrupting the output docx if Word gets stuck mid-save.
    with tempfile.NamedTemporaryFile(
        prefix=f"{src.stem}__fmt__",
        suffix=src.suffix,
        dir=str(src.parent),
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    pid_path = Path(str(tmp_path) + ".word.pid")
    try:
        shutil.copy2(src, tmp_path)

        cmd = [
            sys.executable,
            "-m",
            "app.formatting.runner",
            "--docx_path",
            str(tmp_path),
            "--root_dir",
            resolved_root,
            "--profile",
            profile,
        ]
        env = os.environ.copy()
        # Avoid recursive subprocess spawning inside the runner.
        env["FORMAT_PROFILE_SUBPROCESS"] = "0"
        # Force isolated Word instance for this subprocess; safe to terminate on timeout.
        env["WORD_COM_ISOLATED"] = "1"
        env["WORD_AUTOMATION_PID_PATH"] = str(pid_path)

        start = time.monotonic()
        try:
            completed = subprocess.run(
                cmd,
                cwd=resolved_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=None if timeout_s == 0.0 else timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - start
            if kill_word_on_timeout and os.name == "nt":
                try:
                    pid_value = pid_path.read_text(encoding="utf-8").strip()
                    pid = int(pid_value)
                except Exception:
                    pid = 0
                killed_pid = False
                if pid > 0:
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(pid), "/T", "/F"],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            check=False,
                        )
                        killed_pid = True
                    except Exception:
                        pass
                # If we didn't manage to read/kill the automation Word PID (e.g. timed out
                # before the runner wrote it), fall back to killing only newly created
                # Word processes when there were no pre-existing Word instances.
                if not killed_pid and not pre_word_pids:
                    for _ in range(3):
                        extra_pids = sorted(_winword_pids() - pre_word_pids)
                        if not extra_pids:
                            break
                        for extra_pid in extra_pids:
                            try:
                                subprocess.run(
                                    ["taskkill", "/PID", str(extra_pid), "/T", "/F"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    check=False,
                                )
                            except Exception:
                                continue
                        time.sleep(0.75)
            raise RuntimeError(
                (
                    f"format profile '{profile}' timed out after {elapsed:.1f}s；"
                    "Word 可能卡在打开/排版（建议关闭所有 Word 窗口后重试）"
                    + (
                        ("\n" + (exc.stdout or "").strip()) if (exc.stdout or "").strip() else ""
                    )
                    + (
                        ("\n" + (exc.stderr or "").strip()) if (exc.stderr or "").strip() else ""
                    )
                ).rstrip()
            ) from exc

        if completed.returncode != 0:
            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()
            details = "\n".join(part for part in (stdout, stderr) if part)
            raise RuntimeError(
                f"format profile '{profile}' failed (exit={completed.returncode})\n{details}".rstrip()
            )

        os.replace(str(tmp_path), resolved_docx)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            pid_path.unlink(missing_ok=True)
        except Exception:
            pass


def apply_format_profile(*, docx_path: str, root_dir: str, profile: str) -> None:
    profile = resolve_profile(profile)
    if profile == "none":
        return
    if _should_use_subprocess():
        _run_profile_subprocess(docx_path=docx_path, root_dir=root_dir, profile=profile)
        return
    _apply_format_profile_inprocess(docx_path=docx_path, root_dir=root_dir, profile=profile)


def default_zhengda_template_path(root_dir: str) -> Path:
    return Path(root_dir) / "templates" / "正大杯报告格式.dotx"
