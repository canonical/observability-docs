Disable charmed rules
*********************

By default, prometheus and loki will be configured to evaluate and post alerts for all the
`charmed rules <charmed-rules>`_ that they receive over relation data.

In some cases, such as troubleshooting, it could be desirable to disable or silence some
charmed rules.

Disable forwarding of rule files
=================================

Disabling the forwarding of rule files can be accomplished at various aggregation points,
using a boolean config option, called ``forward_alert_rules``:

- grafana-agent
- cos-proxy
- prometheus-scrape-config

For example, to disable forwarding of all alert rules from grafana agent,

.. code-block::

    juju config grafana-agent forward_alert_rules=false

Silence charmed rules using alertmanager config
===============================================

Alertmanager can be `configured <https://prometheus.io/docs/alerting/latest/configuration/>`_
to silence alerts by labels. This can be used to silence all alerts that contain
juju topology labels, for example:

.. code-block::

      - receiver: 'charmed-rules-silencer'
        matchers:
        - juju_model=~".+"
