# Security Hardening Guide

This page is an overview of how to configure COS securely.  While COS is designed with security in mind, some steps are required to ensure your COS is deployed and configured to ensure proper security.

## Secure your substrate

COS can only be as secure as what it is deployed on.  To ensure your substrate is as secure as possible, refer to any hardening guides provided by those layers.  For example, privileged users (both in Juju and the Kubernetes cluster) may be able to get shell access in the running units and inspect the file system.  It is recommended you review the following guides for hardening your substrate:
* [Juju Security](https://canonical-juju.readthedocs-hosted.com/en/latest/user/explanation/juju-security/)
* [Securing Charmed Kubernetes](https://ubuntu.com/kubernetes/charmed-k8s/docs/how-to-security)

## Secure COS

### Enable end-to-end encryption

For a secure deployment, it is recommended that COS be deployed with end-to-end encryption.  By default, the [cos-lite bundle](https://charmhub.io/cos-lite) deploys COS without encryption for simplicity, but COS can be configured with end-to-end encryption using the recommended TLS overlay.  See [COS and TLS](https://charmhub.io/topics/canonical-observability-stack/explanation/tls) for instructions.

### Manage the user accounts in Grafana

Grafana has built-in authentication and authorization features that can be leveraged for better security.  For example, user accounts can be created from within Grafana that have specific access (e.g. User1 can access Dashboard1, User2 access Dashboard2, etc).

By default, applications of Charmed Grafana are deployed with a single administrator account that has a randomly generated password and is able to view all dashboards.  It is recommended you:
* change this password as described [in the Grafana charm docs](https://github.com/canonical/grafana-k8s-operator?tab=readme-ov-file#web-interface)
* consider adding less-privileged accounts as needed (see the [official Grafana Docs](https://grafana.com/docs/grafana/latest/) for how to do this manually inside Grafana)

If you're using the Canonical Identity Platform to manage authentication, this could be used to manage Grafana user accounts directly.  See [the Hydra docs](https://charmhub.io/hydra/docs/how-to/integrate-oidc-compatible-charms) for more details.

### Be judicious about what is exposed via an ingress

Generally, some COS components must be exposed via ingress to other audiences for COS to work effectively.  Examples where this is necessary include:
* allowing applications to send metrics to COS when COS is deployed on a different substrate (as recommended by the [COS deployment best practices guide](https://charmhub.io/topics/canonical-observability-stack/reference/best-practices#deploy-in-isolation) 
* exposing Grafana dashboards outside the COS network

Whatever the reason, administrators should consider what should be exposed and to which audiences, and set up their ingresses accordingly.  For example:
* Loki, Prometheus, and Tempo are implemented without authentication, thus network access to these workloads should be restricted to trusted applications (for example, it is not secure to offer Prometheus through a public ingress)
* Grafana is configured with basic authentication.  This means it might be suitable for publishing through a public ingress, depending on the criticality of the data and your tolerance for risk

A COS deployment topology that follows the above guidelines is:
* COS is deployed on its own substrate.  All resources in COS are by default not accessible from other applications
* COS components that must be reachable by the applications they monitor (for example, Prometheus, Loki, and Tempo) are related to an ingress that makes them routable **from the monitored applications** (but not an unsecured network, like the public internet)
* Grafana is related to an ingress that is accessible by the users that need access to Grafana's dashboards.  For example, this could be an ingress routable only by users on a company VPN, or this could be an ingress on the public internet

For cases where:
* public ingress is required
* unauthenticated access cannot be allowed

It may be possible to secure the entire ingress with authentication.  For example, see the [basic authentication](https://charmhub.io/traefik-k8s/configurations#basic_auth_user) and [`forward_auth`](https://charmhub.io/traefik-k8s/configurations#enable_experimental_forward_auth) integrations on the Traefik charm.