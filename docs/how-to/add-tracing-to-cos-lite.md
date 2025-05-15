# Add tracing to COS Lite

If you have an existing COS Lite deployment and you wish to add tracing 
capabilities to it, you can follow the few steps below.

## Deploy the Tempo Coordinator

In the same Juju model as you have COS Lite deployed, deploy the ``tempo-coordinator-k8s`` app
using the following command: 

```bash
$ juju deploy tempo-coordinator-k8s tempo \
    --channel edge \
    --trust
```

While you can pick any arbitrary name, we recommend that you name your 
`tempo-coordinator-k8s` app `tempo`, as that will act as the single entry 
point to the Tempo deployment as a whole. You will never have to interact 
with the worker nodes directly.
    
## Deploy the Tempo Worker

```bash    
$ juju deploy tempo-worker-k8s tempo-worker \
    --channel edge \
    --trust
```

In this tutorial we deploy the 'monolithic' version of `tempo`, where a 
single worker node is assigned all the roles. For alternative deployment 
modes and a migration guide, refer to  [this post on Discourse](https://discourse.charmhub.io/t/cos-lite-docs-managing-deployments-of-cos-lite-ha-addons/15213).

## Integrate with s3

Tempo uses object storage for storing traces and the charm consequently 
requires an s3 integration.

If you don't have an s3 bucket ready at hand, follow [this guide](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio-for-s3-testing/15211) to deploy Minio in your testing environment.

Once you're done deploying ``minio`` and ``s3``, you can run:

```bash
$ juju integrate tempo s3
```

And wait for the `tempo` application to go to `active/idle`.


## Integrate coordinator and workers

```bash    
$ juju integrate tempo tempo-worker
```

At this point your `juju status` should look like this:

![image|690x181](assets/add-tracing-support-to-cos-lite.png)


```{note}
Coordinator is reporting 'degraded' because not all roles are assigned in the recommended number (see [this open bug](https://github.com/canonical/cos-lib/issues/42) for progress on making the status message more informative).
```

## Integrate with COS Lite

You can enable self-monitoring for ``tempo`` by integrating it with the other COS Lite components.
 
```bash
$ juju integrate loki:logging tempo:logging
$ juju integrate s3:s3-credentials tempo:s3
$ juju integrate tempo:grafana-dashboard grafana:grafana-dashboard
$ juju integrate tempo:grafana-source grafana:grafana-source
$ juju integrate tempo:metrics-endpoint prometheus:metrics-endpoint
$ juju integrate tempo:tempo-cluster tempo-worker:tempo-cluster
$ juju integrate traefik:traefik-route tempo:ingress
```

Similarly, you can enable tracing in COS Lite by integrating the COS Lite charms that support 
it to `tempo` over the `tracing` relation:

```bash 
$ juju integrate tempo:tracing alertmanager:tracing
$ juju integrate tempo:tracing catalogue:tracing
$ juju integrate tempo:tracing traefik:charm-tracing
$ juju integrate tempo:tracing traefik:workload-tracing
$ juju integrate tempo:tracing loki:charm-tracing
$ juju integrate tempo:tracing loki:workload-tracing
$ juju integrate tempo:tracing grafana:charm-tracing
$ juju integrate tempo:tracing grafana:workload-tracing
$ juju integrate tempo:tracing prometheus:charm-tracing
$ juju integrate tempo:tracing prometheus:workload-tracing
```

```{note}
You can also achieve the same by running ``jhack imatrix fill``.
```

## Integrate with a CA

If you have a charm offering a `certificates` endpoint such as [`self-signed-certificates`](https://charmhub.io/self-signed-certificates), you can integrate it with `tempo`:

```bash
$ juju integrate tempo:certificates ca:certificates 
```

to enable traces to be sent to `tempo` over HTTPS (or gRPCs).

```{note}
For this to work, Tempo needs to trust the same CA as Traefik. If you're 
using different certificate authorities to provide certificates to Tempo and Traefik, you'll 
need to integrate the CA charms with ``cert-transfer``.
```
