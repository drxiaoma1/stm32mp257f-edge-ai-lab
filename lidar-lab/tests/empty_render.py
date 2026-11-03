#!/usr/bin/env python3
"""Off-screen regression only. Synthetic input must never be presented as a measurement."""
import csv
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, '/opt/c1-lab')
from render_pointcloud import render
with tempfile.TemporaryDirectory(prefix='c1-empty-regression-') as directory:
    root = Path(directory)
    csv_path = root / 'empty.csv'
    with csv_path.open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['scan_id','elapsed_s','angle_deg','distance_m','quality','valid','x_m','y_m'])
        for index in range(512):
            writer.writerow([1,1,index*360/512,0,0,0,'',''])
    metadata = {'live':True,'timed':False,'sequence':1,'elapsed_seconds':1,'frames':1,
                'samples':512,'valid_points':0,'total_frames':1,'stop_command_ok':False}
    Path(str(csv_path)+'.json').write_text(json.dumps(metadata))
    result = render(csv_path,root/'empty.png','test-only','test-only','TEST ONLY','TEST ONLY','manual')
    assert result['valid_points'] == 0
    assert (root/'empty.png').read_bytes().startswith(b'\x89PNG')
    print('PASS: all-invalid live frame renders empty axes without exiting or replaying old points.')
