"""Local LAN control of the Bambu Lab P1S: status, camera, light, and guarded print start.

Credentials come from Windows Credential Manager (service "omni-o1": p1s_ip, p1s_serial,
p1s_access_code) and never from files. Status, camera and light work while the printer is on
Bambu Cloud; uploading and starting prints needs LAN-only + Developer Mode and a microSD card.
"""
import datetime
import json
import os
import re
import ssl
import time
import zipfile

import keyring
import paho.mqtt.client as mqtt

import bambu_profiles as bp
import bambu_slice as bs

SERVICE = 'omni-o1'
BUSY = {'RUNNING', 'PREPARE', 'PAUSE', 'SLICING'}
PLATE_NAMES = {'High Temp Plate': 'Smooth PEI (High Temp Plate)', 'Textured PEI Plate': 'Textured PEI',
               'Cool Plate': 'Cool Plate', 'Engineering Plate': 'Engineering Plate', 'Supertack Plate': 'Cool Plate SuperTack'}


def _creds(name='p1s'):
    vals = [keyring.get_password(SERVICE, '%s_%s' % (name, k)) for k in ('ip', 'serial', 'access_code')]
    if not all(vals):
        raise RuntimeError('credentials for %s missing in Windows Credential Manager (service %s)' % (name, SERVICE))
    return vals


def _mqtt(name='p1s'):
    ip, serial, code = _creds(name)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='omni-o1-%d' % os.getpid())
    c.username_pw_set('bblp', code)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # the printer presents a self-signed certificate
    c.tls_set_context(ctx)
    return c, ip, serial


def report(name='p1s', timeout=15):
    """Full status report (the P1S only sends deltas, so ask for a full push)."""
    c, ip, serial = _mqtt(name)
    got = {}

    def on_connect(cl, u, flags, rc, props=None):
        if rc.is_failure:
            got['error'] = str(rc)
            return
        cl.subscribe('device/%s/report' % serial)
        cl.publish('device/%s/request' % serial, json.dumps({'pushing': {'sequence_id': '0', 'command': 'pushall'}}))

    def on_message(cl, u, msg):
        d = json.loads(msg.payload).get('print', {})
        if 'gcode_state' in d:
            got['print'] = d

    c.on_connect, c.on_message = on_connect, on_message
    c.connect(ip, 8883, 30)
    c.loop_start()
    end = time.time() + timeout
    while time.time() < end and 'print' not in got and 'error' not in got:
        time.sleep(0.2)
    c.loop_stop()
    c.disconnect()
    if 'error' in got:
        raise RuntimeError('MQTT connect failed: ' + got['error'])
    if 'print' not in got:
        raise TimeoutError('no status from printer within %ds' % timeout)
    return got['print']


def _publish(payload, name='p1s'):
    """Send one command to the printer's request topic and wait until it is delivered."""
    c, ip, serial = _mqtt(name)
    c.connect(ip, 8883, 30)
    c.loop_start()
    try:
        info = c.publish('device/%s/request' % serial, json.dumps(payload), qos=1)
        info.wait_for_publish(timeout=10)
    finally:
        c.loop_stop()
        c.disconnect()


VERIFY_FAILED = (0x05000500, 0x00010007)  # HMS 0500-0500-0001-0007: command rejected by Authorization Control


def _rejected_since(st, t0):
    return any((h.get('attr'), h.get('code')) == VERIFY_FAILED and h.get('timestamp', 0) >= t0 - 5 for h in st['errors'])


