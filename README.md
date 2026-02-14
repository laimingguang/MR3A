# MR3A - 忍者必须死3自动化脚本

<div align="center">

<img src="assets/MR3A_logo.jpg" alt="MR3A Logo" width="200"/>

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/originalsage/MR3A)](https://github.com/originalsage/MR3A/releases)
[![License](https://img.shields.io/github/license/originalsage/MR3A)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](#)

一个基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 构建的《忍者必须死3》自动化脚本项目。

[快速开始](#快速开始) • [功能特性](#功能特性) • [开发指南](#开发指南) • [使用说明](#使用说明) • [常见问题](#常见问题)

</div>

## 📖 项目简介

MR3A 是一个专门为《忍者必须死3》设计的自动化脚本项目，利用 MaaFramework 强大的图像识别和自动化能力，帮助玩家自动完成日常任务，提升游戏体验。

> 💡 **提示**：本项目基于 [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate) 模板创建，遵循 MaaFramework 最佳实践。

## ✨ 功能特性

### 🎮 自动化任务
- ✅ **启动游戏** - 自动启动《忍者必须死3》应用
- ✅ **神龙契约** - 自动领取神龙契约奖励
- ✅ **领取饭团** - 自动收集每日饭团
- ✅ **忍者小屋** - 自动进行小屋修炼
- ✅ **忍村试炼** - 自动挑战试炼关卡（支持多关卡配置）
- ✅ **每日商店** - 自动购买商店物品（支持忍币购买开关）
- ✅ **好友忍币** - 自动收取好友忍币
- ✅ **家族祈福** - 自动进行家族祈福
- ✅ **免费召唤** - 自动进行免费召唤（支持4000忍币召唤配置）
- ✅ **每日悬赏** - 自动完成悬赏任务
- ✅ **领取战令** - 自动领取战令奖励
- ✅ **每日藏宝图** - 自动探索藏宝图

### 🔧 技术特性
- 🔄 **智能流程控制**：基于JSON配置的灵活任务编排
- 👁️ **多重识别方式**：支持模板匹配和OCR文字识别
- ⚙️ **可配置选项**：丰富的任务参数和开关设置
- 📊 **实时监控**：详细的任务执行状态反馈
- 🔒 **安全可靠**：模拟真实用户操作，降低封号风险

## 🚀 快速开始

### 系统要求

- **操作系统**：Windows 10/11 或 Android 5.0+


## 🛠️ 开发指南

### 项目结构

```
MR3A/
├── agent/                  # Python扩展模块
│   ├── main.py            # Agent主程序
│   ├── my_action.py       # 自定义动作模块
│   └── my_reco.py         # 自定义识别模块
├── assets/                # 资源文件
│   ├── resource/          # 游戏资源
│   │   ├── model/         # OCR模型
│   │   └── pipeline/      # 任务流程配置
│   └── interface.json     # 界面配置文件
├── deps/                  # 依赖库（MaaFramework）
├── tools/                 # 工具脚本
│   ├── install.py         # 安装脚本
│   ├── configure.py       # 配置工具
│   └── validate_schema.py # 配置验证
└── docs/                  # 文档
```
## 如何开发

0. 使用右上角 `Use this template` - `Create a new repository` 来基于本模板创建您自己的项目。

1. 克隆本项目（地址请修改为您基于本模板创建的新项目地址）。

    ```bash
    git clone https://github.com/MaaXYZ/MaaPracticeBoilerplate.git
    ```

2. 下载 MaaFramework 的 [Release 包](https://github.com/MaaXYZ/MaaFramework/releases)，解压到 `deps` 文件夹中。

3. 下载 OCR（文字识别）资源文件 [ppocr_v5.zip](https://download.maafw.xyz/MaaCommonAssets/OCR/ppocr_v5/ppocr_v5-zh_cn.zip) 解压到 `assets/resource/model/ocr/` 目录下，确保路径如下：

    ```tree
    assets/resource/model/ocr/
    ├── det.onnx
    ├── keys.txt
    └── rec.onnx
    ```

    _请注意，您不需要将 OCR 资源文件上传到您的代码仓库中。`.gitignore` 已经忽略了 `assets/resource/model/ocr/` 目录，且 GitHub workflow 在发布版本时会自动配置这些资源文件。_

4. 进行开发工作，按您的业务需求修改 `assets` 中的资源文件，请参考 [MaaFramework 相关文档](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/1.1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B.md#%E8%B5%84%E6%BA%90%E5%87%86%E5%A4%87)。

5. 完成开发后，上传您的代码并发布版本。

    ```bash
    # 配置 git 信息（仅第一次需要，后续不用再配置）
    git config user.name "您的 GitHub 昵称"
    git config user.email "您的 GitHub 邮箱"
    
    # 提交修改
    git add .
    git commit -m "XX 新功能"
    git push origin HEAD -u
    ```

6. 发布您的版本

    需要**先**修改仓库设置 `Settings` - `Actions` - `General` - `Read and write permissions` - `Save`

    ```bash
    # CI 检测到 tag 会自动进行发版
    git tag v1.0.0
    git push origin v1.0.0
    ```

7. 更多操作，请参考 [个性化配置](./docs/zh_cn/个性化配置.md)（可选）

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework) - 强大的自动化框架
- [MaaAssistant](https://github.com/MaaAssistantArknights/MaaAssistantArknights) - 优秀的GUI工具
- 所有贡献者和支持者

## 📞 联系方式

- **QQ**: 3625720746
- **GitHub Issues**: [提交问题](https://github.com/originalsage/MR3A/issues)

---

<p align="center">
  如果你觉得这个项目对你有帮助，请给个⭐Star支持一下！
</p>