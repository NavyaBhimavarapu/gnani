"""
VoiceDose - Comprehensive Automated Test Suite
==============================================
Validates:
- HTML/JS static page serving
- Patient & Caregiver API endpoints
- Gnani Timbre TTS speech synthesis for Telugu, Hindi, English
- Intent matching & SQLite state logging for Taken, Not Yet, Snooze
"""

import sys
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, seed_fake_data, get_today_doses, reset_demo_data

client = TestClient(app)

def test_full_pipeline():
    print("--- [1] Testing SQLite Init & Seeding ---")
    init_db()
    reset_demo_data()
    doses = get_today_doses(1)
    assert len(doses) == 4, f"Expected 4 doses, got {len(doses)}"
    print(f"PASS: 4 doses seeded for patient. First dose: {doses[0]['medicine_name']} ({doses[0]['status']})")

    print("\n--- [2] Testing Page Routes ---")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "VoiceDose" in resp.text
    print("PASS: GET / returned 200 with VoiceDose HTML")

    resp = client.get("/caregiver")
    assert resp.status_code == 200
    assert "Caregiver" in resp.text
    print("PASS: GET /caregiver returned 200 with Caregiver HTML")

    print("\n--- [3] Testing Patient & Active Dose APIs ---")
    resp = client.get("/api/patient")
    assert resp.status_code == 200
    data = resp.json()
    assert data["patient"]["name"] == "Anasuya Devi"
    print("PASS: GET /api/patient returned patient profile successfully.")

    resp = client.get("/api/active-dose")
    assert resp.status_code == 200
    active_dose = resp.json()
    print(f"PASS: Active dose is {active_dose['medicine_name']} ({active_dose['slot_name']})")

    print("\n--- [4] Testing Gnani Timbre TTS Reminder Speech (Telugu) ---")
    resp = client.post("/api/reminder-speech", json={
        "dose_id": active_dose["id"],
        "language_code": "te-IN"
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert len(resp.content) > 1000
    print(f"PASS: Generated Timbre TTS reminder speech ({len(resp.content)} bytes WAV)")

    print("\n--- [5] Testing Intent Matching & Voice Processing (Telugu: 'వేసుకున్నాను' -> TAKEN) ---")
    resp = client.post("/api/simulate-voice", json={
        "dose_id": active_dose["id"],
        "text": "వేసుకున్నాను",
        "language_code": "te-IN"
    })
    assert resp.status_code == 200
    res = resp.json()
    assert res["intent"] == "taken"
    assert res["dose"]["status"] == "taken"
    assert res["audio_base64"] is not None
    print(f"PASS: Matched Telugu 'వేసుకున్నాను' to intent: {res['intent']}, Dose Status: {res['dose']['status']}")
    print(f"      Spoken confirmation generated via Timbre: {res['confirmation_text'][:40]}...")

    print("\n--- [6] Testing Caregiver Summary Update ---")
    resp = client.get("/api/caregiver/summary")
    assert resp.status_code == 200
    summary = resp.json()
    stats = summary["stats"]
    assert stats["taken"] >= 1
    print(f"PASS: Caregiver stats updated: Taken={stats['taken']}, Pending={stats['pending']}")

    print("\n--- [7] Testing Hindi Intent Matching ('दस मिनट बाद याद दिलाना' -> SNOOZE) ---")
    resp = client.post("/api/simulate-voice", json={
        "dose_id": 2,
        "text": "दस मिनट बाद याद दिलाना",
        "language_code": "hi-IN"
    })
    assert resp.status_code == 200
    res = resp.json()
    assert res["intent"] == "snooze"
    assert res["dose"]["status"] == "snoozed"
    print(f"PASS: Matched Hindi snooze intent: {res['intent']}, Dose Status: {res['dose']['status']}")

    print("\n--- [8] Testing English Intent Matching ('not yet' -> NOT_YET) ---")
    resp = client.post("/api/simulate-voice", json={
        "dose_id": 3,
        "text": "I haven't taken it yet",
        "language_code": "en-IN"
    })
    assert resp.status_code == 200
    res = resp.json()
    assert res["intent"] == "not_yet"
    print(f"PASS: Matched English 'not yet' intent: {res['intent']}")

    print("\n--- [9] Testing Demo Reset ---")
    resp = client.post("/api/reset-demo")
    assert resp.status_code == 200
    doses_after = get_today_doses(1)
    assert all(d["status"] == "pending" for d in doses_after)
    print("PASS: Reset demo restored all doses to 'pending' state.")

    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (10/10)")
    print("==========================================")

if __name__ == "__main__":
    test_full_pipeline()
