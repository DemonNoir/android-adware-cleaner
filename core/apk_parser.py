"""APK Inspector and Icon Extractor.

Extracts app name and icon directly from base.apk using pyaxmlparser or zipfile.
Caches icons locally in cache/icons/{package_name}.png.
Generates clean fallback icons with Pillow if APK icon is not accessible.
Strictly offline and local.
"""

import os
import zipfile
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    from pyaxmlparser import APK
    PYAXMLPARSER_AVAILABLE = True
except ImportError:
    PYAXMLPARSER_AVAILABLE = False


class ApkParser:
    """Extracts application labels and icons from Android APK files."""

    def __init__(self, cache_dir: str = "cache/icons"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_icon_path(self, package_name: str) -> str:
        return os.path.join(self.cache_dir, f"{package_name}.png")

    def has_cached_icon(self, package_name: str) -> bool:
        path = self.get_cached_icon_path(package_name)
        return os.path.exists(path) and os.path.getsize(path) > 0

    def generate_fallback_icon(self, package_name: str, app_name: Optional[str] = None) -> str:
        """Create a clean, colorful fallback icon if APK icon is missing."""
        out_path = self.get_cached_icon_path(package_name)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path

        size = (72, 72)
        # Generate stable color from package name hash
        h = abs(hash(package_name))
        colors = [
            (239, 68, 68),   # Red
            (245, 158, 11),  # Amber
            (16, 185, 129),  # Emerald
            (59, 130, 246),  # Blue
            (139, 92, 246),  # Purple
            (236, 72, 153),  # Pink
            (14, 165, 233),  # Sky
        ]
        bg_color = colors[h % len(colors)]
        
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded rectangle background
        radius = 16
        draw.rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=bg_color)

        # Display first letter of app name or package
        display_letter = (app_name or package_name).strip()
        display_letter = display_letter[0].upper() if display_letter else "A"

        # Simple font fallback
        try:
            # Try to load default font
            font = ImageFont.load_default()
        except Exception:
            font = None

        # Draw letter centered
        if font:
            bbox = draw.textbbox((0, 0), display_letter, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (size[0] - w) // 2
            y = (size[1] - h) // 2
            draw.text((x, y), display_letter, fill=(255, 255, 255, 255), font=font)

        img.save(out_path, "PNG")
        return out_path

    def extract_from_apk(self, apk_path: str, package_name: str) -> Tuple[Optional[str], str]:
        """Extract app name and icon from base.apk. Returns (app_name, icon_path)."""
        app_name: Optional[str] = None
        icon_path = self.get_cached_icon_path(package_name)

        if not os.path.exists(apk_path):
            fallback = self.generate_fallback_icon(package_name, app_name)
            return app_name, fallback

        # 1. Try pyaxmlparser
        if PYAXMLPARSER_AVAILABLE:
            try:
                apk = APK(apk_path)
                app_name = apk.application
                icon_bytes = apk.get_icon()
                if icon_bytes:
                    with open(icon_path, "wb") as f:
                        f.write(icon_bytes)
                    
                    # Ensure it is a valid, resized PNG
                    with Image.open(icon_path) as im:
                        im = im.convert("RGBA").resize((72, 72), Image.Resampling.LANCZOS)
                        im.save(icon_path, "PNG")
                    return app_name, icon_path
            except Exception:
                pass

        # 2. Try raw zipfile inspection
        try:
            with zipfile.ZipFile(apk_path, "r") as zf:
                # Find icon files in res/mipmap-xxxhdpi or res/drawable-xxhdpi etc.
                icon_candidates = [
                    f for f in zf.namelist()
                    if ("res/mipmap" in f or "res/drawable" in f) and f.endswith(".png") and "ic_launcher" in f
                ]
                if not icon_candidates:
                    icon_candidates = [
                        f for f in zf.namelist()
                        if ("res/mipmap" in f or "res/drawable" in f) and f.endswith(".png")
                    ]

                if icon_candidates:
                    # Pick the largest or highest density candidate
                    best_icon = sorted(icon_candidates, key=lambda x: ("xxxhdpi" in x, "xxhdpi" in x, len(x)), reverse=True)[0]
                    with zf.open(best_icon) as icon_file:
                        with Image.open(icon_file) as im:
                            im = im.convert("RGBA").resize((72, 72), Image.Resampling.LANCZOS)
                            im.save(icon_path, "PNG")
                            return app_name, icon_path
        except Exception:
            pass

        # Fallback if extraction was unsuccessful
        fallback = self.generate_fallback_icon(package_name, app_name)
        return app_name, fallback

    def clear_cache(self) -> None:
        """Clear cached icons for next customer device."""
        if os.path.exists(self.cache_dir):
            for fname in os.listdir(self.cache_dir):
                if fname.endswith(".png"):
                    try:
                        os.remove(os.path.join(self.cache_dir, fname))
                    except Exception:
                        pass
