#!/usr/bin/env python3
"""Render measured CSV on the board with its existing Cairo installation."""
import csv, json, math
from pathlib import Path
import cairo

def text(cr,x,y,s,size=16,color=(.09,.18,.23),bold=False):
    cr.set_source_rgb(*color)
    cr.select_font_face('Sans',cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size);cr.move_to(x,y);cr.show_text(str(s))

def render(csv_path,png_path,boot_id,kernel,student_name='mingkang ma',student_id='523031910621'):
    csv_path=Path(csv_path)
    meta=json.loads(Path(str(csv_path)+'.json').read_text())
    points=[]; frames=set(); below=0
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            frames.add(int(row['scan_id']))
            if int(row['valid']):
                d=float(row['distance_m']);points.append((float(row['x_m']),float(row['y_m']),d))
                below += d < .05
    if not points: raise RuntimeError('No valid points to draw')
    full=max(1,math.ceil(max(max(abs(x),abs(y)) for x,y,d in points)))
    surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,1024,600);cr=cairo.Context(surface)
    cr.set_source_rgb(.97,.985,.99);cr.paint()
    text(cr,24,35,'RPLIDAR C1 | automatic 10-second scan',25,bold=True)
    text(cr,24,63,f'{student_name}  |  {student_id}',18)
    text(cr,24,89,f"{meta['scan_window_seconds']:.3f} s scan window  |  {len(frames)} scans  |  {len(points):,} valid returns  |  {meta['scan_rate_hz']:.2f} Hz",16)
    for left,limit,label in [(54,full,f'Full view: +/-{full} m'),(564,1,'Near view: +/-1 m')]:
        top=140;size=350;mid_x=left+size/2;mid_y=top+size/2;scale=size/(limit*2)
        text(cr,left,top-18,label,18,bold=True)
        cr.set_source_rgb(1,1,1);cr.rectangle(left,top,size,size);cr.fill()
        for i in range(5):
            pos=left+size*i/4;py=top+size*i/4
            cr.set_source_rgb(.85,.89,.91);cr.set_line_width(1)
            cr.move_to(pos,top);cr.line_to(pos,top+size);cr.move_to(left,py);cr.line_to(left+size,py);cr.stroke()
            value=-limit+i*limit/2
            text(cr,pos-12,top+size+22,f'{value:g}',13)
            text(cr,left-38,py+5,f'{-value:g}',13)
        cr.save();cr.rectangle(left,top,size,size);cr.clip()
        for x,y,d in points:
            if abs(x)>limit or abs(y)>limit:continue
            cr.set_source_rgba(*((.88,.49,.07,.35) if d<.05 else (.04,.46,.58,.12)))
            cr.arc(mid_x+x*scale,mid_y-y*scale,1.25,0,2*math.pi);cr.fill()
        cr.restore();cr.set_source_rgb(.86,.23,.17);cr.set_line_width(2)
        cr.move_to(mid_x-7,mid_y);cr.line_to(mid_x+7,mid_y);cr.move_to(mid_x,mid_y-7);cr.line_to(mid_x,mid_y+7);cr.stroke()
        text(cr,left+size-28,top+size+42,'x (m)',14);text(cr,left-22,top-7,'y (m)',13)
    text(cr,24,551,f'Scan complete; SDK stop() returned OK. Orange: {below} returns below 0.05 m.',14)
    text(cr,24,574,f'Kernel: {kernel}  |  Boot: {boot_id}',12)
    text(cr,24,593,'Measured 2D points in sensor coordinates. Esc: close display.',12)
    temp=Path(str(png_path)+'.tmp');surface.write_to_png(str(temp));temp.replace(png_path)
    return {'frames':len(frames),'valid_points':len(points),'below_0_05m':below,**meta}

if __name__=='__main__':
    import sys,os
    if len(sys.argv)!=3:raise SystemExit('Usage: render_pointcloud.py input.csv output.png')
    result=render(sys.argv[1],sys.argv[2],Path('/proc/sys/kernel/random/boot_id').read_text().strip(),os.uname().release)
    print(json.dumps(result))
