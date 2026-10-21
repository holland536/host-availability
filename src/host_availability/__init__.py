# Host Availability Checker
#
# Probes a list of host-port pairs with short connect timeouts and returns
# reachable, unreachable, and timeout classifications.
#
# Interpretation decisions (stated plainly so users know what to expect):
#
#   - A connection that completes before the timeout is REACHABLE.
#   - A socket.error whose errno is ECONNREFUSED (111 on Linux) or EHOSTUNREACH
#     (113) is UNREACHABLE. Refused means the host is up but nothing is
#     listening; host-unreachable means the network layer cannot find the host.
#     These are distinguishable outcomes in practice and we surface both as
#     UNREACHABLE rather than inventing a fourth class the brief does not
#     mention.
#   - Everything else (timeout, DNS failure, permission denied, unexpected
#     errno) is TIMEOUT. This is deliberately coarse: the brief asks for three
#     buckets, and "something went wrong that is not a clean refusal" is the
#     bucket of last resort. The string form of the underlying error is
#     preserved in .detail for callers who need more.
#   - A port of 0 is treated as an invalid target and classified UNREACHABLE
#     with detail "invalid port" rather than passed to the socket layer,
#     because connect(2) semantics for port 0 vary by platform and should not
#     leak into the result.

from .core import HostChecker, Result, Classification

__all__ = ["HostChecker", "Result", "Classification"]
