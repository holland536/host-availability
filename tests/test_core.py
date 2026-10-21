import socket
import unittest
import errno
from unittest.mock import patch

from host_availability.core import HostChecker, Result, Classification, _probe_one


class TestHostChecker(unittest.TestCase):
    def test_reachable(self):
        # Patch at the module level so create_connection is intercepted
        # before any real network call is attempted.
        fake_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with patch("host_availability.core.socket.create_connection",
                    return_value=fake_sock) as mock_conn:
            checker = HostChecker(timeout=0.5)
            result = checker.check(("127.0.0.1", 80))
        mock_conn.assert_called_once_with(("127.0.0.1", 80), timeout=0.5)
        fake_sock.close()
        self.assertEqual(result.classification, Classification.REACHABLE)
        self.assertEqual(result.host, "127.0.0.1")
        self.assertEqual(result.port, 80)
        self.assertEqual(result.detail, "")

    def test_timeout(self):
        with patch("host_availability.core.socket.create_connection",
                    side_effect=socket.timeout("timed out")):
            checker = HostChecker(timeout=0.01)
            result = checker.check(("10.255.255.1", 80))
        self.assertEqual(result.classification, Classification.TIMEOUT)
        self.assertEqual(result.detail, "timed out")

    def test_connection_refused_is_unreachable(self):
        err = OSError(errno.ECONNREFUSED, "Connection refused")
        with patch("host_availability.core.socket.create_connection",
                    side_effect=err):
            result = HostChecker(timeout=0.5).check(("127.0.0.1", 1))
        self.assertEqual(result.classification, Classification.UNREACHABLE)
        self.assertIn("refused", result.detail.lower())

    def test_host_unreachable_is_unreachable(self):
        err = OSError(errno.EHOSTUNREACH, "No route to host")
        with patch("host_availability.core.socket.create_connection",
                    side_effect=err):
            result = HostChecker(timeout=0.5).check(("192.0.2.99", 80))
        self.assertEqual(result.classification, Classification.UNREACHABLE)

    def test_unknown_errno_is_timeout(self):
        # EACCES (permission denied) is neither refusal nor host-unreachable.
        # The brief defines three buckets; we place unexpected errors in the
        # TIMEOUT bucket and preserve the original message in .detail.
        err = OSError(errno.EACCES, "Permission denied")
        with patch("host_availability.core.socket.create_connection",
                    side_effect=err):
            result = HostChecker(timeout=0.5).check(("10.0.0.1", 80))
        self.assertEqual(result.classification, Classification.TIMEOUT)
        self.assertIn("denied", result.detail.lower())

    def test_dns_failure_is_timeout(self):
        # socket.gaierror is a subclass of OSError; it carries no standard
        # errno, so it falls into the catch-all TIMEOUT bucket.
        err = socket.gaierror("Name or service not known")
        with patch("host_availability.core.socket.create_connection",
                    side_effect=err):
            result = HostChecker(timeout=0.5).check(("nonexistent.invalid", 80))
        self.assertEqual(result.classification, Classification.TIMEOUT)

    def test_port_zero_is_invalid(self):
        # Port 0 has platform-dependent semantics for connect(); we reject it
        # up front so the classification is stable across platforms.
        with patch("host_availability.core.socket.create_connection") as mock:
            result = HostChecker(timeout=0.5).check(("127.0.0.1", 0))
        mock.assert_not_called()
        self.assertEqual(result.classification, Classification.UNREACHABLE)
        self.assertEqual(result.detail, "invalid port")

    def test_check_many_returns_in_order(self):
        fake_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        refused = OSError(errno.ECONNREFUSED, "refused")
        with patch("host_availability.core.socket.create_connection",
                    side_effect=[fake_sock, refused]):
            results = HostChecker(timeout=0.5).check_many(
                [("127.0.0.1", 80), ("127.0.0.1", 1)]
            )
        fake_sock.close()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].classification, Classification.REACHABLE)
        self.assertEqual(results[1].classification, Classification.UNREACHABLE)

    def test_result_is_immutable(self):
        r = Result("h", 1, Classification.REACHABLE, "")
        with self.assertRaises(Exception):
            r.host = "other"  # type: ignore[misc]

    def test_invalid_timeout_rejected(self):
        with self.assertRaises(ValueError):
            HostChecker(timeout=0)
        with self.assertRaises(ValueError):
            HostChecker(timeout=-1)

    def test_default_timeout(self):
        checker = HostChecker()
        self.assertEqual(checker.timeout, 2.0)


if __name__ == "__main__":
    unittest.main()
