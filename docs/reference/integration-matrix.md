# Integration matrix


|             | K8s charm                                                                                                                                               | Machine charm                                                                                  | Legacy charms - LMA         | Non-juju workload                          |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------ |
| Logs        |  | [cos_agent] (subordinate, pulls logs from `/var/log` or from other snaps with a matching slot) | [cos-proxy]                      | [grafana-agent snap] (manually configured) |
| Metrics     | [prometheus_scrape] (in-model), [prometheus_remote_write] (CMR) - with grafana-agent                                                                    | [cos_agent]                                                                                    | [cos-proxy]                      | [scrape-target], [grafana-agent snap]      |
| Traces      | [tracing] (instrumented workloads), [charm_tracing] (for the charm itself)                                                                                | [tracing] (CMR), [cos_agent]                                                                   | N/A                              | [grafana-agent charm]                      | 
| Dashboards  | [grafana_dashboard], [cos-configuration]                                                                                                                | [cos_agent], [cos-configuration]                                                               | [cos-proxy], [cos-configuration] | [cos-configuration]                        |
| Alert rules | via metrics and logs relations, [cos-configuration]                                                                                                     | [cos_agent], [cos-configuration]                                                               | [cos-proxy], [cos-configuration] | [cos-configuration]                        |

- The [COS Lite bundle](https://charmhub.io/cos-lite) does not include tracing by default; however, there's a bundle overlay for that.

[loki_push_api]: https://charmhub.io/loki-k8s/libraries/loki_push_api
[prometheus_scrape]: https://charmhub.io/prometheus-k8s/libraries/prometheus_scrape
[prometheus_remote_write]: https://charmhub.io/prometheus-k8s/libraries/prometheus_remote_write
[tracing]: https://charmhub.io/tempo-k8s/libraries/tracing
[charm_tracing]: https://charmhub.io/tempo-k8s/libraries/charm_tracing
[grafana_dashboard]: https://charmhub.io/grafana-k8s/libraries/grafana_dashboard
[cos-configuration]: https://charmhub.io/cos-configuration-k8s
[cos_agent]: https://charmhub.io/grafana-agent/libraries/cos_agent
[cos-proxy]: https://charmhub.io/cos-proxy
[grafana-agent snap]: https://snapcraft.io/grafana-agent
[grafana-agent charm]: https://charmhub.io/grafana-agent-k8s
[scrape-target]: https://charmhub.io/prometheus-scrape-target-k8s
 [LogProxyConsumer]: https://charmhub.io/loki-k8s/libraries/loki_push_api

## External links
- [Monitoring Agents Comparative Study]( https://lf-anuket.atlassian.net/wiki/spaces/HOME/pages/21878543/Monitoring+Agents+Comparative+Study)
- [How to integrate COS Lite with non-juju workloads](https://discourse.charmhub.io/t/how-to-integrate-cos-lite-with-uncharmed-applications/12005)