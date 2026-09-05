"""Unit test verifying zero network calls (100% offline guarantee)."""

import socket
import pytest
from core.analyzer import AppRiskAnalyzer
from core.db import DatabaseManager
from core.report import ServiceReportGenerator


def test_zero_network_calls(monkeypatch, tmp_path):
    """Ensure socket connections are never attempted in any core component."""
    def guarded_connect(*args, **kwargs):
        raise RuntimeError("Forbidden external network attempt detected!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    # 1. Database operations
    db = DatabaseManager(db_path=":memory:", is_demo=True)
    db.record_device_connection("TEST-OFFLINE-01", "Samsung", "A54", "14")
    db.record_visit(
        device_serial="TEST-OFFLINE-01",
        apps_scanned_count=5,
        apps_removed=[{"package_name": "com.test.ads", "app_name": "Test Ads", "risk_level": "high"}],
        risk_summary="high"
    )

    # 2. Risk analysis
    res = AppRiskAnalyzer.analyze_app(
        package_name="com.test.ads",
        app_name="Test Ads",
        installer=None,
        permissions=["android.permission.SYSTEM_ALERT_WINDOW"]
    )
    assert res["risk_level"] == "high"

    # 3. Report generation
    rg = ServiceReportGenerator(output_dir=str(tmp_path))
    pdf_path, html_path = rg.generate_report(
        device_info={"serial": "TEST-OFFLINE-01", "manufacturer": "Samsung", "model": "A54", "release": "14"},
        apps_scanned_count=5,
        removed_apps=[{"package_name": "com.test.ads", "app_name": "Test Ads", "risk_level": "high", "reasons": ["Test"]}]
    )

    import os
    assert os.path.exists(html_path)
