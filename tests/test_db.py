"""Unit tests for DatabaseManager, 30-day alerts, and Threat Intelligence."""

import os
from datetime import datetime, timedelta
from core.db import DatabaseManager


def test_isolated_in_memory_db():
    db = DatabaseManager(db_path=":memory:", is_demo=True)
    conn_info = db.record_device_connection("DEV-001", "Samsung", "S23", "14")
    assert conn_info["is_repeat"] is False
    assert conn_info["days_since_last_visit"] is None

    # Reconnecting same serial
    conn_info2 = db.record_device_connection("DEV-001", "Samsung", "S23", "14")
    assert conn_info2["is_repeat"] is True
    assert conn_info2["days_since_last_visit"] == 0
    assert "⚠️ เครื่องนี้เคยเข้ามารับบริการ" in conn_info2["alert_message"]


def test_30_day_alert_boundary():
    db = DatabaseManager(db_path=":memory:", is_demo=True)
    serial = "DEV-REPEAT-1"
    
    # Simulate a past visit 15 days ago
    past_date = (datetime.now() - timedelta(days=15)).isoformat()
    with db._get_connection() as conn:
        conn.execute(
            "INSERT INTO devices (serial, manufacturer, model, android_version, first_seen, last_seen, visit_count) "
            "VALUES (?, 'Xiaomi', 'Redmi Note 12', '13', ?, ?, 1)",
            (serial, past_date, past_date)
        )
        conn.commit()

    # Now reconnect today
    info = db.record_device_connection(serial, "Xiaomi", "Redmi Note 12", "13")
    assert info["is_repeat"] is True
    assert info["days_since_last_visit"] == 15
    assert info["alert_message"] is not None
    assert "15 วันที่แล้ว" in info["alert_message"]

    # If past visit was 45 days ago (> 30 days), no 30-day warning
    serial_old = "DEV-OLD-1"
    old_date = (datetime.now() - timedelta(days=45)).isoformat()
    with db._get_connection() as conn:
        conn.execute(
            "INSERT INTO devices (serial, manufacturer, model, android_version, first_seen, last_seen, visit_count) "
            "VALUES (?, 'OPPO', 'Reno 8', '13', ?, ?, 1)",
            (serial_old, old_date, old_date)
        )
        conn.commit()

    info_old = db.record_device_connection(serial_old, "OPPO", "Reno 8", "13")
    assert info_old["is_repeat"] is True
    assert info_old["days_since_last_visit"] == 45
    assert info_old["alert_message"] is None


def test_shop_threat_intelligence_aggregation():
    db = DatabaseManager(db_path=":memory:", is_demo=True)

    # Customer 1 has fake adware removed
    db.record_visit(
        device_serial="DEVICE-CUST-1",
        apps_scanned_count=10,
        apps_removed=[
            {
                "package_name": "com.rogue.adware",
                "app_name": "Speed Booster",
                "risk_level": "high",
                "reason": "Overlay ads"
            }
        ],
        risk_summary="high"
    )

    intel1 = db.get_known_threat("com.rogue.adware")
    assert intel1 is not None
    assert intel1["distinct_devices_count"] == 1
    assert intel1["times_removed"] == 1

    # Customer 2 also has the same fake adware removed!
    db.record_visit(
        device_serial="DEVICE-CUST-2",
        apps_scanned_count=15,
        apps_removed=[
            {
                "package_name": "com.rogue.adware",
                "app_name": "Speed Booster Pro",
                "risk_level": "high",
                "reason": "Popups"
            }
        ],
        risk_summary="high"
    )

    intel2 = db.get_known_threat("com.rogue.adware")
    assert intel2 is not None
    assert intel2["distinct_devices_count"] == 2
    assert intel2["times_removed"] == 2
