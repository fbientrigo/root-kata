#!/usr/bin/env python3
"""
check_constraints.py — helper verification logic for GitHub Pages hosting constraints.
Supports:
  1. Checking WebAssembly binaries for shared memory flags (SharedArrayBuffer requirement)
  2. Checking GitHub Pages size limits (100MB per-file, 1GB total site)
  3. Validating captured network request logs (strict static same-origin check)
"""

import sys
import os
import json
import urllib.parse

def check_wasm_shared_memory(filepath):
    """
    Parses a WebAssembly binary or dynamic library to verify whether shared memory
    (which requires SharedArrayBuffer and COOP/COEP cross-origin isolation) is requested.
    Returns (has_shared_memory, message).
    """
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
            if header[:4] != b"\x00asm":
                raise ValueError("magic header mismatch")
            f.seek(8)
            data = f.read()

        offset = 0
        has_shared = False
        while offset < len(data):
            sec_id = data[offset]
            offset += 1
            # read leb128 section size
            size = 0
            shift = 0
            while offset < len(data):
                b = data[offset]
                offset += 1
                size |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
            sec_end = offset + size
            sec_data = data[offset:sec_end]
            offset = sec_end

            # Section 5: Memory Section
            if sec_id == 5:
                # count
                idx = 0
                count = 0
                shift = 0
                while idx < len(sec_data):
                    b = sec_data[idx]
                    idx += 1
                    count |= (b & 0x7F) << shift
                    if not (b & 0x80):
                        break
                    shift += 7
                for _ in range(count):
                    if idx >= len(sec_data):
                        break
                    flags = sec_data[idx]
                    idx += 1
                    if flags & 0x02:
                        has_shared = True
                    # skip min
                    while idx < len(sec_data) and (sec_data[idx] & 0x80):
                        idx += 1
                    idx += 1
                    if flags & 0x01:
                        # skip max
                        while idx < len(sec_data) and (sec_data[idx] & 0x80):
                            idx += 1
                        idx += 1

            # Section 2: Import Section
            elif sec_id == 2:
                idx = 0
                count = 0
                shift = 0
                while idx < len(sec_data):
                    b = sec_data[idx]
                    idx += 1
                    count |= (b & 0x7F) << shift
                    if not (b & 0x80):
                        break
                    shift += 7
                for _ in range(count):
                    if idx >= len(sec_data):
                        break
                    # mod len
                    mod_len = 0
                    shift = 0
                    while idx < len(sec_data):
                        b = sec_data[idx]
                        idx += 1
                        mod_len |= (b & 0x7F) << shift
                        if not (b & 0x80):
                            break
                        shift += 7
                    idx += mod_len
                    # field len
                    field_len = 0
                    shift = 0
                    while idx < len(sec_data):
                        b = sec_data[idx]
                        idx += 1
                        field_len |= (b & 0x7F) << shift
                        if not (b & 0x80):
                            break
                        shift += 7
                    idx += field_len
                    if idx >= len(sec_data):
                        break
                    kind = sec_data[idx]
                    idx += 1
                    if kind == 2:  # Memory import
                        flags = sec_data[idx]
                        idx += 1
                        if flags & 0x02:
                            has_shared = True
                        while idx < len(sec_data) and (sec_data[idx] & 0x80):
                            idx += 1
                        idx += 1
                        if flags & 0x01:
                            while idx < len(sec_data) and (sec_data[idx] & 0x80):
                                idx += 1
                            idx += 1
                    elif kind == 0:  # Function
                        while idx < len(sec_data) and (sec_data[idx] & 0x80):
                            idx += 1
                        idx += 1
                    elif kind == 1:  # Table
                        idx += 1  # element type
                        flags = sec_data[idx]
                        idx += 1
                        while idx < len(sec_data) and (sec_data[idx] & 0x80):
                            idx += 1
                        idx += 1
                        if flags & 0x01:
                            while idx < len(sec_data) and (sec_data[idx] & 0x80):
                                idx += 1
                            idx += 1
                    elif kind == 3:  # Global
                        idx += 2

        if has_shared:
            return True, "Shared memory flag detected in WebAssembly binary"
        return False, "No shared memory flags (single-threaded memory)"
    except Exception as e:
        raise RuntimeError(f"Could not inspect wasm: {e}") from e

