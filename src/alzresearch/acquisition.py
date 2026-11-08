"""Small, bounded downloader for explicitly selected public research files.

No archive extraction or external programs are used. Gzip integrity and the
expanded byte ceiling are checked by streaming to a fixed-size buffer.
"""

import contextlib
import dataclasses
import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Optional
import urllib.error
import urllib.parse
import urllib.request
import zlib


class AcquisitionError(RuntimeError):
    """A reproducible acquisition or validation failure."""


class LimitError(AcquisitionError):
    """A configured size, time, or free-space limit would be exceeded."""


@dataclasses.dataclass(frozen=True)
class Limits:
    max_file_bytes: int = 250_000_000
    max_total_bytes: int = 2_000_000_000
    max_expanded_bytes: int = 2_000_000_000
    timeout_seconds: float = 45
    max_elapsed_seconds: float = 300
    retries: int = 2
    min_interval_seconds: float = 1
    disk_reserve_bytes: int = 16_000_000

    def __post_init__(self):
        for name in ("max_file_bytes", "max_total_bytes", "max_expanded_bytes"):
            if getattr(self, name) <= 0:
                raise ValueError(name + " must be positive")
        if self.timeout_seconds <= 0 or self.max_elapsed_seconds <= 0:
            raise ValueError("timeouts must be positive")
        if self.retries < 0 or self.min_interval_seconds < 0 or self.disk_reserve_bytes < 0:
            raise ValueError("retries, interval, and disk reserve must be nonnegative")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_bytes(data_root: Path) -> int:
    """Count stored data including temporary files; count hardlinked bytes once.

    Package caches can hardlink the same inode at several paths. Counting those
    as repeated stored content would incorrectly exhaust a disk-storage budget.
    Symlink targets outside data_root are not followed.
    """
    total = 0
    seen = set()
    for path in Path(data_root).rglob('*'):
        if path.is_file() and not path.is_symlink():
            stat = path.stat()
            key = (stat.st_dev, stat.st_ino)
            if key not in seen:
                seen.add(key)
                total += stat.st_size
    return total


def _not_error_page(prefix: bytes, content_type: str = "") -> None:
    value = prefix.lstrip().lower()
    if ("text/html" in content_type.lower() or
            value.startswith((b"<!doctype html", b"<html", b"<head", b"<body")) or
            value.startswith((b"<?xml", b"<error", b"access denied", b"error:", b"404 not found"))):
        raise AcquisitionError("Response is an HTML/XML/error page, not a data file")


def validate_content(path: Path, *, max_expanded_bytes: int,
                     content_type: str = "", gzip_expected: Optional[bool] = None,
                     allow_html: bool = False, content_kind: Optional[str] = None) -> dict:
    """Reject error pages, truncated gzip streams, empty data, and expansion bombs."""
    path = Path(path)
    with path.open("rb") as handle:
        prefix = handle.read(4096)
    if not prefix:
        raise AcquisitionError("Empty data file")
    if not allow_html:
        _not_error_page(prefix, content_type)
    compressed = prefix.startswith(b"\x1f\x8b")
    if gzip_expected is True and not compressed:
        raise AcquisitionError("Expected gzip content, but gzip magic bytes are absent")
    expanded_bytes = 0
    if compressed:
        try:
            with gzip.open(path, "rb") as handle:
                first = True
                while True:
                    # Read one byte beyond the cap to detect overflow without a large allocation.
                    chunk = handle.read(min(65536, max_expanded_bytes - expanded_bytes + 1))
                    if not chunk:
                        break
                    expanded_bytes += len(chunk)
                    if expanded_bytes > max_expanded_bytes:
                        raise LimitError("Expanded gzip exceeds max_expanded_bytes=%d" % max_expanded_bytes)
                    if first:
                        if not allow_html:
                            _not_error_page(chunk)
                        prefix = chunk
                        first = False
            if not expanded_bytes:
                raise AcquisitionError("Gzip file contains no data")
        except (OSError, EOFError, zlib.error) as exc:
            raise AcquisitionError("Invalid or truncated gzip: %s" % exc) from exc
    else:
        expanded_bytes = path.stat().st_size
        if expanded_bytes > max_expanded_bytes:
            raise LimitError("Uncompressed file exceeds max_expanded_bytes")
    if content_kind not in (None, "geo_matrix"):
        raise ValueError("Unknown content_kind: %s" % content_kind)
    if content_kind == "geo_matrix" and not prefix.lstrip().startswith(
            (b"!Series_", b"!Sample_", b"!series_matrix_table_begin")):
        raise AcquisitionError("Data lacks expected GEO series-matrix metadata markers")
    return {"gzip": compressed, "expanded_bytes": expanded_bytes}


