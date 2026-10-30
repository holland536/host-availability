# host-availability

Probes a list of host-port pairs with short connect timeouts and returns reachable, unreachable, and timeout classifications.

```python
from host_availability import HostChecker, Result, Classification

checker = HostChecker(timeout=2.0)
results = checker.check_many([("127.0.0.1", 80), ("10.0.0.1", 443)])
for r in results:
    print(r.host, r.port, r.classification.value, r.detail)
```

`HostChecker(timeout)` takes a single positive float. `check((host, port))` returns a `Result`; `check_many` returns a list in input order. `Result` has `host`, `port`, `classification` (a `Classification` enum: `REACHABLE`, `UNREACHABLE`, `TIMEOUT`), and `detail` (a string holding the underlying error message or "" on success).

## Why

This exists because the three outcomes a probe actually produces — reachable, refused/unreachable, and timed-out — are what callers act on, and wrapping `socket.create_connection` with that mapping is ten lines people keep rewriting badly. The trade-off: classification is coarse. `ECONNREFUSED` and `EHOSTUNREACH` both collapse into `UNREACHABLE`; DNS failures, permission errors, and anything unexpected collapses into `TIMEOUT`. The original error string is preserved in `.detail` for callers who need finer granularity, but the three-bucket API stays simple.

## Edge cases

Port 0 is rejected up front as `UNREACHABLE` with `detail="invalid port"` rather than passed to the socket layer, where its meaning varies by platform. A timeout value of zero or negative raises `ValueError` at construction. Probes are sequential; if you need concurrency, wrap the calls yourself.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

