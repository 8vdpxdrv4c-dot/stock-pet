"""Render publication layouts using original project assets without altering them."""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[1]
DATA = json.loads((OUT / '制作源文件/content.json').read_text(encoding='utf-8'))

SOURCES = {
    'character.png': 'assets/cat/sitting-idle/idle_000.png',
    'drag-sheet.png': 'assets/cat/drag-play-actions-v2.png',
    'sleep.png': 'assets/cat/sleep-idle/sleep_000.png',
    'play.png': 'assets/cat/playing-idle/idle_045.png',
    'eat.png': 'assets/cat/eating-video-v7/idle_030.png',
    'actions.png': 'preview-pet-actions-orbit.png',
    'chat.png': 'preview-chat-cream.png',
    'paw-fix.jpg': 'preview-eating-leg-fix.jpg',
    'playing-loop.gif': 'preview-playing-idle.gif',
    'playing-source.mp4': 'assets/cat/videos/playing-source.mp4',
    'eating-source.mp4': 'assets/cat/videos/eating-source-v7.mp4',
    'eating-preview.mp4': 'preview-eating-video-v7.mp4',
}

for name, source in SOURCES.items():
    shutil.copy2(ROOT / source, OUT / 'assets' / name)
shutil.copy2(ROOT / 'docs/桌面宠物制作教程.md', OUT / '完整流程与提示词.md')

CSS = '''
*{box-sizing:border-box}body{margin:0;background:#e9e4dc;color:#302c27;font-family:"Microsoft YaHei","PingFang SC",sans-serif}
.canvas{position:relative;width:1200px;overflow:hidden;background:#fff8ed;padding:52px 60px;}
.eyebrow{font-size:20px;font-weight:700;letter-spacing:3px;color:#95632b;margin-bottom:18px}
h1,h2,h3,p{margin:0}h1{font-size:76px;line-height:1.19;letter-spacing:-2px}h2{font-size:49px;line-height:1.3;letter-spacing:-1px}h3{font-size:30px;line-height:1.4}
.lead{font-size:24px;color:#756958;margin-top:14px;line-height:1.6}.orange{color:#c55d23}
.foot{position:absolute;left:60px;right:60px;bottom:26px;display:flex;justify-content:space-between;font-size:17px;letter-spacing:1px;color:#8b7a64;border-top:1px solid #ddceba;padding-top:14px}
.row{display:flex;gap:24px;margin-top:34px}.box{border-radius:24px;background:#fffefb;border:1px solid #eddfcb;padding:26px;flex:1;min-width:0}.stage{display:flex;align-items:center;justify-content:center;border-radius:18px;overflow:hidden}
.tag{font-size:18px;letter-spacing:1px;color:#a8642c;font-weight:700;margin-bottom:12px}.desc{font-size:23px;line-height:1.7;color:#746653;margin-top:12px}
.pill{display:inline-block;background:#f7e5cb;color:#855523;border-radius:30px;padding:10px 22px;font-size:23px;margin-right:12px}
.checker{background-color:#f8f4ed;background-image:linear-gradient(45deg,#e9e1d4 25%,transparent 25%),linear-gradient(-45deg,#e9e1d4 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e9e1d4 75%),linear-gradient(-45deg,transparent 75%,#e9e1d4 75%);background-size:32px 32px;background-position:0 0,0 16px,16px -16px,-16px 0}
img{object-fit:contain;max-width:100%}.dark{background:#171922;color:#fff8eb}
.statement{font-size:29px;line-height:1.6;border-left:5px solid #cc722d;padding-left:22px;margin-top:24px}
'''


def image(name, style=''):
    return f'<img src="../assets/{name}" style="{style}" alt="{name}">'


