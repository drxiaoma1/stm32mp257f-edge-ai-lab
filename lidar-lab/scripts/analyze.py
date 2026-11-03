#!/usr/bin/env python3
"""Validate CSV, export PCD and a self-contained HTML replay; optionally plot with matplotlib."""
import argparse, csv, hashlib, json, math, statistics, os, shutil
from pathlib import Path

lab = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('csv', nargs='?', type=Path, default=lab/'data/c1-20261027-100scans.csv')
p.add_argument('--output-dir', type=Path, help='Save this run separately without replacing earlier results')
p.add_argument('--log', type=Path, help='Actual acquisition log for this run')
p.add_argument('--condition', default='Initial capture', help='Short description of the measurement setup')
a = p.parse_args()
out = a.output_dir.resolve() if a.output_dir else lab
(out/'data').mkdir(parents=True,exist_ok=True)
csv_copy = out/'data'/a.csv.name
if a.csv.resolve() != csv_copy.resolve(): shutil.copy2(a.csv,csv_copy)
rows = list(csv.DictReader(a.csv.open()))
frames = {}
for r in rows:
    fid = int(r['scan_id'])
    angle, distance, quality = float(r['angle_deg']), float(r['distance_m']), int(r['quality'])
    assert 0 <= angle < 360 and distance >= 0
    assert abs(angle-int(r['angle_z_q14'])*90/16384) < 1e-6
    assert abs(distance-int(r['dist_mm_q2'])/4000) < 1e-6
    assert quality == int(r['quality_raw']) >> 2
    valid = int(r['valid'])
    assert valid == int(distance > 0 and quality > 0)
    f = frames.setdefault(fid, {'id':fid, 'time':float(r['elapsed_s']), 'samples':0, 'points':[]})
    assert f['time'] == float(r['elapsed_s'])
    f['samples'] += 1
    if valid:
        x,y = float(r['x_m']),float(r['y_m'])
        assert abs(x-distance*math.cos(math.radians(angle))) < 1e-6
        assert abs(y+distance*math.sin(math.radians(angle))) < 1e-6
        f['points'].append([x,y,distance,quality])
    else:
        assert r['x_m'] == r['y_m'] == ''
