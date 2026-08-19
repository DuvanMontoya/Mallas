from __future__ import annotations

import ctypes
import multiprocessing
import os
import queue
import threading
from importlib import import_module
from multiprocessing.context import SpawnContext
from typing import Any

from django.conf import settings

from domain.history import HistoryFormatError, ParseReport
from domain.history.parsers import PdfHistoryCandidateParser


class IsolatedParserError(HistoryFormatError):
    """Safe public failure from the bounded parser process."""


class ParserCapacityError(IsolatedParserError):
    """Transient failure when the bounded parser slot is already occupied."""


def _apply_posix_memory_limit(memory_bytes: int) -> None:
    if os.name == "nt":
        return
    try:
        resource: Any = import_module("resource")
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError("PDF parser memory isolation is unavailable") from exc


def _pdf_worker(
    content: bytes,
    source_name: str,
    memory_bytes: int,
    start_event: Any,
    result_queue: Any,
) -> None:
    start_event.wait()
    _apply_posix_memory_limit(memory_bytes)
    try:
        report = PdfHistoryCandidateParser().parse(content, source_name=source_name)
        result_queue.put(("ok", report))
    except HistoryFormatError as exc:
        result_queue.put(("format_error", str(exc)))
    except MemoryError:
        result_queue.put(("resource_error", "PDF parsing exceeded its memory budget"))
    except BaseException:
        result_queue.put(("parser_error", "PDF could not be parsed safely"))


def _assign_windows_memory_job(process_id: int, memory_bytes: int) -> int | None:
    if os.name != "nt":
        return None

    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32: Any = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)  # noqa: B009
    get_last_error = getattr(ctypes, "get_last_error")  # noqa: B009
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(get_last_error(), "Could not create parser memory job")
    process_handle = kernel32.OpenProcess(0x0100 | 0x0001, False, process_id)
    if not process_handle:
        kernel32.CloseHandle(job)
        raise OSError(get_last_error(), "Could not open parser process")
    try:
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00000100
        limits.ProcessMemoryLimit = memory_bytes
        if not kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise OSError(get_last_error(), "Could not configure parser memory job")
        if not kernel32.AssignProcessToJobObject(job, process_handle):
            raise OSError(get_last_error(), "Could not isolate parser process")
    except BaseException:
        kernel32.CloseHandle(job)
        raise
    finally:
        kernel32.CloseHandle(process_handle)
    return int(job)


def _close_windows_handle(handle: int | None) -> None:
    if handle is not None and os.name == "nt":
        from ctypes import wintypes

        kernel32: Any = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)  # noqa: B009
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(handle)


_PARSER_CAPACITY = threading.BoundedSemaphore(1)


def _parse_pdf_history_isolated(content: bytes, *, source_name: str) -> ParseReport:
    timeout_seconds = float(settings.HISTORY_PDF_PARSE_TIMEOUT_SECONDS)
    memory_bytes = int(settings.HISTORY_PDF_PARSE_MEMORY_MIB) * 1024 * 1024
    context: SpawnContext = multiprocessing.get_context("spawn")
    result_queue = context.Queue(maxsize=1)
    start_event = context.Event()
    process = context.Process(
        target=_pdf_worker,
        args=(content, source_name, memory_bytes, start_event, result_queue),
        name="history-pdf-parser",
        daemon=True,
    )
    windows_job: int | None = None
    process.start()
    try:
        try:
            if process.pid is None:
                raise OSError("Parser process did not expose a process identifier")
            windows_job = _assign_windows_memory_job(process.pid, memory_bytes)
        except OSError as exc:
            process.terminate()
            process.join(timeout=1)
            raise IsolatedParserError("PDF parser isolation could not be established") from exc
        start_event.set()
        try:
            kind, payload = result_queue.get(timeout=timeout_seconds)
        except queue.Empty as exc:
            process.terminate()
            process.join(timeout=1)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(timeout=1)
            raise IsolatedParserError("PDF parsing exceeded its time or memory budget") from exc
        process.join(timeout=1)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
        if kind == "ok" and isinstance(payload, ParseReport):
            return payload
        raise IsolatedParserError(str(payload))
    finally:
        start_event.set()
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
        _close_windows_handle(windows_job)
        result_queue.close()


def parse_pdf_history_isolated(content: bytes, *, source_name: str) -> ParseReport:
    if not _PARSER_CAPACITY.acquire(blocking=False):
        raise ParserCapacityError("PDF parser capacity is busy; retry shortly")
    try:
        return _parse_pdf_history_isolated(content, source_name=source_name)
    finally:
        _PARSER_CAPACITY.release()
