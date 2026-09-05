"""ADB Controller and Device Interface for Android Adware Removal Tool.

Handles device discovery, multi-device selection, package scanning (strictly -3),
dumpsys inspection, device admin removal, and uninstallation.
Includes a fully isolated Simulated/Demo provider for offline testing and demos.
Strictly local subprocess execution, zero network calls.
"""

import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple


def find_adb_binary() -> str:
    """Find adb executable path on host system."""
    # 1. System PATH
    found = shutil.which("adb")
    if found:
        return found
        
    # 2. Common macOS / Linux / Windows paths
    candidates = [
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
        os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools/adb.exe"),
        "C:\\platform-tools\\adb.exe",
        "platform-tools/adb",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    return "adb"  # Fallback to name in PATH


class AdbController:
    """Manages communications with Android devices over ADB."""

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or find_adb_binary()
        self.active_serial: Optional[str] = None
        self.temp_dir = tempfile.mkdtemp(prefix="adware_cleaner_")
        self.is_demo_mode = False

    def run_cmd(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        """Execute local adb subprocess with timeout."""
        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return res.returncode, res.stdout, res.stderr
        except FileNotFoundError:
            return -1, "", f"ADB binary not found at: {self.adb_path}"
        except subprocess.TimeoutExpired:
            return -2, "", "ADB command timed out"
        except Exception as e:
            return -3, "", str(e)

    def run_device_shell(self, cmd_str: str, timeout: int = 15) -> Tuple[int, str, str]:
        """Run adb shell command on active device."""
        if not self.active_serial:
            return -1, "", "No active device selected"
        return self.run_cmd(["-s", self.active_serial, "shell", cmd_str], timeout=timeout)

    def list_devices(self) -> List[Dict[str, str]]:
        """List all connected Android devices."""
        code, out, _ = self.run_cmd(["devices", "-l"])
        devices = []
        if code != 0 or not out:
            return devices

        for line in out.strip().splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model = "Unknown"
                product = "Unknown"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                    elif p.startswith("product:"):
                        product = p.split(":", 1)[1]

                devices.append({
                    "serial": serial,
                    "model": model,
                    "product": product,
                    "display_name": f"{model} ({serial})"
                })
        return devices

    def set_active_device(self, serial: str) -> None:
        """Select device serial to operate on."""
        self.active_serial = serial

    def get_device_info(self) -> Dict[str, str]:
        """Get manufacturer, model, and Android OS version."""
        if not self.active_serial:
            return {"manufacturer": "Unknown", "model": "Unknown", "release": "Unknown", "serial": ""}

        _, mfg, _ = self.run_device_shell("getprop ro.product.manufacturer")
        _, mdl, _ = self.run_device_shell("getprop ro.product.model")
        _, rel, _ = self.run_device_shell("getprop ro.build.version.release")

        return {
            "serial": self.active_serial,
            "manufacturer": mfg.strip() or "Android",
            "model": mdl.strip() or "Device",
            "release": rel.strip() or "Unknown"
        }

    def list_third_party_packages(self) -> List[Dict[str, Optional[str]]]:
        """Scan 3rd party packages with installer: pm list packages -3 -i."""
        code, out, err = self.run_device_shell("pm list packages -3 -i")
        if code != 0:
            return []

        packages = []
        # Format example:
        # package:com.example.ads  installer=null
        # package:com.shopee.th  installer=com.android.vending
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("package:"):
                continue

            pkg_part = line[len("package:"):].strip()
            pkg_name = ""
            installer = None

            if "installer=" in pkg_part:
                chunks = pkg_part.split("installer=", 1)
                pkg_name = chunks[0].strip()
                installer_val = chunks[1].strip()
                if installer_val and installer_val.lower() not in ("null", "none"):
                    installer = installer_val
            else:
                pkg_name = pkg_part.split()[0].strip()

            if pkg_name:
                packages.append({
                    "package_name": pkg_name,
                    "installer": installer
                })

        return packages

    def get_package_details(self, package_name: str) -> Dict[str, Any]:
        """Extract permissions, targetSdk, install time, and admin state from dumpsys."""
        code, out, _ = self.run_device_shell(f"dumpsys package {package_name}")
        details = {
            "permissions": [],
            "target_sdk": None,
            "first_install_time": None,
            "is_device_admin": False,
            "apk_path": None
        }
        if code != 0 or not out:
            return details

        # 1. Parse permissions
        in_perms_section = False
        perms = set()
        for line in out.splitlines():
            sline = line.strip()
            if "requested permissions:" in sline.lower() or "install permissions:" in sline.lower():
                in_perms_section = True
                continue
            if in_perms_section:
                if sline.startswith("runtime permissions:") or sline.startswith("queriesPackages:"):
                    in_perms_section = False
                    continue
                # Permission names like android.permission.SYSTEM_ALERT_WINDOW: granted=true
                perm_match = re.match(r"^([a-zA-Z0-9_\.]+)", sline)
                if perm_match:
                    p = perm_match.group(1).split(":")[0].strip()
                    if "." in p:
                        perms.add(p)

        details["permissions"] = list(perms)

        # 2. Parse targetSdk
        sdk_match = re.search(r"targetSdk=(\d+)", out)
        if sdk_match:
            try:
                details["target_sdk"] = int(sdk_match.group(1))
            except Exception:
                pass

        # 3. Parse firstInstallTime
        fit_match = re.search(r"firstInstallTime=([0-9\- :]+)", out)
        if fit_match:
            details["first_install_time"] = fit_match.group(1).strip()

        # 4. Check device admin receivers
        if "android.permission.BIND_DEVICE_ADMIN" in out or "DeviceAdmin" in out:
            details["is_device_admin"] = True

        # 5. Extract APK path
        path_code, path_out, _ = self.run_device_shell(f"pm path {package_name}")
        if path_code == 0 and "package:" in path_out:
            for pline in path_out.splitlines():
                if pline.startswith("package:"):
                    details["apk_path"] = pline.replace("package:", "").strip()
                    break

        return details

    def pull_apk(self, remote_apk_path: str, local_name: str) -> Optional[str]:
        """Pull base.apk to temp folder for icon extraction."""
        if not self.active_serial or not remote_apk_path:
            return None
        dest = os.path.join(self.temp_dir, f"{local_name}.apk")
        if os.path.exists(dest):
            return dest

        code, _, _ = self.run_cmd(["-s", self.active_serial, "pull", remote_apk_path, dest], timeout=15)
        if code == 0 and os.path.exists(dest):
            return dest
        return None

    def remove_device_admin(self, package_name: str) -> Tuple[bool, str]:
        """Remove active device admin: dpm remove-active-admin."""
        # Find active admin component for package
        code, out, _ = self.run_device_shell("dumpsys device_policy")
        component = None
        if code == 0 and out:
            for line in out.splitlines():
                if package_name in line and "/" in line:
                    match = re.search(rf"({package_name}/[a-zA-Z0-9_\.]+)", line)
                    if match:
                        component = match.group(1)
                        break

        if not component:
            # Try default receiver component format
            component = f"{package_name}/.DeviceAdminReceiver"

        res_code, res_out, res_err = self.run_device_shell(f"dpm remove-active-admin {component}")
        combined = f"{res_out} {res_err}".strip()

        if "Success" in combined or res_code == 0:
            return True, f"ถอนสิทธิ์ Device Admin สำเร็จ ({component})"
        else:
            return False, (
                f"ไม่สามารถถอนสิทธิ์อัตโนมัติได้ ({combined})\n"
                "กรุณาไปที่เมนูมือถือ: การตั้งค่า (Settings) > ความปลอดภัย (Security) > "
                "แอปผู้ดูแลระบบ (Device admin apps) แล้วปิดสิทธิ์ด้วยตนเองก่อนลบแอป"
            )

    def uninstall_package(self, package_name: str) -> Tuple[bool, str]:
        """Safely uninstall 3rd party package: adb uninstall <pkg>."""
        if not self.active_serial:
            return False, "ไม่มีเครื่องที่เชื่อมต่ออยู่"

        code, out, err = self.run_cmd(["-s", self.active_serial, "uninstall", package_name], timeout=20)
        combined = f"{out} {err}".strip()
        if "Success" in combined:
            return True, "ลบแอปสำเร็จ (Success)"
        else:
            return False, f"ลบไม่สำเร็จ: {combined}"

    def reset_state(self) -> None:
        """Reset session state when switching devices."""
        self.active_serial = None
        # Clean up pulled APKs
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = tempfile.mkdtemp(prefix="adware_cleaner_")


class DemoAdbController(AdbController):
    """Simulated ADB provider for testing, training, and demo scenarios.

    Completely isolated, zero network, realistic adware & legitimate app samples.
    """

    def __init__(self):
        super().__init__()
        self.is_demo_mode = True
        self.active_serial = "DEMO-SM-A546E-001"
        self._mock_installed_packages = [
            {
                "package_name": "com.superclean.booster.ads",
                "app_name": "Super Cleaner & Battery Booster",
                "installer": None,
                "permissions": [
                    "android.permission.SYSTEM_ALERT_WINDOW",
                    "android.permission.BIND_ACCESSIBILITY_SERVICE",
                    "android.permission.BIND_DEVICE_ADMIN",
                    "android.permission.REQUEST_INSTALL_PACKAGES",
                    "android.permission.RECEIVE_BOOT_COMPLETED",
                    "com.samsung.android.permission.CUSTOM_AUTOSTART"
                ],
                "is_device_admin": True,
                "target_sdk": 21,
                "first_install_time": "2026-09-01 14:22:10"
            },
            {
                "package_name": "com.bright.flashlight.free",
                "app_name": "Ultra Bright Flashlight HD",
                "installer": None,
                "permissions": [
                    "android.permission.SYSTEM_ALERT_WINDOW",
                    "android.permission.RECEIVE_BOOT_COMPLETED",
                    "android.permission.QUERY_ALL_PACKAGES"
                ],
                "is_device_admin": False,
                "target_sdk": 22,
                "first_install_time": "2026-09-02 09:15:00"
            },
            {
                "package_name": "com.tube.video.downloader.apk",
                "app_name": "HD Video Downloader Pro",
                "installer": "com.android.packageinstaller",
                "permissions": [
                    "android.permission.SYSTEM_ALERT_WINDOW",
                    "android.permission.REQUEST_INSTALL_PACKAGES",
                    "android.permission.WRITE_EXTERNAL_STORAGE"
                ],
                "is_device_admin": False,
                "target_sdk": 26,
                "first_install_time": "2026-09-03 18:40:12"
            },
            {
                "package_name": "com.antivirus.security.pro",
                "app_name": "Virus Master Security 2026",
                "installer": None,
                "permissions": [
                    "android.permission.BIND_DEVICE_ADMIN",
                    "android.permission.BIND_ACCESSIBILITY_SERVICE"
                ],
                "is_device_admin": True,
                "target_sdk": 24,
                "first_install_time": "2026-08-25 11:30:00"
            },
            {
                "package_name": "com.cool.call.recorder",
                "app_name": "Call Recorder Automatic",
                "installer": None,
                "permissions": [
                    "android.permission.RECORD_AUDIO",
                    "android.permission.READ_PHONE_STATE",
                    "android.permission.RECEIVE_BOOT_COMPLETED"
                ],
                "is_device_admin": False,
                "target_sdk": 28,
                "first_install_time": "2026-08-29 16:05:00"
            },
            {
                "package_name": "com.linecorp.line",
                "app_name": "LINE",
                "installer": "com.android.vending",
                "permissions": [
                    "android.permission.CAMERA",
                    "android.permission.RECORD_AUDIO"
                ],
                "is_device_admin": False,
                "target_sdk": 34,
                "first_install_time": "2024-01-10 10:00:00"
            },
            {
                "package_name": "com.shopee.th",
                "app_name": "Shopee",
                "installer": "com.android.vending",
                "permissions": [
                    "android.permission.INTERNET"
                ],
                "is_device_admin": False,
                "target_sdk": 34,
                "first_install_time": "2024-05-15 12:00:00"
            },
            {
                "package_name": "com.kbank.kplus",
                "app_name": "K PLUS",
                "installer": "com.android.vending",
                "permissions": [
                    "android.permission.USE_BIOMETRIC"
                ],
                "is_device_admin": False,
                "target_sdk": 34,
                "first_install_time": "2024-02-20 09:30:00"
            },
            {
                "package_name": "com.sec.android.app.sbrowser",
                "app_name": "Samsung Internet Browser",
                "installer": "com.sec.android.app.samsungapps",
                "permissions": [
                    "android.permission.INTERNET"
                ],
                "is_device_admin": False,
                "target_sdk": 34,
                "first_install_time": "2024-01-01 08:00:00"
            }
        ]

    def list_devices(self) -> List[Dict[str, str]]:
        return [
            {
                "serial": "DEMO-SM-A546E-001",
                "model": "Galaxy A54 5G (SM-A546E)",
                "product": "a54x",
                "display_name": "Galaxy A54 5G [จำลอง Demo] (DEMO-SM-A546E-001)"
            },
            {
                "serial": "DEMO-CPH2343-002",
                "model": "OPPO Reno8 Z 5G",
                "product": "cph2343",
                "display_name": "OPPO Reno8 Z [จำลอง Demo] (DEMO-CPH2343-002)"
            }
        ]

    def get_device_info(self) -> Dict[str, str]:
        if self.active_serial == "DEMO-CPH2343-002":
            return {
                "serial": "DEMO-CPH2343-002",
                "manufacturer": "OPPO",
                "model": "OPPO Reno8 Z 5G",
                "release": "13"
            }
        return {
            "serial": "DEMO-SM-A546E-001",
            "manufacturer": "Samsung",
            "model": "Galaxy A54 5G",
            "release": "14"
        }

    def list_third_party_packages(self) -> List[Dict[str, Optional[str]]]:
        return [
            {"package_name": p["package_name"], "installer": p["installer"]}
            for p in self._mock_installed_packages
        ]

    def get_package_details(self, package_name: str) -> Dict[str, Any]:
        for p in self._mock_installed_packages:
            if p["package_name"] == package_name:
                return {
                    "permissions": p["permissions"],
                    "target_sdk": p["target_sdk"],
                    "first_install_time": p["first_install_time"],
                    "is_device_admin": p["is_device_admin"],
                    "apk_path": None
                }
        return {
            "permissions": [],
            "target_sdk": None,
            "first_install_time": None,
            "is_device_admin": False,
            "apk_path": None
        }

    def remove_device_admin(self, package_name: str) -> Tuple[bool, str]:
        for p in self._mock_installed_packages:
            if p["package_name"] == package_name:
                p["is_device_admin"] = False
                return True, f"ถอนสิทธิ์ Device Admin สำเร็จ ({package_name})"
        return False, "ไม่พบแอปดังกล่าว"

    def uninstall_package(self, package_name: str) -> Tuple[bool, str]:
        before_len = len(self._mock_installed_packages)
        self._mock_installed_packages = [
            p for p in self._mock_installed_packages if p["package_name"] != package_name
        ]
        if len(self._mock_installed_packages) < before_len:
            return True, "ลบแอปสำเร็จ (Success)"
        return False, "ไม่พบแอปที่ต้องการลบ"

    def reset_state(self) -> None:
        self.__init__()
