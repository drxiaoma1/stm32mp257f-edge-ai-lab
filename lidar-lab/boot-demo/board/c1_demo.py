#!/usr/bin/env python3
"""Touch application: one boot scan, repeatable user-space manual scans, saved results."""
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Gio, GdkPixbuf
from render_pointcloud import render

ROOT = Path('/var/lib/c1-lab')
SECONDS = 10


def uptime():
    return float(Path('/proc/uptime').read_text().split()[0])


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


class LidarApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.gkc.C1Lab', flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.proc = None
        self.log = None
        self.surface = None
        self.run_dir = None
        self.state = {}
        self.busy = False
        self.hello = ''
        self.student_name = ''
        self.student_id = ''
        self.boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.boot_dir = ROOT / 'boots' / self.boot
        self.auto_dir = self.boot_dir / 'automatic'
        self.boot_dir.mkdir(parents=True, exist_ok=True)
        self.auto_state = self.auto_dir / 'state.json'
        self.hello_path = self.boot_dir / 'hello.txt'
        self.connect('command-line', self.command_line)
        signal.signal(signal.SIGINT, lambda *args: GLib.idle_add(self.quit))
        signal.signal(signal.SIGTERM, lambda *args: GLib.idle_add(self.quit))

    def command_line(self, app, command):
        args = command.get_arguments()[1:]
        if any(arg not in ('--home', '--manual') for arg in args):
            command.printerr('Usage: c1_demo.py [--home|--manual]\n')
            return 2
        first = self.window is None
        if first:
            self.build_window()
            try:
                self.prepare_identity()
            except Exception as error:
                self.show_error(str(error))
                return 1
        self.window.show_all()
        self.window.present()
        if self.busy:
            return 0
        if '--manual' in args:
            GLib.idle_add(self.start_scan, 'manual')
        elif '--home' in args:
            self.show_home()
        elif first and not self.auto_state.exists():
            GLib.idle_add(self.start_scan, 'automatic')
        elif first:
            # Restarting the UI must not print Hello again or launch another boot scan.
            self.show_home()
        return 0

    def build_window(self):
        css = Gtk.CssProvider()
        css.load_from_path('/opt/c1-lab/style.css')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title='C1 Lidar Lab')
        self.window.set_default_size(1024, 600)
        self.window.fullscreen()
        self.window.connect('delete-event', self.hide_window)
        self.window.connect('key-press-event', self.key)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(layout)
        header = Gtk.Box(spacing=12)
        header.get_style_context().add_class('header')
        self.home_button = self.button('Home', self.show_home)
        header.pack_start(self.home_button, False, False, 0)
        self.title = Gtk.Label(label='C1 LIDAR LAB', xalign=0)
        self.title.get_style_context().add_class('title')
        header.pack_start(self.title, True, True, 0)
        self.stop_button = self.button('Stop', self.stop_scan)
        self.stop_button.get_style_context().add_class('stop')
        self.stop_button.set_no_show_all(True)
        header.pack_start(self.stop_button, False, False, 0)
        self.desktop_button = self.button('Desktop', self.hide_window)
        header.pack_end(self.desktop_button, False, False, 0)
        layout.pack_start(header, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        layout.pack_start(self.stack, True, True, 0)
        self.build_home()
        self.build_progress()
        self.build_result()
        self.build_error()
        self.footer = Gtk.Label(xalign=0)
        self.footer.get_style_context().add_class('footer')
        layout.pack_end(self.footer, False, False, 0)
        self.window.show_all()

    @staticmethod
    def button(label, callback):
        button = Gtk.Button(label=label) if label else Gtk.Button()
        button.connect('clicked', lambda widget: callback())
        return button

    def build_home(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(20)
        title = Gtk.Label(label='Explore your surroundings', xalign=0)
        title.get_style_context().add_class('hero')
        box.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label='Tap Start scanning. The live view refreshes every second until you tap Stop.', xalign=0)
        box.pack_start(subtitle, False, False, 0)
        cards = Gtk.Box(spacing=22, homogeneous=True)
        scan = self.button('', lambda: self.start_scan('manual'))
        scan.get_style_context().add_class('scan-card')
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(16)
        icon = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale('/opt/c1-lab/c1-icon.png', 96, 96, True))
        content.pack_start(icon, True, True, 0)
        label = Gtk.Label(label='Start scanning')
        label.get_style_context().add_class('hero')
        content.pack_start(label, False, False, 0)
        content.pack_start(Gtk.Label(label='C1  /  Continuous live view'), False, False, 0)
        scan.add(content)
        cards.pack_start(scan, True, True, 0)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, homogeneous=True)
        self.auto_button = self.button('View boot scan', lambda: self.show_saved(self.auto_dir))
        self.last_button = self.button('View latest scan', lambda: self.show_saved(ROOT / 'latest'))
        side.pack_start(self.auto_button, True, True, 0)
        side.pack_start(self.last_button, True, True, 0)
        cards.pack_start(side, True, True, 0)
        box.pack_start(cards, True, True, 0)
        self.home_status = Gtk.Label(xalign=0)
        box.pack_start(self.home_status, False, False, 0)
        self.stack.add_named(box, 'home')

    def build_progress(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(26)
        self.progress_title = Gtk.Label(xalign=0)
        self.progress_title.get_style_context().add_class('hero')
        box.pack_start(self.progress_title, False, False, 0)
        self.hello_label = Gtk.Label(xalign=0, yalign=0)
        self.hello_label.get_style_context().add_class('terminal')
        box.pack_start(self.hello_label, True, True, 0)
        self.progress = Gtk.ProgressBar(show_text=True)
        box.pack_start(self.progress, False, False, 0)
        self.stack.add_named(box, 'progress')

    def build_result(self):
        self.area = Gtk.DrawingArea()
        self.area.connect('draw', self.draw_result)
        self.stack.add_named(self.area, 'result')

    def build_error(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_border_width(36)
        label = Gtk.Label(label='Scan unavailable', xalign=0)
        label.get_style_context().add_class('hero')
        box.pack_start(label, False, False, 0)
        self.error_label = Gtk.Label(xalign=0)
        self.error_label.set_line_wrap(True)
        box.pack_start(self.error_label, True, True, 0)
        box.pack_start(self.button('Return home', self.show_home), False, False, 0)
        self.stack.add_named(box, 'error')

    def prepare_identity(self):
        if not self.hello_path.exists():
            legacy = ROOT / 'latest' / 'hello.txt'
            # Preserve a Hello already printed by the previous UI in this same boot.
            if legacy.exists() and f'Boot ID: {self.boot}' in legacy.read_text():
                self.hello_path.write_text(legacy.read_text())
            else:
                result = subprocess.run(['/opt/hello-lab/hello_world'], stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, timeout=5)
                if result.returncode:
                    raise RuntimeError(result.stdout)
                self.hello_path.write_text(result.stdout)
                print('HELLO_USER_OUTPUT_BEGIN\n' + result.stdout + 'HELLO_USER_OUTPUT_END', flush=True)
        self.hello = self.hello_path.read_text()
        fields = dict(line.split(':', 1) for line in self.hello.splitlines() if ':' in line)
        self.student_name = fields.get('Name', '').strip()
        self.student_id = fields.get('Student ID', '').strip()
        if not self.student_name or not self.student_id:
            raise RuntimeError('Hello World must print Name: and Student ID:.')
        self.footer.set_text(f'{self.student_name}   |   {self.student_id}   |   Linux {os.uname().release}')

    def phase(self, name, **values):
        self.state.update(values)
        self.state['phase'] = name
        self.state[name + '_uptime_s'] = uptime()
        save_json(self.run_dir / 'state.json', self.state)
        if name != 'live':
            print('C1_APP ' + json.dumps(self.state), flush=True)

    def show_home(self):
        if self.busy:
            return
        self.title.set_text('C1 LIDAR LAB  /  HOME')
        self.auto_button.set_sensitive(self.completed(self.auto_dir))
        self.last_button.set_sensitive(self.completed(ROOT / 'latest'))
        connected = Path('/dev/c1lidar').exists()
        self.home_status.set_text('C1 connected  |  All scans run in user space' if connected else 'Connect C1 to the board USB HOST port, then tap Start scanning.')
        self.stack.set_visible_child_name('home')

    @staticmethod
    def completed(directory):
        try:
            return json.loads((directory / 'state.json').read_text())['phase'] == 'complete' and (directory / 'pointcloud.png').is_file()
        except (OSError, ValueError, KeyError):
            return False

    def start_scan(self, mode):
        if self.busy:
            return False
        self.busy = True
        self.surface = None
        self.run_dir = self.auto_dir if mode == 'automatic' else ROOT / 'runs' / f'{self.boot[:8]}-manual-{time.time_ns()}'
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state = {'boot_id': self.boot, 'kernel': os.uname().release, 'run_directory': str(self.run_dir),
                      'mode': mode, 'execution_context': 'user space', 'seconds': SECONDS if mode == 'automatic' else None,
                      'hello_exit_status': 0, 'student_name': self.student_name, 'student_id': self.student_id}
        (self.run_dir / 'hello.txt').write_text(self.hello)
        self.home_button.set_sensitive(False)
        self.desktop_button.set_sensitive(False)
        self.stop_button.set_visible(mode == 'manual')
        self.stop_button.set_sensitive(True)
        self.stop_requested = False
        self.live_sequence = 0
        self.title.set_text('C1 LIDAR LAB  /  ' + ('BOOT SCAN' if mode == 'automatic' else 'MANUAL SCAN'))
        self.progress_title.set_text('Hello, world  →  C1 scan' if mode == 'automatic' else 'Scanning your surroundings')
        lines = self.hello.splitlines()
        self.hello_label.set_text('\n'.join(line for line in lines if not line.startswith(('Boot ID:', 'Both stages', 'Kernel message', 'Architecture:', 'User process'))))
        self.progress.set_fraction(0)
        self.progress.set_text('Preparing C1...')
        self.stack.set_visible_child_name('progress')
        self.capture_started = None
        self.launched = time.monotonic()
        self.phase('preparing')
        try:
            if not Path('/dev/c1lidar').exists():
                raise RuntimeError('C1 is not connected. Connect its USB adapter to USB HOST, then return home and tap Start scanning.')
            self.log = (self.run_dir / 'capture.log').open('w')
            environment = dict(os.environ, C1_STUDENT_NAME=self.student_name, C1_STUDENT_ID=self.student_id)
            collector = ['/opt/c1-lab/c1_capture', '/dev/c1lidar', '--seconds', str(SECONDS), str(self.run_dir / 'scan.csv')] if mode == 'automatic' else ['/opt/c1-lab/c1_live', '/dev/c1lidar', str(self.run_dir)]
            self.proc = subprocess.Popen(['/usr/bin/flock', '-n', '-F', str(ROOT / 'serial.lock')] + collector,
                stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True, env=environment)
            self.phase('scanning', capture_pid=self.proc.pid)
            GLib.timeout_add(100, self.poll_capture)
        except Exception as error:
            self.fail(error)
        return False

    def stop_scan(self):
        if self.busy and self.proc and self.proc.poll() is None and not self.stop_requested:
            self.stop_requested = True
            self.stop_button.set_sensitive(False)
            self.title.set_text('C1 LIDAR LAB  /  STOPPING...')
            os.killpg(self.proc.pid, signal.SIGINT)

    def poll_live_frame(self):
        pointer = self.run_dir / 'live.json'
        if not pointer.exists():
            return
        current = json.loads(pointer.read_text())
        if current['sequence'] == self.live_sequence:
            return
        csv_path = self.run_dir / current['csv']
        try:
            result = render(csv_path, self.run_dir / 'pointcloud.png', self.boot,
                            os.uname().release, self.student_name, self.student_id, 'manual')
        except FileNotFoundError:
            return  # A rotated frame was replaced; the next poll reads its successor.
        self.live_sequence = current['sequence']
        self.surface = cairo.ImageSurface.create_from_png(str(self.run_dir / 'pointcloud.png'))
        self.stack.set_visible_child_name('result')
        self.area.queue_draw()
        self.phase('live', live_sequence=self.live_sequence, capture=result)
        self.title.set_text('C1 LIDAR LAB  /  LIVE  /  TAP STOP TO FINISH')

    def poll_capture(self):
        code = self.proc.poll()
        manual = self.state['mode'] == 'manual'
        if manual:
            try:
                self.poll_live_frame()
            except Exception as error:
                self.cleanup()
                self.fail(error)
                return False
        if code is None:
            if self.capture_started is None and 'Selected mode:' in (self.run_dir / 'capture.log').read_text():
                self.capture_started = time.monotonic()
            if not manual and time.monotonic() - self.launched > 30:
                self.cleanup()
                self.fail(RuntimeError('Capture timed out. Check C1 and try again from Home.'))
                return False
            if manual:
                self.progress.pulse()
                self.progress.set_text('Preparing live data...')
                return True
            if self.capture_started is not None:
                elapsed = min(SECONDS, time.monotonic() - self.capture_started)
                self.progress.set_fraction(elapsed / SECONDS)
                self.progress.set_text(f'Capturing: {elapsed:.1f} / {SECONDS} seconds')
            else:
                self.progress.pulse()
            return True
        self.log.close()
        self.log = None
        try:
            if code:
                detail = (self.run_dir / 'capture.log').read_text()[-500:]
                raise RuntimeError(f'C1 capture exited with {code}.\n{detail}')
            self.phase('rendering', capture_exit_status=code)
            started = time.monotonic()
            session = None
            if manual:
                session = json.loads((self.run_dir / 'session.json').read_text())
                if not session['stop_command_ok'] or not session['stop_requested']:
                    raise RuntimeError('Continuous scan did not stop cleanly.')
                if not (self.run_dir / 'live.json').exists():
                    self.phase('cancelled', session=session)
                    self.busy = False
                    self.home_button.set_sensitive(True)
                    self.desktop_button.set_sensitive(True)
                    self.stop_button.hide()
                    self.show_home()
                    return False
                current = json.loads((self.run_dir / 'live.json').read_text())
                csv_path = self.run_dir / current['csv']
                shutil.copy2(csv_path, self.run_dir / 'scan.csv')
                meta = json.loads(Path(str(csv_path) + '.json').read_text())
                meta.update(stopped=True, stop_command_ok=True, elapsed_seconds=session['elapsed_seconds'])
                save_json(self.run_dir / 'scan.csv.json', meta)
            result = render(self.run_dir / 'scan.csv', self.run_dir / 'pointcloud.png', self.boot,
                            os.uname().release, self.student_name, self.student_id, self.state['mode'])
            if not manual and (abs(result['scan_window_seconds'] - SECONDS) > .15 or not result['stop_command_ok']):
                raise RuntimeError('Scan duration or stop validation failed; see capture.log.')
            self.phase('complete', capture=result, session=session, image=str(self.run_dir / 'pointcloud.png'),
                       render_seconds=time.monotonic() - started, total_seconds=time.monotonic() - self.launched)
            link = ROOT / f'.latest-{os.getpid()}'
            link.unlink(missing_ok=True)
            link.symlink_to(self.run_dir)
            link.replace(ROOT / 'latest')
            self.busy = False
            self.stop_button.hide()
            self.home_button.set_sensitive(True)
            self.desktop_button.set_sensitive(True)
            self.show_saved(self.run_dir)
        except Exception as error:
            self.fail(error)
        return False

    def fail(self, error):
        if self.log:
            self.log.close()
            self.log = None
        self.phase('failed', error=str(error))
        self.busy = False
        self.stop_button.hide()
        self.home_button.set_sensitive(True)
        self.desktop_button.set_sensitive(True)
        self.show_error(str(error))

    def show_error(self, message):
        self.title.set_text('C1 LIDAR LAB  /  SCAN UNAVAILABLE')
        self.error_label.set_text(message)
        self.stack.set_visible_child_name('error')

    def show_saved(self, directory):
        try:
            if not self.completed(directory):
                raise RuntimeError('No completed scan here yet. Return home and tap Start scanning.')
            state = json.loads((directory / 'state.json').read_text())
            self.surface = cairo.ImageSurface.create_from_png(str(directory / 'pointcloud.png'))
            label = 'BOOT SCAN' if state.get('mode', 'automatic') == 'automatic' else 'MANUAL SCAN'
            self.title.set_text(f'C1 LIDAR LAB  /  {label}  /  COMPLETE')
            self.stack.set_visible_child_name('result')
            self.area.queue_draw()
        except Exception as error:
            self.show_error(str(error))

    def draw_result(self, widget, cr):
        cr.set_source_rgb(.97, .985, .99)
        cr.paint()
        if self.surface:
            width, height = widget.get_allocated_width(), widget.get_allocated_height()
            sw, sh = self.surface.get_width(), self.surface.get_height()
            scale = min(width / sw, height / sh)
            cr.translate((width - sw * scale) / 2, (height - sh * scale) / 2)
            cr.scale(scale, scale)
            cr.set_source_surface(self.surface, 0, 0)
            cr.paint()
        return False

    def hide_window(self, *args):
        if not self.busy:
            self.window.hide()
        return True

    def key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape and not self.busy:
            self.show_home()
            return True
        return False

    def cleanup(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGINT)
            try:
                self.proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=5)
        if self.log:
            self.log.close()
            self.log = None


if __name__ == '__main__':
    app = LidarApp()
    try:
        sys.exit(app.run(sys.argv))
    finally:
        app.cleanup()
