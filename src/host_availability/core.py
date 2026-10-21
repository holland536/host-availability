import socket
import errno
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Tuple


class Classification(Enum):
    # Three buckets, no more. The brief asks for exactly these.
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class Result:
    # Immutable so callers can stash results without worrying about aliasing.
    host: str
    port: int
    classification: Classification
    detail: str


def _probe_one(host: str, port: int, timeout: float) -> Result:
    # Single-host probe. Kept as a module function (not a method) so that it
    # can be unit-tested in isolation if ever needed, and because it has no
    # dependency on HostChecker state.
    if port == 0:
        # Port 0 means "let the OS pick a port" for bind(); for connect() its
        # meaning is platform-dependent and never useful for an availability
        # probe. Fail fast with a stable classification instead of letting the
        # socket layer produce a surprising errno.
        return Result(host, port, Classification.UNREACHABLE, "invalid port")

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            # We do not send any data. A successful TCP handshake is the
            # entire signal; sending bytes would couple this probe to
            # application-layer behaviour we have no business testing.
            return Result(host, port, Classification.REACHABLE, "")
    except socket.timeout:
        # socket.timeout is a subclass of OSError, so we must catch it first.
        return Result(host, port, Classification.TIMEOUT, "timed out")
    except OSError as exc:
        # Map ECONNREFUSED and EHOSTUNREACH to UNREACHABLE; everything else
        # falls through to TIMEOUT as the catch-all third bucket.
        if exc.errno in (errno.ECONNREFUSED, errno.EHOSTUNREACH):
            return Result(host, port, Classification.UNREACHABLE, str(exc))
        return Result(host, port, Classification.TIMEOUT, str(exc))


class HostChecker:
    def __init__(self, timeout: float = 2.0) -> None:
        # The timeout is the only knob. We deliberately do not expose retries,
        # concurrency, or custom socket options — each would expand the test
        # surface and the brief asks for something small.
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout

    def check(self, target: Tuple[str, int]) -> Result:
        host, port = target
        return _probe_one(host, port, self.timeout)

    def check_many(self, targets: List[Tuple[str, int]]) -> List[Result]:
        # Sequential on purpose. Concurrency would add threading complexity
        # and make tests non-deterministic unless carefully faked. For the
        # intended scale (tens of hosts, short timeouts) sequential is fine.
        return [self.check(t) for t in targets]