@contextlib.contextmanager
def _data_lock(root: Path):
    # Serializing downloads across processes is intentionally conservative: one
    # is below the allowed two, and makes aggregate byte accounting race-free.
    with (root / ".acquisition.lock").open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _rate_limit(lock_handle, seconds: float) -> None:
    lock_handle.seek(0)
    try:
        previous = float(lock_handle.read() or "0")
    except ValueError:
        previous = 0
    pause = max(0, seconds - (time.time() - previous))
    if pause:
        time.sleep(pause)
    lock_handle.seek(0)
    lock_handle.truncate()
    lock_handle.write(str(time.time()))
    lock_handle.flush()


def _inside(path: Path, root: Path) -> Path:
    path = path.absolute()
    if path.is_symlink():
        raise AcquisitionError("Refusing a symlink destination: %s" % path)
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise AcquisitionError("Destination must be inside data_root") from exc
    return path.resolve()


def _available(root: Path, limits: Limits, next_bytes: int, current_bytes=None) -> None:
    used = data_bytes(root) if current_bytes is None else current_bytes
    if used + next_bytes > limits.max_total_bytes:
        raise LimitError("Project data would exceed max_total_bytes=%d" % limits.max_total_bytes)
    if shutil.disk_usage(root).free < next_bytes + limits.disk_reserve_bytes:
        raise LimitError("Insufficient free disk space including configured reserve")


