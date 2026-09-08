#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Steps for features/alerting.feature.

`cos-configuration-k8s` supplies the rule. It is deployed once per session and
memoised in `_STATE`, because the `juju` fixture is rebuilt per scenario, and
removed by a session-scoped finaliser.
"""

import os
import re
from typing import Optional

import httpx
import jubilant
import pytest
from cos_api import poll_until, remote_write_push
from helpers import wait_for_active_idle
from pytest_bdd import given, then, when

COS_CONFIG_CHARM = "cos-configuration-k8s"
COS_CONFIG_APP = "cos-config"
# Same track as the COS charms pinned in terraform/cos-lite.
COS_CONFIG_CHANNEL = os.environ.get("COS_CONFIG_CHANNEL", "dev/edge")
COS_CONFIG_REPO = "https://github.com/canonical/cos-configuration-k8s-operator"

# tests/samples/prometheus_alert_rules/cpu_overuse.rule in that repo:
# `process_cpu_seconds_total > 0.12` with `for: 0m`.
ALERT_NAME = "CPUOverUse"
ALERT_METRIC = "process_cpu_seconds_total"
ALERT_THRESHOLD = 0.12
TRIGGER_VALUE = 9.99

RULE_DELIVERY_TIMEOUT = 600.0
FIRING_TIMEOUT = 300.0
ALERTMANAGER_TIMEOUT = 420.0
REMOVE_TIMEOUT = 300.0
# Re-push on every poll so the series stays inside Prometheus' five-minute lookback.
PUSH_INTERVAL = 5.0

_EXACT_MATCHER_RE = re.compile(r'(\w+)="([^"]*)"')
_STATE: dict = {}


def _label_matchers(expression: str, metric: str) -> Optional[dict]:
    """Exact-match matchers on `metric` in `expression`, or None if it is not selected."""
    match = re.search(
        rf"(?<![\w:]){re.escape(metric)}(?![\w:])(\{{[^}}]*\}})?", expression
    )
    if match is None:
        return None
    return dict(_EXACT_MATCHER_RE.findall(match.group(1) or ""))


def _find_rule(prometheus: httpx.Client, name: str) -> Optional[dict]:
    response = prometheus.get("/api/v1/rules")
    if response.status_code != 200:
        return None
    for group in response.json().get("data", {}).get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("type") == "alerting" and rule.get("name") == name:
                return rule
    return None


def _remove_cos_config(juju: jubilant.Juju) -> None:
    if COS_CONFIG_APP not in juju.status().apps:
        return
    juju.remove_application(COS_CONFIG_APP, destroy_storage=True, force=True)
    poll_until(
        lambda: COS_CONFIG_APP not in juju.status().apps,
        timeout=REMOVE_TIMEOUT,
        message=f"{COS_CONFIG_APP} was not removed from {juju.model}",
    )


@pytest.fixture(scope="session")
def cos_config_teardown():
    yield
    juju = _STATE.pop("juju", None)
    _STATE.pop("rule", None)
    if juju is not None:
        _remove_cos_config(juju)


@given(
    "an alert rule has been configured through cos-configuration",
    target_fixture="alert_rule",
)
def an_alert_rule_has_been_configured(
    cos_model: jubilant.Juju, prometheus: httpx.Client, cos_config_teardown: None
) -> dict:
    if "rule" in _STATE:
        return _STATE["rule"]

    _remove_cos_config(cos_model)
    cos_model.deploy(
        COS_CONFIG_CHARM,
        COS_CONFIG_APP,
        channel=COS_CONFIG_CHANNEL,
        config={
            "git_repo": COS_CONFIG_REPO,
            "git_branch": "main",
            "prometheus_alert_rules_path": "tests/samples/prometheus_alert_rules",
        },
        trust=True,
    )
    # Registered for teardown before any wait below can fail.
    _STATE["juju"] = cos_model
    cos_model.integrate(
        f"{COS_CONFIG_APP}:prometheus-config", "prometheus:metrics-endpoint"
    )
    wait_for_active_idle(cos_model)
    cos_model.run(f"{COS_CONFIG_APP}/0", "sync-now")

    _STATE["rule"] = poll_until(
        lambda: _find_rule(prometheus, ALERT_NAME),
        timeout=RULE_DELIVERY_TIMEOUT,
        message=(
            f"[{cos_model.model}] alert rule {ALERT_NAME!r} never reached "
            f"Prometheus /api/v1/rules after integrating "
            f"{COS_CONFIG_APP}:prometheus-config with prometheus:metrics-endpoint"
        ),
    )
    return _STATE["rule"]


@when(
    "a sample crossing the rule's threshold is written to Prometheus",
    target_fixture="trigger",
)
def a_sample_is_written(
    cos_model: jubilant.Juju, prometheus: httpx.Client, run_id: str, alert_rule: dict
):
    expression = alert_rule["query"]
    matchers = _label_matchers(expression, ALERT_METRIC)
    assert matchers is not None, (
        f"[{cos_model.model}] the effective expression for {ALERT_NAME} does "
        f"not select {ALERT_METRIC}, so no synthetic series can trigger it: "
        f"{expression!r}"
    )

    labels = {
        "__name__": ALERT_METRIC,
        **matchers,
        "instance": f"cos-solution-test-{run_id}",
        "job": f"cos-solution-test-{run_id}",
        "run_id": run_id,
    }

    class Trigger:
        expr = expression
        series_labels = labels

        @staticmethod
        def push() -> None:
            remote_write_push(prometheus, [(labels, TRIGGER_VALUE)])

    Trigger.push()
    return Trigger


@then("Prometheus reports the alert as firing")
def prometheus_reports_the_alert_firing(
    cos_model: jubilant.Juju, prometheus: httpx.Client, run_id: str, trigger
) -> None:
    model = cos_model.model

    def probe() -> Optional[dict]:
        trigger.push()
        rule = _find_rule(prometheus, ALERT_NAME)
        for alert in (rule or {}).get("alerts", []):
            if alert["labels"].get("run_id") == run_id and alert["state"] == "firing":
                return alert
        return None

    alert = poll_until(
        probe,
        timeout=FIRING_TIMEOUT,
        interval=PUSH_INTERVAL,
        message=(
            f"[{model}] Prometheus never reported {ALERT_NAME} firing for "
            f"run_id={run_id} while {ALERT_METRIC}={TRIGGER_VALUE} "
            f"(> {ALERT_THRESHOLD}) was being remote-written with "
            f"{trigger.series_labels}; effective expression: {trigger.expr!r}"
        ),
    )

    assert float(alert["value"]) > ALERT_THRESHOLD, (
        f"[{model}] {ALERT_NAME} fired on value {alert['value']!r}, which does "
        f"not exceed the rule threshold {ALERT_THRESHOLD}"
    )


@then("Alertmanager lists the alert as active")
def alertmanager_lists_the_alert_active(
    cos_model: jubilant.Juju, alertmanager: httpx.Client, run_id: str, trigger
) -> None:
    model = cos_model.model

    def probe() -> Optional[dict]:
        trigger.push()
        response = alertmanager.get(
            "/api/v2/alerts",
            params={"active": "true", "silenced": "false", "inhibited": "false"},
        )
        if response.status_code != 200:
            return None
        for alert in response.json():
            labels = alert["labels"]
            if labels.get("alertname") == ALERT_NAME and labels.get("run_id") == run_id:
                return alert
        return None

    alert = poll_until(
        probe,
        timeout=ALERTMANAGER_TIMEOUT,
        interval=PUSH_INTERVAL,
        message=(
            f"[{model}] Alertmanager /api/v2/alerts never listed {ALERT_NAME} "
            f"for run_id={run_id}; the prometheus:alertmanager integration may not "
            f"be delivering notifications"
        ),
    )

    assert alert["status"]["state"] == "active", (
        f"[{model}] {ALERT_NAME} for run_id={run_id} is in Alertmanager state "
        f"{alert['status']['state']!r}, expected 'active'"
    )
