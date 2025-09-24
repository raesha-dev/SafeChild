import os
import sqlite3
from datetime import datetime
import requests
from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, atan2
import logging

load_dotenv()

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_db():
    conn = sqlite3.connect("reports.db")
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        status TEXT,
        urgency TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
        created_at TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def geocode_location(location_str):
    subscription_key = os.getenv("AZURE_MAPS_KEY")
    if not subscription_key:
        logging.error("AZURE_MAPS_KEY is not set. Using default coordinates.")
        return 12.9141, 74.8560  # Default fallback

    endpoint = f"https://atlas.microsoft.com/search/address/json?api-version=1.0&subscription-key={subscription_key}&query={location_str}"
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        results = response.json()
        if results.get('results'):
            position = results['results'][0]['position']
            return position['lat'], position['lon']
        else:
            logging.error("No results found in geocoding response.")
            return 12.9141, 74.8560
    except Exception as e:
        logging.error(f"Geocoding error: {e}")
        return 12.9141, 74.8560

def save_report(phone, message, urgency="Normal", status="Pending", location="Unknown"):
    lat, lon = geocode_location(location)
    try:
        conn = sqlite3.connect("reports.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO reports
            (phone, message, status, urgency, location, latitude, longitude, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (phone, message, status, urgency, location, lat, lon, datetime.utcnow()))
        conn.commit()
    except Exception as e:
        logging.error(f"Error saving report: {e}")
    finally:
        conn.close()

def get_reports(status_filter=None, urgency_filter=None, location_coords=None, max_distance_km=50):
    reports = []
    try:
        conn = sqlite3.connect("reports.db")
        c = conn.cursor()
        query = """
            SELECT id, phone, message, status, urgency, location, latitude, longitude, created_at
            FROM reports
            WHERE 1=1
        """
        params = []
        if status_filter and status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
        if urgency_filter and urgency_filter != "All":
            query += " AND urgency = ?"
            params.append(urgency_filter)
        if location_coords:
            lat, lon = location_coords.get('lat'), location_coords.get('lon')
            if lat is not None and lon is not None:
                radius_deg = max_distance_km / 111.0  # Approximate degrees
                query += " AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
                params.extend([lat - radius_deg, lat + radius_deg, lon - radius_deg, lon + radius_deg])
        query += " ORDER BY created_at DESC"
        c.execute(query, tuple(params))
        reports = c.fetchall()
    except Exception as e:
        logging.error(f"Error fetching reports: {e}")
    finally:
        conn.close()

    if location_coords:
        filtered = []
        for r in reports:
            lat_r, lon_r = r[6], r[7]
            if lat_r is None or lon_r is None:
                continue
            dist = haversine_distance(location_coords['lat'], location_coords['lon'], lat_r, lon_r)
            if dist <= max_distance_km:
                filtered.append(r)
        return filtered
    return reports

def update_status(report_id, new_status):
    try:
        conn = sqlite3.connect("reports.db")
        c = conn.cursor()
        c.execute("UPDATE reports SET status = ? WHERE id = ?", (new_status, report_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating status: {e}")
    finally:
        conn.close()

# Blacklist feature: locations with reports count >= threshold
def get_blacklisted_locations(threshold=3):
    try:
        conn = sqlite3.connect("reports.db")
        c = conn.cursor()
        c.execute("""
            SELECT location, COUNT(*) as count
            FROM reports
            GROUP BY location
            HAVING count >= ?
        """, (threshold,))
        results = c.fetchall()
        return set(location for location, count in results if location)
    except Exception as e:
        logging.error(f"Error fetching blacklisted locations: {e}")
        return set()
    finally:
        conn.close()
