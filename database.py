"""
SATHI 2026 - Database Module (raw sqlite3)
"""
import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'sathi.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'School',
            contact_person TEXT, email TEXT, phone TEXT,
            address TEXT, city TEXT, state TEXT,
            mou_status TEXT DEFAULT 'Pending', mou_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            visual_acuity TEXT,
            vision_category TEXT DEFAULT 'Low Vision',
            disability_certificate TEXT DEFAULT 'N',
            partner_id INTEGER REFERENCES partners(id),
            employment_status TEXT DEFAULT 'Student',
            class_or_year TEXT,
            education_qualification TEXT,
            aadhar_no TEXT,
            location TEXT,
            city TEXT, state TEXT,
            phone TEXT, email TEXT,
            smartphone_model TEXT,
            port_type TEXT,
            financial_status TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS device_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT, unit_cost REAL DEFAULT 0,
            specifications TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_type_id INTEGER NOT NULL REFERENCES device_types(id),
            batch_number TEXT, quantity INTEGER DEFAULT 0,
            vendor TEXT, procurement_date TEXT,
            unit_cost REAL DEFAULT 0, total_cost REAL DEFAULT 0,
            notes TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            event_type TEXT DEFAULT 'Distribution',
            partner_id INTEGER REFERENCES partners(id),
            event_date TEXT, location TEXT, city TEXT, state TEXT,
            status TEXT DEFAULT 'Planned',
            expected_beneficiaries INTEGER DEFAULT 0,
            actual_beneficiaries INTEGER DEFAULT 0,
            chief_guest TEXT, notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS distributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id INTEGER NOT NULL REFERENCES beneficiaries(id),
            device_type_id INTEGER NOT NULL REFERENCES device_types(id),
            event_id INTEGER REFERENCES events(id),
            serial_number TEXT, distribution_date TEXT,
            condition_at_delivery TEXT DEFAULT 'New',
            notes TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS training_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id INTEGER NOT NULL REFERENCES beneficiaries(id),
            device_type_id INTEGER REFERENCES device_types(id),
            training_type TEXT DEFAULT 'Device Usage',
            trainer_name TEXT, training_date TEXT,
            duration_hours REAL DEFAULT 1,
            status TEXT DEFAULT 'Scheduled',
            completion_date TEXT, certificate_issued INTEGER DEFAULT 0,
            notes TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id INTEGER NOT NULL REFERENCES beneficiaries(id),
            followup_date TEXT, followup_type TEXT DEFAULT 'Phone Call',
            device_working INTEGER DEFAULT 1,
            usage_frequency TEXT DEFAULT 'Daily',
            satisfaction_rating INTEGER DEFAULT 5,
            challenges TEXT, success_story TEXT,
            needs_support INTEGER DEFAULT 0,
            conducted_by TEXT, notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, description TEXT,
            quarter TEXT, amount REAL DEFAULT 0, spent REAL DEFAULT 0,
            vendor TEXT, payment_status TEXT DEFAULT 'Pending',
            payment_date TEXT, invoice_number TEXT,
            notes TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT,
            target_value INTEGER DEFAULT 0, current_value INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'units', deadline TEXT,
            status TEXT DEFAULT 'In Progress', notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL, entity_type TEXT,
            entity_id INTEGER, entity_name TEXT, details TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    _seed_device_types(conn)
    _seed_milestones(conn)
    conn.close()

def _seed_device_types(conn):
    if conn.execute("SELECT COUNT(*) FROM device_types").fetchone()[0] > 0: return
    conn.executemany("INSERT INTO device_types (name,category,unit_cost,specifications,description) VALUES (?,?,?,?,?)", [
        ('Laptop with Screen Reader','Computing',35000,'NVDA/JAWS, 15.6\" display','Laptops with assistive software'),
        ('Smartphone (Accessible)','Computing',12000,'TalkBack enabled, 6.5\"','Budget smartphones with accessibility'),
        ('AI Smart Vision Glasses','Smart Glasses',25000,'Text reader, face recognition','AI-powered glasses'),
        ('AR Aura Glasses','Smart Glasses',45000,'Magnification, contrast','AR glasses for low vision'),
        ('Portable Digital Magnifier','Magnification',5000,'2x-32x zoom, LED','Handheld electronic magnifiers'),
        ('RLF Tactile Braille Book Set','Educational',3000,'STEM content, tactile diagrams','Braille books'),
        ('Tablet for CVI Children','Computing',18000,'High contrast display','Tablets for cortical visual impairment'),
        ('See TV Device','Magnification',8000,'TV-connected magnification','TV magnification system'),
        ('Optical Filter/Spectacles','Optical',2000,'Custom tinted lenses','Specialized optical filters'),
        ('Computer Lab Setup','Infrastructure',200000,'10 accessible stations','Complete computer lab'),
    ])
    conn.commit()

def _seed_milestones(conn):
    if conn.execute("SELECT COUNT(*) FROM milestones").fetchone()[0] > 0: return
    conn.executemany("INSERT INTO milestones (name,category,target_value,current_value,unit,deadline) VALUES (?,?,?,?,?,?)", [
        ('Laptop Distribution','Device Distribution',200,0,'laptops','2026-12-31'),
        ('Smartphone Distribution','Device Distribution',500,0,'phones','2026-12-31'),
        ('AI Glasses Distribution','Device Distribution',300,0,'glasses','2026-12-31'),
        ('Digital Magnifier Distribution','Device Distribution',1500,0,'magnifiers','2026-12-31'),
        ('New Partner Onboarding','Partnerships',20,0,'partners','2026-12-31'),
        ('Training Sessions Completed','Training',1000,0,'sessions','2026-12-31'),
        ('Distribution Events Held','Events',50,0,'events','2026-12-31'),
        ('Total Beneficiaries Reached','Impact',5000,0,'beneficiaries','2026-12-31'),
    ])
    conn.commit()

def log_activity(conn, action, entity_type=None, entity_id=None, entity_name=None, details=None):
    conn.execute("INSERT INTO activity_log (action,entity_type,entity_id,entity_name,details) VALUES (?,?,?,?,?)",
        (action, entity_type, entity_id, entity_name, details))
    conn.commit()
