"""Seed script to populate database with realistic admin testing data.

Columns are taken verbatim from database.sql so inserts will never fail
due to wrong column names.
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.security import hash_password

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv(".env")
load_dotenv(".env.local")

engine = create_async_engine(
    os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://"),
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------
async def seed():
    async with engine.begin() as conn:
        print("=== Starting seed ===")

        # ------------------------------------------------------------------
        # 1. Admin users  (user_role = 'admin', admin_role in admin_profiles)
        # ------------------------------------------------------------------
        admin_defs = [
            ("super_admin@climasync.ai", "Admin User", "super_admin"),
            ("moderator@climasync.ai", "Moderator User", "moderator"),
        ]
        admin_ids: list[uuid.UUID] = []

        for email, full_name, admin_role_val in admin_defs:
            row = await conn.execute(
                text("SELECT user_id FROM users WHERE email = :e"), {"e": email}
            )
            uid = row.scalar()
            if uid is None:
                uid = uuid.uuid4()
                await conn.execute(
                    text("""
                        INSERT INTO users (user_id, email, password_hash, role, is_active, email_verified)
                        VALUES (:uid, :email, :pwd, 'admin', true, true)
                    """),
                    {"uid": uid, "email": email, "pwd": hash_password("password123")},
                )
                await conn.execute(
                    text("""
                        INSERT INTO admin_profiles (admin_id, full_name, admin_role, department, is_online)
                        VALUES (:uid, :name, :role, 'Operations', true)
                    """),
                    {"uid": uid, "name": full_name, "role": admin_role_val},
                )
                print(f"  + admin  {email}")
            admin_ids.append(uid)

        super_admin_id = admin_ids[0]

        # ------------------------------------------------------------------
        # 2. NGO users  (user_role = 'ngo_user')
        # ------------------------------------------------------------------
        ngo_defs = [
            ("Edhi Foundation",      "edhi@test.com",       "verified",  "REG-10001"),
            ("Chhipa Welfare",       "chhipa@test.com",     "verified",  "REG-10002"),
            ("Aman Foundation",      "aman@test.com",       "verified",  "REG-10003"),
            ("Alkhidmat Foundation", "alkhidmat@test.com",  "verified",  "REG-10004"),
            ("PRCS",                 "prcs@test.com",       "verified",  "REG-10005"),
            ("Saylani Welfare",      "saylani@test.com",    "verified",  "REG-10006"),
            ("TCF",                  "tcf@test.com",        "pending",   "REG-10007"),
            ("HOPE",                 "hope@test.com",       "verified",  "REG-10008"),
            ("Zindagi Trust",        "zindagi@test.com",    "suspended", "REG-10009"),
            ("Akhuwat",              "akhuwat@test.com",    "verified",  "REG-10010"),
            ("SOS Children",         "sos@test.com",        "verified",  "REG-10011"),
            ("Darul Sakun",          "darul@test.com",      "pending",   "REG-10012"),
            ("LRBT",                 "lrbt@test.com",       "verified",  "REG-10013"),
            ("Shaukat Khanum",       "skmch@test.com",      "verified",  "REG-10014"),
            ("SIUT",                 "siut@test.com",       "pending",   "REG-10015"),
        ]

        ngo_ids: list[uuid.UUID] = []
        for org_name, email, ver_status, reg_num in ngo_defs:
            row = await conn.execute(
                text("SELECT user_id FROM users WHERE email = :e"), {"e": email}
            )
            uid = row.scalar()
            if uid is None:
                uid = uuid.uuid4()
                # users row
                await conn.execute(
                    text("""
                        INSERT INTO users (user_id, email, password_hash, role, is_active, email_verified)
                        VALUES (:uid, :email, :pwd, 'ngo_user', true, true)
                    """),
                    {"uid": uid, "email": email, "pwd": hash_password("password123")},
                )
                # ngo_profiles row  (columns from database.sql TABLE 6)
                await conn.execute(
                    text("""
                        INSERT INTO ngo_profiles
                            (ngo_id, org_name, org_email, registration_number,
                             verification_status, rating, base_city, base_province)
                        VALUES (:uid, :org, :email, :reg, :vs, :rating, 'Karachi', 'Sindh')
                    """),
                    {
                        "uid": uid, "org": org_name, "email": email,
                        "reg": reg_num, "vs": ver_status,
                        "rating": round(random.uniform(3.5, 5.0), 1),
                    },
                )
                # ngo_resources row  (columns from database.sql TABLE 7)
                await conn.execute(
                    text("""
                        INSERT INTO ngo_resources
                            (ngo_id, ambulances, rescue_boats, doctors, volunteers_available)
                        VALUES (:uid, :amb, :boats, :docs, :vols)
                    """),
                    {
                        "uid": uid,
                        "amb": random.randint(2, 30),
                        "boats": random.randint(0, 10),
                        "docs": random.randint(5, 50),
                        "vols": random.randint(20, 200),
                    },
                )
                print(f"  + ngo    {org_name}")
            ngo_ids.append(uid)

        # ------------------------------------------------------------------
        # 3. Disaster events
        # ------------------------------------------------------------------
        disaster_defs = [
            ("Sindh River Flood",       "flood",      "POINT(68.12 25.34)", "active"),
            ("Karachi Heatwave",        "heatwave",   "POINT(67.00 24.86)", "active"),
            ("Quetta Earthquake",       "earthquake", "POINT(66.97 30.17)", "monitoring"),
            ("Balochistan Drought",     "drought",    "POINT(64.25 28.49)", "monitoring"),
            ("Gawadar Cyclone",         "cyclone",    "POINT(62.32 25.12)", "resolved"),
            ("Swat Landslide",          "landslide",  "POINT(72.35 35.22)", "active"),
            ("Punjab Urban Flood",      "flood",      "POINT(74.35 31.52)", "active"),
            ("Gilgit Glacial Outburst", "flood",      "POINT(74.38 35.92)", "active"),
        ]

        event_ids: list[uuid.UUID] = []
        for title, etype, loc_wkt, estatus in disaster_defs:
            row = await conn.execute(
                text("SELECT event_id FROM disaster_events WHERE title = :t"),
                {"t": title},
            )
            eid = row.scalar()
            if eid is None:
                eid = uuid.uuid4()
                await conn.execute(
                    text("""
                        INSERT INTO disaster_events
                            (event_id, event_type, title, location, event_status,
                             severity_score, created_by)
                        VALUES (:eid, :typ, :title,
                                ST_GeomFromText(:loc, 4326),
                                :status, :sev, :admin)
                    """),
                    {
                        "eid": eid, "typ": etype, "title": title,
                        "loc": loc_wkt, "status": estatus,
                        "sev": round(random.uniform(5, 9), 1),
                        "admin": super_admin_id,
                    },
                )
                print(f"  + event  {title}")
            event_ids.append(eid)

        # ------------------------------------------------------------------
        # 4. Tasks  (30 rows)
        # ------------------------------------------------------------------
        row = await conn.execute(text("SELECT COUNT(*) FROM tasks"))
        if row.scalar() < 30:
            task_types = ["ambulance", "boat", "medical", "food", "evacuation", "shelter"]
            priorities = ["low", "medium", "high", "critical"]
            statuses   = ["unallocated", "assigned", "in_progress", "completed"]

            for i in range(30):
                st = random.choice(statuses)
                nid = random.choice(ngo_ids) if st != "unallocated" else None
                await conn.execute(
                    text("""
                        INSERT INTO tasks
                            (task_id, event_id, task_label, task_type, priority,
                             status, assigned_ngo_id, created_by_type, created_at)
                        VALUES (:tid, :eid, :label, :typ, :pri,
                                :st, :nid, 'admin', :ca)
                    """),
                    {
                        "tid": uuid.uuid4(),
                        "eid": random.choice(event_ids),
                        "label": f"Relief Mission {i + 1}",
                        "typ": random.choice(task_types),
                        "pri": random.choice(priorities),
                        "st": st,
                        "nid": nid,
                        "ca": datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
                    },
                )
            print("  + 30 tasks")

        # ------------------------------------------------------------------
        # 5. Alerts  (20 rows)
        # ------------------------------------------------------------------
        row = await conn.execute(text("SELECT COUNT(*) FROM alerts"))
        if row.scalar() < 20:
            for i in range(20):
                await conn.execute(
                    text("""
                        INSERT INTO alerts
                            (alert_id, alert_type, title, source_type, status,
                             location, severity_score)
                        VALUES (:aid, :typ, :title, 'citizen', :st,
                                ST_GeomFromText('POINT(67.0 24.8)', 4326), :sev)
                    """),
                    {
                        "aid": uuid.uuid4(),
                        "typ": random.choice(["flood", "earthquake", "heatwave"]),
                        "title": f"Incoming Alert {i + 1}",
                        "st": random.choice(["new", "verified", "false_alarm"]),
                        "sev": round(random.uniform(3, 9), 1),
                    },
                )
            print("  + 20 alerts")

        # ------------------------------------------------------------------
        # 6. Social posts  (12 rows) + platforms
        # ------------------------------------------------------------------
        row = await conn.execute(text("SELECT COUNT(*) FROM social_posts"))
        if row.scalar() < 12:
            for i in range(12):
                sid = uuid.uuid4()
                await conn.execute(
                    text("""
                        INSERT INTO social_posts
                            (social_post_id, event_id, content_text, status,
                             created_by, created_by_type)
                        VALUES (:sid, :eid, :txt, 'published', :uid, 'admin')
                    """),
                    {
                        "sid": sid,
                        "eid": random.choice(event_ids),
                        "txt": f"Emergency Update #{i + 1}: Please evacuate low-lying areas immediately.",
                        "uid": super_admin_id,
                    },
                )
                await conn.execute(
                    text("""
                        INSERT INTO social_post_platforms
                            (social_post_id, platform, status, views, likes, shares)
                        VALUES (:sid, 'twitter', 'published', :v, :l, :s)
                    """),
                    {
                        "sid": sid,
                        "v": random.randint(100, 10000),
                        "l": random.randint(10, 500),
                        "s": random.randint(5, 100),
                    },
                )
            print("  + 12 social posts")

        print("=== Seed completed ===")


if __name__ == "__main__":
    asyncio.run(seed())
