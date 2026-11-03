from pathlib import Path
import csv,json,statistics,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
run=Path(__file__).resolve().parent
lab=run.parents[1]
paths=[lab/'data/c1-20261027-100scans.csv',run/'data/c1-20261027-obstacles-100scans.csv']
records=[]; cloud=[]
for p in paths:
 rows=list(csv.DictReader(p.open()));valid=[r for r in rows if int(r['valid'])]
 distance=[float(r['distance_m']) for r in valid]
 records.append({'csv':p.name,'valid_points':len(valid),'within_0_30m':sum(d<.3 for d in distance),'within_0_30m_percent':100*sum(d<.3 for d in distance)/len(valid),'below_0_05m':sum(d<.05 for d in distance),'minimum_reported_m':min(distance),'maximum_reported_m':max(distance)})
 cloud.append(np.array([[float(r['x_m']),float(r['y_m']),float(r['distance_m'])] for r in valid]))
(run/'data/comparison.json').write_text(json.dumps(records,indent=2)+'\n')
fig,axes=plt.subplots(1,3,figsize=(15,6),layout='constrained')
fig.suptitle('C1 | nearby obstacle experiment',fontsize=21,fontweight='bold')
for idx,ax in enumerate(axes):
 pts=cloud[0 if idx==0 else 1];limit=1 if idx<2 else .3
 in_view=(abs(pts[:,0])<=limit)&(abs(pts[:,1])<=limit); pts=pts[in_view]
 normal=pts[:,2]>=.05
 ax.scatter(pts[normal,0],pts[normal,1],s=2.5,c='#167d92',alpha=.18,linewidths=0)
 if any(~normal): ax.scatter(pts[~normal,0],pts[~normal,1],s=4,c='#d48616',alpha=.35,linewidths=0,label='Reported range < 5 cm')
 ax.scatter([0],[0],marker='+',s=130,c='#d34838',linewidths=2,label='Lidar origin')
 ax.set_xlim(-limit,limit);ax.set_ylim(-limit,limit);ax.set_aspect('equal');ax.grid(alpha=.2)
 ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
 ax.set_title(['Previous capture | 100 scans','Obstacles added | 100 scans','Current capture | close-up'][idx],fontsize=12,pad=12)
 if idx==2:
  ax.add_patch(plt.Circle((0,0),.05,fill=False,edgecolor='#d48616',linestyle='--',linewidth=1))
  ax.legend(loc='upper right',fontsize=8)
 else:
  s=records[idx];ax.text(.03,.96,f"Returns < 0.30 m: {s['within_0_30m_percent']:.1f}%",transform=ax.transAxes,va='top',fontsize=10,bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
fig.supxlabel('mingkang ma | 523031910621 | 2026-10-27\nEach scan uses its own sensor frame; no pose registration. Orange points are below the rated 0.05 m minimum.',fontsize=10)
fig.savefig(run/'images/nearby-obstacles-comparison.png',dpi=165)
print(json.dumps(records,indent=2))
