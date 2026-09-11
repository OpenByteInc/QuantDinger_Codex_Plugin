# 安装 → 连接账户 → 完成第一次回测

[English](INSTALL.md) · [简体中文](INSTALL.zh-CN.md) · [返回首页](../README.zh-CN.md)

## 开始前准备

需要 QuantDinger 账户、Git，以及支持插件的 Codex 客户端。在 Windows 的 PowerShell 或 Mac 的「终端」中检查：

```text
git --version
codex --version
codex plugin --help
```

如果找不到命令，先安装 [Git](https://git-scm.com/downloads) 或 [Codex CLI](https://developers.openai.com/codex/cli)，再重新打开终端。安装时使用与 Codex 桌面应用相同的系统账户和配置目录；自定义 `CODEX_HOME` 与默认配置是分开的。

## Windows 安装

支持 Windows 10/11 x64。在 **PowerShell** 粘贴：

```powershell
codex plugin marketplace add OpenByteInc/QuantDinger_Codex_Plugin
codex plugin add quantdinger@quantdinger
```

插件内置 Python 和依赖。首次启动会校验并解压专用运行环境，无需自行安装 Python、执行 pip 或配置 API Key 环境变量。

## Mac 安装

打开「**终端**」，先安装一次 [uv](https://docs.astral.sh/uv/getting-started/installation/)：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

如果已经使用 Homebrew，也可以执行 `brew install uv`，二选一即可。启动器会检查常见的 uv、Homebrew 安装路径和 `PATH`。

```bash
codex plugin marketplace add OpenByteInc/QuantDinger_Codex_Plugin
codex plugin add quantdinger-macos@quantdinger
```

选择 **QuantDinger for Mac**，不要安装 Windows 入口。本版支持 **Apple Silicon（`arm64`，M 系列）**。暂不支持 Intel Mac：当前加密依赖没有提供官方 Intel macOS 安装包。请使用原生 arm64 终端和 Codex 客户端，不要通过 Rosetta 运行。这是 Mac 桌面端／CLI 集成，不是 iOS 应用。

首次启动需要联网：uv 会下载独立的 Python 3.13，并按固定版本和文件哈希安装依赖，可能需要几分钟。后续启动复用环境；查询行情和调用云端功能仍需要网络。

## 在 Codex 中打开

**新建一个任务**，输入 `@`，Windows 选择 **QuantDinger**，Mac 选择 **QuantDinger for Mac**。也可以打开插件详情，点击右上角「**立即试用 / Try now**」或示例提示词。

![真实插件详情：右上角 Try now 和中间示例提示词](assets/codex-plugin-screen.png)

<sub>维护者提供的 Windows 实际截图，拍摄于 0.2.0 简化名称和新增 Mac 入口之前。不同版本的 Codex 控件文字可能略有不同。</sub>

先发送：

```text
检查我的 QuantDinger 连接状态。如果已连接，核实环境地址和权限。
不要创建策略，也不要下单。
```

第一次使用提示未配置账户是正常的。如果工具根本没有出现或启动失败，应先检查安装，而不是反复更换 Token。

## 连接账户

1. 登录 [QuantDinger](https://ai.quantdinger.com)。
2. 打开「[个人中心 → Agent Tokens](https://ai.quantdinger.com/#/profile?tab=agentTokens)」，创建可撤销、权限适当的 Token。建议先用仅模拟交易权限。
3. 让 Codex 连接 QuantDinger，按提示提供 Token。
4. 检查返回的 **`connected`、环境地址、权限和仅模拟交易状态**，然后在同一个任务里继续使用。

连接器验证成功后才保存凭证。安装和连接都不会自动启动交易。如果替换凭证失败，旧连接会保留；切换账户时应先解决错误，再继续操作。

本地 Token 保存在 Windows 凭据管理器或 macOS 钥匙串中。Mac 如果弹出钥匙串访问请求，请确认它属于刚安装的 Python 运行环境。插件不会把 Token 写入明文配置文件；但在聊天中输入的 Token 仍会出现在对话／工具历史里。

### 不想把 Token 发到聊天里

可以下载仓库，使用不回显的终端输入：

```text
git clone https://github.com/OpenByteInc/QuantDinger_Codex_Plugin.git
cd QuantDinger_Codex_Plugin
```

Windows PowerShell：

```powershell
.\plugins\quantdinger\scripts\launch-quantdinger.cmd configure
```

Mac 终端：

```bash
/bin/bash plugins/quantdinger-macos/scripts/launch-quantdinger.sh configure
```

在隐藏输入提示中粘贴 Token。这个本地目录与已安装插件共用当前系统用户的连接存储。回到 Codex，让它验证连接即可。不要把 Token 直接写在命令、截图或公开 Issue 中。

### 连接自部署版本

明确告诉 Codex 你的**后端根地址**，并提供该环境签发的 Token。也可以在上面的 `configure` 命令后加 `--base-url https://your-quantdinger.example`。把示例替换为实际根地址，不要追加 `/mcp` 或 API 路径。除 `http://127.0.0.1:5000` 等本机回环地址外，必须使用 HTTPS。

切换环境时需要该环境的 Token。本地插件通过 stdio 提供 MCP，不要求你另外搭建公网 MCP 地址。

## 跑一条能在历史中找到的回测

```text
为 NVDA 创建 MA20/MA60 均线交叉策略，回测最近 90 天。
初始资金 10,000，手续费 0.1%，滑点 0.05%。
保存结果，返回 runId、实际数据起止日期、收益率、最大回撤、
已完成交易数和剩余持仓。不要部署，也不要启动交易。
```

Codex 应完成策略编译／保存，并等待回测任务结束。提交成功不等于回测完成。使用返回的 **`runId`**，在 QuantDinger 的回测历史中对应标准记录。如果调用失败，应检查失败步骤和错误，不能把估算结果当成已保存的回测。

比较结果时看实际数据日期和成本设置。后端可能主动排除最后一天，以避免时区或数据源可用性导致失败。有些策略在所选区间确实只有未平仓持仓，或没有完整交易；同时查看成交笔数和完整交易数。

接着可以试试港股 `0700.HK`、ETF `SPY` 或加密货币 `BTC/USDT`。支持范围取决于后端和数据源。云端操作可能消耗 QuantDinger 积分，Codex 用量另计。投研由助手结合工具组织分析，当前没有单独暴露原生 AI 报告生成工具。

## 更新、本地安装与卸载

更新 GitHub 插件源：

```text
codex plugin marketplace upgrade quantdinger
```

然后重新执行对应平台的 `codex plugin add` 命令，并新建任务。同一台电脑只启用适合该平台的入口。

如果使用本地克隆或下载的源码压缩包，进入含有 `.agents/plugins/marketplace.json` 的根目录，执行 `codex plugin marketplace add .`，再执行相同的平台安装命令。如果已注册同名 GitHub 插件源，请继续使用原源，或先移除原源注册再切换，不要重复注册同名源。

卸载时按平台**选择一条**：

```text
codex plugin remove quantdinger@quantdinger
codex plugin remove quantdinger-macos@quantdinger
```

卸载**不会**撤销 Token、清除共享凭据或停止后端运行中的策略。不再使用的 Token 请在 QuantDinger 撤销；只有确实需要停止策略时，才执行停止操作。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 找不到 `codex` 或 `plugin` 命令 | 安装／更新 Codex CLI，重新打开终端，确认客户端支持插件。 |
| 安装后在应用中看不到 | 检查系统用户和配置目录是否相同，新建任务，确认插件源及平台入口；必要时重启应用刷新。 |
| Mac 尝试执行 `cmd.exe` | 移除 Windows 入口，改装 `quantdinger-macos@quantdinger`。 |
| `apple_silicon_required` | 使用 M 系列 Mac 和原生 arm64 终端／客户端。本版暂不支持 Intel Mac。 |
| `uv_required` | 按上方官方方式安装 uv；启动器会检查常见用户目录及 Homebrew 路径。 |
| Mac 首次启动超时 | 检查 Python 下载源和 PyPI 网络连通性，再重试。已完成的环境会复用；不完整的环境会隔离后重建。 |
| Mac 凭据保存失败 | 解锁登录钥匙串，检查对应的访问提示；不要关闭钥匙串保护。 |
| 身份验证被拒绝 | 检查环境地址、Token 有效性和撤销状态。网络不可达与凭证被拒绝是不同问题。 |
| 权限不足或余额不足 | 检查后端权限、仅模拟限制及余额；重新安装不能授予权限或积分。 |
| 历史里找不到回测 | 确认任务已完成且返回 `runId`，核对网页与插件是否使用同一账户、同一环境。 |

运行环境缓存与非敏感连接配置位于：

- Windows：`%LOCALAPPDATA%\QuantDinger\Connector`
- Mac：`~/Library/Application Support/QuantDinger/Connector`

提交 [Issue](https://github.com/OpenByteInc/QuantDinger_Codex_Plugin/issues) 时，请附系统／架构、Codex 版本、插件版本、失败步骤和脱敏错误。不要上传 Token、凭据存储或私人账户导出文件。