def card(title, body, height=760, extra=''):
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>{CSS}{extra}</style>
<body><main class="canvas" style="height:{height}px">{body}<footer class="foot"><span>用 AI 做自己的桌面宠物</span><span>{title}</span></footer></main></body></html>'''


cards = {}
cards['01-公众号封面'] = card('项目实作 / 流程与提示词', f'''
<div style="position:absolute;width:530px;height:530px;border-radius:50%;background:#f5d5a2;right:-25px;top:15px"></div>
<div style="position:relative;z-index:2"><div class="eyebrow">我的 AI 桌宠制作记录</div>
<h1>把一张猫图<br>变成 <span class="orange">AI 桌宠</span></h1>
<p class="lead" style="margin-top:25px">定角色 · 做动作 · 让 AI 组装</p>
<p style="font-size:20px;color:#8a7257;margin-top:20px">附制作原理与可复制提示词</p></div>
{image('character.png','position:absolute;right:37px;top:31px;width:440px;height:420px;z-index:3')}
''', 510)

cards['02-制作路线'] = card('01 / 先把顺序理清楚', f'''
<div class="eyebrow">从一个角色 到一个桌面伙伴</div><h2>先定角色，再做动作，最后组装</h2>
<div class="row">
<section class="box"><div class="tag">01　角色定稿</div><div class="stage" style="height:280px">{image('character.png','height:265px')}</div><h3>始终是同一只猫</h3><p class="desc">固定脸型、毛色和比例<br>每次生成都带上参考图</p></section>
<section class="box"><div class="tag">02　制作动作</div><div class="stage" style="height:280px;background:#f9efde">{image('drag-sheet.png','height:268px')}</div><h3>让姿势连续起来</h3><p class="desc">小动作用连续图片<br>大动作用短视频</p></section>
<section class="box"><div class="tag">03　接入桌宠</div><div class="stage dark" style="height:280px">{image('actions.png','width:310px')}</div><h3>能操作，也能聊天</h3><p class="desc">描述点击与拖动规则<br>让 AI 实现并运行验证</p></section>
</div>''', 820)

cards['03-动作怎么做'] = card('02 / 动作素材的两条路线', f'''
<div class="eyebrow">素材制作</div><h2>小动作用图集，大动作用视频</h2>
<div class="row">
<section class="box"><div class="tag">路线 A　连续动作图</div><div class="stage" style="height:350px;background:#f8efdf">{image('drag-sheet.png','height:338px')}</div><h3 style="margin-top:18px">眨眼 / 挥爪 / 探头</h3><p class="desc">同一张脸，同一个位置<br>只让需要的部位动起来</p></section>
<section class="box"><div class="tag">路线 B　图片生成短视频</div><div class="stage" style="height:350px;background:#f8efdf">{image('play.png','height:345px')}</div><h3 style="margin-top:18px">翻滚 / 伸懒腰 / 吃饭</h3><p class="desc">固定镜头，身体不变形<br>全身始终留在画面内</p></section>
</div>''', 900)

cards['04-透明动画流程'] = card('03 / 先处理素材，再放进桌面', f'''
<div class="eyebrow">让动画稳定下来的关键</div><h2>去掉背景，还要统一大小与位置</h2>
<div class="row" style="gap:20px">
<section class="box" style="padding:20px"><div class="tag">① 原始视频</div><div class="stage" style="height:300px;background:#ecebe7"><video muted preload="auto" src="../assets/eating-source.mp4" style="width:100%;height:100%;object-fit:contain"></video></div><p class="desc">先检查动作和角色<br>再开始处理背景</p></section>
<section class="box" style="padding:20px"><div class="tag">② 透明角色</div><div class="stage checker" style="height:300px">{image('eat.png','width:285px')}</div><p class="desc">只去掉外部背景<br>保住毛发和白色身体</p></section>
<section class="box" style="padding:20px"><div class="tag">③ 放到桌面</div><div class="stage dark" style="height:300px">{image('eat.png','width:285px')}</div><p class="desc">整段统一画布与比例<br>再检查首尾循环</p></section>
</div><div class="statement">不要每张图片单独裁紧后放大，猫会忽大忽小。</div>''', 860)

cards['05-修复真实问题'] = card('04 / 来自项目的真实修复记录', f'''
<div class="eyebrow">具体反馈 比“再自然一点”更有用</div><h2>白色脚掌，被当成了背景</h2>
<div class="stage" style="height:505px;margin-top:25px;background:#262933">{image('paw-fix.jpg','height:505px;width:1030px')}</div>
<div class="statement" style="font-size:27px">“恢复身体内部，只去背景。其他满意的部分保持不变。”</div>''', 890)

cards['06-组装成桌宠'] = card('05 / 项目历史界面展示', f'''
<div class="eyebrow">把素材变成能用的小伙伴</div><h2>动作、交互、聊天，一项项接起来</h2>
<div class="row" style="height:480px">
<section class="box" style="flex:1.1"><div class="tag">点击菜单 · 切换动作</div><div class="stage dark" style="height:320px">{image('actions.png','width:450px;height:300px')}</div><p class="desc">默认待机，拖动后恢复</p></section>
<section class="box" style="flex:1"><div class="tag">接入聊天 · 设定性格</div><div class="stage" style="height:350px">{image('chat.png','height:350px')}</div><p class="desc" style="font-size:21px;margin-top:6px">性格靠设定，记忆需要真正实现</p></section>
</div>''', 760)

cards['07-视频号竖版封面'] = card('从一张角色图开始', f'''
<div style="position:absolute;width:1050px;height:1050px;background:#f5d29a;border-radius:50%;left:170px;top:550px"></div>
<div style="position:relative;z-index:2"><div class="eyebrow" style="font-size:27px;margin-top:80px">我的 AI 桌宠制作记录</div>
<h1 style="font-size:112px;line-height:1.23;margin-top:32px">让 AI<br>做一只<br><span class="orange">桌面宠物</span></h1>
<p style="font-size:35px;margin-top:35px;color:#786249">角色怎么定，动作怎么做？</p></div>
{image('character.png','position:absolute;left:170px;top:740px;width:780px;height:810px;z-index:3')}
<div style="position:absolute;left:80px;bottom:210px;font-size:35px;line-height:1.9">定角色 → 做动作 → 让 AI 组装<br><span style="color:#896c4a;font-size:28px">完整流程与提示词 · 项目实作</span></div>
''', 1920, '.canvas{width:1080px;padding:70px 80px}.foot{left:80px;right:80px;bottom:65px;font-size:22px}')

for name, content in cards.items():
    (OUT / '制作源文件' / f'{name}.html').write_text(content, encoding='utf-8')


def inline(text):
    text = html.escape(text)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def markdown_body(source):
    parts = []
    for block in source.strip().split('\n\n'):
        if block.startswith('!['):
            alt, src = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', block).groups()
            parts.append(f'<figure><img src="{src}" alt="{html.escape(alt)}"><figcaption>{html.escape(alt)}</figcaption></figure>')
        elif block.startswith('## '):
            parts.append('<h2>' + inline(block[3:]) + '</h2>')
        elif block.startswith('# '):
            parts.append('<h1>' + inline(block[2:]) + '</h1>')
        elif block.startswith('>'):
            parts.append('<blockquote>' + '<br>'.join(inline(line.lstrip('> ')) for line in block.splitlines()) + '</blockquote>')
        elif block.startswith('- '):
            parts.append('<ul>' + ''.join('<li>' + inline(line[2:]) + '</li>' for line in block.splitlines()) + '</ul>')
        else:
            parts.append('<p>' + inline(block).replace('\n', '<br>') + '</p>')
    return '\n'.join(parts)


article_css = '''
*{box-sizing:border-box}body{margin:0;background:#f4f0e8;color:#353029;font-family:"Microsoft YaHei","PingFang SC",sans-serif}
article{max-width:820px;margin:32px auto;background:#fffdf9;padding:48px 46px;border-radius:18px}
h1{font-size:34px;line-height:1.45;margin:0 0 24px;letter-spacing:-.5px}h2{font-size:25px;line-height:1.55;margin:48px 0 20px;color:#9f531e;border-top:1px solid #eddfce;padding-top:25px}
p,li{font-size:18px;line-height:1.95;margin:20px 0}strong{color:#ab541b}blockquote{margin:20px 0;padding:20px 24px;background:#fbf0de;border-left:4px solid #cf8540;border-radius:0 12px 12px 0;font-size:17px;line-height:1.9}
figure{margin:25px 0 32px}img{max-width:100%;display:block;border-radius:10px}figcaption{font-size:13px;color:#988571;line-height:1.6;margin-top:10px;text-align:center}ul{padding-left:25px}li{margin:9px 0}
@media(max-width:600px){body{background:#fffdf9}article{padding:24px 20px;margin:0;border-radius:0}h1{font-size:27px}h2{font-size:23px}p,li{font-size:17px}blockquote{font-size:16px;padding:16px 18px}}
'''
article = DATA['article']
(OUT / '公众号图文稿.md').write_text(article, encoding='utf-8')
(OUT / '公众号图文预览.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>这只 AI 桌宠是怎么做出来的</title><style>' + article_css + '</style><article>' + markdown_body(article) + '</article></html>', encoding='utf-8')

scenes = DATA['scenes']
video = ['# 视频号短视频文稿', '', '主题：这只 AI 桌宠是怎么做出来的。', '',
         '形式：竖版短视频，真人口播或配音，穿插项目真实图片和动作素材。目标时长约 90 秒；以下时码为剪辑预案，录音后按实际语速调整。', '',
         '## 可直接录制的口播', '', '\n\n'.join(scene['voice'] for scene in scenes), '', '## 分镜与屏幕文字', '']
for n, scene in enumerate(scenes, 1):
    video += [f"### 镜头 {n}　{scene['start']:02d} 至 {scene['end']:02d} 秒　{scene['title']}", '',
              '**口播：**' + scene['voice'], '', '**画面：**' + scene['visual'], '',
              '**屏幕短句：**' + scene['screen'], '', '**可用素材：**' + scene['asset'], '',
              '**剪辑说明：**' + scene['edit'], '']
video += ['## 发布文案', '',
          '这只住在桌面上的小猫，从角色图、动作素材到程序，都交给 AI 制作。分享这次项目的四步流程：定角色、做动作、处理素材、组装交互。也把抠图误删脚掌等踩坑过程放进来了。你会给自己的桌宠起什么名字？', '',
          '#AI桌面宠物 #AI创作 #桌面宠物 #制作过程', '', '## 配音和剪辑提醒', '',
          '先录完整口播，再按停顿切画面。背景音乐保持轻，不盖住讲解。不要同时展示整段提示词和大段字幕，屏幕短句只保留当前步骤的关键词。', '',
          '现有菜单和聊天图片为项目历史预览；若希望展示真实点击、拖动和回复过程，请补录当前程序。未补录时按素材展示剪辑，不把静态图片包装成连续实机操作。', '',
          '90秒字幕预排.srt 与这份口播同源，但尚未与实际录音对齐，录音后需要微调时间。']
(OUT / '视频号90秒口播与分镜.md').write_text('\n'.join(video), encoding='utf-8')


def stamp(seconds):
    ms = round(seconds * 1000)
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


srt = []
index = 1
for scene in scenes:
    pieces = re.findall(r'[^，。！？：；]+[，。！？：；]?', scene['voice'])
    chunks = []
    current = ''
    for part in pieces:
        if current and len(current + part) > 26:
            chunks.append(current)
            current = part
        else:
            current += part
    if current:
        chunks.append(current)
    total = sum(len(chunk) for chunk in chunks)
    position = scene['start']
    for i, chunk in enumerate(chunks):
        end = scene['end'] if i == len(chunks) - 1 else position + (scene['end'] - scene['start']) * len(chunk) / total
        # Keep subtitles to two short lines without changing the spoken words.
        if len(chunk) > 16:
            split = min(range(max(7, len(chunk)//2 - 3), min(len(chunk)-3, len(chunk)//2 + 4)), key=lambda p: abs(p-len(chunk)/2) - (4 if chunk[p-1] in '，：。' else 0))
            display = chunk[:split] + '\n' + chunk[split:]
        else:
            display = chunk
        srt += [str(index), f'{stamp(position)} --> {stamp(end)}', display, '']
        index += 1
        position = end
(OUT / '90秒字幕预排.srt').write_text('\n'.join(srt), encoding='utf-8-sig')

manifest = ['# 素材来源与编辑说明', '', '历史素材均从项目复制，保留原始文件内容。新增配图是用原素材进行文字排版和流程展示，没有重新生成角色，也没有把生成示意图冒充实机截图。', '',
            '| 稿件素材 | 项目来源 |', '| --- | --- |']
for name, source in SOURCES.items():
    manifest.append(f'| assets/{name} | {source} |')
manifest += ['', '## 新增版式', '',
             'images 中包含 6 张公众号横版配图和 1 张视频号竖版封面。公众号封面为 1200×510，流程配图宽 1200，竖版封面为 1080×1920。这是本套稿件的设计尺寸，上传时按编辑器实际裁切预览检查。', '',
             '04 号图左侧为 eating-source-v7.mp4 约第 1 秒的原视频画面，中间和右侧使用该动作处理后的第 30 帧，棋盘格只用于说明透明区域。05 号图内的修复前后对比保留历史预览中的原标注。', '',
             '公众号 HTML 为本地阅读与排版预览，发布时复制正文并按顺序上传 images 配图。本地 HTML 路径不会自动成为公众号可访问的图片地址。', '',
             '原始视频和动态 GIF 放在 assets，便于剪辑引用。本交付为图文、封面、视频文稿和字幕预排，不含已配音剪好的最终视频。']
(OUT / '素材来源与编辑说明.md').write_text('\n'.join(manifest), encoding='utf-8')

titles = '''# 发布标题与摘要

## 公众号

主标题：这只 AI 桌宠是怎么做出来的

备选标题：

- 我把一张猫图做成了 AI 桌宠，分享整套制作流程
- 从角色图到桌面伙伴，用 AI 做一只自己的宠物

摘要：定角色、做动作、去背景、接入聊天。用一只真实完成的橘猫桌宠，讲清 AI 制作流程，附提示词和修图前后对比。

封面：images/01-公众号封面.png。

## 视频号

主标题：让 AI 做一只自己的桌面宠物

短标题：一张猫图，怎么变成桌宠？

封面：images/07-视频号竖版封面.png。

文案：角色、动作、程序，都交给 AI 制作。我把这只橘猫桌宠的制作过程整理成四步，也保留了素材修复的真实对比。你想让什么角色住进自己的桌面？

话题：#AI桌面宠物 #AI创作 #桌面宠物 #制作过程

配套长文和视频分别发布后，再在平台允许的位置关联。此处不预设尚未生成的链接、二维码或领取口令。
'''
(OUT / '发布标题与摘要.md').write_text(titles, encoding='utf-8')

checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe')
    page = browser.new_page(viewport={'width': 1200, 'height': 2000}, device_scale_factor=1)
    for name in cards:
        page.goto((OUT / '制作源文件' / f'{name}.html').as_uri())
        page.evaluate('document.fonts.ready')
        page.wait_for_function('Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)')
        if page.locator('video').count():
            page.wait_for_function('document.querySelector("video").readyState >= 2')
            page.evaluate('document.querySelector("video").currentTime = 1.0')
            page.wait_for_function('!document.querySelector("video").seeking')
        page.locator('.canvas').screenshot(path=str(OUT / 'images' / f'{name}.png'))
        checks.append({'name': name, 'images': page.locator('img').count(), 'overflow': page.evaluate('Array.from(document.querySelectorAll(".box,.stage")).filter(e=>e.scrollHeight>e.clientHeight+2 || e.scrollWidth>e.clientWidth+2).map(e=>e.className)')})
    page.goto((OUT / '公众号图文预览.html').as_uri())
    page.wait_for_function('Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)')
    page.screenshot(path=str(OUT / '制作源文件/公众号桌面预览.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(OUT / '制作源文件/公众号手机预览.png'), full_page=True)
    checks.append({'name': 'mobile-article', 'horizontalOverflow': page.evaluate('document.documentElement.scrollWidth > innerWidth')})
    browser.close()

hashes = {name: hashlib.sha256((OUT / 'assets' / name).read_bytes()).hexdigest() for name in SOURCES}
(OUT / '制作源文件/检查记录.json').write_text(json.dumps({'render_checks': checks, 'asset_sha256': hashes, 'voice_characters': sum(len(s['voice']) for s in scenes), 'subtitle_blocks': index-1}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(checks, ensure_ascii=False))
print('Voice characters:', sum(len(s['voice']) for s in scenes), 'Subtitle blocks:', index-1)
