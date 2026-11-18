import unittest

from app.config import check_daemon_url


class DaemonUrlTests(unittest.TestCase):
    def test_a_plain_http_public_daemon_is_refused(self):
        for url in [
            "http://node.wownero.example:34568",
            "http://node.example.org:34568",
            "http://93.184.216.34:34568",
            "node.example.org:34568",
        ]:
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                check_daemon_url(url)

    def test_own_daemons_are_accepted(self):
        for url in [
            "http://wownerod:34568",
            "http://127.0.0.1:34568",
            "http://192.168.1.20:34568",
            "http://10.0.0.5:34568",
            "http://host.docker.internal:34568",
            "https://node.example.org:34569",
            None,
        ]:
            with self.subTest(url=url):
                check_daemon_url(url)


class ShippedDefaultTests(unittest.TestCase):
    def test_no_shipped_file_defaults_to_a_plain_http_public_daemon(self):
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parents[2]
        pattern = re.compile(r"MONERO_DAEMON_URL(?::-|=)(http://[^}\s\"]+)")
        for name in ["docker-compose.yml", ".env.example", "api/.env.example"]:
            path = root / name
            if not path.exists():
                continue
            for url in pattern.findall(path.read_text()):
                with self.subTest(file=name, url=url):
                    check_daemon_url(url)


if __name__ == "__main__":
    unittest.main()
