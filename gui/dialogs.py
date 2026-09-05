"""Dialog modals for confirmation, Device Admin guidance, and Threat Intel history."""

from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk


class ConfirmUninstallDialog(ctk.CTkToplevel):
    """Safety confirmation modal listing apps before technician uninstalls them."""

    def __init__(
        self,
        master,
        apps_to_delete: List[Dict[str, Any]],
        on_confirm_callback: Callable[[], None]
    ):
        super().__init__(master)
        self.apps_to_delete = apps_to_delete
        self.on_confirm_callback = on_confirm_callback

        self.title("ยืนยันการลบแอปพลิเคชัน (Confirm Uninstall)")
        self.geometry("560x480")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        # Header banner
        header = ctk.CTkFrame(self, fg_color="#ef4444", corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="⚠️ โปรดยืนยันการลบแอปพลิเคชันออกจากเครื่องลูกค้า",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        title.pack(pady=18)

        # Body container
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        desc = ctk.CTkLabel(
            body,
            text=(
                f"คุณกำลังจะทำการถอนการติดตั้ง {len(self.apps_to_delete)} แอปพลิเคชันที่เลือก\n"
                "ทุกการลบไม่สามารถย้อนกลับได้ โปรดตรวจสอบรายชื่อแอปด้านล่างนี้:"
            ),
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w"
        )
        desc.pack(fill="x", pady=(0, 10))

        # Scrollable list of apps
        list_scroll = ctk.CTkScrollableFrame(body, height=220)
        list_scroll.pack(fill="both", expand=True, pady=(0, 15))

        for app in self.apps_to_delete:
            card = ctk.CTkFrame(list_scroll, fg_color=("#f1f5f9", "#1e293b"), corner_radius=6)
            card.pack(fill="x", pady=3, padx=2)

            name_lbl = ctk.CTkLabel(
                card,
                text=f"📱 {app.get('app_name', app.get('package_name'))}",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            )
            name_lbl.pack(fill="x", padx=10, pady=(6, 2))

            pkg_lbl = ctk.CTkLabel(
                card,
                text=f"ID: {app.get('package_name')}",
                font=ctk.CTkFont(size=11, family="Courier"),
                text_color=("#64748b", "#94a3b8"),
                anchor="w"
            )
            pkg_lbl.pack(fill="x", padx=10, pady=(0, 6))

        # Action Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="ยกเลิก (Cancel)",
            fg_color=("#94a3b8", "#475569"),
            hover_color=("#64748b", "#334155"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.destroy,
            height=38
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        confirm_btn = ctk.CTkButton(
            btn_row,
            text=f"ยืนยันการลบ {len(self.apps_to_delete)} รายการ",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_confirm,
            height=38
        )
        confirm_btn.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _on_confirm(self) -> None:
        self.destroy()
        self.on_confirm_callback()


class DeviceAdminGuideDialog(ctk.CTkToplevel):
    """Step-by-step modal guiding the technician to manually revoke Device Admin on phone."""

    def __init__(self, master, package_name: str, app_name: str, raw_error: str = ""):
        super().__init__(master)
        self.package_name = package_name
        self.app_name = app_name
        self.raw_error = raw_error

        self.title("คำแนะนำการถอนสิทธิ์ Device Admin บนมือถือ")
        self.geometry("540x440")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="#f59e0b", corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="🛡️ ต้องถอนสิทธิ์ผู้ดูแลระบบ (Device Admin) ด้วยตนเอง",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#1e293b"
        )
        title.pack(pady=16)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        info = ctk.CTkLabel(
            body,
            text=f"แอป: {self.app_name} ({self.package_name})\n"
                 "ระบบความปลอดภัยของ Android ป้องกันไม่ให้ถอนสิทธิ์ผ่านสายอัตโนมัติ",
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w"
        )
        info.pack(fill="x", pady=(0, 12))

        steps_box = ctk.CTkFrame(body, fg_color=("#f1f5f9", "#1e293b"), corner_radius=8)
        steps_box.pack(fill="both", expand=True, pady=(0, 16), padx=2)

        steps_text = (
            "ขั้นตอนการปิดสิทธิ์บนมือถือลูกค้า:\n\n"
            "1. ปลดล็อกหน้าจอเครื่อง Android ของลูกค้า\n"
            "2. ไปที่ การตั้งค่า (Settings) > ความปลอดภัยและความเป็นส่วนตัว (Security)\n"
            "3. เลือกเมนู 'แอปผู้ดูแลระบบ' (Device admin apps)\n"
            f"4. แตะที่แอป '{self.app_name}' แล้วเลือก 'ปิดใช้งาน' (Deactivate)\n"
            "5. เมื่อปิดแล้ว ให้กลับมากดปุ่ม 'ลบแอปที่เลือก' ในโปรแกรมนี้อีกครั้ง"
        )
        steps_lbl = ctk.CTkLabel(
            steps_box,
            text=steps_text,
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w"
        )
        steps_lbl.pack(padx=16, pady=16)

        ok_btn = ctk.CTkButton(
            self,
            text="เข้าใจแล้ว (ดำเนินการต่อ)",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.destroy,
            height=38
        )
        ok_btn.pack(fill="x", padx=24, pady=(0, 20))


class HistoryAndIntelDialog(ctk.CTkToplevel):
    """Modal displaying device visit history and Shop Threat Intelligence."""

    def __init__(self, master, db_manager, current_serial: str):
        super().__init__(master)
        self.db = db_manager
        self.current_serial = current_serial

        self.title("ประวัติการซ่อม & Shop Threat Intelligence")
        self.geometry("700x520")
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=16, pady=16)

        tab_history = tabview.add("ประวัติเครื่องนี้")
        tab_intel = tabview.add("🔥 Shop Threat Intelligence")

        # 1. Device History Tab
        history_scroll = ctk.CTkScrollableFrame(tab_history)
        history_scroll.pack(fill="both", expand=True)

        visits = self.db.get_device_history(self.current_serial) if self.current_serial else []
        if visits:
            for v in visits:
                card = ctk.CTkFrame(history_scroll, fg_color=("#ffffff", "#1e293b"), corner_radius=8)
                card.pack(fill="x", pady=6, padx=4)

                header_text = f"🗓️ วันที่: {v.get('visit_date', '')[:16].replace('T', ' ')} | ลบไป {v.get('apps_removed_count', 0)} แอป"
                ctk.CTkLabel(card, text=header_text, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

                apps = v.get("apps_removed_list", [])
                for a in apps:
                    a_text = f"  • {a.get('app_name', a.get('package_name'))} ({a.get('package_name')})"
                    ctk.CTkLabel(card, text=a_text, font=ctk.CTkFont(size=11, family="Courier"), text_color=("#64748b", "#94a3b8")).pack(anchor="w", padx=12)
        else:
            ctk.CTkLabel(
                history_scroll,
                text=f"ยังไม่มีประวัติการเข้ารับบริการก่อนหน้าสำหรับ Serial: {self.current_serial or 'ไม่มี'}",
                font=ctk.CTkFont(size=13),
                text_color=("#64748b", "#94a3b8")
            ).pack(pady=40)

        # 2. Shop Threat Intel Tab
        intel_scroll = ctk.CTkScrollableFrame(tab_intel)
        intel_scroll.pack(fill="both", expand=True)

        threats = self.db.get_all_threats()
        if threats:
            ctk.CTkLabel(
                intel_scroll,
                text="📊 สถิติแอปมัลแวร์และโฆษณาที่ตรวจพบข้ามลูกค้าหลายคน (สะสมจากงานจริงในร้าน):",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(4, 10))

            for t in threats:
                card = ctk.CTkFrame(intel_scroll, fg_color=("#ffffff", "#1e293b"), corner_radius=8)
                card.pack(fill="x", pady=4, padx=4)

                t_name = t.get("app_name") or t.get("package_name")
                pkg = t.get("package_name")
                dev_count = t.get("distinct_devices_count", 1)
                rem_count = t.get("times_removed", 1)

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=10, pady=(6, 2))

                ctk.CTkLabel(top_row, text=f"🚨 {t_name}", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
                badge_color = "#ef4444" if dev_count >= 2 else "#f59e0b"
                ctk.CTkLabel(
                    top_row,
                    text=f"พบในลูกค้า {dev_count} เครื่อง (ลบ {rem_count} ครั้ง)",
                    text_color=badge_color,
                    font=ctk.CTkFont(size=12, weight="bold")
                ).pack(side="right")

                ctk.CTkLabel(
                    card,
                    text=f"ID: {pkg}",
                    font=ctk.CTkFont(size=11, family="Courier"),
                    text_color=("#64748b", "#94a3b8")
                ).pack(anchor="w", padx=10, pady=(0, 6))
        else:
            ctk.CTkLabel(
                intel_scroll,
                text="ยังไม่มีข้อมูล Threat Intelligence ในระบบ — ข้อมูลจะเริ่มสะสมเมื่อมีการลบแอปจริงหน้าร้าน",
                font=ctk.CTkFont(size=13),
                text_color=("#64748b", "#94a3b8")
            ).pack(pady=40)
