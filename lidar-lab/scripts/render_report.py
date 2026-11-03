#!/usr/bin/env python3
"""Render the lab guide using only the Python standard library."""
from pathlib import Path
import html, re
lab=Path(__file__).resolve().parents[1]
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'https://[A-Za-z0-9_./#?=\-&;%]+',lambda m:f'<a href="{m[0]}">{m[0]}</a>',s)
    return s
lines=(lab/'实验指导.md').read_text().splitlines();out=[];i=0
while i<len(lines):
    line=lines[i]
    if not line.strip():i+=1;continue
    if line.startswith('```'):
        block=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
        out.append('<div class="code"><button type="button">复制</button><pre>'+html.escape('\n'.join(block))+'</pre></div>')
    elif line.startswith('# '):out.append('<h1>'+inline(line[2:])+'</h1>')
    elif line.startswith('## '):out.append('<h2>'+inline(line[3:])+'</h2>')
    elif line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            row=lines[i];i+=1
            if re.fullmatch('[| :\-]+',row):continue
            rows.append([inline(c.strip()) for c in row.strip('|').split('|')])
        i-=1
        out.append('<table><thead><tr>'+''.join('<th>'+c+'</th>' for c in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in r)+'</tr>' for r in rows[1:])+'</tbody></table>')
    elif line.startswith('- '):
        items=[]
        while i<len(lines) and lines[i].startswith('- '):items.append(inline(lines[i][2:]));i+=1
        i-=1;out.append('<ul>'+''.join('<li>'+s+'</li>' for s in items)+'</ul>')
    else:out.append('<p>'+inline(line)+'</p>')
    i+=1
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C1 激光点云实验指导</title><style>
body{margin:0;background:#f4f7f8;color:#173039;font:16px/1.85 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}main{max-width:960px;margin:30px auto;padding:36px 50px;background:white}h1{font-size:31px;line-height:1.4}h2{font-size:23px;margin-top:36px;color:#146e7e}a{color:#146e7e}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 12px;border:1px solid #d5e3e7;text-align:left;vertical-align:top}th{background:#edf5f7}code{font:14px ui-monospace,monospace;background:#eef4f5;padding:2px 4px;overflow-wrap:anywhere}pre{font:14px/1.65 ui-monospace,monospace;overflow:auto;background:#173039;color:#e3f4f6;padding:24px 18px;border-radius:5px}.code{position:relative}.code button{position:absolute;right:8px;top:7px;background:#355761;color:white;border:0;border-radius:3px;padding:3px 8px;cursor:pointer}figure{margin:24px 0}img{max-width:100%;height:auto}figcaption{color:#5a747b;font-size:13px}.nav{border-bottom:1px solid #cedee2;padding-bottom:16px;display:flex;gap:20px;flex-wrap:wrap}footer{margin-top:35px;font-size:13px;color:#59747b}@media(max-width:700px){main{margin:0;padding:24px 18px}h1{font-size:27px}}@media print{body{background:white}main{margin:0;padding:0}button{display:none}pre{white-space:pre-wrap;background:#eef4f5;color:#173039}table,.code,figure{break-inside:avoid}}
</style><main><nav class="nav"><a href="boot-demo/实验指导.html">新增：开机屏幕点云实验</a><a href="点云回放.html">打开实测点云回放</a><a href="images/c1-replay.gif">查看回放动画</a><a href="实验指导.md">纯文本指导</a><a href="evidence/05-c1-capture.txt">实际采集输出</a></nav>'''+''.join(out)+'''<h2>本次真实点云图</h2><figure><img src="images/c1-point-cloud.png" alt="C1 实际单圈与 100 圈叠加点云"><figcaption>左：第 50 号扫描；右：100 圈有效测距叠加。所有点来自板卡 CSV。</figcaption></figure><footer>2026-10-27 · mingkang ma · 523031910621</footer></main><script>document.querySelectorAll('.code button').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(b.parentElement.querySelector('pre').textContent);b.textContent='已复制';setTimeout(()=>b.textContent='复制',1500)}catch(e){b.textContent='请选中文本复制'}});</script></html>'''
(lab/'实验指导.html').write_text(page)
print(lab/'实验指导.html')
