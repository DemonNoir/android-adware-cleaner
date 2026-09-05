"""Database and Local Threat Intelligence Manager for Android Adware Removal Tool.

Handles SQLite storage for customer device records, visit history, 30-day alerts,
and shop-specific threat intelligence. Strictly local and offline.
Supports complete isolation between Live Mode and Demo Mode.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class DatabaseManager:
    """Manages SQLite storage for shop visits, removal logs, and threat intel."""

    def __init__(self, db_path: str = "data/repair_shop.db", is_demo: bool = False):
        self.is_demo = is_demo
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path == ":memory:" and self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Initialize required tables with indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    serial TEXT PRIMARY KEY,
                    manufacturer TEXT,
                    model TEXT,
                    android_version TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    visit_count INTEGER DEFAULT 1
                )
            """)

            # Visits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_serial TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    apps_scanned_count INTEGER DEFAULT 0,
                    apps_removed_count INTEGER DEFAULT 0,
                    risk_level_summary TEXT,
                    apps_removed_json TEXT,
                    notes TEXT,
                    FOREIGN KEY (device_serial) REFERENCES devices(serial)
                )
            """)

            # Removal logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS removal_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    device_serial TEXT NOT NULL,
                    package_name TEXT NOT NULL,
                    app_name TEXT,
                    risk_level TEXT,
                    reason TEXT
                )
            """)

            # Shop Threat Intelligence table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS known_threats (
                    package_name TEXT PRIMARY KEY,
                    app_name TEXT,
                    times_detected INTEGER DEFAULT 1,
                    times_removed INTEGER DEFAULT 1,
                    distinct_devices_count INTEGER DEFAULT 1,
                    first_seen TEXT,
                    last_seen TEXT,
                    notes TEXT
                )
            """)

            # Unique device-threat tracking to accurately count distinct customer devices
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threat_device_map (
                    package_name TEXT NOT NULL,
                    device_serial TEXT NOT NULL,
                    first_seen TEXT,
                    PRIMARY KEY (package_name, device_serial)
                )
            """)

            conn.commit()

    def record_device_connection(
        self,
        serial: str,
        manufacturer: str,
        model: str,
        android_version: str
    ) -> Dict[str, Any]:
        """Record or update device connection and evaluate 30-day return window."""
        now_iso = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE serial = ?", (serial,))
            row = cursor.fetchone()

            is_repeat = False
            days_since_last_visit: Optional[int] = None
            last_visit_date: Optional[str] = None
            alert_message: Optional[str] = None

            if row:
                is_repeat = True
                last_visit_date = row["last_seen"]
                try:
                    last_dt = datetime.fromisoformat(last_visit_date)
                    current_dt = datetime.now()
                    diff = current_dt - last_dt
                    days_since_last_visit = diff.days
                    if 0 < days_since_last_visit <= 30:
                        alert_message = (
                            f"⚠️ เครื่องนี้เคยเข้ามารับบริการเมื่อ {days_since_last_visit} วันที่แล้ว "
                            f"(วันที่ {last_dt.strftime('%d/%m/%Y %H:%M')}) — "
                            f"มีโอกาสติดแอปโฆษณาซ้ำสูง ควรแนะนำแพ็กเกจป้องกันและตรวจสอบพฤติกรรมการใช้งาน"
                        )
                    elif days_since_last_visit == 0:
                        alert_message = (
                            f"⚠️ เครื่องนี้เคยเข้ามารับบริการในวันเดียวกัน (วันที่ {last_dt.strftime('%d/%m/%Y %H:%M')}) — "
                            f"มีโอกาสติดแอปโฆษณาซ้ำสูง ควรแนะนำแพ็กเกจป้องกันและตรวจสอบพฤติกรรมการใช้งาน"
                        )
                except Exception:
                    pass

                # Update device info
                cursor.execute("""
                    UPDATE devices
                    SET manufacturer = ?,
                        model = ?,
                        android_version = ?,
                        last_seen = ?,
                        visit_count = visit_count + 1
                    WHERE serial = ?
                """, (manufacturer, model, android_version, now_iso, serial))
            else:
                cursor.execute("""
                    INSERT INTO devices (serial, manufacturer, model, android_version, first_seen, last_seen, visit_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (serial, manufacturer, model, android_version, now_iso, now_iso))

            conn.commit()

            return {
                "serial": serial,
                "is_repeat": is_repeat,
                "days_since_last_visit": days_since_last_visit,
                "last_visit_date": last_visit_date,
                "alert_message": alert_message
            }

    def record_visit(
        self,
        device_serial: str,
        apps_scanned_count: int,
        apps_removed: List[Dict[str, Any]],
        risk_summary: str,
        notes: str = ""
    ) -> int:
        """Record a completed customer visit session."""
        now_iso = datetime.now().isoformat()
        apps_removed_json = json.dumps([
            {
                "package_name": a.get("package_name"),
                "app_name": a.get("app_name"),
                "risk_level": a.get("risk_level"),
                "reason": a.get("reason", "")
            }
            for a in apps_removed
        ], ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visits (
                    device_serial, visit_date, apps_scanned_count,
                    apps_removed_count, risk_level_summary, apps_removed_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                device_serial,
                now_iso,
                apps_scanned_count,
                len(apps_removed),
                risk_summary,
                apps_removed_json,
                notes
            ))
            visit_id = cursor.lastrowid

            # Log each removed app & update threat intel
            for app in apps_removed:
                pkg = app.get("package_name", "")
                name = app.get("app_name", "")
                risk = app.get("risk_level", "high")
                reason = app.get("reason", "")

                cursor.execute("""
                    INSERT INTO removal_logs (
                        timestamp, device_serial, package_name, app_name, risk_level, reason
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (now_iso, device_serial, pkg, name, risk, reason))

                # Update threat intelligence
                self._update_threat_intel(cursor, pkg, name, device_serial, now_iso)

            conn.commit()
            return visit_id

    def _update_threat_intel(
        self,
        cursor: sqlite3.Cursor,
        package_name: str,
        app_name: str,
        device_serial: str,
        timestamp_iso: str
    ) -> None:
        """Increment threat intelligence counters across customer devices."""
        # Check if this device already had this threat mapped
        cursor.execute(
            "SELECT 1 FROM threat_device_map WHERE package_name = ? AND device_serial = ?",
            (package_name, device_serial)
        )
        already_mapped = cursor.fetchone() is not None

        if not already_mapped:
            cursor.execute(
                "INSERT INTO threat_device_map (package_name, device_serial, first_seen) VALUES (?, ?, ?)",
                (package_name, device_serial, timestamp_iso)
            )

        # Count total distinct devices with this threat
        cursor.execute(
            "SELECT COUNT(DISTINCT device_serial) as cnt FROM threat_device_map WHERE package_name = ?",
            (package_name,)
        )
        distinct_count = cursor.fetchone()["cnt"]

        # Insert or update known_threats
        cursor.execute("SELECT * FROM known_threats WHERE package_name = ?", (package_name,))
        threat_row = cursor.fetchone()

        if threat_row:
            cursor.execute("""
                UPDATE known_threats
                SET times_removed = times_removed + 1,
                    times_detected = times_detected + 1,
                    distinct_devices_count = ?,
                    app_name = COALESCE(NULLIF(?, ''), app_name),
                    last_seen = ?
                WHERE package_name = ?
            """, (distinct_count, app_name, timestamp_iso, package_name))
        else:
            cursor.execute("""
                INSERT INTO known_threats (
                    package_name, app_name, times_detected, times_removed,
                    distinct_devices_count, first_seen, last_seen
                ) VALUES (?, ?, 1, 1, ?, ?, ?)
            """, (package_name, app_name, distinct_count, timestamp_iso, timestamp_iso))

    def get_known_threat(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Query local threat intelligence for a given package."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM known_threats WHERE package_name = ?", (package_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_threats(self) -> List[Dict[str, Any]]:
        """Retrieve list of all shop-known threats ordered by prevalence."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM known_threats
                ORDER BY distinct_devices_count DESC, times_removed DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_device_history(self, serial: str) -> List[Dict[str, Any]]:
        """Get past visit history for a specific device serial."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM visits
                WHERE device_serial = ?
                ORDER BY visit_date DESC
            """, (serial,))
            visits = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("apps_removed_json"):
                    try:
                        item["apps_removed_list"] = json.loads(item["apps_removed_json"])
                    except Exception:
                        item["apps_removed_list"] = []
                visits.append(item)
            return visits

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """List all recorded devices in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
            return [dict(r) for r in cursor.fetchall()]
