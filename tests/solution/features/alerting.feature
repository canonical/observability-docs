@cos-lite
Feature: Alerting
  An alert rule supplied as configuration should reach Prometheus, fire when a
  metric crosses its threshold, and be delivered on to Alertmanager.

  The two scenarios are deliberately separate: a rule that fires in Prometheus
  but never reaches Alertmanager is a real and distinct failure, and merging
  them would hide which half broke.

  Scenario: A configured alert rule fires in Prometheus
    Given the solution has been deployed
    And an alert rule has been configured through cos-configuration
    When a sample crossing the rule's threshold is written to Prometheus
    Then Prometheus reports the alert as firing

  Scenario: The firing alert reaches Alertmanager
    Given the solution has been deployed
    And an alert rule has been configured through cos-configuration
    When a sample crossing the rule's threshold is written to Prometheus
    Then Alertmanager lists the alert as active
