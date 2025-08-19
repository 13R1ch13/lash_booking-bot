import sqlite3
from datetime import datetime, timedelta
from services.services import services

DB_PATH = "appointments.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                service TEXT,
                date TEXT,
                time TEXT
            )
        """)
        conn.commit()

def save_appointment(user_id, username, service, date, time):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (user_id, username, service, date, time)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, service, date, time))
        conn.commit()

def get_user_appointments(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT service, date, time FROM appointments
            WHERE user_id = ?
            ORDER BY date, time
        """, (user_id,))
        return cursor.fetchall()

def get_appointments_for_date(date):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT time, service FROM appointments
            WHERE date = ?
        """, (date,))
        return cursor.fetchall()

def is_time_range_available(date, start_time_str, duration_minutes):
    """
    Ensures that the selected time plus service duration
    does not overlap with existing appointments on that day
    """
    start_time = datetime.strptime(start_time_str, "%H:%M")
    end_time = start_time + timedelta(minutes=duration_minutes)

    appointments = get_appointments_for_date(date)

    for booked_time_str, service in appointments:
        booked_start = datetime.strptime(booked_time_str, "%H:%M")
        booked_end = booked_start + timedelta(minutes=services.get(service, 0))

        if not (end_time <= booked_start or start_time >= booked_end):
            return False

    return True
def delete_user_appointment(user_id, service, date, time):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM appointments
            WHERE user_id = ? AND service = ? AND date = ? AND time = ?
        """, (user_id, service, date, time))
        conn.commit()
