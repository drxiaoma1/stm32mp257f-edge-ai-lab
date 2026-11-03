#!/usr/bin/env python3
"""Draw real CSV data using Cairo; aggregate display pixels, preserve full raw data."""
import csv
import json
import math
from pathlib import Path
import cairo


def text(cr, x, y, value, size=16, color=(.09, .18, .23), bold=False):
    cr.set_source_rgb(*color)
    cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    cr.move_to(x, y)
    cr.show_text(str(value))


def render(csv_path, png_path, boot_id, kernel, student_name='mingkang ma', student_id='523031910621', mode='automatic'):
    csv_path = Path(csv_path)
    meta = json.loads(Path(str(csv_path) + '.json').read_text())
    points, frames = [], set()
    below = 0
    with csv_path.open() as source:
        for row in csv.DictReader(source):
            frames.add(int(row['scan_id']))
            if int(row['valid']):
                distance, x, y = float(row['distance_m']), float(row['x_m']), float(row['y_m'])
                if not all(math.isfinite(v) for v in (distance, x, y)):
                    raise ValueError('Non-finite point in capture')
                points.append((x, y, distance))
                below += distance < .05
    if not points and not meta.get('live'):
        raise RuntimeError('No valid points to draw')
    if len(points) != meta['valid_points'] or len(frames) != meta['frames']:
        raise ValueError('CSV and capture summary do not match')
    live = meta.get('live', False)
    full = 12 if live else max(1, math.ceil(max(max(abs(x), abs(y)) for x, y, distance in points)))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 480)
    cr = cairo.Context(surface)
    cr.set_source_rgb(.97, .985, .99)
    cr.paint()
    heading = 'Boot scan' if mode == 'automatic' else ('Manual scan (stopped)' if meta.get('stopped') else 'LIVE scan')
    text(cr, 24, 29, f'RPLIDAR C1  |  {heading}  |  User space', 23, bold=True)
    text(cr, 24, 55, f'{student_name}  |  {student_id}', 17)
    summary = (f"Elapsed {meta['elapsed_seconds']:.1f} s  |  Display frame {meta['sequence']}  |  {len(points):,} valid returns in this revolution  |  ~1 Hz refresh" if live else
               f"{meta['scan_window_seconds']:.3f} s capture  |  {len(frames)} scans  |  {len(points):,} valid returns  |  {meta['scan_rate_hz']:.2f} Hz")
    text(cr, 24, 80, summary, 16)
    for left, limit, label in [(110, full, f'Full view: +/-{full} m'), (620, 1, 'Near view: +/-1 m')]:
        top, size = 116, 288
        middle_x, middle_y = left + size / 2, top + size / 2
        scale = size / (limit * 2)
        text(cr, left, top - 12, label, 17, bold=True)
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(left, top, size, size)
        cr.fill()
        for i in range(5):
            px, py = left + size * i / 4, top + size * i / 4
            cr.set_source_rgb(.85, .89, .91)
            cr.set_line_width(1)
            cr.move_to(px, top); cr.line_to(px, top + size)
            cr.move_to(left, py); cr.line_to(left + size, py)
            cr.stroke()
            value = -limit + i * limit / 2
            text(cr, px - 10, top + size + 19, f'{value:g}', 12)
            text(cr, left - 36, py + 4, f'{-value:g}', 12)
        normal, near = set(), set()
        for x, y, distance in points:
            if abs(x) <= limit and abs(y) <= limit:
                pixel = (round(middle_x + x * scale), round(middle_y - y * scale))
                (near if distance < .05 else normal).add(pixel)
        cr.save()
        cr.rectangle(left, top, size, size)
        cr.clip()
        for pixels, color in [(normal, (.04, .46, .58)), (near, (.88, .49, .07))]:
            cr.set_source_rgb(*color)
            for x, y in pixels:
                cr.rectangle(x, y, 1.5, 1.5)
            cr.fill()
        cr.restore()
        cr.set_source_rgb(.86, .23, .17)
        cr.set_line_width(2)
        cr.move_to(middle_x - 6, middle_y); cr.line_to(middle_x + 6, middle_y)
        cr.move_to(middle_x, middle_y - 6); cr.line_to(middle_x, middle_y + 6)
        cr.stroke()
        text(cr, left + size + 12, top + size + 18, 'x (m)', 12)
        text(cr, left - 34, top - 10, 'y (m)', 12)
    note = 'LIVE: latest measured revolution. Tap Stop to finish.' if live and not meta.get('stopped') else 'Scan stopped. Raw CSV and PNG saved on the board.'
    if live and not points and not meta.get('stopped'):
        note = 'No valid returns in this revolution. Scanning continues; tap Stop to finish.'
    text(cr, 24, 450, f'{note} Orange: {below} returns below 0.05 m.', 14)
    text(cr, 24, 473, f'Linux {kernel}  |  Boot {boot_id[:8]}  |  {"Newest 8 display frames retained; full-session counters saved." if live else "Tap Home to return or start another scan."}', 13)
    temporary = Path(str(png_path) + '.tmp')
    surface.write_to_png(str(temporary))
    temporary.replace(png_path)
    return {'below_0_05m': below, **meta}


if __name__ == '__main__':
    import sys
    import os
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render_pointcloud.py input.csv output.png')
    print(json.dumps(render(sys.argv[1], sys.argv[2], Path('/proc/sys/kernel/random/boot_id').read_text().strip(), os.uname().release)))
