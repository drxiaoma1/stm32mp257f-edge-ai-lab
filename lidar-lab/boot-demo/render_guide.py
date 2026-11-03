#!/usr/bin/env python3
"""Render a self-contained offline guide; screenshots remain local files."""
from pathlib import Path
import html,json,re
root=Path(__file__).resolve().parent
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
lines=(root/'README.md').read_text().splitlines();out=[];i=0
while i<len(lines):
    line=lines[i]
    if line.startswith('```'):
        code=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
        out.append('<pre>'+html.escape('\n'.join(code))+'</pre>')
    elif line.startswith('# '):out.append('<h1>'+inline(line[2:])+'</h1>')
    elif line.startswith('## '):out.append('<h2>'+inline(line[3:])+'</h2>')
    elif line.strip():out.append('<p>'+inline(line)+'</p>')
    i+=1
evidence=root/'evidence/cold-power-on'
label='实际断电上电'
if not (evidence/'observation.json').exists():evidence=root/'evidence/manual-final';label='姓名修正后指令启动实测（物理上电验证已按用户要求暂缓）'
state=json.loads((evidence/'state.json').read_text()) if (evidence/'state.json').exists() else {}
shots=''
for name,caption in [('hello','先执行并显示 Hello World'),('complete','随后显示本次 10 秒扫描结果')]:
    file=evidence/f'{name}-screen.png'
    if file.exists():shots+=f'<figure><img src="{file.relative_to(root)}" alt="{caption}"><figcaption>{label}：{caption}。截图直接来自板卡 HDMI 输出。</figcaption></figure>'
summary=''
if state:
    cap=state['capture'];summary=f'<p>{label}：{cap["scan_window_seconds"]:.6f} 秒，{cap["frames"]} 圈，{cap["valid_points"]:,} 个有效点。内核 {state["kernel"]}；启动编号 <code>{state["boot_id"]}</code>。</p>'
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C1 开机扫描与屏幕显示</title><style>
body{font:16px/1.8 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:#eff5f7;color:#173039}main{max-width:1000px;margin:28px auto;padding:36px 42px;background:white}h1{font-size:30px;line-height:1.4}h2{font-size:23px;color:#116b7a;margin-top:36px}code{font:14px ui-monospace,monospace;background:#edf3f5;padding:2px 4px;overflow-wrap:anywhere}pre{font:14px/1.65 ui-monospace,monospace;background:#163039;color:#e5f6f7;padding:18px;overflow:auto;border-radius:5px}img{max-width:100%;height:auto}figure{margin:22px 0}figcaption{font-size:13px;color:#60747a}a{color:#116b7a}nav{display:flex;gap:22px;flex-wrap:wrap;border-bottom:1px solid #d3e3e8;padding-bottom:15px}.result{background:#eef8f5;padding:16px 20px;margin:20px 0}@media(max-width:700px){main{margin:0;padding:22px}h1{font-size:25px}}@media print{main{margin:0;padding:0}pre{white-space:pre-wrap;color:#173039;background:#edf3f5}figure,pre{break-inside:avoid}}
</style><main><nav><a href="output/c1-boot-demo.tar.gz">离线板卡安装包</a><a href="README.md">文字版指导</a><a href="../实验指导.html">WEEK8 原实验</a></nav>'''
page+='<div class="result"><strong>实际结果</strong>'+summary+'</div>'+shots+''.join(out)+'</main></html>'
(root/'实验指导.html').write_text(page)
print(root/'实验指导.html')
