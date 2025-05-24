# Instrumenting machine charms

## Prerequisites

- A charmed application that is running in a virtual, or physical, machine.
- The Canonical Observability Stack, running on Kubernetes.

## Introduction

This tutorial will teach you how to integrate a charm deployed on a machine substrate with the Canonical Observability Stack, running on Kubernetes.

The Grafana Agent machine charm handles installation, configuration, and Day 2 operations specific to [Grafana Agent](https://grafana.com/oss/agent/), using [Juju](https://juju.is). The charm is designed to run in virtual machines as a [subordinate](https://discourse.charmhub.io/t/subordinate-applications/1053). 

```{note}
Application units are typically run in an isolated container on a machine with no knowledge or access to other applications deployed onto the same machine. With subordinate charms, units of different applications to be deployed into the same container and to have knowledge of each other. Subordinate units scale together with their principal.
```

## Ensure COS Lite is up and running.

Before we get started, we will make sure that the observability stack is up and running in our `cos` model (follow the tutorial on [getting started with COS Lite](/tutorial/installation/getting-started-with-cos-lite)) in a Kubernetes controller, like this:

```text
 juju status --relations

Model  Controller  Cloud/Region        Version  SLA          Timestamp
cos    charm-dev   microk8s/localhost  2.9.42   unsupported  15:43:36-04:00

App           Version  Status  Scale  Charm             Channel  Rev  Address         Exposed  Message
alertmanager  0.25.0   active      1  alertmanager-k8s  edge      67  10.152.183.93   no       
catalogue              active      1  catalogue-k8s     edge      15  10.152.183.193  no       
grafana       9.2.1    active      1  grafana-k8s       edge      77  10.152.183.137  no       
loki          2.7.4    active      1  loki-k8s          edge      82  10.152.183.119  no       
prometheus    2.42.0   active      1  prometheus-k8s    edge     122  10.152.183.51   no       
traefik       2.9.6    active      1  traefik-k8s       edge     125  10.43.8.34      no       

Unit             Workload  Agent  Address     Ports  Message
alertmanager/0*  active    idle   10.1.55.34         
catalogue/0*     active    idle   10.1.55.38         
grafana/0*       active    idle   10.1.55.32         
loki/0*          active    idle   10.1.55.14         
prometheus/0*    active    idle   10.1.55.40         
traefik/0*       active    idle   10.1.55.53         

Offer       Application  Charm           Rev  Connected  Endpoint              Interface                Role
dashboards  grafana      grafana-k8s     124  1/1        grafana-dashboard     grafana_dashboard        requirer
logging     loki         loki-k8s        178  1/1        logging               loki_push_api            provider
metrics     prometheus   prometheus-k8s  217  1/1        receive-remote-write  prometheus_remote_write  provider

Relation provider                   Requirer                     Interface              Type     Message
alertmanager:alerting               loki:alertmanager            alertmanager_dispatch  regular  
alertmanager:alerting               prometheus:alertmanager      alertmanager_dispatch  regular  
alertmanager:grafana-dashboard      grafana:grafana-dashboard    grafana_dashboard      regular  
alertmanager:grafana-source         grafana:grafana-source       grafana_datasource     regular  
alertmanager:replicas               alertmanager:replicas        alertmanager_replica   peer     
alertmanager:self-metrics-endpoint  prometheus:metrics-endpoint  prometheus_scrape      regular  
catalogue:catalogue                 alertmanager:catalogue       catalogue              regular  
catalogue:catalogue                 grafana:catalogue            catalogue              regular  
catalogue:catalogue                 prometheus:catalogue         catalogue              regular  
grafana:grafana                     grafana:grafana              grafana_peers          peer     
grafana:metrics-endpoint            prometheus:metrics-endpoint  prometheus_scrape      regular  
loki:grafana-dashboard              grafana:grafana-dashboard    grafana_dashboard      regular  
loki:grafana-source                 grafana:grafana-source       grafana_datasource     regular  
loki:metrics-endpoint               prometheus:metrics-endpoint  prometheus_scrape      regular  
prometheus:grafana-dashboard        grafana:grafana-dashboard    grafana_dashboard      regular  
prometheus:grafana-source           grafana:grafana-source       grafana_datasource     regular  
prometheus:prometheus-peers         prometheus:prometheus-peers  prometheus_peers       peer     
traefik:ingress                     alertmanager:ingress         ingress                regular  
traefik:ingress                     catalogue:ingress            ingress                regular  
traefik:ingress-per-unit            loki:ingress                 ingress_per_unit       regular  
traefik:ingress-per-unit            prometheus:ingress           ingress_per_unit       regular  
traefik:metrics-endpoint            prometheus:metrics-endpoint  prometheus_scrape      regular  
traefik:traefik-route               grafana:ingress              traefik_route          regular  
```

## Add the required integrations to our charm

In this example we use COS Lite to observe [Zookeeper](https://github.com/canonical/zookeeper-operator).

In order for it to be able to integrate with COS Lite, we will have to make some changes to our charm.

### Obtain the `cos_agent` library

Execute the following command to have Charmcraft fetch the required library from Charmhub.

```shell
charmcraft fetch-lib charms.grafana_agent.v0.cos_agent
```

### Add the needed `provider`

In the `metadata.yaml` of the zookeeper charm, we will now add the
`cos-agent` relation to the `provides` section.

```diff
[...]
provides:
  zookeeper:
    interface: zookeeper
+  cos-agent:
+    interface: cos_agent
+    limit: 1
[...]
```

### Integrate the library in our charm code

In `src/charm.py`, import the library.

```python
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
```

Instantiate the `COSAgentProvider` object in the charm's `__init__` method.

```python
        # ...
        self._grafana_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": NODE_EXPORTER_PORT},
                {"path": "/metrics", "port": JMX_PORT},
                {"path": "/metrics", "port": METRICS_PROVIDER_PORT},
            ],
            metrics_rules_dir="./src/alert_rules/prometheus",
            logs_rules_dir="./src/alert_rules/loki",
            dashboard_dirs=["./src/grafana_dashboards"],
            log_slots=["charmed-zookeeper:logs"],
        )
        # ...
```

As part of this constructor call, you may change the paths where metrics alert rules, log alert rules, and Grafana dashboard files are stored.

```{note}
To learn how to craft alert rules and dashboards, check [these examples](https://github.com/canonical/cos-configuration-k8s-operator/tree/main/tests/samples).
```

### Pack the charm:

We will now pack the charm using Charmcraft.

```shell
$ charmcraft pack
```

## Refreshing the Zookeeper charm

Switch to the machine model and refresh the
Zookeeper charm with the charm file we just created.

```
  juju switch lxd:admin/safari # or wherever your zookeeper charm is deployed
  juju refresh zookeeper --path ./*.charm
```

Juju will now do an in-place upgrade of the charm, adding the `cos-agent` relation we just created. Verify that it's `active/idle` before proceeding.

```
$ juju status zookeeper

Model   Controller  Cloud/Region         Version  SLA          Timestamp
safari  lxd         localhost/localhost  3.6.4    unsupported  14:04:49+02:00

App        Version  Status  Scale  Charm      Channel  Rev  Exposed  Message
zookeeper  3.8.4    active      1  zookeeper             0  no       

Unit          Workload  Agent  Machine  Public address  Ports  Message
zookeeper/0*  active    idle   0        10.190.242.217         

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
```

## Deploy the Grafana Agent machine charm

Now deploy the Grafana Agent machine charm.

```
$ juju deploy grafana-agent
$ juju status

Model   Controller  Cloud/Region         Version  SLA          Timestamp
safari  lxd         localhost/localhost  3.6.4    unsupported  14:06:18+02:00

App            Version  Status   Scale  Charm          Channel        Rev  Exposed  Message
grafana-agent           unknown      0  grafana-agent  latest/stable  456  no       
zookeeper      3.8.4    active       1  zookeeper                       0  no       

Unit          Workload  Agent  Machine  Public address  Ports  Message
zookeeper/0*  active    idle   0        10.190.242.217         

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
```

At this point we have one `zookeeper` unit in `active` state, and a `grafana-agent` in unknown state, with no units. This is, as mentioned earlier, because `grafana-agent` is a [subordinate charm](https://discourse.charmhub.io/t/subordinate-applications/1053).

## Integrate the charms

Now integrate `zookeeper` with `grafana-agent` over the `cos-agent` relation.

```
$ juju integrate zookeeper grafana-agent:cos-agent
```

Once the relation has been established, `grafana-agent` will be deployed together with the `zookeeper` unit, in the same machine. The status of the model at that point will be:

```
$ juju status

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
simme@willow:~$ juju status
Model   Controller  Cloud/Region         Version  SLA          Timestamp
safari  lxd         localhost/localhost  3.6.4    unsupported  14:09:25+02:00

App            Version  Status   Scale  Charm          Channel        Rev  Exposed  Message
grafana-agent           blocked      1  grafana-agent  latest/stable  456  no       Missing ['grafana-cloud-config']|['grafana-dashboards-provider']|['logging-consumer']|['send-remote-write'] for cos-a...
zookeeper      3.8.4    active       1  zookeeper                       0  no       

Unit                Workload  Agent  Machine  Public address  Ports  Message
zookeeper/0*        active    idle   0        10.190.242.217         
  grafana-agent/0*  blocked   idle            10.190.242.217         Missing ['grafana-cloud-config']|['grafana-dashboards-provider']|['logging-consumer']|['send-remote-write'] for cos-a...

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
```

Note that despite `grafana-agent` being deployed and collecting telemetry, it is yet to forward them anywhere due to the lack of relations to the corresponding components in the observability stack.

## Relate Grafana Agent to COS Lite 

As the next step, we will relate Grafana Agent to the COS Lite components. Specifically, to

* Prometheus for the metrics,
* Loki for the logs, and
* Grafana for the dashboards. 

From the model our application is running, we can verify the [`offers`](https://documentation.ubuntu.com/juju/3.6/howto/manage-relations/#manage-relations) COS Lite is exposing:

```shell
$ juju find-offers -m k8s:admin/cos
Store  URL                   Access  Interfaces
k8s    admin/cos.dashboards  admin   grafana_dashboard:grafana-dashboard
k8s    admin/cos.logging     admin   loki_push_api:logging
k8s    admin/cos.metrics     admin   prometheus_remote_write:receive-remote-write
```

To be able to use them, we now need to consume them.


```shell
$ juju consume k8s:admin/cos.metrics
$ juju consume k8s:admin/cos.logging
$ juju consume k8s:admin/cos.dashboards
```

Once these commands have been executed, the status of our model will change slightly.

```
$ juju status
Model   Controller  Cloud/Region         Version  SLA          Timestamp
safari  lxd         localhost/localhost  3.6.4    unsupported  14:16:07+02:00

SAAS        Status  Store  URL
dashboards  active  k8s    admin/cos.dashboards
logging     active  k8s    admin/cos.logging
metrics     active  k8s    admin/cos.metrics

App            Version  Status   Scale  Charm          Channel        Rev  Exposed  Message
grafana-agent           blocked      1  grafana-agent  latest/stable  456  no       Missing ['grafana-cloud-config']|['grafana-dashboards-provider']|['logging-consumer']|['send-remote-write'] for cos-a...
zookeeper      3.8.4    active       1  zookeeper                       0  no       

Unit                Workload  Agent  Machine  Public address  Ports  Message
zookeeper/0*        active    idle   0        10.190.242.217         
  grafana-agent/0*  blocked   idle            10.190.242.217         Missing ['grafana-cloud-config']|['grafana-dashboards-provider']|['logging-consumer']|['send-remote-write'] for cos-a...

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
```

Notice how in the status we now have a new section named `SAAS`. In that section we can see all the interfaces offered by other applications running in other models that we can integrate to.

We will now relate Grafana Agent to these 3 applications:

```shell
$ juju relate grafana-agent metrics
$ juju relate grafana-agent logging
$ juju relate grafana-agent dashboards
```

And the three new relations are established, see the relations sections of the model status:

```
$ juju status
Model   Controller  Cloud/Region         Version  SLA          Timestamp
safari  lxd         localhost/localhost  3.6.4    unsupported  14:17:30+02:00

SAAS        Status  Store  URL
dashboards  active  k8s    admin/cos.dashboards
logging     active  k8s    admin/cos.logging
metrics     active  k8s    admin/cos.metrics

App            Version  Status  Scale  Charm          Channel        Rev  Exposed  Message
grafana-agent           active      1  grafana-agent  latest/stable  456  no       tracing: off
zookeeper      3.8.4    active      1  zookeeper                       0  no       

Unit                Workload  Agent  Machine  Public address  Ports  Message
zookeeper/0*        active    idle   0        10.190.242.217         
  grafana-agent/0*  active    idle            10.190.242.217         tracing: off

Machine  State    Address         Inst id        Base          AZ  Message
0        started  10.190.242.217  juju-0cb42c-0  ubuntu@22.04      Running
```

## Verify that metrics and logs reach Prometheus and Loki

Now that the Cross Model Relations are established between our application model and our observability model, we can easily verify that the metrics `zookeeper` exposes are reaching Prometheus.

```

$ curl -s http://192.168.122.10/cos-prometheus-0/api/v1/query\?query\=zookeeper_DataDirSize | jq
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "zookeeper_DataDirSize",
          "instance": "applications_f201dfb6-896c-4d5e-83c0-55e6bb8b08f3_zookeeper_zookeeper/0",
          "job": "zookeeper_1",
          "juju_application": "zookeeper",
          "juju_model": "applications",
          "juju_model_uuid": "f201dfb6-896c-4d5e-83c0-55e6bb8b08f3",
          "juju_unit": "zookeeper/0",
          "memberType": "Leader",
          "replicaId": "1"
        },
        "value": [
          1678971938.463,
          "67108880"
        ]
      }
    ]
  }
}
```

You can then log into Grafana, head over to the explore tab, and do the same verification for logs, or check the list of dashboards for the ZooKeeper dashboards.

And with that, you're done! Good job!
