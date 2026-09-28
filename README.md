# 股票纪律桌面宠物 · 小戒

一只趴在你桌面右下角的猫，盯你别乱炒股。

## 功能

- 🐱 桌面右下角猫形逐帧动画，可拖动，永远置顶
- 💬 点击弹出聊天框，背后 DeepSeek 大模型
- 📈 定时拉大盘涨跌家数（akshare），暴跌/暴涨时变色警告
- ⏰ 开盘/午盘/尾盘自动弹纪律提醒
- ⚙️ GUI 设置页，API Key 加密存 Windows 凭据管理器
- 🖼️ 支持自定义帧动画（见 CAT_FRAMES.md）

## 快速开始

```bat
pip install -r requirements.txt
python main.py
```

第一次启动会自动弹设置页，填 DeepSeek API Key 即可。

## 打包成 exe

双击 `双击我来打包.bat`（或 `build.bat`），等 3~10 分钟，exe 在 `dist/` 里。

## 项目结构

```
stock_pet/
├── main.py              # 入口
├── pet_widget.py        # 宠物窗口（逐帧动画）
├── chat_panel.py        # 聊天面板
├── discipline_engine.py # 纪律提醒引擎
├── stock_data.py        # 大盘数据（akshare 多源降级）
├── llm_client.py        # DeepSeek 客户端
├── settings_dialog.py   # 设置页
├── config.py            # 配置加载
├── credential_store.py  # API Key 加密存储
├── self_check.py        # 环境自检
├── assets/cat/          # 猫帧动画 PNG
└── CAT_FRAMES.md        # 帧动画制作指南
```

## License

MIT
