COS Lite consists of a number of charms connected by juju relations.

The graph is so dense and interconnected that displaying it in its entirety is confusing and uninformative. Instead, for clarity and readability, we depict the bundle topology using several separate diagrams, each one presenting a view of a specific data flow or functionality group. 
Each line indicates a separate juju relation.

## Ingress view
The workloads that make up COS Lite are servers that need to be reachable from outside the model they are deployed in.
- Grafana ("ingress-to-leader") is the main UI, amalgamating telemetry from all datasources into dashboards.
- Prometheus and Loki (both "ingress-per-unit"), ingest telemetry pushed from grafana agent from another model.
- Alertmanager ("ingress per app"), has a UI for acknowledging or silencing alerts.

```{mermaid}
graph LR

subgraph cos_lite["COS Lite"]

  alrt[Alertmanager]
  click alrt "https://github.com/canonical/alertmanager-k8s-operator"
  
  graf[Grafana]
  click graf "https://github.com/canonical/grafana-k8s-operator"

  prom[Prometheus]
  click prom "https://github.com/canonical/prometheus-k8s-operator"

  loki[Loki]
  click loki "https://github.com/canonical/loki-k8s-operator"

  trfk[Traefik]
  click trfk "https://github.com/canonical/traefik-k8s-operator"

  ctlg[Catalogue]
  click ctlg "https://github.com/canonical/catalogue-k8s-operator"

  trfk --- |<a href='https://charmhub.io/traefik-k8s/libraries/ingress_per_unit'>ipu</a>| loki
  trfk --- |ipu| prom
  trfk --- |<a href='https://charmhub.io/traefik-route-k8s/libraries/traefik_route'>route</a>| graf
  trfk --- |<a href='https://charmhub.io/traefik-k8s/libraries/ingress'>ipa</a>| alrt

  prom --- |<a href='https://charmhub.io/catalogue-k8s/libraries/catalogue'>catalogue</a>| ctlg
  alrt --- |catalogue| ctlg
  graf --- |catalogue| ctlg

end
```

## Datasource view
Many of the COS workloads are (API frontends to) data storages that can query each other:
- Grafana queries loki, prometheus for telemetry and alertmanager for alerts.
- Prometheus and loki evaluate alert rules and post alerts to alertmanager.

```{mermaid}
graph LR

subgraph cos_lite["COS Lite"]

  alrt[Alertmanager]
  click alrt "https://github.com/canonical/alertmanager-k8s-operator"
  
  graf[Grafana]
  click graf "https://github.com/canonical/grafana-k8s-operator"

  prom[Prometheus]
  click prom "https://github.com/canonical/prometheus-k8s-operator"

  loki[Loki]
  click loki "https://github.com/canonical/loki-k8s-operator"

  prom --- |alerting| alrt
  loki --- |alerting| alrt
  graf --- |source| prom
  graf --- |source| alrt
  graf --- |source| loki
end
```

## Self-monitoring view
The observability solution monitors itself to ensure correct functioning. The self-monitoring relations together with [cos-alerter](https://github.com/canonical/cos-alerter) guard against outages of the observability stack itself.

```{mermaid}
graph TD

subgraph cos_lite["COS Lite"]

  alrt[Alertmanager]
  click alrt "https://github.com/canonical/alertmanager-k8s-operator"
  
  graf[Grafana]
  click graf "https://github.com/canonical/grafana-k8s-operator"

  prom[Prometheus]
  click prom "https://github.com/canonical/prometheus-k8s-operator"

  loki[Loki]
  click loki "https://github.com/canonical/loki-k8s-operator"

  trfk[Traefik]
  click trfk "https://github.com/canonical/traefik-k8s-operator"

  trfk --- |metrics| prom
  alrt --- |metrics| prom
  loki --- |metrics| prom
  graf --- |metrics| prom

  graf --- |dashboard| loki
  graf --- |dashboard| prom
  graf --- |dashboard| alrt
end
```