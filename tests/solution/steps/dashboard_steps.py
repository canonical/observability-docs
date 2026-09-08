#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Steps for features/dashboards.feature."""

from typing import Any, Optional

import httpx
import jubilant
import pytest
from cos_api import poll_until
from pytest_bdd import then, when

REQUIRED_TYPES = ("prometheus", "loki", "alertmanager")
PANEL_TITLES = ("cos-solution-test-panel-a", "cos-solution-test-panel-b")

READBACK_TIMEOUT = 60.0
DATASOURCE_TIMEOUT = 300.0
# Loki answers 503 on /ready for about a minute after going active.
PROXY_TIMEOUT = 300.0


def _dashboard(uid: str, title: str) -> dict:
    """Two-panel dashboard payload; no `id`, so Grafana creates it."""
    return {
        "uid": uid,
        "title": title,
        "tags": ["cos-solution-test"],
        "schemaVersion": 39,
        "panels": [
            {
                "id": index + 1,
                "type": "timeseries",
                "title": panel_title,
                "gridPos": {"h": 8, "w": 12, "x": 12 * index, "y": 0},
            }
            for index, panel_title in enumerate(PANEL_TITLES)
        ],
    }


def _datasources_by_type(grafana: httpx.Client, model: str) -> dict:
    """Poll until Grafana lists every required datasource type; they appear one at a time
    while hooks are still running."""

    def probe() -> dict:
        response = grafana.get("/api/datasources")
        if response.status_code != 200:
            raise AssertionError(f"HTTP {response.status_code}: {response.text[:300]}")
        found: dict = {}
        for datasource in response.json():
            found.setdefault(datasource["type"], datasource)
        missing = [kind for kind in REQUIRED_TYPES if kind not in found]
        if missing:
            raise AssertionError(f"missing {missing}, found {sorted(found)}")
        return found

    return poll_until(
        probe,
        timeout=DATASOURCE_TIMEOUT,
        message=(
            f"[{model}] GET /api/datasources never listed all of "
            f"{list(REQUIRED_TYPES)}; the grafana-source integrations to prometheus, "
            f"loki and alertmanager may not have settled"
        ),
    )


@pytest.fixture
def dashboard_cleanup(cos_model: jubilant.Juju, grafana: httpx.Client):
    created: list = []
    yield created
    for uid in created:
        deleted = grafana.delete(f"/api/dashboards/uid/{uid}")
        assert deleted.status_code in (200, 404), (
            f"[{cos_model.model}] cleanup failed, DELETE "
            f"/api/dashboards/uid/{uid} returned HTTP {deleted.status_code}: "
            f"{deleted.text[:300]}"
        )
        survivor = grafana.get(f"/api/dashboards/uid/{uid}")
        assert survivor.status_code == 404, (
            f"[{cos_model.model}] cleanup failed, dashboard uid={uid} is still "
            f"readable (HTTP {survivor.status_code})"
        )


@when("a dashboard is created through the Grafana API", target_fixture="created_dashboard")
def a_dashboard_is_created(
    cos_model: jubilant.Juju, grafana: httpx.Client, run_id: str, dashboard_cleanup: list
) -> dict:
    model = cos_model.model
    uid = f"cossol-{run_id}"
    dashboard = _dashboard(uid, f"COS Lite solution test {run_id}")
    body = {"dashboard": dashboard, "folderUid": "", "overwrite": True}

    response = grafana.post("/api/dashboards/db", json=body)
    dashboard_cleanup.append(uid)
    assert response.status_code == 200, (
        f"[{model}] POST /api/dashboards/db for uid={uid} returned "
        f"HTTP {response.status_code}: {response.text[:500]}"
    )
    assert response.json().get("status") == "success", (
        f"[{model}] Grafana did not report success creating uid={uid}: "
        f"{response.text[:500]}"
    )
    return dashboard


