#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取公开订阅源 -> 去重 -> TCP 测活 -> 生成订阅文件

输出:
  output/sub.txt       明文节点列表(每行一个链接)
  output/sub_b64.txt   base64 订阅(v2ray/v2rayN/NekoBox 通用)
  output/stats.json    本次统计
"""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_FILE = os.path.join(ROOT, "sources.txt")
OUT_DIR = os.path.join(ROOT, "output")

UA = "v2rayN/6.0"
FETCH_TIMEOUT = 20
TEST_TIMEOUT = 3.0
TEST_WORKERS = 64

LINK_RE = re.compile(
    r"(?:vmess|vless|trojan|ss|ssr|hysteria2|hy2|tuic)://[^\s\"'<>\\]+", re.I
)


def log(*a):
    print(*a, flush=True)


def http_get(url: str, tries: int = 3) -> str:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            if i + 1 < tries:
                time.sleep(2 + i * 3)
    raise last


def _b64_pad(s: str) -> str:
    s = s.strip()
    return s + "=" * (-len(s) % 4)


def try_base64(text: str):
    """若整段内容是 base64 编码的链接列表, 解出来; 否则返回 None"""
    s = re.sub(r"\s+", "", text)
    if not s or len(s) < 16:
        return None
    try:
        decoded = base64.b64decode(_b64_pad(s), validate=False).decode("utf-8", "ignore")
    except Exception:
        return None
    return decoded if LINK_RE.search(decoded) else None


def extract_links(text: str):
    found = LINK_RE.findall(text)
    if found:
        return found
    decoded = try_base64(text)
    return LINK_RE.findall(decoded) if decoded else []


def endpoint(link: str):
    """返回 (host, port); 解析失败返回 (None, None)"""
    try:
        scheme, rest = link.split("://", 1)
        scheme = scheme.lower()
        if scheme == "vmess":
            payload = rest.split("#", 1)[0]
            data = json.loads(base64.b64decode(_b64_pad(payload)).decode("utf-8", "ignore"))
            host = str(data.get("add") or "").strip()
            port = int(str(data.get("port") or 0).strip() or 0)
            return (host or None, port or None)
        if scheme == "ssr":
            return (None, None)
        body = rest.split("#", 1)[0]
        if scheme == "ss" and "@" not in body:
            body = base64.b64decode(_b64_pad(body)).decode("utf-8", "ignore")
        u = urllib.parse.urlsplit("//" + body)
        return (u.hostname, u.port)
    except Exception:
        return (None, None)


def tcp_alive(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=TEST_TIMEOUT):
            return True
    except Exception:
        return False


def load_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    out = []
    with open(SOURCES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def main() -> int:
    sources = load_sources()
    log(f"[i] 订阅源 {len(sources)} 个")

    raw_links, per_source = [], {}
    for url in sources:
        try:
            text = http_get(url)
            links = extract_links(text)
            per_source[url] = len(links)
            raw_links.extend(links)
            log(f"    {len(links):5d}  <- {url}")
        except Exception as e:
            per_source[url] = f"ERR:{type(e).__name__}"
            log(f"    ERR   <- {url}  ({type(e).__name__})")

    # 去重(按链接原文, 保留首次出现顺序)
    seen, uniq = set(), []
    for link in raw_links:
        if link not in seen:
            seen.add(link)
            uniq.append(link)
    log(f"[i] 去重后 {len(uniq)} 个节点")

    # 端点表 + 并发测活
    eps = {}
    for link in uniq:
        host, port = endpoint(link)
        if host and port:
            eps.setdefault((host, port), []).append(link)

    log(f"[i] 待测端点 {len(eps)} 个")
    alive = set()
    with ThreadPoolExecutor(max_workers=TEST_WORKERS) as pool:
        futures = {pool.submit(tcp_alive, h, p): (h, p) for (h, p) in eps}
        done = 0
        for fut, key in futures.items():
            try:
                if fut.result():
                    alive.add(key)
            except Exception:
                pass
            done += 1
            if done % 200 == 0:
                log(f"    测活 {done}/{len(eps)} 通过 {len(alive)}")

    kept = [l for l in uniq if endpoint(l) in alive]
    log(f"[i] 测活通过 {len(alive)} 端点 -> 保留 {len(kept)} 个节点")

    os.makedirs(OUT_DIR, exist_ok=True)
    plain = "\n".join(kept) + ("\n" if kept else "")
    with open(os.path.join(OUT_DIR, "sub.txt"), "w", encoding="utf-8") as f:
        f.write(plain)
    with open(os.path.join(OUT_DIR, "sub_b64.txt"), "w", encoding="utf-8") as f:
        f.write(base64.b64encode(plain.encode("utf-8")).decode())

    stats = {
        "sources": len(sources),
        "per_source": per_source,
        "raw": len(raw_links),
        "unique": len(uniq),
        "endpoints": len(eps),
        "alive_endpoints": len(alive),
        "kept": len(kept),
    }
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    log("[ok] 完成 -> output/sub.txt, output/sub_b64.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
