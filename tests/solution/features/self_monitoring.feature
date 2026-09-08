@cos-lite
Feature: COS Lite monitors itself
  A deployed COS Lite observes its own components: Prometheus scrapes them and
  Loki holds the logs they emit. Both are read through the same query APIs the
  signals scenarios use, so a failure here is about the deployment rather than
  about the query path.

  Scenario: Prometheus scrapes every COS Lite component
    Given the solution has been deployed
    Then Prometheus reports every COS Lite component as up

  Scenario: Loki holds the logs the components emit themselves
    Given the solution has been deployed
    Then Loki holds log lines emitted by the COS Lite components themselves
