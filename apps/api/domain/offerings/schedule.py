from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class MeetingWindow:
    """A recurring meeting normalized from a persisted section meeting."""

    meeting_id: str
    section_id: str
    day_of_week: int
    starts_at: time
    ends_at: time
    timezone: str
    starts_on: date | None = None
    ends_on: date | None = None
    session_code: str = ""
    is_alternate: bool = False


@dataclass(frozen=True)
class Conflict:
    left_section_id: str
    right_section_id: str
    left_meeting_id: str
    right_meeting_id: str
    occurrence_date: date
    starts_at_utc: datetime
    ends_at_utc: datetime
    reason: str = "OVERLAP"


@dataclass(frozen=True)
class ScheduleEvaluation:
    state: str
    conflicts: tuple[Conflict, ...]
    unknown_reasons: tuple[str, ...]


def _effective_range(
    meeting: MeetingWindow,
    *,
    term_start: date,
    term_end: date,
) -> tuple[date, date]:
    return max(term_start, meeting.starts_on or term_start), min(
        term_end, meeting.ends_on or term_end
    )


def _occurrences(
    meeting: MeetingWindow,
    *,
    term_start: date,
    term_end: date,
) -> list[tuple[date, datetime, datetime]]:
    if meeting.day_of_week not in range(7):
        return []
    start, end = _effective_range(meeting, term_start=term_start, term_end=term_end)
    if end < start:
        return []
    try:
        zone = ZoneInfo(meeting.timezone)
        utc = ZoneInfo("UTC")
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown meeting timezone: {meeting.timezone}") from exc
    cursor = start + timedelta(days=(meeting.day_of_week - start.weekday()) % 7)
    result: list[tuple[date, datetime, datetime]] = []
    while cursor <= end:
        local_start = datetime.combine(cursor, meeting.starts_at, tzinfo=zone)
        local_end = datetime.combine(cursor, meeting.ends_at, tzinfo=zone)
        result.append((cursor, local_start.astimezone(utc), local_end.astimezone(utc)))
        cursor += timedelta(days=7)
    return result


def detect_conflicts(
    meetings: list[MeetingWindow] | tuple[MeetingWindow, ...],
    *,
    term_start: date,
    term_end: date,
) -> tuple[Conflict, ...]:
    """Detect exact recurring overlaps, accounting for date ranges and DST.

    A conflict is only reported between different sections. Meetings without a
    common occurrence date are not conflicts, so partial-term and alternate
    sessions remain representable. Invalid time zones are surfaced to the API
    as an UNKNOWN schedulability state rather than silently treated as free.
    """

    occurrences = {
        meeting.meeting_id: _occurrences(meeting, term_start=term_start, term_end=term_end)
        for meeting in meetings
    }
    conflicts: list[Conflict] = []
    for index, left in enumerate(meetings):
        for right in meetings[index + 1 :]:
            if left.section_id == right.section_id:
                continue
            for left_date, left_start, left_end in occurrences[left.meeting_id]:
                for right_date, right_start, right_end in occurrences[right.meeting_id]:
                    if abs((left_date - right_date).days) > 1:
                        continue
                    if left_start < right_end and right_start < left_end:
                        conflicts.append(
                            Conflict(
                                left_section_id=left.section_id,
                                right_section_id=right.section_id,
                                left_meeting_id=left.meeting_id,
                                right_meeting_id=right.meeting_id,
                                occurrence_date=left_date,
                                starts_at_utc=max(left_start, right_start),
                                ends_at_utc=min(left_end, right_end),
                            )
                        )
    return tuple(
        sorted(
            conflicts,
            key=lambda item: (
                item.occurrence_date,
                item.left_section_id,
                item.right_section_id,
                item.left_meeting_id,
                item.right_meeting_id,
            ),
        )
    )


def evaluate_schedule(
    meetings: list[MeetingWindow] | tuple[MeetingWindow, ...],
    *,
    term_start: date,
    term_end: date,
) -> ScheduleEvaluation:
    try:
        conflicts = detect_conflicts(meetings, term_start=term_start, term_end=term_end)
    except ValueError as exc:
        return ScheduleEvaluation(state="UNKNOWN", conflicts=(), unknown_reasons=(str(exc),))
    return ScheduleEvaluation(
        state="CONFLICT" if conflicts else "SCHEDULABLE",
        conflicts=conflicts,
        unknown_reasons=(),
    )
