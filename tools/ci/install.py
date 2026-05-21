from pathlib import Path

import shutil
import sys
import json

# 添加当前目录到 Python 路径，便于导入同目录脚本
sys.path.append(str(Path(__file__).parent))
from configure import configure_ocr_model
from generate_manifest_cache import generate_manifest_cache


def remove_json_comments(json_string: str) -> str:
    """移除 JSON 字符串中的 JSONC 注释（支持 // 与 /* */）"""
    state = 0  # 0=正常，1=字符串，2=转义字符
    result = []
    i = 0
    n = len(json_string)

    while i < n:
        if state == 0:
            if json_string[i : i + 2] == "//":
                end = json_string.find("\n", i)
                if end == -1:
                    break
                i = end
            elif json_string[i : i + 2] == "/*":
                end = json_string.find("*/", i + 2)
                if end == -1:
                    break
                i = end + 2
            elif json_string[i] == '"':
                result.append(json_string[i])
                state = 1
                i += 1
            else:
                result.append(json_string[i])
                i += 1
        elif state == 1:
            if json_string[i] == "\\":
                result.append(json_string[i])
                state = 2
                i += 1
            elif json_string[i] == '"':
                result.append(json_string[i])
                state = 0
                i += 1
            else:
                result.append(json_string[i])
                i += 1
        elif state == 2:
            result.append(json_string[i])
            state = 1
            i += 1

    # 保留原始换行/空白，让解析行为尽量不改变
    return "".join(result)


def load_json_maybe_jsonc(text: str) -> dict:
    """优先按标准 JSON 解析；失败再按 JSONC（去注释后）解析。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(remove_json_comments(text))


working_dir = Path(__file__).parent.parent.parent.resolve()
install_path = working_dir / "install"
defaults_path = working_dir / "tools" / "ci" / "defaults" / "maa_option.json"
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

# the first parameter is self name
if sys.argv.__len__() < 4:
    print("Usage: python install.py <version> <os> <arch>")
    print("Example: python install.py v1.0.0 win x86_64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]


def get_dotnet_platform_tag() -> str:
    """自动检测当前平台并返回对应的 dotnet 平台标签"""
    if os_name == "win" and arch == "x86_64":
        return "win-x64"
    if os_name == "win" and arch == "aarch64":
        return "win-arm64"
    if os_name == "macos" and arch == "x86_64":
        return "osx-x64"
    if os_name == "macos" and arch == "aarch64":
        return "osx-arm64"
    if os_name == "linux" and arch == "x86_64":
        return "linux-x64"
    if os_name == "linux" and arch == "aarch64":
        return "linux-arm64"

    print("Unsupported OS or architecture.")
    print("available parameters:")
    print("version: e.g., v1.0.0")
    print("os: [win, macos, linux, android]")
    print("arch: [aarch64, x86_64]")
    sys.exit(1)


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print("请先下载 MaaFramework 到 \"deps\"。")
        sys.exit(1)

    if os_name == "android":
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path,
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "share" / "MaaAgentBinary",
            install_path / "MaaAgentBinary",
            dirs_exist_ok=True,
        )
    else:
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path / "runtimes" / get_dotnet_platform_tag() / "native",
            ignore=shutil.ignore_patterns(
                "*MaaDbgControlUnit*",
                "*MaaThriftControlUnit*",
                "*MaaRpc*",
                "*MaaHttp*",
                "plugins",
                "*.node",
                "*MaaPiCli*",
            ),
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "share" / "MaaAgentBinary",
            install_path / "libs" / "MaaAgentBinary",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "bin" / "plugins",
            install_path / "plugins" / get_dotnet_platform_tag(),
            dirs_exist_ok=True,
        )


def install_resource():
    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(working_dir / "assets" / "interface.json", install_path)

    interface_path = install_path / "interface.json"
    with open(interface_path, "r", encoding="utf-8") as f:
        interface = load_json_maybe_jsonc(f.read())

    interface["version"] = version
    interface["title"] = f"MR3A {version} | 忍三小助手"

    with open(interface_path, "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    for file in ["README.md", "LICENSE", "requirements.txt"]:
        shutil.copy2(working_dir / file, install_path)


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = load_json_maybe_jsonc(f.read())

    if os_name == "win":
        interface["agent"]["child_exec"] = r"./python/python.exe"
    elif os_name == "macos":
        interface["agent"]["child_exec"] = r"./python/bin/python3"
    elif os_name == "linux":
        interface["agent"]["child_exec"] = r"./python/bin/python3"

    interface["agent"]["child_args"] = ["-u", r"./agent/main.py"]

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_manifest_cache():
    """生成初始 manifest 缓存（失败不影响构建）"""
    config_dir = install_path / "config"
    try:
        success = generate_manifest_cache(config_dir)
        if not success:
            print("Warning: Manifest cache generation failed, users will do full check on first run.")
    except Exception as e:
        print(f"Warning: Manifest cache generation raised error: {e}")


def install_or_patch_maa_option():
    """写入 MR3A 默认 maa_option，并保留上游新增字段。"""
    if not defaults_path.exists():
        raise FileNotFoundError(f"Missing default config template: {defaults_path}")

    config_dir = install_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    target_path = config_dir / "maa_option.json"

    with open(defaults_path, "r", encoding="utf-8") as f:
        defaults = load_json_maybe_jsonc(f.read())

    if not isinstance(defaults, dict):
        raise ValueError(f"Invalid default config format in {defaults_path}: expected object")

    existing: dict = {}
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                parsed = load_json_maybe_jsonc(f.read())
            if isinstance(parsed, dict):
                existing = parsed
            else:
                print(f"Warning: {target_path} is not an object, using defaults only.")
        except Exception as e:
            print(f"Warning: Failed to parse {target_path}, using defaults only: {e}")

    merged = dict(existing)
    merged.update(defaults)

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)
        f.write("\n")

    print(f"Patched Maa option config: {target_path}")


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_manifest_cache()
    install_or_patch_maa_option()

    print(f"Install to {install_path} successfully.")

