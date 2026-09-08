@cos-lite
Feature: Signals are ingested and queryable
  Metrics and logs written into COS Lite through its ingestion APIs come back
  out of its query APIs, with the values and labels they were written with.

  Each scenario tags its data with a run-unique label, so runs against the same
  deployment stay independent.

  Scenario: A metric written through the remote-write API can be queried back
    Given the solution has been deployed
    When a synthetic metric sample is remote-written to Prometheus
    Then Prometheus returns that sample with the value and labels it was pushed with

  Scenario: Log lines pushed to the Loki API can be queried back
    Given the solution has been deployed
    When synthetic log lines are pushed to Loki
    Then Loki returns those lines with the stream labels they were pushed with
