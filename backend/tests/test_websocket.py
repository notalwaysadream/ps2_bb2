"""
WebSocket Audio Session Test
Tests full duplex communication on /ws/audio using Starlette TestClient in worker thread
to prevent event loop contention with pytest-asyncio.
"""
import os
os.environ["SIMULATION_MODE"] = "true"

import json
from concurrent.futures import ThreadPoolExecutor
from starlette.testclient import TestClient
from app.main import app

def _run_text_flow():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        # 1. Send language change
        ws.send_text(json.dumps({"event": "set_language", "language": "hi-IN"}))
        msg1 = json.loads(ws.receive_text())
        assert msg1["event"] == "language_changed"

        # 2. Send dictation note
        note = "Beneficiary ID 1042, Sunita Devi ka 3rd ANC checkup kiya. Weight 52 kilo hai. TT injection de diya."
        ws.send_text(json.dumps({"event": "text_note", "text": note}))

        state_msg = json.loads(ws.receive_text())
        assert state_msg["event"] == "state_update"
        assert state_msg["record"]["beneficiary_id"] == "1042"
        assert state_msg["record"]["weight"] == 52.0

        # Drain speech
        m_start = json.loads(ws.receive_text())
        assert m_start["event"] == "agent_speech_start"
        while True:
            m = ws.receive()
            if "text" in m and json.loads(m["text"]).get("event") == "agent_speech_end":
                break

        # 3. Confirm record
        ws.send_text(json.dumps({"event": "confirm_record"}))
        saved_msg = json.loads(ws.receive_text())
        assert saved_msg["event"] == "record_saved"
        assert saved_msg["record"]["is_confirmed"] is True

def _run_danger_flow():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        emergency_note = "Baby ka wazan 2.5 kilo hai, baby ko tez bukhar hai aur doodh nahi pi raha."
        ws.send_text(json.dumps({"event": "text_note", "text": emergency_note}))

        state_msg = json.loads(ws.receive_text())
        assert state_msg["event"] == "state_update"
        assert state_msg["record"]["is_urgent_referral"] is True

        danger_msg = json.loads(ws.receive_text())
        assert danger_msg["event"] == "danger_alert"
        assert "MoHFW" in danger_msg["alert"] or "सावधान" in danger_msg["alert"] or "PHC" in danger_msg["alert"]

def test_websocket_text_flow_and_readback():
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_text_flow).result(timeout=10)

def test_websocket_danger_sign_escalation():
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_danger_flow).result(timeout=10)

def test_websocket_binary_audio_streaming():
    def _run_audio_flow():
        client = TestClient(app)
        with client.websocket_connect("/ws/audio") as ws:
            # Send set_language
            ws.send_text(json.dumps({"event": "set_language", "language": "indic-auto"}))
            m = json.loads(ws.receive_text())
            assert m["event"] == "language_changed"

            # Send binary PCM frames (silence)
            pcm_chunk = b"\x00" * 1024
            for _ in range(5):
                ws.send_bytes(pcm_chunk)

            # Send a note to verify pipeline is alive
            ws.send_text(json.dumps({"event": "text_note", "text": "Weight 50 kilo"}))
            resp = json.loads(ws.receive_text())
            assert resp["event"] == "state_update"
            assert resp["record"]["weight"] == 50.0

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_audio_flow).result(timeout=10)

def test_websocket_stop_recording_flow():
    def _run_stop_rec_flow():
        client = TestClient(app)
        with client.websocket_connect("/ws/audio") as ws:
            # Set language to Kannada
            ws.send_text(json.dumps({"event": "set_language", "language": "kn-IN"}))
            m1 = json.loads(ws.receive_text())
            assert m1["event"] == "language_changed"

            # Press mic button with dictated text
            dictated = "Beneficiary ID 4408, name ಶಾಂತಲಾ, visit type ANC, weight 52 kilo, next visit 18th November."
            ws.send_text(json.dumps({"event": "stop_recording", "text": dictated}))

            s1 = json.loads(ws.receive_text())
            assert s1["event"] == "state_update"
            assert s1["record"]["beneficiary_id"] == "4408"
            assert s1["record"]["weight"] == 52.0

            s2 = json.loads(ws.receive_text())
            assert s2["event"] == "agent_speech_start"
            assert len(s2["text"]) > 0
            assert "sariyagidiya" in s2["text"] or "4408" in s2["text"]

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_stop_rec_flow).result(timeout=10)
