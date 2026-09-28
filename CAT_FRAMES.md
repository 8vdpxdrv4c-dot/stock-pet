# 猫主子帧动画制作指南

## 帧目录

把 PNG 丢进 `assets/cat/`，命名规则：

```
assets/cat/
├── idle_0.png  idle_1.png ...   待机循环
├── warn_0.png  warn_1.png ...   警告
├── panic_0.png panic_1.png ...  恐慌
└── happy_0.png happy_1.png ... 开心
```

- 前缀决定显示时机，同组按文件名排序循环
- 2 帧以上就能做动画
- PNG 透明背景，建议 180×160

## 视频转帧

```bash
ffmpeg -i cat.mp4 -vf "fps=5,chromakey=0x00FF00:0.1:0.0" assets/cat/idle_%d.png
```

## AI 生图提示词

```
Q版橘猫坐姿，正面，全身，透明背景，贴纸风格，平涂，大眼睛，可爱
```

用 remove.bg 去背景，导出 PNG。固定提示词只改表情，4 帧就是同一只猫。
