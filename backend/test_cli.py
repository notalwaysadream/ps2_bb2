"""
Interactive WebSocket CLI Tester for ASHA-Vani Backend
Simulates ASHA worker voice dictation over WebSocket.
"""
import asyncio
import json
import websockets
import httpx

WS_URL = "ws://localhost:8000/ws/audio"
API_URL = "http://localhost:8000"

PRESET_SCENARIOS = {
    "1": {
        "title": "Standard ANC Visit (Dictation)",
        "text": "Beneficiary ID 1042, Sunita Devi ka 3rd ANC checkup kiya. Weight 52 kilo hai. TT injection de diya, aur IFA goli dedi. Next visit 25 November."
    },
    "2": {
        "title": "Voice Correction (Fixing Weight)",
        "text": "Nahi, weight 54 kilo hai."
    },
    "3": {
        "title": "Voice Confirmation (Save to DB)",
        "text": "Haan theek hai, save kar do."
    },
    "4": {
        "title": "Newborn Danger Sign Escalation (High Fever and Poor Feeding)",
        "text": "Beneficiary ID 2088, newborn home visit. Baby ka wazan 2.6 kilo hai, baby ko tez bukhar hai aur doodh nahi pi raha."
    },
    "5": {
        "title": "Pregnancy Danger Sign Escalation (Vaginal Bleeding)",
        "text": "Beneficiary ID 3012, 7th month pregnancy. Patient ko bleeding ho raha hai aur sar dard hai."
    }
}

async def run_scenario(ws, text):
    print(f"\nASHA Worker Spoke: \"{text}\"")
    await ws.send(json.dumps({"event": "text_note", "text": text}))

    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
            if isinstance(msg, bytes):
                print(f"   [Audio Stream] Received {len(msg)} bytes of speech audio")
                continue

            data = json.loads(msg)
            event = data.get("event")

            if event == "state_update":
                rec = data.get("record", {})
                print(f"\n[Form Extracted]:")
                print(f"   - Beneficiary ID : {rec.get('beneficiary_id')}")
                print(f"   - Visit Type     : {rec.get('visit_type')}")
                print(f"   - Weight         : {rec.get('weight')} kg")
                print(f"   - Vaccines       : {rec.get('vaccinations_due')}")
                print(f"   - Supplements    : {rec.get('supplements_given')}")
                print(f"   - Next Visit     : {rec.get('next_visit_date')}")
                print(f"   - Status         : {data.get('status')}")

            elif event == "danger_alert":
                print(f"\n[DANGER SIGN ALERT]")
                print(f"   Advisory: {data.get('alert')}")
                for sign in data.get("signs", []):
                    print(f"   Flagged: {sign.get('name')} -> {sign.get('action_required')}")

            elif event == "agent_speech_start":
                print(f"\n[Agent Read-back]: \"{data.get('text')}\"")

            elif event == "agent_speech_end":
                print("   [Agent finished speaking]")
                break

            elif event == "record_saved":
                print(f"   [Database] Record saved to SQLite (ID: {data['record']['id']})")

        except asyncio.TimeoutError:
            print("   [Response completed]")
            break
        except websockets.exceptions.ConnectionClosed as e:
            print(f"\nConnection closed by server: {e.reason or e}")
            break

async def main():
    print("=" * 60)
    print("   ASHA Voice Field Register - WebSocket Tester")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL) as ws:
            print(f"Connected to {WS_URL}\n")

            while True:
                print("\nChoose an option:")
                for k, v in PRESET_SCENARIOS.items():
                    print(f"  [{k}] {v['title']}")
                print("  [6] Type custom spoken text")
                print("  [7] View saved records from database")
                print("  [q] Quit")

                choice = input("\nEnter choice [1-7 or q]: ").strip()

                if choice.lower() == "q":
                    break
                elif choice in PRESET_SCENARIOS:
                    await run_scenario(ws, PRESET_SCENARIOS[choice]["text"])
                elif choice == "6":
                    custom = input("Enter spoken note: ").strip()
                    if custom:
                        await run_scenario(ws, custom)
                elif choice == "7":
                    async with httpx.AsyncClient() as client:
                        r = await client.get(f"{API_URL}/records")
                        records = r.json()
                        print(f"\nSaved Records in Database ({len(records)} found):")
                        for rec in records:
                            urgent = "[URGENT REFERRAL]" if rec.get('is_urgent_referral') else "[NORMAL]"
                            print(f"  - {rec.get('id')[:8]} | {urgent} ID: {rec.get('beneficiary_id')} | Type: {rec.get('visit_type')} | Weight: {rec.get('weight')}kg")
                else:
                    print("Invalid choice, try again.")

    except ConnectionRefusedError:
        print(f"\nCould not connect to {WS_URL}.")
        print("Please ensure the backend server is running:")
        print("   cd backend")
        print("   source .venv/bin/activate")
        print("   uvicorn app.main:app --reload --port 8000\n")

if __name__ == "__main__":
    asyncio.run(main())
