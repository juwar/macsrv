"""Tests for macsrv configuration."""

from pathlib import Path
from macsrv.config import MacSrvConfig


class TestMacSrvConfig:
    def test_defaults(self):
        cfg = MacSrvConfig.load()
        assert cfg.auto_stop_time == "02:00"
        assert cfg.display_sleep == 10
        assert cfg.logging is True

    def test_set_valid(self):
        cfg = MacSrvConfig()
        success, err = cfg.set("auto_stop_time", "03:00")
        assert success
        assert cfg.auto_stop_time == "03:00"

    def test_set_invalid_key(self):
        cfg = MacSrvConfig()
        success, err = cfg.set("nope", "val")
        assert not success
        assert "Unknown key" in err

    def test_set_invalid_time(self):
        cfg = MacSrvConfig()
        success, err = cfg.set("auto_stop_time", "25:00")
        assert not success

    def test_set_logging_false(self):
        cfg = MacSrvConfig()
        success, err = cfg.set("logging", "false")
        assert success
        assert cfg.logging is False

    def test_display(self):
        cfg = MacSrvConfig()
        d = cfg.display()
        assert d["auto_stop_time"] == "02:00"
        assert d["logging"] == "true"