def status(name='p1s'):
    d = report(name)
    ams = d.get('ams') or {}
    units = ams.get('ams') or []
    return {
        'state': d.get('gcode_state'), 'percent': d.get('mc_percent'),
        'remaining_min': d.get('mc_remaining_time'), 'layer': '%s/%s' % (d.get('layer_num'), d.get('total_layer_num')),
        'job': d.get('subtask_name'), 'bed_c': d.get('bed_temper'), 'bed_target_c': d.get('bed_target_temper'),
        'nozzle_c': d.get('nozzle_temper'), 'nozzle_target_c': d.get('nozzle_target_temper'),
        'chamber_light': next((l.get('mode') for l in d.get('lights_report') or [] if l.get('node') == 'chamber_light'), None),
        'sd_card': d.get('sdcard'), 'errors': d.get('hms') or [], 'print_error': d.get('print_error'),
        'ams': [{'unit': u.get('id'), 'trays': [{'slot': t.get('id'), 'type': t.get('tray_type'), 'color': t.get('tray_color')}
                                                for t in u.get('tray', [])]} for u in units],
        'external_spool': (d.get('vt_tray') or {}).get('tray_type'),
        'wifi': d.get('wifi_signal'),
    }


def _api(name='p1s', camera=False):
    import bambulabs_api as bl
    ip, serial, code = _creds(name)
    p = bl.Printer(ip, code, serial)
    p.mqtt_start()
    if camera:
        p.camera_start()
    for _ in range(100):
        if p.mqtt_client_ready() and (not camera or p.camera_client_alive()):
            break
        time.sleep(0.2)
    return p


def snapshot(path, name='p1s', light=True):
    """Save a camera frame (P1S: 1280x720 JPEG). Turns the chamber light on first if asked."""
    p = _api(name, camera=True)
    try:
        if light:
            p.turn_light_on()
            time.sleep(1.5)
        err = None
        for _ in range(30):
            try:
                img = p.get_camera_image()
                break
            except Exception as e:  # frames arrive a moment after the camera socket connects
                err = e
                time.sleep(0.5)
        else:
            raise RuntimeError('no camera frame: %s' % err)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        img.save(path)
        return {'path': os.path.abspath(path), 'size': img.size}
    finally:
        p.disconnect()


def light(on, name='p1s'):
    p = _api(name)
    try:
        return p.turn_light_on() if on else p.turn_light_off()
    finally:
        p.disconnect()


def _slice_entry(path):
    path = os.path.abspath(path)
    for e in reversed(bs.journal(limit=100000)):
        if e.get('type') == 'slice' and os.path.abspath(e.get('output', '')) == path:
            return e
    return None


