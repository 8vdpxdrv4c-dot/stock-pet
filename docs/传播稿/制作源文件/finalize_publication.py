from pathlib import Path
import html
import json
import re
import zipfile

from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parents[1]
data = json.loads((out / '制作源文件/content.json').read_text(encoding='utf-8'))
for path in out.glob('*.md'):
    for target in re.findall(r'!\[.*?\]\((.*?)\)', path.read_text(encoding='utf-8')):
        assert (out / target).is_file(), target

srt = (out / '90秒字幕预排.srt').read_text(encoding='utf-8-sig')
spoken = ''.join(s['voice'] for s in data['scenes'])
subtitle_text = ''.join(line for line in srt.splitlines() if line and not line.isdigit() and ' --> ' not in line)
assert spoken == subtitle_text, 'Subtitle text differs from voice script'
assert '00:01:30,000' in srt
assert data['scenes'][0]['start'] == 0 and data['scenes'][-1]['end'] == 90
assert all(a['end'] == b['start'] for a, b in zip(data['scenes'], data['scenes'][1:]))

script = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频号 90 秒口播与分镜</title><style>body{margin:0;background:#f7f2e9;color:#302b25;font-family:"Microsoft YaHei",sans-serif}main{max-width:900px;margin:0 auto;padding:40px 24px}h1{font-size:32px}h2{margin-top:40px}p{line-height:1.9}section{background:#fffdfa;border:1px solid #eadcc7;border-radius:16px;padding:24px;margin:20px 0}small{color:#947654}blockquote{margin:16px 0;padding:18px;background:#fbefdc;line-height:1.9}a{color:#aa5c28}figure{margin:16px 0}img{max-width:100%;max-height:340px;object-fit:contain}video{width:100%;max-height:340px}label{font-weight:700;color:#a4672b}</style><main><small>视频号 · 竖版短视频 · 剪辑预案</small><h1>让 AI 做一只自己的桌面宠物</h1><p>目标约 90 秒。以下为口播与剪辑预案，录音后按实际语速对齐字幕。</p><p><a href="视频号90秒口播与分镜.md">打开完整文字稿</a> · <a href="90秒字幕预排.srt">下载预排字幕</a> · <a href="index.html">返回内容包</a></p>']
media = ['assets/playing-loop.gif?v=paws-20261007', 'assets/eating-preview.mp4', 'assets/character.png', 'images/03-动作怎么做.png', 'images/04-透明动画流程.png', 'images/05-修复真实问题.png', 'assets/actions.png', 'assets/chat.png', 'images/07-视频号竖版封面.png']
for n, (scene, src) in enumerate(zip(data['scenes'], media), 1):
    script.append(f'<section><small>镜头 {n} / {scene["start"]:02d}—{scene["end"]:02d} 秒</small><h2 style="margin-top:10px">{scene["title"]}</h2>')
    if src.endswith('.mp4'):
        script.append(f'<video src="{src}" controls preload="metadata"></video>')
    else:
        script.append(f'<figure><img src="{src}" alt="镜头素材参考"></figure>')
    script.append(f'<blockquote>{html.escape(scene["voice"])}</blockquote><p><label>画面：</label>{html.escape(scene["visual"])}</p><p><label>屏幕短句：</label>{html.escape(scene["screen"])}</p><p><label>剪辑说明：</label>{html.escape(scene["edit"])}</p></section>')
script.append('</main></html>')
(out / '视频号分镜预览.html').write_text(''.join(script), encoding='utf-8')

index = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI 桌宠图文与视频文稿</title>
<style>*{box-sizing:border-box}body{margin:0;background:#faf3e7;color:#342c24;font-family:"Microsoft YaHei",sans-serif}main{max-width:1080px;margin:auto;padding:40px 24px}img{width:100%;border-radius:20px}h1{font-size:34px}p{line-height:1.8;color:#78634d}.row{display:grid;grid-template-columns:1fr 1fr;gap:20px}section{background:#fffefa;border:1px solid #ead8be;border-radius:20px;padding:28px;margin-top:20px}a{color:#ad5c24;text-decoration:none;display:block;line-height:2.1}small{color:#a7835a}@media(max-width:640px){.row{grid-template-columns:1fr}h1{font-size:27px}}</style>
<main><small>项目真实素材 · 公众号与视频号 · 待发布文稿</small><h1>用 AI 做一只自己的桌面宠物</h1><img src="images/01-公众号封面.png" alt="公众号封面">
<div class="row"><section><h2>公众号图文</h2><p>按制作顺序讲原理，配真实素材和可复制提示词。</p><a href="公众号图文预览.html">阅读图文预览 →</a><a href="公众号图文稿.md">正文 Markdown</a><a href="完整流程与提示词.md">完整流程与提示词</a></section>
<section><h2>视频号短视频</h2><p>约 90 秒口播，9 个镜头，附素材索引和字幕预排。</p><a href="视频号分镜预览.html">查看带画面的分镜 →</a><a href="视频号90秒口播与分镜.md">口播与分镜文字稿</a><a href="90秒字幕预排.srt">SRT 字幕预排</a><a href="images/07-视频号竖版封面.png">竖版封面</a></section></div>
<section><h2>发布准备</h2><a href="发布标题与摘要.md">标题、摘要与发布文案</a><a href="素材来源与编辑说明.md">素材来源与使用说明</a><p>已配好 6 张公众号横版图片和 1 张视频号竖版封面。发布公众号时，将正文与图片上传到编辑器；视频口播录制后再校准字幕时码。</p></section>
</main></html>'''
(out / 'index.html').write_text(index, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe')
    page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=1)
    page.goto((out/'公众号图文预览.html').as_uri())
    page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
    height = page.evaluate('document.documentElement.scrollHeight')
    for name, y in [('top',0),('middle',height//2),('end',height-844)]:
        page.evaluate('(y)=>scrollTo(0,y)',y)
        page.screenshot(path=str(out/'制作源文件'/f'mobile-{name}.png'))
    page.goto((out/'视频号分镜预览.html').as_uri())
    page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.screenshot(path=str(out/'制作源文件/video-storyboard-mobile.png'))
    browser.close()

archive = out.parent/'AI桌宠-公众号与视频号内容包.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(out.rglob('*')):
        if path.is_file() and '制作源文件' not in path.relative_to(out).parts:
            z.write(path, 'AI桌宠内容包/' + path.relative_to(out).as_posix())
print('Verified image links, continuous 90-second timeline, and exact voice/subtitle text match.')
print('Archive:',archive, 'bytes:',archive.stat().st_size)
