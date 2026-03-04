from pathlib import Path

import shutil
import sys
import json
import re

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))
from configure import configure_ocr_model

def remove_json_comments(json_string):
    """移除 JSON 字符串中的注释"""
    # 状态机：0=正常，1=字符串，2=转义字符
    state = 0
    result = []
    i = 0
    n = len(json_string)
    
    while i < n:
        if state == 0:
            if json_string[i:i+2] == '//':
                # 找到单行注释，跳过到行尾
                end = json_string.find('\n', i)
                if end == -1:
                    break
                i = end
            elif json_string[i:i+2] == '/*':
                # 找到多行注释，跳过到注释结束
                end = json_string.find('*/', i+2)
                if end == -1:
                    break
                i = end + 2
            elif json_string[i] == '"':
                # 进入字符串
                result.append(json_string[i])
                state = 1
                i += 1
            else:
                # 正常字符
                result.append(json_string[i])
                i += 1
        elif state == 1:
            if json_string[i] == '\\':
                # 进入转义字符
                result.append(json_string[i])
                state = 2
                i += 1
            elif json_string[i] == '"':
                # 退出字符串
                result.append(json_string[i])
                state = 0
                i += 1
            else:
                # 字符串内字符
                result.append(json_string[i])
                i += 1
        elif state == 2:
            # 转义字符，直接添加
            result.append(json_string[i])
            state = 1
            i += 1
    
    # 移除多余的空白行
    json_string = ''.join(result)
    json_string = '\n'.join([line for line in json_string.split('\n') if line.strip()])
    return json_string


working_dir = Path(__file__).parent.parent.resolve()
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

# the first parameter is self name
if sys.argv.__len__() < 4:
    print("Usage: python install.py <version> <os> <arch>")
    print("Example: python install.py v1.0.0 win x86_64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]


def get_dotnet_platform_tag():
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        platform_tag = "win-x64"
    elif os_name == "win" and arch == "aarch64":
        platform_tag = "win-arm64"
    elif os_name == "macos" and arch == "x86_64":
        platform_tag = "osx-x64"
    elif os_name == "macos" and arch == "aarch64":
        platform_tag = "osx-arm64"
    elif os_name == "linux" and arch == "x86_64":
        platform_tag = "linux-x64"
    elif os_name == "linux" and arch == "aarch64":
        platform_tag = "linux-arm64"
    else:
        print("Unsupported OS or architecture.")
        print("available parameters:")
        print("version: e.g., v1.0.0")
        print("os: [win, macos, linux, android]")
        print("arch: [aarch64, x86_64]")
        sys.exit(1)

    return platform_tag


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
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
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )


def install_chores():
    for file in ["README.md", "LICENSE", "requirements.txt"]:
        shutil.copy2(
            working_dir / file,
            install_path,
        )
    # shutil.copytree(
    #     working_dir / "docs",
    #     install_path / "docs",
    #     dirs_exist_ok=True,
    #     ignore=shutil.ignore_patterns("*.yaml"),
    # )


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        content = f.read()
        # 移除JSON注释
        content = remove_json_comments(content)
        import json
        interface = json.loads(content)

    if os_name == "win":
        interface["agent"]["child_exec"] = r"./python/python.exe"
    elif os_name == "macos":
        interface["agent"]["child_exec"] = r"./python/bin/python3"
    elif os_name == "linux":
        interface["agent"]["child_exec"] = r"./python/bin/python3"

    interface["agent"]["child_args"] = ["-u", r"./agent/main.py"]

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()

    print(f"Install to {install_path} successfully.")
