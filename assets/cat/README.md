# 桌宠帧目录

这里放桌宠的逐帧动画 PNG。

## 文件命名

```
assets/cat/
├── idle_0.png  idle_1.png  idle_2.png  idle_3.png   待机循环（眨眼/歪头/开心）
├── warn_0.png  warn_1.png  ...                       警告
├── panic_0.png panic_1.png ...                       恐慌
└── happy_0.png happy_1.png ...                       开心
```

- PNG 透明背景，建议 180×160
- 2 帧以上即可做动画，4 帧效果最佳
- 没有 PNG 时程序自动用 QPainter 画占位橘猫兜底

## 本仓库的 PNG 帧

> 说明：GitHub 网页/API 上传 PNG 二进制即可（普通文件上传，无特殊要求）。
> 当前 3D 卡通小狗 4 帧（idle_0~3）由 AI 生成，请直接上传到本目录。

## 从绿幕视频抽帧

```bash
ffmpeg -i dog.mp4 -vf "fps=5,chromakey=0x00B140:0.1:0.0" idle_%d.png
```

详见根目录 `CAT_FRAMES.md`。
