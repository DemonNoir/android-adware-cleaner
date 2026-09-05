"""Unit tests for Risk Analyzer and Shop Threat Intelligence."""

import pytest
from core.analyzer import AppRiskAnalyzer


def test_trusted_installer():
    assert AppRiskAnalyzer.is_trusted_installer("com.android.vending") is True
    assert AppRiskAnalyzer.is_trusted_installer("com.sec.android.app.samsungapps") is True
    assert AppRiskAnalyzer.is_trusted_installer(None) is False
    assert AppRiskAnalyzer.is_trusted_installer("null") is False
    assert AppRiskAnalyzer.is_trusted_installer("") is False


def test_high_risk_adware_detection():
    # Null installer + SYSTEM_ALERT_WINDOW + BIND_ACCESSIBILITY_SERVICE
    res = AppRiskAnalyzer.analyze_app(
        package_name="com.adware.popup",
        app_name="Super Cleaner",
        installer=None,
        permissions=[
            "android.permission.SYSTEM_ALERT_WINDOW",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
            "android.permission.REQUEST_INSTALL_PACKAGES"
        ],
        is_device_admin=False,
        target_sdk=22
    )

    assert res["risk_level"] == "high"
    assert "SYSTEM_ALERT_WINDOW" in res["risky_permissions"]
    assert "BIND_ACCESSIBILITY_SERVICE" in res["risky_permissions"]
    assert any("Sideload" in r for r in res["reasons"])


def test_legitimate_play_store_app():
    res = AppRiskAnalyzer.analyze_app(
        package_name="com.kbank.kplus",
        app_name="K PLUS",
        installer="com.android.vending",
        permissions=["android.permission.USE_BIOMETRIC"],
        is_device_admin=False,
        target_sdk=34
    )

    assert res["risk_level"] == "safe"
    assert len(res["risky_permissions"]) == 0


def test_oem_custom_permission_handling():
    res = AppRiskAnalyzer.analyze_app(
        package_name="com.samsung.custom",
        app_name="Samsung Tool",
        installer="com.sec.android.app.samsungapps",
        permissions=["com.samsung.android.permission.SPECIAL_ACCESS"],
        is_device_admin=False,
        target_sdk=34
    )

    # Must not crash, should capture unknown_permissions
    assert "com.samsung.android.permission.SPECIAL_ACCESS" in res["unknown_permissions"]


def test_shop_threat_intel_elevation():
    # App has standard permissions, but Shop Intel shows it was removed on 3 different customer devices!
    intel = {
        "distinct_devices_count": 3,
        "times_removed": 4
    }
    res = AppRiskAnalyzer.analyze_app(
        package_name="com.shady.cleaner",
        app_name="Clean Master Pro",
        installer=None,
        permissions=["android.permission.INTERNET"],
        is_device_admin=False,
        target_sdk=29,
        threat_intel=intel
    )

    # Elevated due to shop threat intelligence
    assert res["risk_level"] == "high"
    assert any("ประวัติร้าน" in r for r in res["reasons"])
