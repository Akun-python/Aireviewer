from __future__ import annotations

import contextlib
import os
import shutil
import sys
import time
import types
from typing import Callable, TypeVar


T = TypeVar("T")

_RPC_E_CALL_REJECTED = -2147418111
_CO_E_NOTINITIALIZED = -2147221008


def com_error_hresult(exc: BaseException) -> int | None:
    hresult = getattr(exc, "hresult", None)
    if isinstance(hresult, int):
        return hresult
    args = getattr(exc, "args", None)
    if not args:
        return None
    try:
        first = args[0]
    except Exception:
        return None
    return first if isinstance(first, int) else None


def is_com_call_rejected(exc: BaseException) -> bool:
    return com_error_hresult(exc) == _RPC_E_CALL_REJECTED


def is_com_not_initialized(exc: BaseException) -> bool:
    return com_error_hresult(exc) == _CO_E_NOTINITIALIZED


def try_get_pid_from_hwnd(hwnd: int) -> int | None:
    if os.name != "nt":
        return None
    try:
        import ctypes

        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        value = int(pid.value)
        return value or None
    except Exception:
        return None


def try_get_com_app_pid(app) -> int | None:
    try:
        hwnd = getattr(app, "Hwnd", None)
        if hwnd is None:
            return None
        return try_get_pid_from_hwnd(int(hwnd))
    except Exception:
        return None


def maybe_write_com_app_pid(app, *, env_var: str = "WORD_AUTOMATION_PID_PATH") -> int | None:
    path = os.getenv(env_var, "").strip()
    pid = try_get_com_app_pid(app)
    if not path or pid is None:
        return pid
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(pid))
    except Exception:
        pass
    return pid


class _OleMessageFilter:
    def __init__(self, *, retry_delay_ms: int = 100) -> None:
        self._retry_delay_ms = int(max(1, retry_delay_ms))

    def HandleInComingCall(self, dwCallType, hTaskCaller, dwTickCount, lpInterfaceInfo):  # noqa: N802
        try:
            import pythoncom  # type: ignore

            return pythoncom.SERVERCALL_ISHANDLED
        except Exception:
            return 0

    def RetryRejectedCall(self, hTaskCallee, dwTickCount, dwRejectType):  # noqa: N802
        try:
            import pythoncom  # type: ignore

            rejected = pythoncom.SERVERCALL_RETRYLATER
        except Exception:
            rejected = 2

        if dwRejectType in {rejected, 1}:
            return self._retry_delay_ms
        return -1

    def MessagePending(self, hTaskCallee, dwTickCount, dwPendingType):  # noqa: N802
        try:
            import pythoncom  # type: ignore

            return pythoncom.PENDINGMSG_WAITDEFPROCESS
        except Exception:
            return 2


@contextlib.contextmanager
def win32com_context(*, retry_delay_ms: int = 100):
    """
    Initialize COM for this thread and install an OLE MessageFilter to reduce
    "RPC_E_CALL_REJECTED / 被呼叫方拒绝接收呼叫" failures when automating Word.

    Safe to nest; each call balances CoInitialize/CoUninitialize.
    """
    try:
        import pythoncom  # type: ignore
    except Exception:
        yield
        return

    pythoncom.CoInitialize()
    registered = False
    old_filter = None
    new_filter = _OleMessageFilter(retry_delay_ms=retry_delay_ms)
    try:
        try:
            old_filter = pythoncom.CoRegisterMessageFilter(new_filter)
            registered = True
        except Exception:
            registered = False
        yield
    finally:
        if registered:
            try:
                pythoncom.CoRegisterMessageFilter(old_filter)
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def com_retry(fn: Callable[[], T], *, timeout_s: float = 15.0, initial_delay_s: float = 0.05) -> T:
    """
    Retry a COM call when Word is busy (RPC_E_CALL_REJECTED).

    Use for coarse-grained calls like Open/Save/Close/Quit.
    """
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    delay = max(0.0, float(initial_delay_s))
    last_exc: Exception | None = None
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if not is_com_call_rejected(exc):
                raise
            last_exc = exc
            if time.monotonic() >= deadline:
                raise last_exc
            try:
                import pythoncom  # type: ignore

                pythoncom.PumpWaitingMessages()
            except Exception:
                pass
            time.sleep(delay)
            delay = min(0.75, delay * 1.7 + 0.01)


