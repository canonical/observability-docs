#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
"""Ingest, query and wait helpers for the COS solution tests.

Every function takes an `httpx.Client` bound to one application's base URL.
`get_tls_context` is duplicated from tests/integration/helpers.py because the
two test trees cannot import each other.
"""
import ssl
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple

import httpx
import jubilant

REMOTE_WRITE_PATH = "/api/v1/write"
LOKI_PUSH_PATH = "/loki/api/v1/push"
LOOKBACK_NS = 5 * 60 * 1_000_000_000
GRACE_NS = 60 * 1_000_000_000
QUERY_LIMIT = 1000


def get_tls_context(
    temp_path: Path, juju: jubilant.Juju, ca_name: str
) -> Optional[ssl.SSLContext]:
    """Return an SSLContext trusting `ca_name`'s CA, or None if it is not deployed."""
    if ca_name not in juju.status().apps:
        return None

    cert_path = temp_path / "ca.pem"
    task = juju.run(f"{ca_name}/0", "get-ca-certificate")
    cert_path.write_text(task.results["ca-certificate"])

    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cert_path)
    return ctx


def poll_until(
    fn: Callable[[], Any], *, timeout: float, interval: float = 2.0, message: str
) -> Any:
    """Call `fn` until it returns a truthy value; an exception counts as not ready.

    Raises AssertionError quoting `message` and the last observation on timeout.
    """
    if timeout < 0:
        raise ValueError("timeout must be >= 0")
    if interval <= 0:
        raise ValueError("interval must be > 0")

    deadline = time.monotonic() + timeout
    detail = "<never called>"
    attempts = 0
    while True:
        attempts += 1
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            detail = f"{type(exc).__name__}: {exc}"
        else:
            if result:
                return result
            detail = repr(result)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(
                f"{message} (timed out after {timeout:g}s, {attempts} attempt(s); "
                f"last observed: {detail})"
            )
        time.sleep(min(interval, remaining))


class IngestError(AssertionError):
    """A push was rejected by Prometheus or Loki."""


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _tag(field: int, wire_type: int) -> bytes:
    return _varint((field << 3) | wire_type)


def _delimited(field: int, payload: bytes) -> bytes:
    return _tag(field, 2) + _varint(len(payload)) + payload


def _string(field: int, value: str) -> bytes:
    return _delimited(field, value.encode("utf-8"))


def encode_write_request(
    series: Sequence[Tuple[Mapping[str, str], float]], timestamp_ms: int
) -> bytes:
    """Encode a Prometheus remote-write WriteRequest without a protobuf runtime.

    WriteRequest{repeated TimeSeries timeseries = 1},
    TimeSeries{repeated Label labels = 1; repeated Sample samples = 2},
    Label{string name = 1; string value = 2},
    Sample{double value = 1; int64 timestamp = 2}.
    """
    if not series:
        raise ValueError("remote_write_push needs at least one series")
    body = bytearray()
    for index, (labels, value) in enumerate(series):
        if not labels:
            raise ValueError(f"series[{index}] has no labels")
        if "__name__" not in labels:
            raise ValueError(f"series[{index}] has no '__name__' label: {sorted(labels)}")
        timeseries = bytearray()
        # Remote write requires labels sorted by name.
        for name in sorted(labels):
            timeseries += _delimited(1, _string(1, name) + _string(2, str(labels[name])))
        timeseries += _delimited(
            2, _tag(1, 1) + struct.pack("<d", float(value)) + _tag(2, 0) + _varint(timestamp_ms)
        )
        body += _delimited(1, bytes(timeseries))
    return bytes(body)


def snappy_compress(data: bytes) -> bytes:
    """Encode `data` as a snappy block holding one literal run, valid for any decoder."""
    out = bytearray(_varint(len(data)))
    if not data:
        return bytes(out)
    if len(data) <= 60:
        out.append((len(data) - 1) << 2)
    else:
        extra = len(data) - 1
        width = (extra.bit_length() + 7) // 8
        out.append((59 + width) << 2)
        out += extra.to_bytes(width, "little")
    return bytes(out + data)


