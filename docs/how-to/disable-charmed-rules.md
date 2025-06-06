# Disable built-in charm alert rules

By default, Prometheus and Loki will be configured to evaluate and post alerts for all the
[charmed rules](/explanation/charmed-rules) that they receive over relation data.

In some cases, such as troubleshooting, it could be desirable to disable or silence some
charmed rules.

## Disable forwarding of rule files

Disabling the forwarding of rule files can be accomplished at various aggregation points,
using a boolean configuration option, called `forward_alert_rules`:

- `grafana-agent`
- `cos-proxy`
- `prometheus-scrape-config`

For example, to disable forwarding of all alert rules from grafana agent,

```
$ juju config grafana-agent forward_alert_rules=false
```

## Silence charmed rules using alertmanager configuration

Alertmanager can be [configured](https://prometheus.io/docs/alerting/latest/configuration/) 
to silence alerts by labels. This can be used to silence all alerts that contain
juju topology labels, for example:

```
  - receiver: 'charmed-rules-silencer'
    matchers:
    - juju_model=~".+"
```
