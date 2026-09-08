#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Fixtures shared by the COS scenarios: settled model, endpoints, credentials, clients.

They build on the `juju` fixture that the common given step provides.
"""

import json
import ssl
import uuid

import httpx
import jubilant
import pytest
from cos_api import get_tls_context
from helpers import wait_for_active_idle

CA_APP = "ca"  # self-signed-certificates, deployed when internal_tls is true
TRAEFIK_UNIT = "traefik/0"
GRAFANA_UNIT = "grafana/0"
HTTP_TIMEOUT = 30.0

# `juju` is rebuilt per scenario, so this memoises the settle across scenarios.
_SETTLED: set[str] = set()


@pytest.fixture
def cos_model(juju: jubilant.Juju) -> jubilant.Juju:
    if juju.model not in _SETTLED:
        wait_for_active_idle(juju)
        _SETTLED.add(juju.model)
    return juju


@pytest.fixture
def tls_context(cos_model: jubilant.Juju, tmp_path_factory) -> ssl.SSLContext:
    """SSLContext trusting the internal CA; asserted so a renamed CA app cannot
    silently disable verification."""
    context = get_tls_context(tmp_path_factory.mktemp("tls"), cos_model, CA_APP)
    assert context is not None, (
        f"no {CA_APP!r} application in model {cos_model.model!r}; "
        f"found {sorted(cos_model.status().apps)}"
    )
    return context


@pytest.fixture
def grafana_admin(cos_model: jubilant.Juju) -> dict:
    return dict(cos_model.run(GRAFANA_UNIT, "get-admin-password").results)


@pytest.fixture
def grafana_auth(grafana_admin: dict) -> tuple:
    password = grafana_admin.get("admin-password")
    assert password, f"get-admin-password returned no password: {sorted(grafana_admin)}"
    return ("admin", password)


@pytest.fixture
def endpoints(cos_model: jubilant.Juju, grafana_admin: dict) -> dict:
    """Base URL per application, with no trailing slash."""
    task = cos_model.run(TRAEFIK_UNIT, "show-proxied-endpoints")
    proxied = json.loads(task.results["proxied-endpoints"])

    # Keys are per unit ("prometheus/0") or per app ("alertmanager"); lowest unit wins.
    best = {}
    for key, value in proxied.items():
        app, _, unit = key.partition("/")
        index = int(unit) if unit.isdigit() else -1
        url = value["url"] if isinstance(value, dict) else value
        if url and (app not in best or index < best[app][0]):
            best[app] = (index, url)
    resolved = {app: url.rstrip("/") for app, (_, url) in best.items()}

    # Grafana may be missing from Traefik's output; get-admin-password also returns its URL.
    if "grafana" not in resolved:
        grafana_url = grafana_admin.get("url")
        assert grafana_url, (
            f"traefik proxies {sorted(resolved)} and get-admin-password returned no "
            f"url, so Grafana has no resolvable endpoint"
        )
        resolved["grafana"] = grafana_url.rstrip("/")
    return resolved


@pytest.fixture
def clients(endpoints: dict, tls_context: ssl.SSLContext, grafana_auth: tuple) -> dict:
    return {
        app: httpx.Client(
            base_url=base_url,
            auth=grafana_auth if app == "grafana" else None,
            verify=tls_context,
            timeout=HTTP_TIMEOUT,
        )
        for app, base_url in endpoints.items()
    }


def _client(clients: dict, app: str) -> httpx.Client:
    assert app in clients, f"{app} has no resolved endpoint; resolved {sorted(clients)}"
    return clients[app]


@pytest.fixture
def prometheus(clients: dict) -> httpx.Client:
    return _client(clients, "prometheus")


@pytest.fixture
def loki(clients: dict) -> httpx.Client:
    return _client(clients, "loki")


@pytest.fixture
def alertmanager(clients: dict) -> httpx.Client:
    return _client(clients, "alertmanager")


@pytest.fixture
def grafana(clients: dict) -> httpx.Client:
    return _client(clients, "grafana")


@pytest.fixture(scope="session")
def run_id() -> str:
    """Tags this run's test data so reruns against one model stay independent."""
    return uuid.uuid4().hex[:8]
