# Migrate from LMA to COS Lite

COS Lite is not a new version of LMA, but a completely new product that draws upon the lessons learned from LMA to create a heavily integrated, mainly automated, turn-key observability stack. This means that there is no direct, in-place migration path.

```{warning}
This post describes how to migrate from LMA to COS with potentially destructive operations. Make sure you have up-to-date backups before attempting to migrate.
```

Let's assume this is our, heavily simplified, existing environment:

![image|600](assets/migrate-from-lma-to-cos-lite-1.png)

## 1. Upgrade your existing Juju controller

COS requires a Juju version `>=3.6`. Consult the [juju-cross-version-compatibility](https://documentation.ubuntu.com/juju/latest/reference/juju/juju-cross-version-compatibility/) docs to ensure your Juju controller is compatible before continuing. If necessary, [upgrade the Juju controller](https://documentation.ubuntu.com/juju/latest/howto/manage-controllers/#upgrade-a-controller) accordingly.

## 2. Deploy COS to an isolated MicroK8s instance

This model needs to be running Juju `>=3.6`. For instructions, see the [deploy COS on microk8s](https://documentation.ubuntu.com/observability/tutorial/installation/getting-started-with-cos-lite/) tutorial.

It will now look somewhat like this:

![image|600](assets/migrate-from-lma-to-cos-lite-2.png)

## 3. Deploy `cos-proxy` and `grafana-agent` in your pre-existing model

Deploy [COS Proxy](https://charmhub.io/cos-proxy) in your existing model and 
wire it up to all the same targets as you would with LMA. cos-proxy is designed 
to bridge the gap between your current LMA-enabled charms that utilize Filebeat, NRPE, and COS, which utilizes Prometheus and Loki/Promtail. 

Then deploy [Grafana Agent](https://charmhub.io/grafana-agent), and relate it to all your principal charms. By now, you will have something that looks a little something like this:

![image|600](assets/migrate-from-lma-to-cos-lite-3.png)

[COS Proxy](https://charmhub.io/cos-proxy) and [Grafana Agent](https://charmhub.io/grafana-agent) will continue to work on 
Juju 2.9 for the time being. This is mainly to support migrations from LMA 
to COS.

## 4. Evaluate solution parity

You'll now receive your telemetry in both LMA and COS. At this point, you should evaluate coverage for the checks and alarms you're used to when using LMA in COS before deciding to decomission LMA.

## 5. Decommission LMA

With COS Lite up and running, you can now start decommissioning your LMA setup. 

As it is a migration between solutions, none of your historical 
data, in LMA, will be migrated to COS. If this data is important,
retain pre-migration backups until they're no longer relevant.