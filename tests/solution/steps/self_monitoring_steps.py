#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Steps for features/self_monitoring.feature."""

from cos_api import QueryError, all_lines, group_by_label, wait_for_samples, wait_for_streams
from pytest_bdd import then

SCRAPED = ("alertmanager", "grafana", "loki", "prometheus", "traefik")
COMPONENTS = ("alertmanager", "catalogue", "grafana", "loki", "prometheus", "traefik")
# Charm logs carry `application`; logs forwarded by Pebble carry `juju_application`.
LOG_LABELS = ("application", "juju_application")
SCRAPE_TIMEOUT = 300.0
LOG_TIMEOUT = 180.0
LOG_LOOKBACK_NS = 60 * 60 * 1_000_000_000


@then("Prometheus reports every COS Lite component as up")
def prometheus_reports_every_component_up(prometheus):
    expected = set(SCRAPED)

    def all_up(samples):
        by_app = group_by_label(samples, "juju_application")
        return expected.issubset(by_app) and all(
            all(sample.value == 1.0 for sample in by_app[app]) for app in expected
        )

    samples = wait_for_samples(
        prometheus,
        "up",
        timeout=SCRAPE_TIMEOUT,
        message=f"not every component reported up == 1 ({', '.join(sorted(expected))})",
        predicate=all_up,
    )

    by_app = group_by_label(samples, "juju_application")
    assert expected.issubset(by_app), (
        f"no `up` series for {sorted(expected - set(by_app))}; saw {sorted(by_app)}"
    )
    for application in sorted(expected):
        values = [sample.value for sample in by_app[application]]
        assert all(value == 1.0 for value in values), (
            f"juju_application={application!r} has up values {values}"
        )


@then("Loki holds log lines emitted by the COS Lite components themselves")
def loki_holds_component_logs(loki):
    apps = "|".join(sorted(COMPONENTS))
    failures = []

    for label in LOG_LABELS:
        selector = f'{{{label}=~"{apps}"}}'
        try:
            streams = wait_for_streams(
                loki,
                selector,
                timeout=LOG_TIMEOUT,
                lookback_ns=LOG_LOOKBACK_NS,
                message=f"Loki holds no component logs labelled {label!r}",
                predicate=lambda found: bool(all_lines(found)),
            )
        except QueryError as exc:
            failures.append(str(exc))
            continue

        logged = sorted({stream.labels.get(label) for stream in streams} & set(COMPONENTS))
        assert logged, f"{selector} matched no COS Lite component"
        return

    raise AssertionError(
        "Loki holds no logs emitted by any COS Lite component, under either "
        "label scheme:\n" + "\n".join(failures)
    )
