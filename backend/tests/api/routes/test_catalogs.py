import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

CATALOG_SLUGS = [
    "movements",
    "case-materials",
    "target-genders",
    "watch-styles",
]


def _url(slug: str, suffix: str = "") -> str:
    return f"{settings.API_V1_STR}/catalogs/{slug}/{suffix}"


def _create(client: TestClient, headers: dict, slug: str, name: str) -> dict:
    r = client.post(_url(slug), headers=headers, json={"name": name})
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_create_catalog_entry(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    name = f"Test-{slug}-{uuid.uuid4().hex[:8]}"
    r = client.post(_url(slug), headers=superuser_token_headers, json={"name": name})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == name
    assert "id" in data


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_create_catalog_entry_forbidden(
    client: TestClient, normal_user_token_headers: dict[str, str], slug: str
) -> None:
    r = client.post(
        _url(slug),
        headers=normal_user_token_headers,
        json={"name": "Should Not Create"},
    )
    assert r.status_code == 403


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_create_catalog_entry_missing_name(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    r = client.post(_url(slug), headers=superuser_token_headers, json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_read_catalog_entries(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    _create(client, superuser_token_headers, slug, f"List-{slug}-{uuid.uuid4().hex[:8]}")
    r = client.get(_url(slug), headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
    assert isinstance(data["data"], list)
    assert data["count"] >= 1


# ---------------------------------------------------------------------------
# Read one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_read_catalog_entry(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    created = _create(client, superuser_token_headers, slug, f"Read-{slug}-{uuid.uuid4().hex[:8]}")
    r = client.get(_url(slug, created["id"]), headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == created["id"]
    assert data["name"] == created["name"]


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_read_catalog_entry_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    r = client.get(_url(slug, str(uuid.uuid4())), headers=superuser_token_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_update_catalog_entry(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    created = _create(client, superuser_token_headers, slug, f"Upd-{slug}-{uuid.uuid4().hex[:8]}")
    new_name = f"Updated-{uuid.uuid4().hex[:8]}"
    r = client.put(
        _url(slug, created["id"]),
        headers=superuser_token_headers,
        json={"name": new_name},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name
    assert data["id"] == created["id"]


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_update_catalog_entry_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    r = client.put(
        _url(slug, str(uuid.uuid4())),
        headers=superuser_token_headers,
        json={"name": "Ghost"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_delete_catalog_entry(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    created = _create(client, superuser_token_headers, slug, f"Del-{slug}-{uuid.uuid4().hex[:8]}")
    r = client.delete(_url(slug, created["id"]), headers=superuser_token_headers)
    assert r.status_code == 200
    # Confirm gone
    r2 = client.get(_url(slug, created["id"]), headers=superuser_token_headers)
    assert r2.status_code == 404


@pytest.mark.parametrize("slug", CATALOG_SLUGS)
def test_delete_catalog_entry_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], slug: str
) -> None:
    r = client.delete(_url(slug, str(uuid.uuid4())), headers=superuser_token_headers)
    assert r.status_code == 404
