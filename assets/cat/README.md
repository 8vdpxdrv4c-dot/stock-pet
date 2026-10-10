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

## 玩耍待机

`playing-idle/` 来自用户提供的 `猫顽皮舔屏视频生成.mp4`，原视频保存在
`videos/playing-source.mp4`。保留 145 个原始动作帧，去除背景并统一到 360×360
透明画布，以 24 fps 往返循环播放（288 帧，不重复端点），包含翻滚、伸懒腰、抬爪。
没有交叉淡化或重影；源文件校验值和处理参数见 `playing-idle/animation.json`。

使用 Python 3.12、已有的 `build/video-tools` 依赖和 PATH 中的 ffmpeg，运行
`python scripts/build_playing_video.py` 可重新生成。只在构建时需要视频工具，
运行时和 EXE 中只使用透明 PNG 帧。

玩耍素材的原视频含有地面倒影。构建脚本对这份已校验来源的视频，在原始图像
620–640 像素的地面过渡带内，利用填充前的抠图置信度去除脚掌下方残影；保持
原始裁切范围、角色位置和播放顺序。其他来源视频不会自动套用此坐标规则。
使用 `python scripts/build_playing_video.py --preview` 可同时刷新根目录的动态预览。
