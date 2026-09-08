#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Steps for features/signals.feature."""

import time
from typing import Callable

import httpx
import pytest
from cos_api import (
    IngestError,
    all_lines,
    logql_selector,
    loki_push,
    poll_until,
    promql_selector,
    remote_write_push,
    wait_for_samples,
    wait_for_streams,
)
from pytest_bdd import then, when

METRIC = "cos_solution_test_sample"
VALUE = 1234.5  # exactly representable in binary, so the round trip is exact
JOB = "cos-solution-tests"
LINE_COUNT = 3
INGEST_TIMEOUT = 120.0
PUSH_TIMEOUT = 180.0


def _push_until_accepted(push: Callable[[], None], message: str) -> None:
    """Retry a push: Loki answers HTTP 500 "at least 1 live replicas required" for up
    to a minute after going active. Repeats are safe, Loki drops duplicate entries and
    a resent sample keeps its timestamp."""
    last: list = [None]

    def attempt():
        try:
            push()
        except (IngestError, httpx.HTTPError) as exc:
            last[0] = exc
            return None
        return True

    try:
        poll_until(attempt, timeout=PUSH_TIMEOUT, message=message)
    except AssertionError as exc:
        raise AssertionError(
            f"{message}; last error: {type(last[0]).__name__}: {last[0]}"
        ) from exc


@when("a synthetic metric sample is remote-written to Prometheus", target_fixture="pushed_sample")
def a_synthetic_metric_sample_is_remote_written(prometheus, run_id: str) -> dict:
    labels = {"__name__": METRIC, "job": JOB, "run_id": run_id}
    _push_until_accepted(
        lambda: remote_write_push(
            prometheus, [(labels, VALUE)], timestamp_ms=int(time.time() * 1000)
        ),
        "Prometheus never accepted the synthetic remote-write sample",
    )
    return labels


@then("Prometheus returns that sample with the value and labels it was pushed with")
def prometheus_returns_that_sample(prometheus, run_id: str, pushed_sample: dict):
    selector = promql_selector(METRIC, run_id=run_id)
    samples = wait_for_samples(
        prometheus,
        selector,
        timeout=INGEST_TIMEOUT,
        message=f"remote-written sample {selector} never became queryable",
    )

    assert len(samples) == 1, f"expected one series for run_id={run_id!r}"
    sample = samples[0]
    assert sample.value == pytest.approx(VALUE), f"got {sample.value}, pushed {VALUE}"
    assert dict(sample.labels) == pushed_sample, (
        f"labels not preserved: {dict(sample.labels)}"
    )


@when("synthetic log lines are pushed to Loki", target_fixture="pushed_lines")
def synthetic_log_lines_are_pushed(loki, run_id: str) -> tuple:
    stream_labels = {"job": JOB, "run_id": run_id}
    base_ns = time.time_ns()
    entries = [
        (base_ns + index * 1_000_000, f"cos solution test line {index} run_id={run_id}")
        for index in range(LINE_COUNT)
    ]
    _push_until_accepted(
        lambda: loki_push(loki, [(stream_labels, entries)]),
        "Loki never accepted the synthetic log stream",
    )
    return stream_labels, entries


@then("Loki returns those lines with the stream labels they were pushed with")
def loki_returns_those_lines(loki, run_id: str, pushed_lines: tuple):
    stream_labels, entries = pushed_lines
    selector = logql_selector(job=JOB, run_id=run_id)
    streams = wait_for_streams(
        loki,
        selector,
        timeout=INGEST_TIMEOUT,
        message=f"pushed lines for {selector} never became queryable",
        predicate=lambda found: len(all_lines(found)) >= LINE_COUNT,
    )

    assert len(streams) == 1, f"expected one stream for run_id={run_id!r}"
    # Subset: Loki 3 adds service_name and detected_level labels of its own.
    returned = dict(streams[0].labels)
    assert stream_labels.items() <= returned.items(), (
        f"pushed labels {stream_labels} not preserved in returned labels {returned}"
    )
    assert set(streams[0].lines) == {line for _, line in entries}, (
        f"returned {sorted(streams[0].lines)}"
    )