def remote_write_push(
    client: httpx.Client,
    series: List[Tuple[Mapping[str, str], float]],
    timestamp_ms: Optional[int] = None,
) -> None:
    """POST snappy-compressed protobuf to Prometheus /api/v1/write."""
    stamp = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    payload = snappy_compress(encode_write_request(series, stamp))
    response = client.post(
        REMOTE_WRITE_PATH,
        content=payload,
        headers={
            "Content-Encoding": "snappy",
            "Content-Type": "application/x-protobuf",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        },
    )
    if not response.is_success:
        raise IngestError(
            f"remote-write push to {response.url} returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )


def loki_push(
    client: httpx.Client, streams: List[Tuple[Mapping[str, str], List[Tuple[int, str]]]]
) -> None:
    """POST to Loki /loki/api/v1/push."""
    if not streams:
        raise ValueError("loki_push needs at least one stream")
    body: dict = {"streams": []}
    for index, (labels, values) in enumerate(streams):
        if not labels:
            raise ValueError(f"streams[{index}] has no stream labels")
        if not values:
            raise ValueError(f"streams[{index}] has no log lines")
        body["streams"].append(
            {
                "stream": {str(k): str(v) for k, v in labels.items()},
                # Strings: JSON numbers would lose nanosecond precision.
                "values": [[str(int(ts)), line] for ts, line in values],
            }
        )
    response = client.post(LOKI_PUSH_PATH, json=body)
    if not response.is_success:
        raise IngestError(
            f"loki push to {response.url} returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )


class QueryError(AssertionError):
    """A query did not return a well-formed successful result."""


@dataclass(frozen=True)
class Sample:
    """One element of a Prometheus instant vector."""

    labels: Mapping[str, str]
    value: float


@dataclass(frozen=True)
class Stream:
    """One Loki stream: its labels and its (nanosecond, line) entries."""

    labels: Mapping[str, str]
    entries: Tuple[Tuple[int, str], ...]

    @property
    def lines(self) -> Tuple[str, ...]:
        return tuple(line for _, line in self.entries)


def _matchers(labels: Mapping[str, str]) -> str:
    return ",".join(
        '{}="{}"'.format(name, value.replace("\\", "\\\\").replace('"', '\\"'))
        for name, value in sorted(labels.items())
    )


def promql_selector(metric: str, **labels: str) -> str:
    return f"{metric}{{{_matchers(labels)}}}" if labels else metric


def logql_selector(**labels: str) -> str:
    return "{" + _matchers(labels) + "}"


def _successful_body(response: httpx.Response, what: str) -> dict:
    if response.status_code != 200:
        raise QueryError(f"{what} -> HTTP {response.status_code}: {response.text[:400]}")
    try:
        body = response.json()
    except ValueError as exc:
        raise QueryError(f"{what} -> non-JSON body: {response.text[:400]}") from exc
    if not isinstance(body, dict) or body.get("status") != "success":
        raise QueryError(f"{what} -> {str(body)[:400]}")
    return body


def instant_query(client: httpx.Client, query: str) -> List[Sample]:
    """GET /api/v1/query and return the instant vector."""
    response = client.get("/api/v1/query", params={"query": query})
    data = _successful_body(response, f"PromQL {query!r}").get("data") or {}
    if data.get("resultType") != "vector":
        raise QueryError(f"PromQL {query!r} -> resultType={data.get('resultType')!r}")
    try:
        return [
            Sample(dict(item.get("metric") or {}), float(item["value"][1]))
            for item in data.get("result") or []
        ]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise QueryError(
            f"PromQL {query!r} -> malformed vector: {data.get('result')!r}"
        ) from exc


def loki_query_range(
    client: httpx.Client, query: str, *, start_ns: int, end_ns: int
) -> List[Stream]:
    """GET /loki/api/v1/query_range and return the streams."""
    response = client.get(
        "/loki/api/v1/query_range",
        params={
            "query": query,
            "start": str(start_ns),
            "end": str(end_ns),
            "limit": str(QUERY_LIMIT),
            "direction": "backward",
        },
    )
    data = _successful_body(response, f"LogQL {query!r}").get("data") or {}
    if data.get("resultType") != "streams":
        raise QueryError(f"LogQL {query!r} -> resultType={data.get('resultType')!r}")
    try:
        # Loki 3 appends structured metadata as a third element of each entry.
        return [
            Stream(
                dict(item.get("stream") or {}),
                tuple((int(v[0]), str(v[1])) for v in item.get("values") or []),
            )
            for item in data.get("result") or []
        ]
    except (IndexError, TypeError, ValueError) as exc:
        raise QueryError(
            f"LogQL {query!r} -> malformed streams: {data.get('result')!r}"
        ) from exc


def group_by_label(samples: Iterable[Sample], label: str) -> dict:
    """Bucket samples by one label value, dropping samples that lack the label."""
    grouped: dict = {}
    for sample in samples:
        value = sample.labels.get(label)
        if value is not None:
            grouped.setdefault(value, []).append(sample)
    return grouped


def all_lines(streams: Iterable[Stream]) -> Tuple[str, ...]:
    return tuple(line for stream in streams for line in stream.lines)


def _describe(observed: Any) -> str:
    if isinstance(observed, BaseException):
        return f"{type(observed).__name__}: {observed}"
    if not observed:
        return "no results"
    if isinstance(observed[0], Sample):
        return "; ".join(f"{dict(s.labels)}={s.value}" for s in observed[:12])
    return "; ".join(f"{dict(s.labels)} x{len(s.entries)}" for s in observed[:6])


def wait_for_samples(
    client: httpx.Client,
    query: str,
    *,
    timeout: float,
    message: str,
    predicate: Callable[[List[Sample]], bool] = bool,
) -> List[Sample]:
    """Poll an instant query until `predicate` holds, then return the samples."""
    last: list = [None]

    def probe():
        try:
            samples = instant_query(client, query)
        except (QueryError, httpx.HTTPError) as exc:
            last[0] = exc
            return None
        last[0] = samples
        return samples if predicate(samples) else None

    try:
        return poll_until(probe, timeout=timeout, message=message)
    except AssertionError as exc:
        raise QueryError(f"{message} | {query} | last: {_describe(last[0])}") from exc


def wait_for_streams(
    client: httpx.Client,
    query: str,
    *,
    timeout: float,
    message: str,
    lookback_ns: int = LOOKBACK_NS,
    predicate: Callable[[List[Stream]], bool] = bool,
) -> List[Stream]:
    """Poll a Loki range query until `predicate` holds, then return the streams."""
    last: list = [None]

    def probe():
        # The window moves with each probe so lines pushed during the wait are included.
        end_ns = time.time_ns() + GRACE_NS
        try:
            streams = loki_query_range(
                client, query, start_ns=end_ns - lookback_ns, end_ns=end_ns
            )
        except (QueryError, httpx.HTTPError) as exc:
            last[0] = exc
            return None
        last[0] = streams
        return streams if predicate(streams) else None

    try:
        return poll_until(probe, timeout=timeout, message=message)
    except AssertionError as exc:
        raise QueryError(f"{message} | {query} | last: {_describe(last[0])}") from exc
