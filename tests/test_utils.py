"""Tests for macsrv utility functions."""

import pytest
from datetime import datetime, timedelta
from macsrv.utils import parse_time, parse_duration, format_remaining, format_timestamp, seconds_until


class TestParseTime:
    def test_basic(self):
        dt = parse_time("14:00")
        assert dt.hour == 14
        assert dt.minute == 0
        assert dt.second == 0

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("abc")

    def test_invalid_hours(self):
        with pytest.raises(ValueError, match="Time out of range"):
            parse_time("24:00")

    def test_invalid_minutes(self):
        with pytest.raises(ValueError, match="Time out of range"):
            parse_time("12:60")


class TestParseDuration:
    def test_hours(self):
        td = parse_duration("8h")
        assert td == timedelta(hours=8)

    def test_minutes(self):
        td = parse_duration("30m")
        assert td == timedelta(minutes=30)

    def test_combined(self):
        td = parse_duration("2h30m")
        assert td == timedelta(hours=2, minutes=30)

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_duration("xyz")

    def test_zero(self):
        with pytest.raises(ValueError, match="cannot be zero"):
            parse_duration("0h")


class TestFormatRemaining:
    def test_hours_minutes(self):
        assert format_remaining(42000) == "11h 40m"

    def test_zero(self):
        assert format_remaining(0) == "0h 0m"

    def test_negative(self):
        assert format_remaining(-100) == "0h 0m"


class TestFormatTimestamp:
    def test_none(self):
        assert format_timestamp(None) == "-"


class TestSecondsUntil:
    def test_future(self):
        future = datetime.now() + timedelta(hours=1)
        assert seconds_until(future) > 0

    def test_past(self):
        past = datetime.now() - timedelta(hours=1)
        assert seconds_until(past) == 0