def download(url: str, destination: Path, *, accession: str, data_root: Path,
             limits: Limits = Limits(), provenance_path: Optional[Path] = None,
             allow_html: bool = False, content_kind: Optional[str] = None) -> dict:
    """Download one selected URL, or verify an already acquired copy.

    Existing files without matching provenance are never silently overwritten.
    Raises AcquisitionError/LimitError on failure; callers should record these.
    The provenance sidecar contains exact source/final URLs, UTC retrieval time,
    byte count, SHA-256, HTTP headers, and compressed-content validation results.
    """
    if urllib.parse.urlsplit(url).scheme not in ("https", "http"):
        raise AcquisitionError("Only public HTTP(S) download URLs are supported")
    root = Path(data_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = _inside(Path(destination), root)
    provenance = _inside(Path(provenance_path) if provenance_path else
                         destination.with_name(destination.name + ".provenance.json"), root)
    if provenance == destination:
        raise AcquisitionError("Data and provenance destinations must differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    provenance.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    provenance_part = provenance.with_name(provenance.name + ".part")
    for temporary in (part, provenance_part):
        _inside(temporary, root)
    with _data_lock(root) as lock_handle:
        _available(root, limits, 0)
        if destination.exists():
            if not provenance.exists():
                raise AcquisitionError("Existing file lacks provenance; refusing overwrite")
            try:
                record = json.loads(provenance.read_text())
            except (OSError, ValueError) as exc:
                raise AcquisitionError("Cannot read existing provenance: %s" % exc) from exc
            if not isinstance(record, dict):
                raise AcquisitionError("Existing provenance is not a JSON object")
            if (record.get("url") != url or record.get("accession") != accession or
                    record.get("sha256") != sha256_file(destination) or
                    record.get("byte_count") != destination.stat().st_size or
                    record.get("local_path") != str(destination.relative_to(root.parent))):
                raise AcquisitionError("Existing file/provenance mismatch; refusing overwrite")
            if destination.stat().st_size > limits.max_file_bytes:
                raise LimitError("Existing file exceeds current max_file_bytes")
            # A later generic cache check must not weaken the original format
            # check. Keep retrieval provenance immutable and record the current
            # cache check separately, including any newly requested stricter kind.
            effective_kind = content_kind or record.get("content_kind")
            validation = validate_content(
                destination, max_expanded_bytes=limits.max_expanded_bytes,
                gzip_expected=destination.name.lower().endswith(".gz"),
                allow_html=allow_html, content_kind=effective_kind)
            return dict(record, status="cached", cache_validation=dict(
                validation, content_kind=effective_kind, allow_html=allow_html))
        # A previous interrupted run may have left only its own temporary files.
        for temporary in (part, provenance_part):
            if temporary.exists():
                temporary.unlink()
        last_error = None
        for attempt in range(limits.retries + 1):
            _rate_limit(lock_handle, limits.min_interval_seconds)
            started = time.monotonic()
            request = urllib.request.Request(url, headers={
                "User-Agent": "alzheimers-research-feasibility/0.1 (bounded public data acquisition)",
                "Accept-Encoding": "identity",
            })
            try:
                with urllib.request.urlopen(request, timeout=limits.timeout_seconds) as response:
                    headers = dict(response.headers.items())
                    content_type = response.headers.get("Content-Type", "")
                    length_header = response.headers.get("Content-Length")
                    expected_bytes = None
                    if length_header is not None:
                        try:
                            expected_bytes = int(length_header)
                        except ValueError as exc:
                            raise AcquisitionError("Invalid Content-Length header") from exc
                        if expected_bytes < 0:
                            raise AcquisitionError("Negative Content-Length header")
                        if expected_bytes > limits.max_file_bytes:
                            raise LimitError("Content-Length exceeds max_file_bytes=%d" % limits.max_file_bytes)
                        _available(root, limits, expected_bytes)
                    written = 0
                    # The data lock serializes managed downloads. Account for
                    # streamed growth directly rather than rescanning thousands
                    # of cached runtime files for every 64 KB chunk. Completion
                    # performs a fresh total check before writing provenance.
                    bytes_at_start = data_bytes(root)
                    digest = hashlib.sha256()
                    with part.open("wb") as output:
                        while True:
                            if time.monotonic() - started > limits.max_elapsed_seconds:
                                raise LimitError("Download exceeded max_elapsed_seconds")
                            chunk = response.read(min(65536, limits.max_file_bytes - written + 1))
                            if not chunk:
                                break
                            if not written and not allow_html:
                                _not_error_page(chunk, content_type)
                            if written + len(chunk) > limits.max_file_bytes:
                                raise LimitError("Streaming response exceeds max_file_bytes=%d" % limits.max_file_bytes)
                            _available(root, limits, len(chunk), bytes_at_start + written)
                            output.write(chunk)
                            output.flush()
                            digest.update(chunk)
                            written += len(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    if expected_bytes is not None and written != expected_bytes:
                        raise AcquisitionError("Content-Length mismatch: expected %d, obtained %d" %
                                               (expected_bytes, written))
                    validation = validate_content(
                        part, max_expanded_bytes=limits.max_expanded_bytes,
                        content_type=content_type,
                        gzip_expected=destination.name.lower().endswith(".gz"),
                        allow_html=allow_html, content_kind=content_kind)
                    record = {
                        "accession": accession, "url": url,
                        "final_url": response.geturl(),
                        "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "local_path": str(destination.relative_to(root.parent)),
                        "byte_count": written, "sha256": digest.hexdigest(),
                        "http_status": getattr(response, "status", None),
                        "http_headers": headers,
                        "content_kind": content_kind,
                        "allow_html": allow_html,
                        "validation": validation,
                    }
                    encoded = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
                    _available(root, limits, len(encoded))
                    provenance_part.write_bytes(encoded)
                    # Complete data first. A crash between these renames leaves a
                    # file lacking provenance, which is a visible blocker on rerun.
                    os.replace(part, destination)
                    os.replace(provenance_part, provenance)
                    return dict(record, status="downloaded")
            except urllib.error.HTTPError as exc:
                last_error = "HTTP %d %s for %s" % (exc.code, exc.reason, url)
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
                if not retryable or attempt == limits.retries:
                    raise AcquisitionError(last_error) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_error = "%s: %s for %s" % (type(exc).__name__, exc, url)
                if attempt == limits.retries:
                    raise AcquisitionError(last_error) from exc
            finally:
                for temporary in (part, provenance_part):
                    if temporary.exists():
                        temporary.unlink()
            time.sleep(min(2 ** attempt, 8))
        raise AcquisitionError(last_error or "Download failed")
