"""End-to-end integration test for GUI logic and simulated device workflow."""

import os
import pytest
from core.adb import DemoAdbController
from core.analyzer import AppRiskAnalyzer
from core.db import DatabaseManager
from core.report import ServiceReportGenerator


def test_full_repair_shop_workflow(tmp_path):
    # 1. Initialize isolated Demo DB and Demo ADB
    db = DatabaseManager(db_path=str(tmp_path / "test_demo.db"), is_demo=True)
    adb = DemoAdbController()

    # 2. Connect device
    devices = adb.list_devices()
    assert len(devices) >= 2
    adb.set_active_device(devices[0]["serial"])

    dev_info = adb.get_device_info()
    assert dev_info["manufacturer"] == "Samsung"
    assert dev_info["model"] == "Galaxy A54 5G"

    # 3. First visit check
    conn_res1 = db.record_device_connection(
        dev_info["serial"], dev_info["manufacturer"], dev_info["model"], dev_info["release"]
    )
    assert conn_res1["is_repeat"] is False

    # 4. Scan 3rd-party packages (-3)
    packages = adb.list_third_party_packages()
    assert len(packages) >= 5

    scanned_results = []
    for p in packages:
        details = adb.get_package_details(p["package_name"])
        threat_intel = db.get_known_threat(p["package_name"])
        risk = AppRiskAnalyzer.analyze_app(
            package_name=p["package_name"],
            app_name=p["package_name"],
            installer=p["installer"],
            permissions=details.get("permissions", []),
            is_device_admin=details.get("is_device_admin", False),
            target_sdk=details.get("target_sdk"),
            first_install_time=details.get("first_install_time"),
            threat_intel=threat_intel
        )
        scanned_results.append(risk)

    high_risk = [a for a in scanned_results if a["risk_level"] == "high"]
    assert len(high_risk) >= 2  # Super Cleaner, Flashlight, HD Video Downloader, etc.

    # 5. Revoke Device Admin for the rogue cleaner
    admin_pkg = "com.superclean.booster.ads"
    success_admin, msg_admin = adb.remove_device_admin(admin_pkg)
    assert success_admin is True

    # 6. Uninstall rogue packages
    apps_to_remove = high_risk[:2]
    removed_apps = []
    for a in apps_to_remove:
        ok, msg = adb.uninstall_package(a["package_name"])
        assert ok is True
        removed_apps.append(a)

    # 7. Record visit & Shop Threat Intelligence
    db.record_visit(
        device_serial=dev_info["serial"],
        apps_scanned_count=len(scanned_results),
        apps_removed=removed_apps,
        risk_summary="high",
        notes="Customer reported popup ads during calls"
    )

    # Verify Shop Threat Intelligence has recorded the removed adware
    intel = db.get_known_threat(removed_apps[0]["package_name"])
    assert intel is not None
    assert intel["times_removed"] == 1
    assert intel["distinct_devices_count"] == 1

    # 8. Generate Service Report (PDF + HTML)
    rep_gen = ServiceReportGenerator(output_dir=str(tmp_path / "reports"))
    pdf_path, html_path = rep_gen.generate_report(
        device_info=dev_info,
        apps_scanned_count=len(scanned_results),
        removed_apps=removed_apps,
        technician_name="ช่างเอ็ดดี้"
    )
    assert os.path.exists(html_path)
    assert os.path.getsize(html_path) > 0

    # 9. Verify 30-Day Alert triggers on repeat visit
    conn_res2 = db.record_device_connection(
        dev_info["serial"], dev_info["manufacturer"], dev_info["model"], dev_info["release"]
    )
    assert conn_res2["is_repeat"] is True
    assert conn_res2["days_since_last_visit"] == 0
    assert "⚠️ เครื่องนี้เคยเข้ามารับบริการ" in conn_res2["alert_message"]
