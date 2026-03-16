# MR3A - 忍者必须死3自动化脚本

<div align="center">
  <img src="assets/logo.png" alt="MR3A Logo" width="256" height="256"/>
  
  [![GitHub release (latest by date)](https://img.shields.io/github/v/release/originalsage/MR3A)](https://github.com/originalsage/MR3A/releases)
  [![License](https://img.shields.io/github/license/originalsage/MR3A)](LICENSE)
  [![Platform](https://img.shields.io/badge/platform-Windows-blue)](#)
  
  一个基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 构建的《忍者必须死3》自动化脚本项目
  
  Powered by [MaaFramework](https://github.com/MaaXYZ/MaaFramework) & [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia)
</div>

## 使用须知

这是一个**正在快速迭代**的项目，可能会有一些小 BUG 出没 🐛（我们会努力消灭它们的！）

遇到问题？欢迎来提 [ISSUE](https://github.com/originalsage/MR3A/issues) 反馈，我们会第一时间处理！更多功能正在路上，敬请期待 ✨


## 项目简介

MR3A 是一个专门为《忍者必须死3》设计的自动化脚本项目，利用 MaaFramework 强大的图像识别和自动化能力，帮助玩家自动完成日常任务，提升游戏体验。

> 💡 **提示**：新版本会自动检测更新，可通过设置中选择github自动更新哦~

## 功能特性

### 核心自动化任务

- ✅ **启动游戏** - 自动启动《忍者必须死3》应用（暂时只支持官服/vivo服切换）
- ✅ **神龙契约** - 自动领取神龙契约奖励
- ✅ **领取饭团** - 自动收集每日饭团（支持指定好友送饭团功能）
- ✅ **竞技场** - 自动进行竞技场跑酷（直接挂机，老板娘问答随机选择）
- ✅ **通灵巡逻** - 自动进行通灵巡逻（支持有忍阶任务才巡逻，可选择巡逻关卡）
- ✅ **忍者小屋** - 自动进行小屋修炼
- ✅ **忍村试炼** - 自动挑战试炼关卡（支持1-5关自定义配置，可选择保留包子数量）
- ✅ **每日商店** - 自动购买商店物品（支持神秘商店和悬赏商店的忍币购买开关）
- ✅ **好友忍币** - 自动收取好友忍币
- ✅ **家族祈福** - 自动进行家族祈福
- ✅ **免费召唤** - 自动进行免费召唤（支持4000忍币召唤白银武库开关）
- ✅ **每日悬赏** - 自动完成悬赏任务
- ✅ **3v3** - 自动进行3v3匹配（当前仅支持困难图，依赖固定延时点击，仍在测试中）
- ✅ **领取战令** - 自动领取战令奖励
- ✅ **忍阶任务** - 自动领取每日忍阶声望
- ✅ **每日藏宝图** - 自动刷取藏宝图（支持属性选择：神炎国/海之国/雷王山/云之国/任意属性）
- ✅ **神品传颂藏宝图** - 专刷神品和传颂品质藏宝图
- ✅ **S/SS/SS+悬赏** - 专刷高级悬赏（跳过低级悬赏）

## 新手上路

### Windows

- 99.99%的用户下载 [release](https://github.com/originalsage/MR3A/releases/latest) 中的 `MR3A-win-x86_64-vxxx.zip` 压缩包即可。

### Linux

~~我上哪找又玩忍三又用 Linux 的人啊~~

### Android(手机端)

- 暂不支持
### 推荐配置
- **模拟器**：推荐使用 Mumu 模拟器或雷电模拟器

### 重要提醒 ⚠️
1. 确保模拟器分辨率比例为16:9
2. 请在游戏设置中关闭好友组队邀请功能

###  系统要求

- **操作系统**：Windows 10/11

🌟 如果你觉得这个项目对你有帮助，请给个⭐Star支持一下！

## 开发指南（仅对开发者）

###  技术特性

- **智能流程控制**：基于JSON配置的灵活任务编排
- **多重识别方式**：支持模板匹配和OCR文字识别
- **可配置选项**：丰富的任务参数和开关设置
- **实时监控**：详细的任务执行状态反馈

###  项目结构

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

###  如何开发

请前往 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 查看详细开发文档

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 致谢

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework) - 强大的自动化框架
- [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia) - 优秀的GUI工具
- 所有贡献者和支持者

## 联系方式

- **MR3A用户QQ群**: 1090310179
- **GitHub Issues**: [提交问题](https://github.com/originalsage/MR3A/issues)

---
## Star History

[![Star History Chart](https://api.star-history.com/image?repos=originalsage/MR3A&type=date&legend=top-left)](https://www.star-history.com/?repos=originalsage%2FMR3A&type=date&legend=bottom-right)
<div align="center">
  
  🌟 如果你觉得这个项目对你有帮助，请给个⭐Star支持一下！
  
  ---
  
  **项目持续开放中，有bug请联系开发者，用户QQ群:1090310179**
  
</div>