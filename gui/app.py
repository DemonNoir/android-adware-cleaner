"""Main Desktop Application Window for Android Adware Removal Tool.

Designed specifically for mobile phone repair shops.
Supports live ADB connections and fully isolated Demo Mode.
Strictly local and offline.
"""

import os
import subprocess
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import customtkinter as ctk
from PIL import Image

from core.adb import AdbController, DemoAdbController
from core.analyzer import AppRiskAnalyzer
from core.apk_parser import ApkParser
from core.db import DatabaseManager
from core.report import ServiceReportGenerator
from gui.components import AppCard, RiskBadge
from gui.dialogs import ConfirmUninstallDialog, DeviceAdminGuideDialog, HistoryAndIntelDialog

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AdwareRemovalApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("เครื่องมือลบแอปโฆษณา & มัลแวร์ — สำหรับหน้าร้านซ่อมมือถือ")
        self.geometry("1220x800")
        self.minsize(1050, 700)

        # State initialization
        self.is_demo_mode = True  # Start in Demo mode for safe preview, can toggle to live
        self._init_controllers()

        self.scanned_apps: List[Dict[str, Any]] = []
        self.selected_packages: Set[str] = set()
        self.app_cards: Dict[str, AppCard] = {}
        self.selected_app_inspect: Optional[Dict[str, Any]] = None
        self.removed_apps_this_session: List[Dict[str, Any]] = []
        self.repeat_alert_text: Optional[str] = None

        self._build_ui()
        self._refresh_device_list()

    def _init_controllers(self) -> None:
        """Initialize ADB, DB, Parser, and Report generator depending on mode."""
        if self.is_demo_mode:
            self.adb = DemoAdbController()
            # Demo mode uses separate in-memory or demo DB file
            self.db = DatabaseManager(db_path="data/demo_shop.db", is_demo=True)
        else:
            self.adb = AdbController()
            self.db = DatabaseManager(db_path="data/repair_shop.db", is_demo=False)

        self.apk_parser = ApkParser()
        self.report_gen = ServiceReportGenerator()

    def _build_ui(self) -> None:
        """Construct application layout."""
        # Root grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Top Header Bar (Device Info & Mode Indicator)
        self._build_header_bar()

        # 2. 30-Day Warning Banner Container
        self.banner_frame = ctk.CTkFrame(self, fg_color="#b45309", corner_radius=0, height=0)
        self.banner_frame.grid(row=1, column=0, sticky="ew")
        self.banner_label = ctk.CTkLabel(
            self.banner_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        self.banner_label.pack(pady=8, padx=16)
        self.banner_frame.grid_remove()  # Hidden by default

        # 3. Main Workspace (Split: Left App List, Right Inspector & Logs)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=2, column=0, sticky="nsew", padx=16, pady=(10, 16))
        self.main_container.grid_columnconfigure(0, weight=6)
        self.main_container.grid_columnconfigure(1, weight=4)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Quick Action Toolbar (Row 0 of main container)
        self._build_action_toolbar()

        # Left: App list scrollable frame
        self._build_app_list_panel()

        # Right: Inspector & Log panel
        self._build_inspector_panel()

    def _build_header_bar(self) -> None:
        header = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1e293b"), corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        # Left section: Mode Indicator & Toggle
        mode_box = ctk.CTkFrame(header, fg_color="transparent")
        mode_box.pack(side="left", padx=16, pady=10)

        mode_bg = "#f59e0b" if self.is_demo_mode else "#10b981"
        mode_txt = "🟡 DEMO MODE (ข้อมูลจำลอง)" if self.is_demo_mode else "🟢 LIVE (เครื่องจริง)"
        self.mode_badge = ctk.CTkLabel(
            mode_box,
            text=mode_txt,
            fg_color=mode_bg,
            text_color="#1e293b" if self.is_demo_mode else "#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.mode_badge.pack(side="left", padx=(0, 10))

        self.mode_toggle_btn = ctk.CTkButton(
            mode_box,
            text="สลับเป็นโหมดจริง" if self.is_demo_mode else "สลับเป็นโหมดจำลอง",
            font=ctk.CTkFont(size=11),
            width=135,
            height=32,
            fg_color=("#64748b", "#334155"),
            command=self._toggle_mode
        )
        self.mode_toggle_btn.pack(side="left")

        # Center section: Connected Device Dropdown
        dev_box = ctk.CTkFrame(header, fg_color="transparent")
        dev_box.pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(dev_box, text="อุปกรณ์:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))

        self.device_dropdown = ctk.CTkOptionMenu(
            dev_box,
            values=["กำลังค้นหา..."],
            command=self._on_device_selected,
            width=285,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        self.device_dropdown.pack(side="left", padx=(0, 6))

        self.refresh_btn = ctk.CTkButton(
            dev_box,
            text="🔄",
            width=34,
            height=34,
            command=self._refresh_device_list
        )
        self.refresh_btn.pack(side="left")

        # Device info chips (Manufacturer, Model, Android)
        self.dev_info_lbl = ctk.CTkLabel(
            header,
            text="ยี่ห้อ: - | รุ่น: - | Android: -",
            font=ctk.CTkFont(size=12),
            text_color=("#475569", "#cbd5e1")
        )
        self.dev_info_lbl.pack(side="left", padx=12)

        # Right section: "เปลี่ยนเครื่อง (Switch / Reset)"
        switch_btn = ctk.CTkButton(
            header,
            text="👥 เปลี่ยนเครื่อง (Reset คิว)",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self._reset_for_next_customer
        )
        switch_btn.pack(side="right", padx=16, pady=10)


    def _build_action_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self.main_container, fg_color=("#ffffff", "#1e293b"), corner_radius=10, height=58)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        toolbar.grid_propagate(False)

        # Action buttons
        self.scan_btn = ctk.CTkButton(
            toolbar,
            text="🔍 สแกนแอป (-3)",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.start_scan_async
        )
        self.scan_btn.pack(side="left", padx=(10, 5), pady=10)

        self.select_high_risk_btn = ctk.CTkButton(
            toolbar,
            text="⚡ เลือกแอปเสี่ยงสูงทั้งหมด",
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="#1e293b",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.select_all_high_risk
        )
        self.select_high_risk_btn.pack(side="left", padx=5, pady=10)

        self.remove_admin_btn = ctk.CTkButton(
            toolbar,
            text="🛡️ ถอนสิทธิ์ Admin",
            fg_color=("#64748b", "#475569"),
            hover_color=("#475569", "#334155"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.remove_selected_device_admin
        )
        self.remove_admin_btn.pack(side="left", padx=5, pady=10)

        self.delete_btn = ctk.CTkButton(
            toolbar,
            text="🗑️ ลบแอปที่เลือก",
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.confirm_and_uninstall_selected
        )
        self.delete_btn.pack(side="left", padx=5, pady=10)

        self.rescan_btn = ctk.CTkButton(
            toolbar,
            text="🔄 สแกนซ้ำ",
            fg_color=("#64748b", "#334155"),
            font=ctk.CTkFont(size=12),
            height=36,
            command=self.start_scan_async
        )
        self.rescan_btn.pack(side="left", padx=5, pady=10)

        self.report_btn = ctk.CTkButton(
            toolbar,
            text="📄 ใบรายงานบริการ (PDF)",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.generate_service_report
        )
        self.report_btn.pack(side="right", padx=(5, 10), pady=10)

        self.history_btn = ctk.CTkButton(
            toolbar,
            text="📊 ประวัติร้าน & Intel",
            fg_color=("#475569", "#334155"),
            font=ctk.CTkFont(size=12),
            height=36,
            command=self.show_history_dialog
        )
        self.history_btn.pack(side="right", padx=5, pady=10)


    def _build_app_list_panel(self) -> None:
        left_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        left_container.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left_container.grid_rowconfigure(1, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        # Header summary row
        self.list_summary_lbl = ctk.CTkLabel(
            left_container,
            text="พร้อมสแกน — กดปุ่ม 'สแกนแอปทั้งหมด' เพื่อเริ่มต้น",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.list_summary_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # Scrollable app cards container
        self.app_list_scroll = ctk.CTkScrollableFrame(left_container, fg_color=("#f1f5f9", "#0f172a"))
        self.app_list_scroll.grid(row=1, column=0, sticky="nsew")

    def _build_inspector_panel(self) -> None:
        right_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        right_container.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right_container.grid_rowconfigure(0, weight=5)
        right_container.grid_rowconfigure(1, weight=4)
        right_container.grid_columnconfigure(0, weight=1)

        # Top Right: Inspector card
        inspector_frame = ctk.CTkFrame(right_container, fg_color=("#ffffff", "#1e293b"), corner_radius=10)
        inspector_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        inspector_frame.grid_columnconfigure(0, weight=1)
        inspector_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            inspector_frame,
            text="🔍 รายละเอียดแอปที่เลือก (App Inspector)",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        self.inspector_scroll = ctk.CTkScrollableFrame(inspector_frame, fg_color="transparent")
        self.inspector_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.inspector_placeholder = ctk.CTkLabel(
            self.inspector_scroll,
            text="คลิกเลือกแอปพลิเคชันจากการ์ดทางซ้าย\nเพื่อดูการวิเคราะห์ความเสี่ยงและ Permissions ทั้งหมด",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8")
        )
        self.inspector_placeholder.pack(pady=40)

        # Bottom Right: Real-time Action Log
        log_frame = ctk.CTkFrame(right_container, fg_color=("#ffffff", "#1e293b"), corner_radius=10)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_frame,
            text="📋 บันทึกการทำงาน (Action Log)",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))

        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(size=11, family="Courier"),
            fg_color=("#0f172a", "#090d16"),
            text_color="#38bdf8",
            wrap="word"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.log("🚀 โปรแกรมพร้อมทำงาน — " + ("โหมดจำลอง (Demo Mode)" if self.is_demo_mode else "โหมดร้านค้าจริง (Live Mode)"))

    def log(self, message: str) -> None:
        """Append log message with timestamp."""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{time_str}] {message}\n")
        self.log_textbox.see("end")

    # -------------------------------------------------------------
    # Mode & Device Management
    # -------------------------------------------------------------

    def _toggle_mode(self) -> None:
        """Switch between Live Mode and Demo Mode."""
        self.is_demo_mode = not self.is_demo_mode
        self._init_controllers()

        mode_bg = "#f59e0b" if self.is_demo_mode else "#10b981"
        mode_txt = "🟡 DEMO MODE (ข้อมูลจำลอง)" if self.is_demo_mode else "🟢 LIVE (เครื่องจริง)"
        self.mode_badge.configure(text=mode_txt, fg_color=mode_bg, text_color="#1e293b" if self.is_demo_mode else "#ffffff")
        self.mode_toggle_btn.configure(text="สลับเป็นโหมดจริง" if self.is_demo_mode else "สลับเป็นโหมดจำลอง")

        self.log(f"🔄 สลับระบบเป็น: {mode_txt}")
        self._reset_for_next_customer()

    def _refresh_device_list(self) -> None:
        """Fetch and populate connected devices in the dropdown."""
        devices = self.adb.list_devices()
        if not devices:
            self.device_dropdown.configure(values=["ไม่พบอุปกรณ์ที่เชื่อมต่อ"])
            self.device_dropdown.set("ไม่พบอุปกรณ์ที่เชื่อมต่อ")
            self.dev_info_lbl.configure(text="ยี่ห้อ: - | รุ่น: - | Android: -")
            self.banner_frame.grid_remove()
            self.log("⚠️ ไม่พบอุปกรณ์ที่เชื่อมต่อผ่านสาย ADB")
            return

        display_options = [d["display_name"] for d in devices]
        self.device_dropdown.configure(values=display_options)
        
        # Select first device
        first_display = display_options[0]
        self.device_dropdown.set(first_display)
        self._on_device_selected(first_display)

    def _on_device_selected(self, display_name: str) -> None:
        """Handle device selection from dropdown."""
        devices = self.adb.list_devices()
        for d in devices:
            if d["display_name"] == display_name:
                self.adb.set_active_device(d["serial"])
                self._update_device_info(d["serial"])
                break

    def _update_device_info(self, serial: str) -> None:
        info = self.adb.get_device_info()
        mfg = info.get("manufacturer", "Android")
        mdl = info.get("model", "Device")
        rel = info.get("release", "-")
        self.dev_info_lbl.configure(text=f"ยี่ห้อ: {mfg} | รุ่น: {mdl} | Android: {rel}")

        # Check 30-day visit alert in SQLite database
        conn_res = self.db.record_device_connection(serial, mfg, mdl, rel)
        if conn_res.get("alert_message"):
            self.repeat_alert_text = conn_res["alert_message"]
            self.banner_label.configure(text=self.repeat_alert_text)
            self.banner_frame.grid()
            self.log(f"🚨 {self.repeat_alert_text}")
        else:
            self.banner_frame.grid_remove()
            self.repeat_alert_text = None

        self.log(f"📱 เชื่อมต่อสำเร็จ: {mfg} {mdl} (Serial: {serial}, Android {rel})")

    def _reset_for_next_customer(self) -> None:
        """Completely reset state for the next customer in the queue."""
        self.scanned_apps.clear()
        self.selected_packages.clear()
        self.app_cards.clear()
        self.selected_app_inspect = None
        self.removed_apps_this_session.clear()
        self.apk_parser.clear_cache()
        self.adb.reset_state()

        for widget in self.app_list_scroll.winfo_children():
            widget.destroy()

        self._render_inspector_empty()
        self.list_summary_lbl.configure(text="พร้อมสแกน — กดปุ่ม 'สแกนแอปทั้งหมด' เพื่อเริ่มต้น")
        self.banner_frame.grid_remove()
        self.log("🧹 รีเซ็ตระบบพร้อมรับเครื่องลูกค้ารายถัดไปเรียบร้อยแล้ว")
        self._refresh_device_list()

    # -------------------------------------------------------------
    # Scanning & Analysis Pipeline
    # -------------------------------------------------------------

    def start_scan_async(self) -> None:
        """Run scan in background thread to keep GUI responsive."""
        if not self.adb.active_serial:
            self.log("❌ ไม่สามารถสแกนได้: ยังไม่ได้เลือกเครื่อง")
            return

        self.scan_btn.configure(state="disabled", text="⏳ กำลังสแกน...")
        self.log(f"🔍 เริ่มต้นสแกนแอป 3rd-party ในเครื่อง {self.adb.active_serial}...")

        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        # Step 1: List packages -3 -i
        raw_packages = self.adb.list_third_party_packages()
        analyzed_results: List[Dict[str, Any]] = []

        for p in raw_packages:
            pkg_name = p["package_name"]
            installer = p["installer"]

            # Step 2: Dumpsys details
            details = self.adb.get_package_details(pkg_name)

            # Query Shop Threat Intelligence
            threat_intel = self.db.get_known_threat(pkg_name)

            # Extract icon and app name from APK if path is present or fallback
            app_name = None
            if details.get("apk_path"):
                local_apk = self.adb.pull_apk(details["apk_path"], pkg_name)
                if local_apk:
                    app_name, icon_path = self.apk_parser.extract_from_apk(local_apk, pkg_name)
                else:
                    icon_path = self.apk_parser.generate_fallback_icon(pkg_name, app_name)
            else:
                # Check if we have mock app_name from demo
                if self.is_demo_mode and hasattr(self.adb, "_mock_installed_packages"):
                    for m in self.adb._mock_installed_packages:
                        if m["package_name"] == pkg_name:
                            app_name = m.get("app_name")
                            break
                icon_path = self.apk_parser.generate_fallback_icon(pkg_name, app_name)

            # Analyze Risk
            risk_res = AppRiskAnalyzer.analyze_app(
                package_name=pkg_name,
                app_name=app_name or pkg_name,
                installer=installer,
                permissions=details.get("permissions", []),
                is_device_admin=details.get("is_device_admin", False),
                target_sdk=details.get("target_sdk"),
                first_install_time=details.get("first_install_time"),
                threat_intel=threat_intel
            )
            risk_res["icon_path"] = icon_path
            analyzed_results.append(risk_res)

        # Step 3: Sort: High risk first, then Suspicious, then Safe
        risk_order = {"high": 0, "suspicious": 1, "safe": 2}
        analyzed_results.sort(key=lambda x: (risk_order.get(x["risk_level"], 9), -x["risk_score"]))

        # Update GUI on main thread
        self.after(0, lambda: self._on_scan_completed(analyzed_results))

    def _on_scan_completed(self, results: List[Dict[str, Any]]) -> None:
        self.scanned_apps = results
        self.selected_packages.clear()
        self.app_cards.clear()
        self.scan_btn.configure(state="normal", text="🔍 สแกนแอปทั้งหมด (-3)")

        # Clear existing cards
        for widget in self.app_list_scroll.winfo_children():
            widget.destroy()

        high_count = sum(1 for a in results if a["risk_level"] == "high")
        susp_count = sum(1 for a in results if a["risk_level"] == "suspicious")
        safe_count = sum(1 for a in results if a["risk_level"] == "safe")

        summary_text = (
            f"สแกนพบทั้งหมด {len(results)} แอป | "
            f"🔴 เสี่ยงสูง: {high_count} | 🟡 น่าสงสัย: {susp_count} | 🟢 ปลอดภัย: {safe_count}"
        )
        self.list_summary_lbl.configure(text=summary_text)

        for app in results:
            pkg = app["package_name"]
            card = AppCard(
                self.app_list_scroll,
                app_data=app,
                on_select_callback=self._on_app_selected_toggle,
                on_click_callback=self._on_app_card_clicked
            )
            card.pack(fill="x", pady=4, padx=2)
            self.app_cards[pkg] = card

        # Show inspector for first high-risk app or first item
        if results:
            self._render_inspector_details(results[0])

        self.log(f"✅ สแกนเสร็จสิ้น: พบ {len(results)} แอป (เสี่ยงสูง {high_count}, น่าสงสัย {susp_count}, ปลอดภัย {safe_count})")

    def _on_app_selected_toggle(self, package_name: str, is_checked: bool) -> None:
        if is_checked:
            self.selected_packages.add(package_name)
        else:
            self.selected_packages.discard(package_name)

        self._update_selected_counter()

    def _update_selected_counter(self) -> None:
        count = len(self.selected_packages)
        self.delete_btn.configure(text=f"🗑️ ลบแอปที่เลือก ({count})" if count > 0 else "🗑️ ลบแอปที่เลือก")
        self.remove_admin_btn.configure(text=f"🛡️ ถอนสิทธิ์ Admin ({count})" if count > 0 else "🛡️ ถอนสิทธิ์ Admin")

    def _on_app_card_clicked(self, app_data: Dict[str, Any]) -> None:
        self._render_inspector_details(app_data)

    def select_all_high_risk(self) -> None:
        """One-click selection for all High Risk apps (never auto-deletes)."""
        high_risk_pkgs = [a["package_name"] for a in self.scanned_apps if a["risk_level"] == "high"]
        if not high_risk_pkgs:
            self.log("ℹ️ ไม่พบแอปที่มีความเสี่ยงสูงในผลการสแกนปัจจุบัน")
            return

        for pkg in high_risk_pkgs:
            self.selected_packages.add(pkg)
            if pkg in self.app_cards:
                self.app_cards[pkg].set_checked(True)

        self._update_selected_counter()
        self.log(f"⚡ ติ๊กเลือกแอปความเสี่ยงสูงอัตโนมัติ {len(high_risk_pkgs)} รายการ — กรุณากดยืนยันการลบ")

    # -------------------------------------------------------------
    # Inspector Details Rendering
    # -------------------------------------------------------------

    def _render_inspector_empty(self) -> None:
        for w in self.inspector_scroll.winfo_children():
            w.destroy()
        self.inspector_placeholder = ctk.CTkLabel(
            self.inspector_scroll,
            text="คลิกเลือกแอปพลิเคชันจากการ์ดทางซ้าย\nเพื่อดูการวิเคราะห์ความเสี่ยงและ Permissions ทั้งหมด",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8")
        )
        self.inspector_placeholder.pack(pady=40)

    def _render_inspector_details(self, app: Dict[str, Any]) -> None:
        self.selected_app_inspect = app
        for w in self.inspector_scroll.winfo_children():
            w.destroy()

        # Header Info
        header_frame = ctk.CTkFrame(self.inspector_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        app_name = app.get("app_name") or app.get("package_name")
        ctk.CTkLabel(
            header_frame,
            text=app_name,
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            header_frame,
            text=app.get("package_name", ""),
            font=ctk.CTkFont(size=11, family="Courier"),
            text_color=("#64748b", "#94a3b8"),
            anchor="w"
        ).pack(fill="x")

        # Risk badge & score
        score_row = ctk.CTkFrame(self.inspector_scroll, fg_color="transparent")
        score_row.pack(fill="x", pady=(0, 10))

        RiskBadge(score_row, risk_level=app.get("risk_level", "safe")).pack(side="left")
        ctk.CTkLabel(
            score_row,
            text=f"Risk Score: {app.get('risk_score', 0)}/100",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#ef4444" if app.get("risk_level") == "high" else "#64748b")
        ).pack(side="left", padx=10)

        # Meta attributes
        meta_box = ctk.CTkFrame(self.inspector_scroll, fg_color=("#f1f5f9", "#0f172a"), corner_radius=6)
        meta_box.pack(fill="x", pady=(0, 10), padx=2)

        installer = app.get("installer") or "ไม่มี (Sideload / Direct APK)"
        target_sdk = str(app.get("target_sdk")) if app.get("target_sdk") else "ไม่ระบุ"
        install_time = app.get("first_install_time") or "ไม่ระบุ"
        is_admin = "มีสิทธิ์ Device Admin ⚠️" if app.get("is_device_admin") else "ไม่มี"

        meta_lines = [
            f"• แหล่งติดตั้ง: {installer}",
            f"• สิทธิ์ผู้ดูแลระบบ: {is_admin}",
            f"• Target SDK: {target_sdk}",
            f"• วันที่ติดตั้ง: {install_time}"
        ]
        for line in meta_lines:
            ctk.CTkLabel(
                meta_box,
                text=line,
                font=ctk.CTkFont(size=11),
                anchor="w"
            ).pack(fill="x", padx=8, pady=2)

        # Reasons
        reasons = app.get("reasons", [])
        if reasons:
            ctk.CTkLabel(
                self.inspector_scroll,
                text="🚩 เหตุผล / พฤติกรรมเสี่ยง:",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(4, 2))

            for r in reasons:
                r_card = ctk.CTkFrame(self.inspector_scroll, fg_color=("#fee2e2", "#450a0a"), corner_radius=4)
                r_card.pack(fill="x", pady=2)
                ctk.CTkLabel(
                    r_card,
                    text=f"• {r}",
                    font=ctk.CTkFont(size=11),
                    text_color=("#991b1b", "#fca5a5"),
                    anchor="w",
                    wraplength=340,
                    justify="left"
                ).pack(fill="x", padx=8, pady=4)

        # Risky Permissions
        risky_perms = app.get("risky_permissions", [])
        if risky_perms:
            ctk.CTkLabel(
                self.inspector_scroll,
                text="⚠️ สิทธิ์อันตรายที่ขอใช้งาน:",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(8, 2))

            for rp in risky_perms:
                ctk.CTkLabel(
                    self.inspector_scroll,
                    text=f"  ⚡ {rp}",
                    font=ctk.CTkFont(size=11, family="Courier", weight="bold"),
                    text_color="#ef4444",
                    anchor="w"
                ).pack(fill="x")

        # Unknown / OEM Permissions
        unknown_perms = app.get("unknown_permissions", [])
        if unknown_perms:
            ctk.CTkLabel(
                self.inspector_scroll,
                text=f"⚙️ Custom/OEM Permissions ({len(unknown_perms)} รายการ):",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(8, 2))

            for up in unknown_perms[:5]:
                ctk.CTkLabel(
                    self.inspector_scroll,
                    text=f"  • {up}",
                    font=ctk.CTkFont(size=10, family="Courier"),
                    text_color=("#64748b", "#94a3b8"),
                    anchor="w"
                ).pack(fill="x")

    # -------------------------------------------------------------
    # Removal & Admin Revocation Pipeline
    # -------------------------------------------------------------

    def remove_selected_device_admin(self) -> None:
        """Revoke device admin for selected packages."""
        if not self.selected_packages:
            self.log("⚠️ กรุณาเลือกแอปพลิเคชันที่ต้องการถอนสิทธิ์ Device Admin ก่อน")
            return

        for pkg in list(self.selected_packages):
            app_meta = next((a for a in self.scanned_apps if a["package_name"] == pkg), {})
            app_name = app_meta.get("app_name", pkg)
            self.log(f"🛡️ กำลังถอนสิทธิ์ Device Admin: {app_name} ({pkg})...")
            success, msg = self.adb.remove_device_admin(pkg)

            if success:
                self.log(f"✅ {msg}")
            else:
                self.log(f"⚠️ {msg}")
                DeviceAdminGuideDialog(self, package_name=pkg, app_name=app_name, raw_error=msg)

    def confirm_and_uninstall_selected(self) -> None:
        """Open strict confirmation dialog before uninstalling."""
        if not self.selected_packages:
            self.log("⚠️ กรุณาติ๊กเลือกแอปพลิเคชันที่ต้องการลบก่อน")
            return

        apps_to_delete = [
            a for a in self.scanned_apps if a["package_name"] in self.selected_packages
        ]

        # Safety confirmation modal
        ConfirmUninstallDialog(
            master=self,
            apps_to_delete=apps_to_delete,
            on_confirm_callback=lambda: self._execute_uninstall(apps_to_delete)
        )

    def _execute_uninstall(self, apps_to_delete: List[Dict[str, Any]]) -> None:
        """Execute uninstallation sequentially, logging each action and updating DB."""
        serial = self.adb.active_serial or "UNKNOWN"
        deleted_this_run = []

        for app in apps_to_delete:
            pkg = app["package_name"]
            name = app.get("app_name", pkg)
            self.log(f"🗑️ กำลังลบแอป: {name} ({pkg})...")

            success, msg = self.adb.uninstall_package(pkg)
            if success:
                self.log(f"✅ ลบสำเร็จ: {name} ({pkg})")
                deleted_this_run.append(app)
                self.removed_apps_this_session.append(app)

                # Remove from UI cards
                if pkg in self.app_cards:
                    self.app_cards[pkg].destroy()
                    del self.app_cards[pkg]
                self.selected_packages.discard(pkg)
            else:
                self.log(f"❌ ลบไม่สำเร็จ: {name} ({pkg}) — {msg}")

        # Record visit & update Shop Threat Intelligence in SQLite
        if deleted_this_run:
            self.db.record_visit(
                device_serial=serial,
                apps_scanned_count=len(self.scanned_apps),
                apps_removed=deleted_this_run,
                risk_summary="high" if any(a.get("risk_level") == "high" for a in deleted_this_run) else "suspicious",
                notes="ล้างแอปโฆษณาหน้าร้าน"
            )
            self.log(f"💾 บันทึกประวัติเครื่องและอัปเดต Shop Threat Intelligence เรียบร้อย ({len(deleted_this_run)} รายการ)")

        self._update_selected_counter()
        self.list_summary_lbl.configure(
            text=f"ลบแอปเสร็จสิ้น {len(deleted_this_run)}/{len(apps_to_delete)} รายการ — แนะนำให้กดปุ่ม 'สแกนซ้ำ'"
        )

    # -------------------------------------------------------------
    # Reports & History Dialogs
    # -------------------------------------------------------------

    def generate_service_report(self) -> None:
        """Generate PDF & HTML customer service report."""
        if not self.adb.active_serial:
            self.log("⚠️ ไม่พบข้อมูลเครื่องสำหรับออกใบรายงาน")
            return

        device_info = self.adb.get_device_info()
        pdf_path, html_path = self.report_gen.generate_report(
            device_info=device_info,
            apps_scanned_count=len(self.scanned_apps),
            removed_apps=self.removed_apps_this_session,
            technician_name="ช่างประจำหน้าร้าน"
        )

        self.log(f"📄 ออกใบรายงานบริการสำเร็จ!")
        self.log(f"   • PDF: {pdf_path}")
        self.log(f"   • HTML: {html_path}")

        # Auto-open report in default viewer (PDF or HTML)
        target_to_open = pdf_path if os.path.exists(pdf_path) else html_path
        try:
            if os.name == "posix":
                subprocess.Popen(["open", target_to_open])
            elif os.name == "nt":
                os.startfile(target_to_open)
        except Exception:
            pass

    def show_history_dialog(self) -> None:
        """Display Device History & Shop Threat Intelligence modal."""
        HistoryAndIntelDialog(self, self.db, self.adb.active_serial or "")


def launch_app():
    app = AdwareRemovalApp()
    app.mainloop()


if __name__ == "__main__":
    launch_app()
