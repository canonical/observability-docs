Charmed alert rules
*******************

What are alert rules?
=====================

Prometheus and Loki would post alerts to Alertmanager when alert expressions are
evaluated as "true". Alert expressions are stored in yaml files called "alert rules".

- Metrics-based alert rule expressions are written in PromQL, and are evaluated by prometheus.
- Log-based alert rule expressions are written in LogQL, and are evaluated by Loki.

As of writing, there is no official centralized store for alert rules. Often, operators
refer to the `Awesome Prometheus Rules <https://samber.github.io/awesome-prometheus-alerts/>`_
project as a starting point.

What are charmed alert rules
============================

A charmed operator is meant to encapsulate programmatically the knowledge needed to
operate a workload, and alert rules make an important part of that knowledge.

Charmed operators may include "built-in" alert rules (aka "charmed alert rules").
By default, rule files are located at ``./src/prometheus_alert_rules`` and ``./src/loki_alert_rules``
relative to the charm's root folder.

When the built-in alert rules are picked up by the charmed operator, they are transformed
and forwarded to prometheus or loki charms over relation data.

The main advantage of charmed rules is that operation knowledge is centralized, and is readily available
with the charmed operator.
The main disadvantage of charmed rules is that alert thresholds are opinionated and not configurable. This
means that authors of charmed rules must pay special attention to wide applicability.
Charmed rules can be `disabled <disable-charmed-rules>`_.

Automatic modifications made to charmed alert rules
---------------------------------------------------
- All alert expressions are automatically injected with juju topology matchers.
- Juju topology alert labels are automaticall added to all alerts.