def install_ole_message_filter(*, retry_delay_ms: int = 100):
    """
    Install an OLE MessageFilter on the current thread.

    Returns (old_filter, new_filter). Keep the returned new_filter referenced
    until you call `restore_ole_message_filter` to avoid it being GC'ed.
    """
    try:
        import pythoncom  # type: ignore
    except Exception:
        return None, None
    new_filter = _OleMessageFilter(retry_delay_ms=retry_delay_ms)
    try:
        old_filter = pythoncom.CoRegisterMessageFilter(new_filter)
    except Exception:
        return None, None
    return old_filter, new_filter


def restore_ole_message_filter(old_filter) -> None:
    try:
        import pythoncom  # type: ignore
    except Exception:
        return
    try:
        pythoncom.CoRegisterMessageFilter(old_filter)
    except Exception:
        pass


def _clean_gen_py_modules() -> None:
    for key in list(sys.modules.keys()):
        if key.startswith("win32com.gen_py"):
            sys.modules.pop(key, None)


def try_fix_gen_py_cache(exc: Exception | None = None, *, aggressive: bool = False) -> bool:
    if exc is not None:
        message = str(exc)
        if (
            "CLSIDToClassMap" not in message
            and "CLSIDToPackageMap" not in message
            and "win32com.gen_py" not in message
        ):
            return False
    try:
        import win32com.client.gencache as gencache  # type: ignore
    except Exception:
        return False

    def _ensure_gen_py_package() -> str | None:
        try:
            gen_path = gencache.GetGeneratePath()
        except Exception:
            return None
        try:
            os.makedirs(gen_path, exist_ok=True)
        except Exception:
            return gen_path
        init_path = os.path.join(gen_path, "__init__.py")
        try:
            if not os.path.exists(init_path):
                with open(init_path, "w", encoding="utf-8") as handle:
                    handle.write("# generated by pywin32\n")
        except Exception:
            pass
        # Ensure win32com.gen_py is importable as a package, even if win32com's
        # package init didn't set it up correctly for this environment.
        if "win32com.gen_py" not in sys.modules:
            gen_py = types.ModuleType("win32com.gen_py")
            gen_py.__path__ = [gen_path]  # type: ignore[attr-defined]
            sys.modules[gen_py.__name__] = gen_py
        else:
            module = sys.modules.get("win32com.gen_py")
            try:
                module.__path__ = [gen_path]  # type: ignore[attr-defined]
            except Exception:
                pass
        return gen_path

    _ensure_gen_py_package()

    _clean_gen_py_modules()
    try:
        gencache.is_readonly = False
    except Exception:
        pass

    fixed = False
    try:
        gencache.Rebuild()
        fixed = True
    except Exception:
        fixed = False

    if not fixed:
        try:
            gen_path = gencache.GetGeneratePath()
        except Exception:
            gen_path = None
        if gen_path:
            _ensure_gen_py_package()
            # Word's TypeLib GUID often appears as:
            # win32com.gen_py.00020905-0000-0000-C000-000000000046x0x8x7
            # If the generated module is corrupted/missing maps, remove it first.
            try:
                import glob

                pattern = os.path.join(gen_path, "00020905-0000-0000-C000-000000000046*")
                for candidate in glob.glob(pattern):
                    try:
                        shutil.rmtree(candidate, ignore_errors=True)
                    except Exception:
                        pass
            except Exception:
                pass
            # Prefer clearing contents instead of deleting the root folder, as
            # some environments may point this to a protected location.
            try:
                for name in os.listdir(gen_path):
                    if name in {"__init__.py", "__pycache__"}:
                        continue
                    target = os.path.join(gen_path, name)
                    try:
                        if os.path.isdir(target):
                            shutil.rmtree(target, ignore_errors=True)
                        else:
                            os.remove(target)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                gencache.Rebuild()
                fixed = True
            except Exception:
                fixed = False

    if aggressive:
        try:
            from win32com.client import makepy  # type: ignore

            makepy.GenerateFromTypeLibSpec("Microsoft Word 16.0 Object Library")
        except Exception:
            pass

    return fixed


