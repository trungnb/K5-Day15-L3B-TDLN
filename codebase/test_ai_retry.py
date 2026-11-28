"""ai.post_json thử lại khi API model quá tải / lỗi tạm (429, 5xx, mất kết nối) — chuẩn bị demo 28/11, nhiều BS
nhắn cùng lúc. Lỗi khác (400, 401, 403…) và hết giờ chờ báo ngay, không thử lại."""
import io
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai  # noqa: E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http(code):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b'{"error": "x"}'))


class PostJsonRetry(unittest.TestCase):
    def _run(self, *outcomes):
        calls = []

        def fake_urlopen(req, timeout):
            calls.append(1)
            o = outcomes[len(calls) - 1]
            if isinstance(o, Exception):
                raise o
            return _Resp(b'{"ok": 1}')
        old_open, old_sleep = ai.urllib.request.urlopen, ai.time.sleep
        ai.urllib.request.urlopen, ai.time.sleep = fake_urlopen, (lambda s: None)
        try:
            return ai.post_json("https://example.invalid/u", {}, {}), len(calls)
        except RuntimeError as e:
            return e, len(calls)
        finally:
            ai.urllib.request.urlopen, ai.time.sleep = old_open, old_sleep

    def test_transient_errors_are_retried(self):
        for err in (_http(429), _http(500), _http(503), urllib.error.URLError("reset")):
            self.assertEqual(self._run(err, None), ({"ok": 1}, 2), err)

    def test_gives_up_after_three_attempts(self):
        res, n = self._run(_http(429), _http(429), _http(429))
        self.assertIsInstance(res, RuntimeError)
        self.assertIn("HTTP 429", str(res))
        self.assertEqual(n, 3)

    def test_client_errors_and_timeouts_are_not_retried(self):
        for err in (_http(400), _http(401), _http(403)):
            res, n = self._run(err, None)
            self.assertIsInstance(res, RuntimeError, err)
            self.assertEqual(n, 1, err)
        with self.assertRaises(TimeoutError):
            self._run(TimeoutError("timed out"), None)


if __name__ == "__main__":
    unittest.main()
