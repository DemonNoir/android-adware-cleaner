"""Reusable UI components for Android Adware Removal Tool."""

import os
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk
from PIL import Image


class RiskBadge(ctk.CTkFrame):
    """Visual badge for Safe, Suspicious, or High Risk."""

    def __init__(self, master, risk_level: str, **kwargs):
        super().__init__(master, corner_radius=6, **kwargs)
        self.risk_level = risk_level.lower()

        if self.risk_level == "high":
            bg_color = "#ef4444"
            fg_text = "#ffffff"
            label_text = "🔴 น่าสงสัยมาก (High)"
        elif self.risk_level == "suspicious":
            bg_color = "#f59e0b"
            fg_text = "#1e293b"
            label_text = "🟡 น่าสงสัย (Suspicious)"
        else:
            bg_color = "#10b981"
            fg_text = "#ffffff"
            label_text = "🟢 ปลอดภัย (Safe)"

        self.configure(fg_color=bg_color)
        self.label = ctk.CTkLabel(
            self,
            text=label_text,
            text_color=fg_text,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.label.pack(padx=10, pady=4)


class AppCard(ctk.CTkFrame):
    """Interactive card representing a scanned Android application."""

    def __init__(
        self,
        master,
        app_data: Dict[str, Any],
        on_select_callback: Callable[[str, bool], None],
        on_click_callback: Callable[[Dict[str, Any]], None],
        **kwargs
    ):
        super().__init__(master, corner_radius=10, fg_color=("#ffffff", "#1e293b"), **kwargs)
        self.app_data = app_data
        self.package_name = app_data.get("package_name", "")
        self.on_select_callback = on_select_callback
        self.on_click_callback = on_click_callback
        self.is_selected = ctk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        # Bind click on entire card
        self.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Checkbox
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.is_selected,
            command=self._on_check_toggle,
            width=24,
            checkbox_width=20,
            checkbox_height=20
        )
        self.checkbox.pack(side="left", padx=(12, 6), pady=12)

        # App Icon
        icon_path = self.app_data.get("icon_path")
        self.icon_image = None
        if icon_path and os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path).resize((44, 44), Image.Resampling.LANCZOS)
                self.icon_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
            except Exception:
                pass

        if self.icon_image:
            self.icon_label = ctk.CTkLabel(self, image=self.icon_image, text="")
        else:
            self.icon_label = ctk.CTkLabel(
                self,
                text="📱",
                font=ctk.CTkFont(size=24),
                width=44,
                height=44
            )
        self.icon_label.pack(side="left", padx=8, pady=12)
        self.icon_label.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # 1. Right side: Badges & Tags (MUST PACK FIRST so it never gets squeezed)
        right_frame = ctk.CTkFrame(self, fg_color="transparent", width=175)
        right_frame.pack(side="right", padx=(6, 14), pady=10)
        right_frame.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Risk badge
        risk_level = self.app_data.get("risk_level", "safe")
        self.risk_badge = RiskBadge(right_frame, risk_level=risk_level)
        self.risk_badge.pack(anchor="e", pady=(0, 4))
        self.risk_badge.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Installer / Admin tags
        meta_tags = []
        installer = self.app_data.get("installer")
        if installer:
            if "vending" in installer:
                meta_tags.append("Google Play")
            elif "samsung" in installer:
                meta_tags.append("Galaxy Store")
            elif "packageinstaller" in installer.lower():
                meta_tags.append("PackageInstaller")
            else:
                meta_tags.append(installer[:16])
        else:
            meta_tags.append("Sideload")

        if self.app_data.get("is_device_admin"):
            meta_tags.append("Admin")

        self.tags_label = ctk.CTkLabel(
            right_frame,
            text=" | ".join(meta_tags),
            font=ctk.CTkFont(size=10),
            text_color=("#64748b", "#94a3b8"),
            anchor="e"
        )
        self.tags_label.pack(anchor="e")
        self.tags_label.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # 2. Center info frame (Packs after right_frame and expands in the remaining space)
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(side="left", fill="both", expand=True, padx=(8, 12), pady=8)
        center_frame.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Title row
        title_row = ctk.CTkFrame(center_frame, fg_color="transparent")
        title_row.pack(fill="x")
        title_row.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        app_name = self.app_data.get("app_name") or self.package_name
        self.name_label = ctk.CTkLabel(
            title_row,
            text=app_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        self.name_label.pack(side="left")
        self.name_label.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Package name
        self.pkg_label = ctk.CTkLabel(
            center_frame,
            text=self.package_name,
            font=ctk.CTkFont(size=11, family="Courier"),
            text_color=("#64748b", "#94a3b8"),
            anchor="w"
        )
        self.pkg_label.pack(fill="x")
        self.pkg_label.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))

        # Reasons tags
        reasons = self.app_data.get("reasons", [])
        if reasons:
            reasons_summary = " • ".join(reasons[:2])
            if len(reasons) > 2:
                reasons_summary += f" (+{len(reasons)-2})"
            self.reasons_label = ctk.CTkLabel(
                center_frame,
                text=reasons_summary,
                font=ctk.CTkFont(size=11),
                text_color=("#b91c1c", "#f87171") if self.app_data.get("risk_level") == "high" else ("#475569", "#cbd5e1"),
                anchor="w"
            )
            self.reasons_label.pack(fill="x", pady=(2, 0))
            self.reasons_label.bind("<Button-1>", lambda e: self.on_click_callback(self.app_data))


    def _on_check_toggle(self) -> None:
        self.on_select_callback(self.package_name, self.is_selected.get())

    def set_checked(self, checked: bool) -> None:
        self.is_selected.set(checked)
