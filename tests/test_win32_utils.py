from __future__ import annotations

from app.tools.revision_engine import Win32WordEngine
from app.tools.win32_utils import get_win32_constants


class _InvalidConstants:
    wdPageBreak = None
    wdWithInTable = None
    wdCollapseEnd = None


class _ValidConstants:
    wdPageBreak = 7
    wdWithInTable = 12
    wdCollapseEnd = 0


class _FakeWin32Invalid:
    constants = _InvalidConstants()


class _FakeWin32Valid:
    constants = _ValidConstants()


def test_get_win32_constants_falls_back_when_values_are_none() -> None:
    constants = get_win32_constants(_FakeWin32Invalid())
    assert int(constants.wdPageBreak) == 7
    assert int(constants.wdWithInTable) == 12
    assert int(constants.wdCollapseEnd) == 0


def test_get_win32_constants_keeps_valid_constants_object() -> None:
    fake = _FakeWin32Valid()
    constants = get_win32_constants(fake)
    assert constants is fake.constants


def test_const_int_uses_default_for_missing_or_invalid_values() -> None:
    engine = object.__new__(Win32WordEngine)
    engine._constants = _InvalidConstants()

    assert engine._const_int("wdCollapseEnd", 0) == 0
    assert engine._const_int("wdWithInTable", 12) == 12
    assert engine._const_int("missing_name", 99) == 99
