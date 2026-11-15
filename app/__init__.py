"""LangChain FastAPI Hugging Face Chatbot Application."""
import sys
import types
import hashlib

# Compatibility shim for environments where native xxhash C-extensions are blocked by AppLocker/security policies
try:
    import xxhash  # noqa: F401
except Exception:
    fake_xxhash = types.ModuleType("xxhash")

    class _HashWrapper:
        def __init__(self, data=b""):
            self._h = hashlib.sha256(data if isinstance(data, (bytes, bytearray)) else str(data).encode())

        def digest(self):
            return self._h.digest()[:16]

        def hexdigest(self):
            return self._h.hexdigest()[:32]

        def intdigest(self):
            return int.from_bytes(self.digest(), "big")

    def _make_hash(d=b""):
        return _HashWrapper(d)

    fake_xxhash.xxh3_128 = _make_hash
    fake_xxhash.xxh128 = _make_hash
    fake_xxhash.xxh3_64 = _make_hash
    fake_xxhash.xxh64 = _make_hash
    fake_xxhash.xxh32 = _make_hash
    fake_xxhash.algorithms_available = {"xxh32", "xxh64", "xxh3_64", "xxh128", "xxh3_128"}
    sys.modules["xxhash"] = fake_xxhash

__version__ = "1.0.0"
