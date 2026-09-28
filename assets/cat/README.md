# 猫帧目录

这里放猫的逐帧动画 PNG。命名规则见根目录 `CAT_FRAMES.md`。

## 快速开始

把你的 PNG 按下面命名丢进来：

```
idle_0.png  idle_1.png  idle_2.png  ...   待机循环
warn_0.png  warn_1.png  ...               警告
panic_0.png panic_1.png ...               恐慌
happy_0.png happy_1.png ...               开心
```

- PNG 透明背景，建议 180×160
- 2 帧以上就能做动画
- 没有帧时程序自动用 QPainter 画的占位橘猫

## 从绿幕视频抽帧

```bash
ffmpeg -i cat.mp4 -vf "fps=5,chromakey=0x00FF00:0.1:0.0" idle_%d.png
```

详见根目录 `CAT_FRAMES.md`。
