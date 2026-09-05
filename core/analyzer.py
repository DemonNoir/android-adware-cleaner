"""Risk Analysis Engine for Android Applications.

Analyzes third-party Android packages for adware, malware, overlay hijacking,
accessibility abuse, and device admin persistence.
Integrates local shop threat intelligence (offline).
Handles custom OEM permissions gracefully without crashes.
"""

from typing import Any, Dict, List, Optional, Set

# Known official app stores
TRUSTED_INSTALLERS: Set[str] = {
    "com.android.vending",                  # Google Play Store
    "com.sec.android.app.samsungapps",      # Samsung Galaxy Store
    "com.huawei.appmarket",                 # Huawei AppGallery
    "com.xiaomi.mipicks",                   # Xiaomi GetApps
    "com.oppo.market",                      # OPPO App Market
    "com.vivo.appstore",                    # Vivo App Store
}

# Critical permissions commonly weaponized by adware and rogue apps
CRITICAL_PERMISSIONS = {
    "android.permission.SYSTEM_ALERT_WINDOW": {
        "score": 35,
        "name": "SYSTEM_ALERT_WINDOW",
        "th_desc": "ขอสิทธิ์แสดงทับหน้าจออื่น (โฆษณาเด้ง/Popup กวนใจ)"
    },
    "android.permission.BIND_ACCESSIBILITY_SERVICE": {
        "score": 45,
        "name": "BIND_ACCESSIBILITY_SERVICE",
        "th_desc": "ขอสิทธิ์บริการช่วยเหลือพิเศษ (ดักจับหน้าจอ/คลิกเองอัตโนมัติ)"
    },
    "android.permission.BIND_DEVICE_ADMIN": {
        "score": 50,
        "name": "BIND_DEVICE_ADMIN",
        "th_desc": "ขอสิทธิ์ผู้ดูแลระบบอุปกรณ์ (ป้องกันการลบแอปตามปกติ)"
    },
    "android.permission.REQUEST_INSTALL_PACKAGES": {
        "score": 30,
        "name": "REQUEST_INSTALL_PACKAGES",
        "th_desc": "ขอสิทธิ์แอบดาวน์โหลดและติดตั้ง APK อื่นลงเครื่อง"
    },
    "android.permission.RECEIVE_BOOT_COMPLETED": {
        "score": 10,
        "name": "RECEIVE_BOOT_COMPLETED",
        "th_desc": "เริ่มทำงานทันทีเมื่อเปิดเครื่อง (Autostart)"
    },
    "android.permission.QUERY_ALL_PACKAGES": {
        "score": 15,
        "name": "QUERY_ALL_PACKAGES",
        "th_desc": "สอดส่องรายชื่อแอปทั้งหมดในเครื่อง"
    }
}

STANDARD_AOSP_PREFIXES = ("android.permission.", "com.android.")


