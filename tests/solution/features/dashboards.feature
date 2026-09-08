@cos-lite
Feature: Grafana dashboards
  Grafana should accept a dashboard and give it back unchanged, should list the
  datasources its grafana-source integrations create, and should actually be
  able to reach each of those datasources.

  Nothing else in this repo exercises the Grafana API, so a Grafana that comes
  up active while unable to reach Prometheus currently looks healthy.

  Scenario: A dashboard can be created and read back
    Given the solution has been deployed
    When a dashboard is created through the Grafana API
    Then the dashboard reads back with the same title and panels

  Scenario: The configured datasources are listed
    Given the solution has been deployed
    Then Grafana lists a Prometheus, a Loki and an Alertmanager datasource

  Scenario: Each datasource answers a query through its proxy
    Given the solution has been deployed
    Then a query through each datasource proxy returns a well-formed result
