"""Customer Service Report Generator.

Generates professional PDF and printable HTML service reports
for mobile repair shop customers after adware/malware removal.
Prevents disputes, establishes trust, and provides customer prevention advice.
Strictly local and offline.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Register Unicode Thai font with cross-platform fallbacks
FONT_NAME = "Helvetica"
FONT_BOLD_NAME = "Helvetica-Bold"

_THAI_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Thonburi.ttc", 0),
    ("/System/Library/Fonts/Supplemental/SukhumvitSet.ttc", 0),
    ("C:\\Windows\\Fonts\\tahoma.ttf", None),
    ("C:\\Windows\\Fonts\\LeelawUI.ttf", None),
    ("/usr/share/fonts/truetype/tlwg/Garuda.ttf", None),
    ("/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf", None),
]

for font_path, subfont_idx in _THAI_FONT_CANDIDATES:
    if os.path.exists(font_path):
        try:
            if subfont_idx is not None:
                pdfmetrics.registerFont(TTFont("CustomThai", font_path, subfontIndex=subfont_idx))
            else:
                pdfmetrics.registerFont(TTFont("CustomThai", font_path))
            FONT_NAME = "CustomThai"
            FONT_BOLD_NAME = "CustomThai"
            break
        except Exception:
            continue


class ServiceReportGenerator:
    """Creates PDF and HTML service reports for completed jobs."""

    def __init__(self, output_dir: str = "reports", shop_name: str = "SMARTPHONE SERVICE & REPAIR LAB"):
        self.output_dir = output_dir
        self.shop_name = shop_name
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(
        self,
        device_info: Dict[str, str],
        apps_scanned_count: int,
        removed_apps: List[Dict[str, Any]],
        technician_name: str = "ช่างประจำสาขา",
        notes: str = ""
    ) -> Tuple[str, str]:
        """Generate both PDF and HTML reports. Returns (pdf_path, html_path)."""
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        serial = device_info.get("serial", "UNKNOWN")
        clean_serial = "".join(c for c in serial if c.isalnum() or c in ("-", "_")) or "DEVICE"

        pdf_filename = f"service_report_{clean_serial}_{timestamp_str}.pdf"
        html_filename = f"service_report_{clean_serial}_{timestamp_str}.html"

        pdf_path = os.path.join(self.output_dir, pdf_filename)
        html_path = os.path.join(self.output_dir, html_filename)

        # 1. Generate HTML Report
        self._generate_html(html_path, device_info, apps_scanned_count, removed_apps, technician_name, notes, now)

        # 2. Generate PDF Report
        try:
            self._generate_pdf(pdf_path, device_info, apps_scanned_count, removed_apps, technician_name, notes, now)
        except Exception as e:
            # If PDF rendering encounters any font issue, HTML is always guaranteed
            pass

        return pdf_path, html_path

    def _generate_pdf(
        self,
        pdf_path: str,
        device_info: Dict[str, str],
        apps_scanned_count: int,
        removed_apps: List[Dict[str, Any]],
        technician_name: str,
        notes: str,
        now: datetime
    ) -> None:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            fontName=FONT_BOLD_NAME,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e293b"),
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            "ReportSubTitle",
            fontName=FONT_NAME,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#64748b"),
            alignment=1
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            fontName=FONT_BOLD_NAME,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=12,
            spaceAfter=6
        )
        normal_style = ParagraphStyle(
            "NormalText",
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        bold_style = ParagraphStyle(
            "BoldText",
            fontName=FONT_BOLD_NAME,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#0f172a")
        )

        elements = []

        # Header
        elements.append(Paragraph(self.shop_name, title_style))
        elements.append(Paragraph("ใบรับรองผลการให้บริการล้างแอปโฆษณาและมัลแวร์ (Service Report)", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=15))

        # Device & Service Meta Table
        meta_data = [
            [
                Paragraph("<b>วันที่/เวลา:</b> " + now.strftime("%d/%m/%Y %H:%M น."), normal_style),
                Paragraph("<b>เลขที่ใบงาน:</b> SR-" + now.strftime("%y%m%d%H%M"), normal_style)
            ],
            [
                Paragraph("<b>ยี่ห้อ / รุ่น:</b> " + f"{device_info.get('manufacturer', '')} {device_info.get('model', '')}", normal_style),
                Paragraph("<b>Serial / ID:</b> " + device_info.get("serial", "-"), normal_style)
            ],
            [
                Paragraph("<b>เวอร์ชัน Android:</b> " + device_info.get("release", "-"), normal_style),
                Paragraph("<b>ช่างผู้ให้บริการ:</b> " + technician_name, normal_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Summary Metrics Table
        metrics_data = [
            [
                Paragraph("<font size=14 color='#3b82f6'><b>" + str(apps_scanned_count) + "</b></font><br/>จำนวนแอปที่สแกนทั้งหมด", subtitle_style),
                Paragraph("<font size=14 color='#ef4444'><b>" + str(len(removed_apps)) + "</b></font><br/>จำนวนแอปไม่พึงประสงค์ที่ลบออก", subtitle_style),
                Paragraph("<font size=14 color='#10b981'><b>ผ่านการตรวจสอบ</b></font><br/>สถานะเครื่องหลังสแกนซ้ำ", subtitle_style)
            ]
        ]
        metrics_table = Table(metrics_data, colWidths=[173, 173, 174])
        metrics_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 15))

        # Table of Removed Apps
        elements.append(Paragraph("รายการแอปไม่พึงประสงค์ที่ได้รับการถอนการติดตั้ง", heading_style))
        if removed_apps:
            table_header = [
                Paragraph("<b>ชื่อแอปพลิเคชัน</b>", bold_style),
                Paragraph("<b>Package ID</b>", bold_style),
                Paragraph("<b>ระดับความเสี่ยง</b>", bold_style),
                Paragraph("<b>เหตุผล / พฤติกรรมที่พบ</b>", bold_style)
            ]
            table_rows = [table_header]

            for a in removed_apps:
                risk_color = "#ef4444" if a.get("risk_level") == "high" else "#f59e0b"
                risk_label = "น่าสงสัยมาก" if a.get("risk_level") == "high" else "น่าสงสัย"
                reasons_text = ", ".join(a.get("reasons", [])) if isinstance(a.get("reasons"), list) else str(a.get("reason", "-"))

                table_rows.append([
                    Paragraph(a.get("app_name", "-"), normal_style),
                    Paragraph(f"<font size=8>{a.get('package_name', '-')}</font>", normal_style),
                    Paragraph(f"<font color='{risk_color}'><b>{risk_label}</b></font>", normal_style),
                    Paragraph(reasons_text, normal_style)
                ])

            apps_table = Table(table_rows, colWidths=[110, 150, 70, 190])
            apps_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(apps_table)
        else:
            elements.append(Paragraph("<i>ไม่พบรายการแอปที่ถูกลบในการให้บริการรอบนี้</i>", normal_style))

        elements.append(Spacer(1, 15))

        # Customer Recommendations
        elements.append(Paragraph("คำแนะนำการใช้งานเพื่อความปลอดภัย (สำหรับลูกค้า)", heading_style))
        advice_html = (
            "1. <b>หลีกเลี่ยงการดาวน์โหลดหรือเปิดไฟล์ .APK นอก Play Store:</b> ลิงก์ที่ส่งผ่านข้อความ SMS, LINE หรือเว็บไซต์ไม่ระบุชื่อ มักแฝงแอปโฆษณา<br/>"
            "2. <b>ระวังโฆษณาหลอกลวง (Fake Ads):</b> ป๊อปอัปแจ้งว่า 'ความจำเครื่องเต็ม', 'แบตเตอรี่เสื่อม' หรือ 'เครื่องติดไวรัส 10 ตัว' ล้วนเป็นกับดักหลอกให้ติดตั้งแอป<br/>"
            "3. <b>เปิดการทำงานของ Google Play Protect:</b> ใน Google Play Store > โปรไฟล์ > Play Protect ควรเปิดสแกนอัตโนมัติเสมอ<br/>"
            "4. <b>หากพบโฆษณาเด้งขึ้นมาอีก:</b> สามารถนำเครื่องกลับมาตรวจเช็คได้ทันที ทางร้านยินดีให้บริการตรวจสอบอย่างต่อเนื่อง"
        )
        elements.append(Paragraph(advice_html, normal_style))
        elements.append(Spacer(1, 20))

        # Signatures
        sig_data = [
            [
                Paragraph("ลงชื่อช่างผู้ให้บริการ:<br/><br/>....................................................................<br/>(" + technician_name + ")", normal_style),
                Paragraph("ลงชื่อลูกค้ารับเครื่องคืน:<br/><br/>....................................................................<br/>(............................................................)", normal_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[260, 260])
        sig_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(sig_table)

        doc.build(elements)

    def _generate_html(
        self,
        html_path: str,
        device_info: Dict[str, str],
        apps_scanned_count: int,
        removed_apps: List[Dict[str, Any]],
        technician_name: str,
        notes: str,
        now: datetime
    ) -> None:
        rows_html = ""
        for a in removed_apps:
            risk_color = "#ef4444" if a.get("risk_level") == "high" else "#f59e0b"
            risk_label = "น่าสงสัยมาก" if a.get("risk_level") == "high" else "น่าสงสัย"
            reasons = ", ".join(a.get("reasons", [])) if isinstance(a.get("reasons"), list) else str(a.get("reason", "-"))
            rows_html += f"""
            <tr>
                <td><strong>{a.get('app_name', '-')}</strong></td>
                <td><code>{a.get('package_name', '-')}</code></td>
                <td><span style="color: {risk_color}; font-weight: bold;">{risk_label}</span></td>
                <td>{reasons}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ใบรับรองผลบริการล้างแอปโฆษณา - {device_info.get('serial', 'Report')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Sarabun", "Thonburi", "Segoe UI", Roboto, sans-serif;
            color: #1e293b;
            background: #f8fafc;
            margin: 0;
            padding: 24px;
        }}
        .report-container {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .shop-name {{
            font-size: 24px;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 6px 0;
        }}
        .report-title {{
            font-size: 15px;
            color: #64748b;
            margin: 0;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            background: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .metric-card {{
            background: #f1f5f9;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }}
        .metric-val {{
            font-size: 22px;
            font-weight: bold;
            display: block;
        }}
        .metric-lbl {{
            font-size: 12px;
            color: #64748b;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            font-size: 13.5px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border: 1px solid #e2e8f0;
        }}
        th {{
            background: #f1f5f9;
            color: #334155;
            font-weight: 600;
        }}
        .advice-box {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 16px;
            border-radius: 4px;
            margin-bottom: 32px;
            font-size: 13.5px;
            line-height: 1.6;
        }}
        .sig-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-top: 36px;
            text-align: center;
            font-size: 13.5px;
        }}
        .sig-line {{
            margin-top: 50px;
            border-top: 1px dashed #94a3b8;
            padding-top: 8px;
        }}
        @media print {{
            body {{ background: #fff; padding: 0; }}
            .report-container {{ box-shadow: none; padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1 class="shop-name">{self.shop_name}</h1>
            <p class="report-title">ใบรับรองผลการให้บริการล้างแอปโฆษณาและมัลแวร์ (Service Report)</p>
        </div>

        <div class="meta-grid">
            <div><strong>วันที่/เวลา:</strong> {now.strftime("%d/%m/%Y %H:%M น.")}</div>
            <div><strong>เลขที่ใบงาน:</strong> SR-{now.strftime("%y%m%d%H%M")}</div>
            <div><strong>ยี่ห้อ / รุ่น:</strong> {device_info.get('manufacturer', '')} {device_info.get('model', '')}</div>
            <div><strong>Serial / ID:</strong> {device_info.get('serial', '-')}</div>
            <div><strong>เวอร์ชัน Android:</strong> {device_info.get('release', '-')}</div>
            <div><strong>ช่างผู้ให้บริการ:</strong> {technician_name}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <span class="metric-val" style="color: #3b82f6;">{apps_scanned_count}</span>
                <span class="metric-lbl">จำนวนแอปที่สแกนทั้งหมด</span>
            </div>
            <div class="metric-card">
                <span class="metric-val" style="color: #ef4444;">{len(removed_apps)}</span>
                <span class="metric-lbl">จำนวนแอปอันตรายที่ลบออก</span>
            </div>
            <div class="metric-card">
                <span class="metric-val" style="color: #10b981;">สะอาดเรียบร้อย</span>
                <span class="metric-lbl">สถานะการตรวจสอบซ้ำ</span>
            </div>
        </div>

        <h3>รายการแอปไม่พึงประสงค์ที่ได้รับการถอนการติดตั้ง</h3>
        <table>
            <thead>
                <tr>
                    <th>ชื่อแอปพลิเคชัน</th>
                    <th>Package ID</th>
                    <th>ความเสี่ยง</th>
                    <th>เหตุผล / พฤติกรรมที่พบ</th>
                </tr>
            </thead>
            <tbody>
                {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center;">ไม่พบรายการแอปที่ถูกลบ</td></tr>'}
            </tbody>
        </table>

        <div class="advice-box">
            <strong>คำแนะนำการใช้งานเพื่อความปลอดภัย (สำหรับลูกค้า):</strong><br/>
            1. <strong>หลีกเลี่ยงการติดตั้งไฟล์ .APK นอก Play Store:</strong> ลิงก์จาก SMS, LINE หรือเว็บดาวน์โหลดมักแฝงแอปขโมยข้อมูลและโฆษณาเด้ง<br/>
            2. <strong>ระวังโฆษณาแจ้งเตือนปลอม:</strong> ป๊อปอัปที่ระบุว่า "เครื่องติดไวรัส" หรือ "ความจำเต็ม" ล้วนเป็นกลโกงหลอกให้กดติดตั้งแอป<br/>
            3. <strong>เปิดใช้งาน Google Play Protect เสมอ:</strong> ตรวจสอบสถานะการป้องกันได้ในแอป Google Play Store<br/>
            4. <strong>หากพบปัญหาโฆษณากวนใจอีก:</strong> สามารถนำเครื่องกลับมารับบริการได้ทันที ทางร้านยินดีดูแลอย่างต่อเนื่อง
        </div>

        <div class="sig-grid">
            <div>
                ลงชื่อช่างผู้ให้บริการ
                <div class="sig-line">({technician_name})</div>
            </div>
            <div>
                ลงชื่อลูกค้ารับเครื่องคืน
                <div class="sig-line">(............................................................)</div>
            </div>
        </div>

        <div class="no-print" style="margin-top: 30px; text-align: center;">
            <button onclick="window.print()" style="background: #3b82f6; color: #fff; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">
                🖨️ พิมพ์ใบรายงานผลบริการ (Print / Save as PDF)
            </button>
        </div>
    </div>
</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