class AppRiskAnalyzer:
    """Evaluates risk levels for scanned Android packages."""

    @staticmethod
    def is_trusted_installer(installer: Optional[str]) -> bool:
        if not installer:
            return False
        clean_installer = installer.strip().lower()
        if clean_installer in ("null", "none", ""):
            return False
        return any(clean_installer == ti.lower() for ti in TRUSTED_INSTALLERS)

    @classmethod
    def analyze_app(
        cls,
        package_name: str,
        app_name: str,
        installer: Optional[str],
        permissions: List[str],
        is_device_admin: bool = False,
        target_sdk: Optional[int] = None,
        first_install_time: Optional[str] = None,
        threat_intel: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a single package and return structured risk assessment."""
        score = 0
        reasons: List[str] = []
        risky_permissions: List[str] = []
        unknown_permissions: List[str] = []

        # 1. Evaluate Installer
        is_trusted = cls.is_trusted_installer(installer)
        clean_installer = (installer or "").strip()
        if clean_installer in ("null", "none"):
            clean_installer = ""

        if not is_trusted:
            if not clean_installer:
                score += 25
                reasons.append("ติดตั้งแบบไม่ทราบแหล่งที่มา (Sideload / Direct APK)")
            elif "packageinstaller" in clean_installer.lower():
                score += 20
                reasons.append(f"ติดตั้งผ่าน Package Installer ({clean_installer})")
            else:
                score += 15
                reasons.append(f"ติดตั้งจากแหล่งภายนอก ({clean_installer})")
        else:
            reasons.append(f"ติดตั้งจาก Store ทางการ ({clean_installer})")

        # 2. Evaluate Permissions
        perm_set = set(permissions or [])
        
        # If device admin flag is set externally or in permissions
        if is_device_admin or "android.permission.BIND_DEVICE_ADMIN" in perm_set:
            score += CRITICAL_PERMISSIONS["android.permission.BIND_DEVICE_ADMIN"]["score"]
            risky_permissions.append("BIND_DEVICE_ADMIN")
            reasons.append(CRITICAL_PERMISSIONS["android.permission.BIND_DEVICE_ADMIN"]["th_desc"])

        for perm_name, meta in CRITICAL_PERMISSIONS.items():
            if perm_name == "android.permission.BIND_DEVICE_ADMIN":
                continue  # Handled above
            if perm_name in perm_set:
                score += meta["score"]
                risky_permissions.append(meta["name"])
                reasons.append(meta["th_desc"])

        # Check for unknown / OEM custom permissions (Samsung, Xiaomi MIUI, Oppo ColorOS, Vivo)
        for perm in perm_set:
            if not perm.startswith(STANDARD_AOSP_PREFIXES):
                unknown_permissions.append(perm)

        if unknown_permissions:
            reasons.append(f"มี custom/OEM permission เฉพาะรุ่น {len(unknown_permissions)} รายการ")

        # 3. Check Target SDK (Ancient SDK bypasses Android runtime permission prompt)
        if target_sdk is not None and target_sdk < 23:
            score += 20
            reasons.append(f"Target SDK เก่าผิดปกติ ({target_sdk}) อาจเจตนาเลี่ยงระบบขอสิทธิ์สมัยใหม่")

        # 4. Integrate Local Threat Intelligence (Shop Intel)
        if threat_intel:
            distinct_devices = threat_intel.get("distinct_devices_count", 0)
            times_removed = threat_intel.get("times_removed", 0)
            if distinct_devices >= 2:
                intel_bonus = min(40, distinct_devices * 15)
                score += intel_bonus
                reasons.insert(
                    0,
                    f"🔥 ประวัติร้าน: พบการลบในเครื่องลูกค้าแล้ว {distinct_devices} ราย "
                    f"(ลบทั้งหมด {times_removed} ครั้ง)"
                )
            elif times_removed >= 1:
                score += 10
                reasons.append(f"ประวัติร้าน: เคยมีช่างลบแอปนี้แล้ว {times_removed} ครั้ง")

        # 5. Determine Overall Risk Level
        # Thresholds:
        # High (น่าสงสัยมาก): score >= 50 or (not trusted and alert_window/accessibility/admin) or intel >= 2 devices
        has_critical_hijack = any(
            p in risky_permissions for p in ["SYSTEM_ALERT_WINDOW", "BIND_ACCESSIBILITY_SERVICE", "BIND_DEVICE_ADMIN"]
        )

        has_intel_flag = threat_intel and threat_intel.get("distinct_devices_count", 0) >= 2

        if (score >= 50) or (not is_trusted and has_critical_hijack) or has_intel_flag:
            risk_level = "high"
        elif (score >= 25) or (not is_trusted and len(risky_permissions) > 0) or is_device_admin:
            risk_level = "suspicious"
        else:
            risk_level = "safe"

        return {
            "package_name": package_name,
            "app_name": app_name or package_name,
            "installer": clean_installer if clean_installer else None,
            "risky_permissions": risky_permissions,
            "unknown_permissions": unknown_permissions,
            "risk_level": risk_level,
            "risk_score": min(100, score),
            "reasons": reasons,
            "first_install_time": first_install_time,
            "target_sdk": target_sdk,
            "is_device_admin": is_device_admin or ("BIND_DEVICE_ADMIN" in risky_permissions),
            "threat_intel": threat_intel
        }
