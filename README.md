# 股票纪律桌面宠物 · 小戒

一只趴在你桌面右下角的猫，盯你别乱炒股。

## 功能

- 🐱 桌面右下角猫形逐帧动画，可拖动，永远置顶
- 🧶 点击操作菜单的「玩耍」（或右键「玩耍」），循环播放视频抽帧的透明翻滚动画；右键「恢复坐姿」返回普通待机。
- 👀 坐姿待机时目光跟随鼠标；在其他窗口按键也会触发单爪敲地（只处理按下事件，不记录输入内容）
- 💬 点击弹出聊天框，背后 DeepSeek 大模型
- 🧠 对话记忆：历史输入及重点摘要长期保存在 `%APPDATA%/StockPet/question-memory.sqlite3`，重启后仍可回忆；不长期保存模型回复。保存时本地提取关键句并去除重复背景，优先保留代号、数值、时间、规则、更正、否定与假设条件，无需额外调用模型。每次只带入最多 5 条相关记忆（每条最多 500 字符，总计不超过 2,000 字符）；长输入还会结合当前问题重新提取相关重点，避免只截首尾而丢失中段信息。临时上下文保留最近 2 轮，用户输入同样提取重点，总计最多 4,000 字符。原输入保留用于检索，重复输入合并记录次数，旧记忆库自动兼容。
- 📚 统一知识库：所有资料统一存放在 `knowledge`，由 `registry.json` 自动索引其中的 `SKILL.md` 和普通 Markdown 笔记。每次读取索引，仅重新解析变动文件，再附上全部启用条目的目录和最多 6 份相关正文（总计不超过 32,000 字符）。相同内容去重，文件修改后下一轮生效；原书、测试和废弃草稿不注入。维护方式见 `knowledge/README.md`。
- ⚙️ GUI 设置页，API Key 加密存 Windows 凭据管理器
- ✅ 本地待办：点击某条事项的“提醒”，选择日期和时间后确认设置；已有提醒可修改或取消，返回不修改。完成、删除和提醒设置均保存在本地，已完成事项不会触发提醒。
- 🗑️ 右键「清空回收站」：宠物走到桌面回收站图标旁，确认后清空，再走回原位
- 🖼️ 支持自定义帧动画（见 CAT_FRAMES.md）

## 快速开始

```bat
pip install -r requirements.txt
python main.py
```

第一次启动会自动弹设置页，填 DeepSeek API Key 即可。

## 打包成 exe

双击 `双击我来打包.bat`，或运行 `python build_distribution.py`，默认生成：

- `dist/StockPet.exe`：单文件免安装程序，包含动画、知识库和运行依赖，无需安装 Python。首次启动解压内置资源需要稍等。

脚本自动检查 `.venv`、`venv`、项目环境和当前 Python 的依赖，也可用 `--python 路径` 指定环境；缺少依赖时按提示安装 `requirements.txt`。单文件打包无需 Inno Setup。

- `python build_distribution.py --onedir`：生成 `dist/StockPet/StockPet.exe`，需保留同目录的 `_internal`，启动更快。
- `python build_distribution.py --installer`：需要 Inno Setup 6，生成程序目录和 `dist/StockPet-Setup-1.0.0.exe` 中文安装程序，安装时可选开机自启动。
- `python build_distribution.py --check`：只检查依赖和资源。错误详情保存在 `build-exe.log`；可运行 `StockPet.exe --smoke-test` 检查成品的界面依赖、动画、知识库和记忆读写，结果写入程序日志。

程序设置中也可以勾选或取消“开机自启动”。设置保存在 `%APPDATA%/StockPet/config.json`，
待办保存在用户数据目录的 `StockPet/todos.json`，登录凭据仍存 Windows 凭据管理器。
安装版的启动日志位于 `%APPDATA%/StockPet/app.log`。卸载会移除开机启动项并保留用户记录。

## macOS 版本

macOS 需使用原生 Mac 或 GitHub Actions 的 macOS 运行器构建，Windows 不能直接生成可运行的 `.app`。

- 本地 Mac：安装 Python 3.11 / 3.12，运行 `bash build-mac.command`。脚本创建独立环境、安装依赖，生成并自检 `StockPet.app`，然后生成 `dist/macos/arm64/StockPet-macOS-arm64.dmg` 或 `dist/macos/x86_64/StockPet-macOS-x86_64.dmg`，架构与所用 Python 相同。
- 已有依赖环境：`python build_macos.py --python /path/to/python`；`--check` 只检查依赖和资源。
- GitHub Actions：在仓库的 Actions 中运行 **Build macOS**，或推送 `codex/macos-*` 分支，分别生成 Apple 芯片和 Intel 版本。构建完成后在该次运行的 Artifacts 下载 DMG。
- 打开 DMG，将应用拖入 Applications。包为本地签名，未使用 Apple Developer 证书或公证；首次启动可能需要在系统设置的隐私与安全性中允许打开。

Mac 配置、记忆、待办和日志位于 `~/Library/Application Support/StockPet/`，API Key 优先保存到钥匙串。登录自启动下一次登录生效，请先安装到 Applications 再勾选。Mac 版暂不启用清空 Windows 回收站和 Windows 后台键盘动作。安装细节见 `docs/macOS安装说明.txt`。

## 项目结构

```
stock_pet/
├── main.py              # 入口
├── pet_widget.py        # 宠物窗口（逐帧动画）
├── chat_panel.py        # 聊天面板
├── llm_client.py        # DeepSeek 客户端
├── settings_dialog.py   # 设置页
├── config.py            # 配置加载
├── credential_store.py  # API Key 加密存储
├── win_recycle.py       # 回收站：定位桌面图标位置 / 清空（纯 ctypes）
├── self_check.py        # 环境自检
├── assets/cat/          # 猫帧动画 PNG
└── CAT_FRAMES.md        # 帧动画制作指南
```

## License

MIT
