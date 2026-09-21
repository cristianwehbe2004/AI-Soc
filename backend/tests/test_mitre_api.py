from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import SessionLocal
from app.detection import build_rule_registry
from app.mitre.catalog import CORE_RULE_MAPPINGS, CORE_TECHNIQUES
from app.repositories.mitre_repository import MitreRepository
from conftest import AUTH_HEADERS


def test_core_mappings_reference_registered_rules_and_seeded_techniques() -> None:
    registry = build_rule_registry()
    technique_ids = {item["external_id"] for item in CORE_TECHNIQUES}

    assert all(registry.get(rule_id) is not None for rule_id, _ in CORE_RULE_MAPPINGS)
    assert all(technique_id in technique_ids for _, technique_id in CORE_RULE_MAPPINGS)


@pytest.mark.anyio
async def test_core_catalog_seeding_is_idempotent() -> None:
    async with SessionLocal() as session:
        repository = MitreRepository(session)
        await repository.seed_core_catalog()
        await repository.seed_core_catalog()
        techniques, total = await repository.list(tactic=None, search=None, limit=100, offset=0)
        spray = await repository.get_for_rule("rule_002_password_spray")

    assert total == 5
    assert len(techniques) == 5
    assert [item.external_id for item in spray] == ["T1110.003"]


@pytest.mark.anyio
async def test_technique_list_supports_tactic_and_search_filters() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/mitre/techniques", headers=AUTH_HEADERS["viewer"]
        )
        tactic_response = await client.get(
            "/api/v1/mitre/techniques",
            headers=AUTH_HEADERS["viewer"],
            params={"tactic": "Credential Access"},
        )
        search_response = await client.get(
            "/api/v1/mitre/techniques",
            headers=AUTH_HEADERS["viewer"],
            params={"search": "password"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert tactic_response.json()["total"] == 2
    assert search_response.json()["items"][0]["external_id"] == "T1110.003"


@pytest.mark.anyio
async def test_technique_detail_returns_pinned_subtechnique_metadata() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/mitre/techniques/t1110.003", headers=AUTH_HEADERS["viewer"]
        )
        missing = await client.get(
            "/api/v1/mitre/techniques/T9999", headers=AUTH_HEADERS["viewer"]
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Password Spraying"
    assert payload["parent_external_id"] == "T1110"
    assert payload["version"] == "1.8"
    assert payload["source_url"] == "https://attack.mitre.org/techniques/T1110/003/"
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_rule_mapping_api_validates_rules_and_leaves_ml_unmapped() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        spray = await client.get(
            "/api/v1/mitre/rules/rule_002_password_spray/techniques",
            headers=AUTH_HEADERS["viewer"],
        )
        ml = await client.get(
            "/api/v1/mitre/rules/rule_006_ml_anomaly/techniques",
            headers=AUTH_HEADERS["viewer"],
        )
        missing = await client.get(
            "/api/v1/mitre/rules/rule_missing/techniques",
            headers=AUTH_HEADERS["viewer"],
        )

    assert spray.status_code == 200
    assert [item["external_id"] for item in spray.json()["techniques"]] == ["T1110.003"]
    assert ml.status_code == 200
    assert ml.json()["techniques"] == []
    assert missing.status_code == 404