@then("the dashboard reads back with the same title and panels")
def the_dashboard_reads_back(
    cos_model: jubilant.Juju, grafana: httpx.Client, created_dashboard: dict
) -> None:
    model = cos_model.model
    uid = created_dashboard["uid"]

    def probe() -> Optional[dict]:
        response = grafana.get(f"/api/dashboards/uid/{uid}")
        return response.json()["dashboard"] if response.status_code == 200 else None

    stored = poll_until(
        probe,
        timeout=READBACK_TIMEOUT,
        message=(
            f"[{model}] dashboard uid={uid} was accepted by "
            f"POST /api/dashboards/db but never became readable"
        ),
    )

    assert stored["title"] == created_dashboard["title"], (
        f"[{model}] read back title {stored['title']!r}, expected "
        f"{created_dashboard['title']!r}"
    )
    panels = sorted(panel["title"] for panel in stored.get("panels", []))
    assert panels == sorted(PANEL_TITLES), (
        f"[{model}] read back panels {panels}, expected {sorted(PANEL_TITLES)}"
    )


@then("Grafana lists a Prometheus, a Loki and an Alertmanager datasource")
def grafana_lists_the_datasources(cos_model: jubilant.Juju, grafana: httpx.Client) -> None:
    model = cos_model.model
    found = _datasources_by_type(grafana, model)

    for kind in REQUIRED_TYPES:
        datasource = found[kind]
        assert datasource.get("uid"), (
            f"[{model}] {kind} datasource has no uid: {datasource}"
        )
        assert datasource.get("url"), (
            f"[{model}] {kind} datasource has no url: {datasource}"
        )


def _check_prometheus(body: Any) -> Optional[str]:
    """Why `body` is not a successful `vector(1)` result, or None if it is."""
    if body.get("status") != "success":
        return f"status is not 'success': {body!r:.300}"
    data = body.get("data", {})
    if data.get("resultType") != "vector":
        return f"resultType is {data.get('resultType')!r}, expected 'vector'"
    result = data.get("result") or []
    if not result:
        return "result vector is empty"
    if float(result[0]["value"][1]) != 1.0:
        return f"vector(1) evaluated to {result[0]['value'][1]!r}, expected '1'"
    return None


def _check_alertmanager(body: Any) -> Optional[str]:
    """Why `body` is not a real Alertmanager status, or None if it is."""
    if not body.get("versionInfo", {}).get("version"):
        return f"versionInfo.version is missing or empty: {body!r:.300}"
    if "cluster" not in body:
        return "no 'cluster' section in the status body"
    return None


# vector(1) asserts on a value the backend computed; Alertmanager has no query language.
PROXY_PROBES = (
    ("prometheus", "/api/v1/query", {"query": "vector(1)"}, _check_prometheus),
    ("loki", "/loki/api/v1/query", {"query": "vector(1)"}, _check_prometheus),
    ("alertmanager", "/api/v2/status", None, _check_alertmanager),
)


@then("a query through each datasource proxy returns a well-formed result")
def each_datasource_proxy_answers(cos_model: jubilant.Juju, grafana: httpx.Client) -> None:
    model = cos_model.model
    found = _datasources_by_type(grafana, model)

    for kind, backend_path, params, check in PROXY_PROBES:
        uid = found[kind]["uid"]
        path = f"/api/datasources/proxy/uid/{uid}{backend_path}"

        def probe(path=path, check=check, params=params) -> bool:
            response = grafana.get(path, params=params)
            if response.status_code != 200:
                raise AssertionError(f"HTTP {response.status_code}: {response.text[:300]}")
            problem = check(response.json())
            if problem:
                raise AssertionError(problem)
            return True

        poll_until(
            probe,
            timeout=PROXY_TIMEOUT,
            message=(
                f"[{model}] a query through the {kind} datasource proxy "
                f"(uid={uid}, {path}) never returned a successful, well-formed body"
            ),
        )