def get_win32_constants(win32):
    class _FallbackConstants:
        # Minimal Word constants used across this repo.
        wdPageBreak = 7
        wdMainTextStory = 1
        wdWithInTable = 12

        wdOutlineNumberGallery = 3
        wdTrailingTab = 1
        wdListNumberStyleArabic = 0
        wdListLevelAlignLeft = 0

        wdOutlineLevel1 = 1
        wdOutlineLevel2 = 2
        wdOutlineLevel3 = 3
        wdOutlineLevelBodyText = 10

        wdCollapseEnd = 0

        wdPaperA4 = 7
        wdLineSpace1pt5 = 1
        wdAlignParagraphLeft = 0
        wdAlignParagraphCenter = 1
        wdAlignParagraphJustify = 3

        wdAutoFitWindow = 2

        wdCaptionPositionAbove = 0
        wdCaptionPositionBelow = 1

        wdSeparatorHyphen = 0

    def _constants_have_required_values(constants) -> bool:
        required = ("wdPageBreak", "wdWithInTable", "wdCollapseEnd")
        for name in required:
            try:
                value = getattr(constants, name)
            except Exception:
                return False
            try:
                int(value)
            except Exception:
                return False
        return True

    try:
        constants = win32.constants
        if _constants_have_required_values(constants):
            return constants
        # Constants object exists but required values are unusable (e.g. None).
        # In this case we directly fall back to numeric defaults.
        return _FallbackConstants()
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        # If gen_py is broken/missing, attempting Rebuild often prints noisy
        # errors and still fails. Fall back to numeric constants instead.
        if "win32com.gen_py" in message or "CLSIDToPackageMap" in message or "CLSIDToClassMap" in message:
            return _FallbackConstants()
        try:
            try_fix_gen_py_cache(exc, aggressive=True)
        except Exception:
            return _FallbackConstants()
        try:
            constants = win32.constants
            if _constants_have_required_values(constants):
                return constants
            return _FallbackConstants()
        except Exception:
            return _FallbackConstants()


def dispatch_word_application(*, isolated: bool | None = None):
    import win32com.client as win32  # type: ignore

    def _dispatch_ex():
        try:
            return win32.DispatchEx("Word.Application")
        except Exception as exc:  # noqa: BLE001
            # A common pywin32 failure mode is a corrupted gen_py cache:
            # "module ... has no attribute CLSIDToClassMap".
            try:
                try_fix_gen_py_cache(exc, aggressive=True)
            except Exception:
                pass
            return win32.DispatchEx("Word.Application")

    if isolated is None:
        isolated = os.getenv("WORD_COM_ISOLATED", "1").strip().lower() not in {"0", "false", "no"}
    if isolated:
        return _dispatch_ex()

    try:
        import win32com.client.gencache as gencache  # type: ignore
    except Exception:
        return win32.DispatchEx("Word.Application")

    try:
        return gencache.EnsureDispatch("Word.Application")
    except Exception as exc:  # noqa: BLE001
        try_fix_gen_py_cache(exc, aggressive=True)
        try:
            return gencache.EnsureDispatch("Word.Application")
        except Exception:
            return _dispatch_ex()


def winword_pids() -> set[int]:
    if os.name != "nt":
        return set()
    try:
        import csv
        import io
        import subprocess

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


def dispatch_word_application_with_pid(
    *, isolated: bool | None = None, pid_env_var: str = "WORD_AUTOMATION_PID_PATH"
):
    pre_pids = winword_pids()
    app = dispatch_word_application(isolated=isolated)
    pid = try_get_com_app_pid(app)
    if pid is None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            diff = winword_pids() - pre_pids
            if len(diff) == 1:
                pid = next(iter(diff))
                break
            if diff:
                pid = sorted(diff)[-1]
                break
            time.sleep(0.1)
    if pid is not None:
        path = os.getenv(pid_env_var, "").strip()
        if path:
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(str(pid))
            except Exception:
                pass
    return app, pid
