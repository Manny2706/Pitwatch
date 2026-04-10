import json
import os
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.template.loader import render_to_string

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

AUTHORITY_EMAILS = {
    "NHAI": os.getenv("AUTHORITY_EMAIL_NHAI", "anshul24154079@akgec.ac.in"),
    "State PWD": os.getenv("AUTHORITY_EMAIL_STATE_PWD", "23kushwahaakash@gmail.com"),
    "Municipal Authority": os.getenv("AUTHORITY_EMAIL_MUNICIPAL_AUTHORITY", "vivekyadav00681@gmail.com"),
    "Unknown": os.getenv("AUTHORITY_EMAIL_UNKNOWN", "mayankgupta270606@gmail.com"),
}


def get_authority_email(authority):
    if not authority:
        return ""

    if "Municipal" in authority:
        return AUTHORITY_EMAILS.get("Municipal Authority", "")

    return AUTHORITY_EMAILS.get(authority, "")


def fetch_osm_road(lat, lon):
    query = f"""
    [out:json];
    way(around:30,{lat},{lon})["highway"];
    out tags;
    """
    try:
        res = requests.get(OVERPASS_URL, params={"data": query}, timeout=5)
        data = res.json()
        if data.get("elements"):
            return data["elements"][0]["tags"]
    except Exception:
        return None
    return None


def get_city(lat, lon):
    try:
        res = requests.get(
            NOMINATIM_URL,
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "your-app-name"},
            timeout=5,
        )
        data = res.json()
        return data.get("address", {}).get("city") or data.get("address", {}).get("town")
    except Exception:
        return None


def map_authority(tags, city=None):
    if not tags:
        return "Unknown"

    name = tags.get("name", "")
    ref = tags.get("ref", "")
    highway = tags.get("highway", "")

    if "NH" in ref or "NH" in name:
        return "NHAI"
    elif "SH" in ref or "SH" in name:
        return "State PWD"
    elif highway in ["primary", "secondary"]:
        return "State PWD"
    elif highway in ["tertiary", "residential", "service"]:
        return f"{city} Municipal Corporation" if city else "Municipal Authority"
    else:
        return "Unknown"


def get_road_authority(lat, lon):
    tags = fetch_osm_road(lat, lon)
    city = get_city(lat, lon)
    authority = map_authority(tags, city)
    authority_email = get_authority_email(authority)

    return {
        "tags": tags,
        "city": city,
        "authority": authority,
        "authority_email": authority_email,
    }


def build_authority_email_context(report, authority_data):
    severity_label = "High Severity" if getattr(report, "cluster_count", 0) else "New Pothole"
    severity_badge = "high" if severity_label == "High Severity" else "normal"
    map_url = None
    if report.latitude is not None and report.longitude is not None:
        map_url = "https://www.google.com/maps/search/?" + urlencode(
            {"api": 1, "query": f"{report.latitude},{report.longitude}"}
        )

    return {
        "report": report,
        "authority": authority_data.get("authority") or "Unknown",
        "authority_email": authority_data.get("authority_email") or "",
        "city": authority_data.get("city") or "N/A",
        "tags": authority_data.get("tags") or {},
        "map_url": map_url,
        "severity_label": severity_label,
        "severity_badge": severity_badge,
        "reporter_name": getattr(report.user, "username", "Anonymous"),
        "reporter_email": getattr(report.user, "email", "N/A"),
        "reporter_id": getattr(report.user, "id", "N/A"),
    }


def build_authority_email_text(context):
    report = context["report"]
    tags = context["tags"]
    return (
        f"PitWatch pothole report alert - {context['severity_label']}\n\n"
        f"Authority: {context['authority']}\n"
        f"Authority Email: {context['authority_email'] or 'N/A'}\n"
        f"City: {context['city']}\n"
        f"Report ID: {report.id}\n"
        f"Title: {report.title}\n"
        f"Description: {report.description or 'N/A'}\n"
        f"Status: {report.status}\n"
        f"Latitude: {report.latitude}\n"
        f"Longitude: {report.longitude}\n"
        f"Created At: {report.created_at}\n"
        f"Resolved At: {report.resolved_at or 'N/A'}\n"
        f"Road Authority: {report.road_authority or 'N/A'}\n"
        f"Road Authority Email: {report.road_authority_email or 'N/A'}\n"
        f"Reporter ID: {context['reporter_id']}\n"
        f"Reporter Name: {context['reporter_name']}\n"
        f"Reporter Email: {context['reporter_email']}\n"
        f"Road Tags: {json.dumps(tags, ensure_ascii=False)}\n"
        f"Google Maps: {context['map_url'] or 'N/A'}\n"
    )


def build_emergency_email_context(report, authority_data):
    map_url = None
    if report.latitude is not None and report.longitude is not None:
        map_url = "https://www.google.com/maps/search/?" + urlencode(
            {"api": 1, "query": f"{report.latitude},{report.longitude}"}
        )

    return {
        "report": report,
        "authority": authority_data.get("authority") or "Emergency Contact",
        "authority_email": authority_data.get("authority_email") or "",
        "city": authority_data.get("city") or "N/A",
        "map_url": map_url,
        "reporter_name": getattr(report.user, "username", "Anonymous"),
        "reporter_email": getattr(report.user, "email", "N/A"),
        "reporter_id": getattr(report.user, "id", "N/A"),
    }


def build_emergency_email_text(context):
    report = context["report"]
    return (
        "PitWatch emergency help request\n\n"
        f"Recipient: {context['authority']}\n"
        f"Recipient Email: {context['authority_email'] or 'N/A'}\n"
        f"City: {context['city']}\n"
        f"Request ID: {report.id}\n"
        f"Title: {report.title}\n"
        f"Description: {report.description or 'N/A'}\n"
        f"Status: {report.status}\n"
        f"Latitude: {report.latitude}\n"
        f"Longitude: {report.longitude}\n"
        f"Created At: {report.created_at}\n"
        f"Requester ID: {context['reporter_id']}\n"
        f"Requester Name: {context['reporter_name']}\n"
        f"Requester Email: {context['reporter_email']}\n"
        f"Google Maps: {context['map_url'] or 'N/A'}\n"
    )


def send_brevo_email(recipient, subject, html_content, text_content):
    if not recipient:
        return False

    api_key = getattr(settings, "BREVO_API_KEY", "")
    api_url = getattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "")
    sender_name = getattr(settings, "BREVO_SENDER_NAME", "PitWatch")

    if not api_key or not sender_email:
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content,
    }

    response = requests.post(
        api_url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key,
        },
        data=json.dumps(payload),
        timeout=30,
    )
    response.raise_for_status()
    return True


def send_authority_notification(report, authority_data):
    recipient = authority_data.get("authority_email") or ""

    context = build_authority_email_context(report, authority_data)
    html_content = render_to_string("reports/email/pothole_report.html", context)
    text_content = build_authority_email_text(context)

    subject_prefix = "HIGH SEVERITY" if context.get("severity_badge") == "high" else "NEW"
    subject = f"PitWatch {subject_prefix} pothole report: {report.title}"

    return send_brevo_email(recipient, subject, html_content, text_content)


def send_emergency_notification(report, authority_data):
    recipient = authority_data.get("authority_email") or ""

    context = build_emergency_email_context(report, authority_data)
    html_content = render_to_string("reports/email/emergency_report.html", context)
    text_content = build_emergency_email_text(context)
    subject = f"PitWatch EMERGENCY help request: {report.title}"

    return send_brevo_email(recipient, subject, html_content, text_content)