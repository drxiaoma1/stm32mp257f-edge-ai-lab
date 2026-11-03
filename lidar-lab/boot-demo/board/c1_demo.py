#!/usr/bin/env python3
"""Hello World, then a timed C1 scan, then a locally generated point-cloud image."""
import json,os,signal,subprocess,time
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,Gdk
import cairo
from render_pointcloud import render,text

class Demo:
    def __init__(self):
        self.boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.root=Path('/var/lib/c1-lab');self.root.mkdir(exist_ok=True)
        self.run=self.root/'runs'/f'{self.boot[:8]}-{time.time_ns()}'
        self.run.mkdir(parents=True)
        link=self.root/f'.latest-{os.getpid()}'
        link.symlink_to(self.run);link.replace(self.root/'latest')
        self.status={'boot_id':self.boot,'kernel':os.uname().release,'run_directory':str(self.run),'phase':'initializing','seconds':10}
        self.proc=None;self.log=None;self.surface=None;self.hello='';self.error=''
        self.student_name='';self.student_id=''
        self.window=Gtk.Window(title='Hello World and C1 point cloud')
        self.window.set_default_size(1024,600);self.window.fullscreen()
        self.area=Gtk.DrawingArea();self.window.add(self.area)
        self.area.connect('draw',self.draw)
        self.window.connect('destroy',lambda *a:Gtk.main_quit())
        self.window.connect('key-press-event',self.key)
        signal.signal(signal.SIGINT,lambda *a:GLib.idle_add(self.close))
        signal.signal(signal.SIGTERM,lambda *a:GLib.idle_add(self.close))
        self.window.show_all()
        GLib.idle_add(self.begin_hello)
    def phase(self,name,**values):
        self.status.update(values);self.status['phase']=name
        self.status[name+'_uptime_s']=float(Path('/proc/uptime').read_text().split()[0])
        tmp=self.run/'state.json.tmp';tmp.write_text(json.dumps(self.status,indent=2)+'\n');tmp.replace(self.run/'state.json')
        print('C1_DEMO',json.dumps(self.status),flush=True);self.area.queue_draw()
    def begin_hello(self):
        try:
            p=subprocess.run(['/opt/hello-lab/hello_world'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
            self.hello=p.stdout;(self.run/'hello.txt').write_text(self.hello)
            if p.returncode:raise RuntimeError(f'Hello World exited with {p.returncode}')
            fields={line.split(':',1)[0].strip():line.split(':',1)[1].strip() for line in self.hello.splitlines() if ':' in line}
            self.student_name=fields.get('Name',fields.get('Student',''))
            self.student_id=fields.get('Student ID','')
            if not self.student_name or not self.student_id:raise RuntimeError('Hello World must print Name: (or Student:) and Student ID:')
            self.phase('hello',hello_exit_status=p.returncode,student_name=self.student_name,student_id=self.student_id)
            GLib.timeout_add_seconds(7,self.start_scan)
        except Exception as e:self.fail(e)
        return False
    def start_scan(self):
        try:
            if not Path('/dev/c1lidar').exists():raise RuntimeError('C1 not found at /dev/c1lidar. Check USB cable, then run c1ctl start.')
            self.log=(self.run/'capture.log').open('w')
            environment=dict(os.environ,C1_STUDENT_NAME=self.student_name,C1_STUDENT_ID=self.student_id)
            self.proc=subprocess.Popen(['/usr/bin/flock','-n','-F',str(self.root/'serial.lock'),'/opt/c1-lab/c1_capture','/dev/c1lidar','--seconds','10',str(self.run/'scan.csv')],stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True,env=environment)
            self.phase('scanning',capture_pid=self.proc.pid)
            GLib.timeout_add(200,self.poll)
        except Exception as e:self.fail(e)
        return False
    def poll(self):
        code=self.proc.poll()
        if code is None:return True
        self.log.close();self.log=None
        try:
            if code:raise RuntimeError(f'C1 capture exited with {code}. See {self.run}/capture.log')
            self.phase('rendering',capture_exit_status=code)
            result=render(self.run/'scan.csv',self.run/'pointcloud.png',self.boot,os.uname().release,self.student_name,self.student_id)
            if abs(result['scan_window_seconds']-10)>.15:raise RuntimeError('Measured scan duration outside 10 s +/- 0.15 s')
            self.surface=cairo.ImageSurface.create_from_png(str(self.run/'pointcloud.png'))
            self.phase('complete',capture=result,image=str(self.run/'pointcloud.png'))
        except Exception as e:self.fail(e)
        return False
    def fail(self,error):
        self.error=str(error);self.phase('failed',error=self.error)
    def key(self,widget,event):
        if event.keyval==Gdk.KEY_Escape:self.close()
    def close(self):
        self.window.destroy();return False
    def cleanup(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid,signal.SIGINT)
            try:self.proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid,signal.SIGTERM);self.proc.wait(timeout=5)
        if self.log:self.log.close()
    def draw(self,widget,cr):
        width,height=widget.get_allocated_width(),widget.get_allocated_height()
        cr.set_source_rgb(.015,.04,.055);cr.paint()
        scale=min(width/1024,height/600);cr.translate((width-1024*scale)/2,(height-600*scale)/2);cr.scale(scale,scale)
        if self.surface:cr.set_source_surface(self.surface,0,0);cr.paint();return False
        text(cr,30,45,'HELLO WORLD  ->  C1 POINT CLOUD',27,(.2,.9,.92),True)
        cr.select_font_face('Monospace',cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_NORMAL);cr.set_font_size(18);cr.set_source_rgb(.92,.96,.96)
        for i,line in enumerate(self.hello.splitlines()[:17]):cr.move_to(32,94+i*24);cr.show_text(line)
        stage=self.status['phase']
        message={'hello':'Next: automatic C1 scan for 10 seconds...','scanning':'Scanning C1 for 10 seconds... Please keep the scene still.','rendering':'Creating the point-cloud image on this board...','failed':self.error}.get(stage,'Starting...')
        text(cr,30,538,message[:105],17,(1,.65,.3) if stage=='failed' else (.2,.9,.92))
        text(cr,30,575,f'{self.student_name} | {self.student_id} | '+os.uname().release,16,(.7,.8,.84))
        return False

if __name__=='__main__':
    app=Demo()
    try:Gtk.main()
    finally:app.cleanup()
