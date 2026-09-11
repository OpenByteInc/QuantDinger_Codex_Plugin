<p align="center">
  <img src="plugins/quantdinger/assets/quantdinger-cat-logo.png" width="96" alt="QuantDinger 标志" />
</p>

# QuantDinger for Codex

**把交易想法，变成可以验证的策略。**

[English](README.md) · [简体中文](README.zh-CN.md) · [官网](https://www.quantdinger.com) · [打开 QuantDinger](https://ai.quantdinger.com) · [后端与 MCP 源码](https://github.com/OpenByteInc/QuantDinger)

直接在 Codex 对话中研究**美股、港股、ETF 和加密货币**：编写策略、计入成本运行历史回测、比较策略表现，并查看 QuantDinger 账户和交易运行情况。

本仓库通过 **GitHub 插件市场源**分发。用户主动添加此来源后安装使用；它不代表已上架 OpenAI 官方公共插件目录，也不代表 OpenAI 背书。

![从策略需求到回测分析的示意图](plugins/quantdinger/assets/strategy-workflow.png)

*图片仅作流程演示，其中结果不构成收益承诺。*

## 能做什么

| 场景 | 可以获得什么 |
| --- | --- |
| 市场研究 | 标的搜索、可用报价、历史价格与成交量、因子和标的池 |
| 策略开发 | Strategy API V2 编写指引、编译检查、源码保存与版本记录 |
| 回测与比较 | 异步回测、标准记录 `runId`、收益、回撤、成本和交易记录 |
| 交易状态查看 | 账户快照、策略持仓、成交、挂单和运行状态 |
| 授权操作 | 在 Token 权限、账户设置和用户明确确认范围内执行支持的模拟或实盘操作 |

AI 助手利用这些工具完成研究与解释；当前版本没有单独暴露 QuantDinger 原生 AI 投研报告生成工具。实际市场、数据时效和券商操作能力由所连接的后端及数据源决定。

## 平台支持

| 平台 | 当前状态 |
| --- | --- |
| Windows 10/11 x64 | 内置运行环境，提供连接器与离线安装回归测试 |
| macOS / Apple Silicon | 计划适配；当前 Windows 包不能在 Mac 上运行 |
| 其他架构 / Linux | 当前版本未提供运行环境安装包 |

插件版本 **0.1.0**，内置 **quantdinger-mcp 0.6.2** 和 Python **3.13.15**。插件与 MCP 独立编号。Windows 包自带依赖，用户无需安装 Python 或 pip；具体电脑还可能受到 Windows 安全策略和 Codex 客户端版本影响。

## Windows 安装

准备支持插件功能的 Codex 客户端、终端可用的 `codex` 命令、Git，以及 QuantDinger 账户或自托管实例。企业管理的工作区可能限制自定义插件来源。

在 PowerShell 中执行：

```powershell
codex plugin marketplace add OpenByteInc/quantdinger-codex-plugin
codex plugin add quantdinger@quantdinger
```

新建一个 Codex 任务，通过 `@` 选择 **QuantDinger**。如果客户端提供插件浏览器，也可以在其中查找 QuantDinger 来源。如果提示不认识 `plugin` 或 `marketplace` 命令，请先更新 Codex。

仓库包含约 26 MB 的 Windows 运行环境压缩包，确保通过市场源安装时文件完整。首次启动会在本机校验并解压，不需要联网下载 Python 或安装依赖；行情查询和账户操作仍需要访问所连接的 QuantDinger 服务。

### 从本地目录安装

```powershell
git clone https://github.com/OpenByteInc/quantdinger-codex-plugin.git
cd quantdinger-codex-plugin
codex plugin marketplace add .
codex plugin add quantdinger@quantdinger
```

使用本地市场源时，请保留这个目录。只下载并解压仓库不会自动完成安装，还需要把解压后的仓库根目录添加为市场源。不同客户端的行为请参考[官方插件打包说明](https://developers.openai.com/plugins/build/plugins)。

## 连接自己的账户

1. 打开 [QuantDinger 的 Agent Token 设置](https://ai.quantdinger.com/#/profile?tab=agentTokens)，创建权限适当、可撤销的 Token。初次测试建议使用仅限模拟交易的权限。
2. 在启用 QuantDinger 的 Codex 任务中要求连接账户，按提示提供 Token。**在对话中输入的 Token 会进入对话和工具历史。** 连接器会向你选择的 QuantDinger 服务验证它，再将本地副本保存到系统凭据库；返回内容不会回显 Token。
3. 核对连接成功后的服务地址、权限及是否仅限模拟交易，然后开始分析或回测。连接账户本身不等于授权下单。

默认后端为 `https://ai.quantdinger.com`。自托管用户需要明确指定实例根地址，并使用该实例签发的 Token。除本机回环开发地址外，要求使用 HTTPS。

如果不希望 Token 出现在对话历史，可以在仓库根目录运行下面的命令，通过终端隐藏输入配置：

```powershell
.\plugins\quantdinger\scripts\launch-quantdinger.cmd configure
```

自托管时追加 `--base-url https://your-quantdinger-host.example`。不要把 Token 本身放入命令行、Git 提交或 GitHub Issue。

## 直接试试这些需求

**美股：编写并回测策略**

> 为 NVDA 创建 MA20/MA60 均线交叉策略，回测最近 90 天。初始资金 10,000，手续费 0.1%，滑点 0.05%。保存回测，返回 runId、最大回撤和完整交易数量。

**港股：理解市场变化**

> 分析腾讯 0700.HK 最近 90 天的趋势、成交量变化和历史回撤，明确说明实际覆盖的数据日期。

**ETF：比较策略差异**

> 在相同时间范围、资金和成本设置下，对比 SPY 的均线策略与 RSI 策略，解释表现差异。

**加密货币：验证完整进出场规则**

> 为 BTC/USDT 编写包含趋势过滤、RSI 入场、2% 止损、3% 止盈和最大持仓时间的策略，运行回测，检查完整交易和剩余持仓。

**账户监控：只读查看**

> 查看我的模拟账户持仓、策略成交和挂单，解释需要关注的问题，不修改账户或策略状态。

为减少时区与数据源末日数据尚未就绪造成的失败，历史数据可能保守排除最近一天。分析和对比时请以实际返回的数据范围为准。特定时间段内没有完整平仓交易，也可能是策略信号的正常结果。

## 运行方式与费用

```text
用户电脑上的 Codex
  → 本地 QuantDinger Connector（stdio MCP）
  → 固定版本的 quantdinger-mcp
  → 用户选择的 QuantDinger 后端（HTTPS Agent Gateway）
```

每个系统用户连接自己的账户。同一系统用户的插件任务共用连接配置，更换凭据影响后续调用。后端负责权限、账户隔离、幂等和计费；仓库不会附带可供所有人共用的管理员 Token。

插件源码开源。使用 QuantDinger 云端功能可能按服务当前价格扣除积分；开源安装不等于云端功能免费。Codex 本身的访问与使用费用另行计算。

## 更新与卸载

通过 GitHub 市场源安装的用户，可以执行：

```powershell
codex plugin marketplace upgrade quantdinger
codex plugin add quantdinger@quantdinger
```

插件更新后新建任务以加载新版本；普通 Token 更换不需要重启 Codex。维护者以完整、经过测试的运行环境包交付更新，不会在用户电脑上执行原地 pip 升级。

卸载插件：

```powershell
codex plugin remove quantdinger@quantdinger
```

卸载插件**不会停止后端正在运行的策略，也不会撤销 Agent Token**，请在 QuantDinger 中单独管理。运行环境缓存和系统凭据库条目可能保留，详见[安全与数据处理说明](SECURITY.md)。

## 常见问题

| 问题 | 排查方向 |
| --- | --- |
| 看不到插件 | 是否添加来源、安装插件并新建任务；检查工作区限制及 Codex 版本 |
| 找不到 `cmd.exe` / 平台不支持 | 当前包仅适用于 Windows x64，Mac 版仍待适配 |
| 首次启动失败 | 压缩包完整性、本地应用数据目录写入权限、Windows 安全策略；不要关闭完整性校验 |
| 身份验证被拒绝 | 后端地址是否正确，Token 是否有效、过期或缺少权限 |
| 积分不足 | 检查 QuantDinger 余额和该操作当前价格 |
| 回测没有完整交易 | 查看入场/退出条件、实际数据范围与未平仓仓位，并打开保存的回测记录 |
| 账户或订单操作被拒绝 | Token 权限、仅限模拟限制、券商环境及是否明确确认操作 |

遇到可复现问题，请在 [Issues](https://github.com/OpenByteInc/quantdinger-codex-plugin/issues) 提供操作系统、Codex/插件版本和脱敏错误信息。不要上传凭据或私有账户记录。

## 开发与许可证

- [构建与测试](BUILDING.md)
- [贡献指南](CONTRIBUTING.md)
- [安全与数据处理](SECURITY.md)
- [更新记录](CHANGELOG.md)

市场目录位于 `.agents/plugins/marketplace.json`，可安装插件位于 `plugins/quantdinger/`。MCP 业务工具继续在[总仓库](https://github.com/OpenByteInc/QuantDinger/tree/main/mcp_server)维护，本仓库使用固定版本的 PyPI 包。

采用 [Apache-2.0](LICENSE) 开源许可证。内置第三方软件保留各自许可证，见 [NOTICE](NOTICE)。开源许可不代表获得 QuantDinger 或 OpenAI 商标背书。交易存在风险，历史回测不保证未来收益。