def check_file_limits(target_dir):
    """
    Checks target_dir against published GitHub Pages limits:
      - 100 MB max per committed file (104,857,600 bytes)
      - 1 GB soft guidance total site size (1,073,741,824 bytes)
    """
    file_limit_bytes = 100 * 1024 * 1024
    site_limit_bytes = 1024 * 1024 * 1024

    total_bytes = 0
    largest_file = None
    largest_file_bytes = 0
    files_report = []

    for root, dirs, filenames in os.walk(target_dir):
        # Do not include test artifact output directories
        dirs[:] = [d for d in dirs if d not in ("hosting_verification", "chrome-profile", ".git")]
        for f in filenames:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, target_dir)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            total_bytes += size
            if size > largest_file_bytes:
                largest_file_bytes = size
                largest_file = rel_path
            files_report.append({
                "path": rel_path,
                "bytes": size,
                "mb": round(size / (1024 * 1024), 3),
                "exceeds_100mb": size > file_limit_bytes
            })

    files_report.sort(key=lambda x: x["bytes"], reverse=True)

    result = {
        "largest_file": largest_file,
        "largest_file_bytes": largest_file_bytes,
        "largest_file_mb": round(largest_file_bytes / (1024 * 1024), 3),
        "file_limit_bytes": file_limit_bytes,
        "file_limit_mb": 100.0,
        "file_limit_pass": largest_file_bytes <= file_limit_bytes,
        "total_site_bytes": total_bytes,
        "total_site_mb": round(total_bytes / (1024 * 1024), 3),
        "site_limit_bytes": site_limit_bytes,
        "site_limit_mb": 1024.0,
        "site_limit_pass": total_bytes <= site_limit_bytes,
        "files": files_report
    }
    return result

def validate_network_requests(requests_json_path, server_origin, target_dir):
    """
    Validates captured requests from Chromium:
      - Strictly same-origin (matches server_origin)
      - Only static file paths existing in target_dir (or harmless 404s like /favicon.ico)
      - No /api/run or compile-server requests
      - No cross-origin network requests
    """
    with open(requests_json_path, "r", encoding="utf-8") as f:
        requests = json.load(f)

    parsed_origin = urllib.parse.urlparse(server_origin)
    expected_netloc = parsed_origin.netloc

    violations = []
    allowed_requests = []

    for req in requests:
        raw_url = req.get("url", "")
        method = req.get("method", "GET")
        req_type = req.get("type", "Other")
        status = req.get("status")

        # Ignore data: or about: URLs if any
        if raw_url.startswith("data:") or raw_url.startswith("about:"):
            continue

        parsed = urllib.parse.urlparse(raw_url)

        # Cross-origin check
        if parsed.netloc != expected_netloc:
            violations.append(f"Cross-origin request prohibited: {raw_url} (origin {parsed.netloc} != {expected_netloc})")
            continue

        # Dynamic backend / API check
        path = parsed.path
        if "/api/" in path or "run" in path.split("/")[-1]:
            violations.append(f"Disallowed API/compile route requested: {raw_url}")
            continue

        # Check file existence on serving origin
        rel_path = path.lstrip("/")
        if rel_path == "":
            rel_path = "index.html"
        disk_path = os.path.join(target_dir, rel_path)

        if not os.path.exists(disk_path):
            if path == "/favicon.ico":
                # Standard browser probe, harmless static 404
                pass
            else:
                violations.append(f"Non-existent asset requested: {path} (not found in {target_dir})")

        allowed_requests.append({
            "url": raw_url,
            "path": path,
            "method": method,
            "type": req_type,
            "status": status
        })

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "total_requests": len(requests),
        "captured_requests": allowed_requests
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check_constraints.py <wasm|limits|network> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "wasm":
        filepath = sys.argv[2]
        shared, msg = check_wasm_shared_memory(filepath)
        print(json.dumps({"has_shared_memory": shared, "message": msg}))
        sys.exit(1 if shared else 0)

    elif cmd == "limits":
        target_dir = sys.argv[2]
        res = check_file_limits(target_dir)
        print(json.dumps(res, indent=2))
        sys.exit(0 if (res["file_limit_pass"] and res["site_limit_pass"]) else 1)

    elif cmd == "network":
        json_path = sys.argv[2]
        origin = sys.argv[3]
        target_dir = sys.argv[4]
        res = validate_network_requests(json_path, origin, target_dir)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["valid"] else 1)
    else:
        print(f"Unknown subcommand {cmd}")
        sys.exit(1)