frames = [frames[k] for k in sorted(frames)]
assert [f['id'] for f in frames] == list(range(len(frames)))
assert all(y['time'] > x['time'] for x,y in zip(frames,frames[1:]))
points = [v for f in frames for v in f['points']]
assert points
rate = (len(frames)-1)/(frames[-1]['time']-frames[0]['time']) if len(frames)>1 else 0
selected = frames[len(frames)//2]
limit = math.ceil(max(abs(v) for point in points for v in point[:2]))
summary = {'date':'2026-10-27', 'name':'mingkang ma','student_id':'523031910621',
 'model':'RPLIDAR C1M1','board':'STM32MP257F-DK','kernel':'6.6.78-gkc-sdk',
 'condition':a.condition,'source_csv':a.csv.name,
 'scans':len(frames),'samples':len(rows),'valid_points':len(points),
 'valid_percent':100*len(points)/len(rows),'scan_rate_hz':rate,
 'min_distance_m':min(v[2] for v in points),'max_distance_m':max(v[2] for v in points),
 'selected_scan_id':selected['id'],'selected_scan_valid_points':len(selected['points']),
 'csv_sha256':hashlib.sha256(a.csv.read_bytes()).hexdigest(),
 'coordinates':'x=r*cos(theta), y=-r*sin(theta), z=0; SDK theta is clockwise; SDK zero is +x.',
 'meaning':'Actual 2D lidar scans, no pose estimation or SLAM; stacked scans are not a reconstructed map.'}
(out/'data/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
pcd = out/f"data/scan-{selected['id']:03d}.pcd"
with pcd.open('w') as stream:
    n=len(selected['points'])
    stream.write('# .PCD v0.7 - real C1 scan; z=0 (2D sensor)\nVERSION 0.7\nFIELDS x y z quality\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n')
    stream.write(f'WIDTH {n}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {n}\nDATA ascii\n')
    for x,y,_,q in selected['points']: stream.write(f'{x:.6f} {y:.6f} 0.000000 {q}\n')
template = (lab/'scripts/viewer-template.html').read_text()
template = template.replace('href="实验指导.html"',f'href="{os.path.relpath(lab/"实验指导.html",out)}"')
template = template.replace('data/c1-20261027-100scans.csv','data/'+csv_copy.name)
log_target = os.path.relpath(a.log.resolve(),out) if a.log else 'data/summary.json'
template = template.replace('evidence/05-c1-capture.txt',log_target).replace('本次实验日志','采集记录 / 统计')
payload = json.dumps({'summary':summary,'frames':frames,'limit':limit},ensure_ascii=False,separators=(',',':'))
(out/'点云回放.html').write_text(template.replace('__DATA_JSON__',payload).replace('__PCD_FILE__',pcd.name))
print(json.dumps(summary,ensure_ascii=False,indent=2))
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    import numpy as np
except ImportError:
    print('HTML replay and PCD are ready. Optional PNG/GIF export needs matplotlib; no package is needed to open the HTML.')
    raise SystemExit(0)
image_dir=out/'images';image_dir.mkdir(exist_ok=True)
xs=[v[0] for v in points]+[0];ys=[v[1] for v in points]+[0]
xpad=max(.2,(max(xs)-min(xs))*.1);ypad=max(.2,(max(ys)-min(ys))*.06)
xlim=(min(xs)-xpad,max(xs)+xpad);ylim=(min(ys)-ypad,max(ys)+ypad)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(1,2,figsize=(13.5,7),layout='constrained')
fig.suptitle('RPLIDAR C1 | measured 2D point cloud',fontsize=20,fontweight='bold')
for ax,pts,title in [(axes[0],selected['points'],f"Single revolution #{selected['id']} | {len(selected['points'])} valid points"),
                     (axes[1],points,f"{len(frames)} revolutions overlaid | {len(points):,} valid points")]:
    ar=np.asarray(pts)
    ax.scatter(ar[:,0],ar[:,1],s=12 if ax==axes[0] else 2,c='#147d92',alpha=.9 if ax==axes[0] else .13,linewidths=0)
    ax.scatter([0],[0],marker='+',s=120,c='#e15635',linewidths=2,label='Lidar origin')
    ax.set_title(title,fontsize=12,pad=12)
    # Same limits and scale across views; show the full measured extent.
    ax.set_xlim(*xlim);ax.set_ylim(*ylim)
    ax.set_aspect('equal');ax.grid(alpha=.23)
    ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.legend(loc='upper left',fontsize=9)
fig.supxlabel(f"mingkang ma | 523031910621     {rate:.2f} Hz | 460800 baud | 2026-10-27\nSDK zero = +x; clockwise angles mapped to negative y. 2D scans; no SLAM or 3D reconstruction.",fontsize=10)
fig.savefig(image_dir/'c1-point-cloud.png',dpi=160)
plt.close(fig)
fig,ax=plt.subplots(figsize=(7,7),layout='constrained')
ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_aspect('equal');ax.grid(alpha=.2)
ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
ax.scatter([0],[0],marker='+',s=90,c='#e15635')
dots=ax.scatter([],[],s=12,c='#147d92',linewidths=0)
heading=ax.set_title('')
fig.supxlabel('RPLIDAR C1 | recorded data replay\nmingkang ma | 523031910621',fontsize=10)
def update(i):
    f=frames[i]
    dots.set_offsets(np.asarray(f['points'])[:,:2])
    heading.set_text(f"Scan {i+1}/{len(frames)} | t = {f['time']-frames[0]['time']:.2f} s")
    return dots,heading
anim=FuncAnimation(fig,update,frames=range(0,len(frames),2),interval=200,blit=False)
anim.save(image_dir/'c1-replay.gif',writer=PillowWriter(fps=5),dpi=100)
plt.close(fig)
print('CSV checks passed; HTML, PCD, PNG and GIF exported.')
