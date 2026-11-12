"""
API Endpoints Test
Verifies REST and health endpoints using httpx AsyncClient.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "asha-vani-backend"

@pytest.mark.asyncio
async def test_danger_signs_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/danger-signs")
        assert response.status_code == 200
        data = response.json()
        assert "danger_signs" in data
        assert "pregnancy_and_postpartum" in data["danger_signs"]
        assert "newborn_and_child" in data["danger_signs"]

@pytest.mark.asyncio
async def test_records_rest_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Clear records first
        clear_res = await client.delete("/records")
        assert clear_res.status_code == 200

        # Post a record
        payload = {
            "beneficiary_id": "BEN-2026",
            "visit_type": "Newborn care",
            "weight": 2.9,
            "vaccinations_due": ["BCG", "OPV-0"],
            "supplements_given": [],
            "next_visit_date": "14 Days",
            "danger_signs_flagged": [],
            "is_urgent_referral": False,
            "raw_transcript": "Newborn visit done.",
            "language": "hi-IN",
            "is_confirmed": True
        }
        create_res = await client.post("/records", json=payload)
        assert create_res.status_code == 200
        record_id = create_res.json()["id"]

        # List records
        list_res = await client.get("/records")
        assert list_res.status_code == 200
        records = list_res.json()
        assert len(records) >= 1
        assert records[0]["beneficiary_id"] == "BEN-2026"

        # Get single
        get_res = await client.get(f"/records/{record_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == record_id

        # Delete
        del_res = await client.delete(f"/records/{record_id}")
        assert del_res.status_code == 200
