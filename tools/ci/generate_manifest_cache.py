# -*- coding: utf-8 -*-
"""
生成初始 manifest 缓存

在打包时调用，将远程 manifest 的时间戳信息保存到本地，
使用户首次启动时可以跳过不必要的检查。
"""

import json
import urllib.error
import urllib.request
from pathlib import Path


API_BASE_URL = "https://api.1999.fan/api"
MANIFEST_URL = f"{API_BASE_URL}/manifest.json"
REQUEST_TIMEOUT = 10

# 忽略的目录（不需要热更新）
IGNORED_DIRS = {"images"}


def _fetch_json(opener, url: str) -> dict:
    with opener.open(url, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _collect_all_manifests(opener, manifest_path: str, collected: dict):
    url = f"{API_BASE_URL}/{manifest_path}"
    print(f"  Fetching: {manifest_path}")

    try:
        manifest = _fetch_json(opener, url)
        collected[manifest_path] = manifest.get("updated", 0)

        for dir_info in manifest.get("directories", []):
            sub_manifest = dir_info.get("manifest", "")
            if sub_manifest:
                _collect_all_manifests(opener, sub_manifest, collected)
    except Exception as e:
        print(f"  Warning: Failed to fetch {manifest_path}: {e}")


def generate_manifest_cache(output_dir: Path) -> bool:
    try:
        print(f"Fetching root manifest from {MANIFEST_URL}...")

        # CI 环境中尽量避免代理导致的国内网络问题
        no_proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(no_proxy_handler)

        root_manifest = _fetch_json(opener, MANIFEST_URL)

        cache = {
            "root_updated": root_manifest.get("updated", 0),
            "manifests": {"manifest.json": root_manifest.get("updated", 0)},
        }

        print("Collecting all sub-manifests...")
        for dir_info in root_manifest.get("directories", []):
            dir_name = dir_info["name"]

            if dir_name in IGNORED_DIRS:
                print(f"  Skipping ignored directory: {dir_name}")
                continue

            sub_manifest = dir_info.get("manifest", "")
            if sub_manifest:
                _collect_all_manifests(opener, sub_manifest, cache["manifests"])

        output_dir.mkdir(parents=True, exist_ok=True)

        cache_file = output_dir / "manifest_cache.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

        print(f"\nGenerated manifest cache: {cache_file}")
        print(f"  root_updated: {cache['root_updated']}")
        print(f"  Total manifests cached: {len(cache['manifests'])}")
        return True

    except urllib.error.URLError as e:
        print(f"Warning: Failed to fetch manifest (URL error): {e}")
        print("Skipping manifest cache generation.")
        return False
    except Exception as e:
        print(f"Warning: Failed to generate manifest cache: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        # 默认输出到 install/config
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / "install" / "config"

    success = generate_manifest_cache(output_dir)
    sys.exit(0 if success else 1)