def print_job(path, plate=1, confirm=False, use_ams=None, ams_slot=None, name='p1s'):
    """Send one plate of a sliced .gcode.3mf to the printer.

    Without confirm=True this only returns what would be printed. Refuses files that were not sliced
    by this pipeline, failed its safety checks, or were sliced for another printer model. With no
    ams_slot given, picks the AMS slot whose colour matches the recipe's "ams_color" (e.g. "FFFFFF").
    """
    path = os.path.abspath(path)
    if not path.endswith('.gcode.3mf') or not os.path.isfile(path):
        raise FileNotFoundError('need a sliced .gcode.3mf: ' + path)
    entry = _slice_entry(path)
    if not entry:
        raise RuntimeError('this file is not in the slicing journal; slice it with the bambu pipeline first')
    if not entry.get('safe_to_print'):
        raise RuntimeError('slice failed safety checks: %s' % entry.get('problems'))
    if os.path.getmtime(path) > datetime.datetime.fromisoformat(entry['time']).timestamp() + 120:
        raise RuntimeError('file changed after it was sliced and checked; re-slice it')
    plate_info = next((p for p in entry['plates'] if p['plate'] == plate), None)
    if not plate_info:
        raise ValueError('plate %d not in job (plates: %s)' % (plate, [p['plate'] for p in entry['plates']]))
    model = bp.resolve('machine', entry['presets']['machine'])['printer_model']
    gcode = zipfile.ZipFile(path).read('Metadata/plate_%d.gcode' % plate).decode('utf-8', 'replace')
    problems = bs._check_plate(gcode, model)
    if problems:
        raise RuntimeError('plate %d failed checks: %s' % (plate, problems))

    st = status(name)
    if st['state'] in BUSY:
        raise RuntimeError('printer is busy (%s, %s%%)' % (st['state'], st['percent']))
    if use_ams is None:
        use_ams = bool(st['ams'])
    trays = {int(u['unit']) * 4 + int(t['slot']): t for u in st['ams'] for t in u['trays'] if t.get('type')}
    want = (bs.load_recipe(entry['recipe']).get('ams_color') or '').upper().lstrip('#')
    if use_ams and ams_slot is None:
        match = [i for i, t in sorted(trays.items()) if want and (t.get('color') or '').upper().startswith(want)]
        if want and not match:
            raise RuntimeError('no AMS slot holds the recipe colour %s; load it or pass ams_slot' % want)
        ams_slot = match[0] if match else 0
    tray = trays.get(ams_slot or 0, {})
    plan = {'job_id': entry['job_id'], 'plate': plate, 'objects': plate_info['objects'],
            'minutes': plate_info['minutes'], 'grams': plate_info['grams'],
            'load_build_plate': PLATE_NAMES.get(entry.get('bed_type'), entry.get('bed_type')), 'filament_source': ('AMS slot %d (%s, colour %s)' % (ams_slot, tray.get('type'), tray.get('color'))) if use_ams else 'external spool (%s)' % st['external_spool'],
            'printer_state': st['state'], 'sd_card': st['sd_card']}
    if not confirm:
        plan['next'] = 'Check the build plate and filament, then call again with confirm=True to start.'
        return plan
    if st['sd_card'] is False:
        raise RuntimeError('no microSD card in the printer; LAN printing needs one')

    remote = re.sub(r'[^\w\-.]', '_', '%s_p%d.gcode.3mf' % (entry['job_id'], plate))
    p = _api(name)
    try:
        with open(path, 'rb') as fh:
            up = p.upload_file(fh, remote)
    finally:
        p.disconnect()
    if '226' not in str(up):
        raise RuntimeError('upload failed: %s' % up)
    t0 = time.time()
    _publish({'print': {
        'sequence_id': str(int(t0)), 'command': 'project_file', 'param': 'Metadata/plate_%d.gcode' % plate,
        'url': 'ftp:///%s' % remote, 'subtask_name': '%s plate %d' % (entry['job_id'], plate),
        'project_id': '0', 'profile_id': '0', 'task_id': '0', 'subtask_id': '0', 'file': '', 'md5': '',
        'bed_type': 'auto', 'timelapse': False, 'bed_levelling': True, 'flow_cali': True,
        'vibration_cali': True, 'layer_inspect': False,
        'use_ams': bool(use_ams), 'ams_mapping': [ams_slot or 0] if use_ams else []}}, name)
    started = None
    for _ in range(12):
        time.sleep(5)
        s = status(name)
        if _rejected_since(s, t0):
            raise RuntimeError('uploaded %s, but the printer rejected the start command (HMS 0500-0500-0001-0007, '
                               'command verification failed): turn on Developer Mode on the printer' % remote)
        if s['state'] in ('PREPARE', 'RUNNING') or (s['job'] and s['job'].startswith(entry['job_id']) and s['state'] != st['state']):
            started = s
            break
    bs._journal({'type': 'print', 'job_id': entry['job_id'], 'plate': plate, 'remote_file': remote,
                 'started': bool(started), 'time': datetime.datetime.now().isoformat(timespec='seconds')})
    if not started:
        raise RuntimeError('uploaded %s but the printer did not start within 60 s; is LAN-only + Developer Mode on?' % remote)
    plan.update({'started': True, 'printer': started})
    return plan


def control(action, name='p1s'):
    """pause / resume / stop the current print."""
    p = _api(name)
    try:
        return {'pause': p.pause_print, 'resume': p.resume_print, 'stop': p.stop_print}[action]()
    finally:
        p.disconnect()
