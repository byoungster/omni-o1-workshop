"""Local LAN control of the Bambu Lab P1S: status, camera, light, and guarded print start.

Credentials come from Windows Credential Manager (service "omni-o1": p1s_ip, p1s_serial,
p1s_access_code) and never from files. Status, camera and light work while the printer is on
Bambu Cloud; uploading and starting prints needs LAN-only + Developer Mode and a microSD card.
"""
import datetime
import json
import os
import re
import socket
import ssl
import time
import zipfile

import keyring
import paho.mqtt.client as mqtt

import bambu_profiles as bp
import bambu_slice as bs

SERVICE = 'omni-o1'
socket.setdefaulttimeout(20)  # a P1S with too many clients can accept TCP and then stall forever
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
    c.connect_timeout = 10
    return c, ip, serial


def report(name='p1s', timeout=15):
    """Full status report (the P1S only sends deltas, so ask for a full push).

    The client runs in the foreground with a deadline: paho's loop_stop() can block forever joining
    its thread when the printer never acknowledges a packet.
    """
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
    end = time.time() + timeout
    try:
        while time.time() < end and 'print' not in got and 'error' not in got:
            c.loop(timeout=0.5)
    finally:
        c.disconnect()
    if 'error' in got:
        raise RuntimeError('MQTT connect failed: ' + got['error'])
    if 'print' not in got:
        raise TimeoutError('no status from printer within %ds' % timeout)
    return got['print']


def _publish(payload, name='p1s', timeout=10):
    """Send one command to the printer's request topic (QoS 0, foreground loop, hard deadline).

    QoS 1 hung forever: the P1S never acknowledged, and paho will not stop its loop thread while a
    QoS 1 message is outstanding.
    """
    c, ip, serial = _mqtt(name)
    state = {}
    c.on_connect = lambda cl, u, flags, rc, props=None: state.update(rc=rc)
    c.connect(ip, 8883, 30)
    end = time.time() + timeout
    try:
        while 'rc' not in state and time.time() < end:
            c.loop(timeout=0.5)
        if 'rc' not in state or state['rc'].is_failure:
            raise RuntimeError('MQTT connect failed: %s' % state.get('rc', 'no CONNACK'))
        info = c.publish('device/%s/request' % serial, json.dumps(payload), qos=0)
        while not info.is_published() and time.time() < end:
            c.loop(timeout=0.2)
        if not info.is_published():
            raise RuntimeError('command was not sent within %ds' % timeout)
    finally:
        c.disconnect()


VERIFY_FAILED = (0x05000500, 0x00010007)  # HMS 0500-0500-0001-0007: command rejected by Authorization Control


def _rejected_since(st, t0):
    return any((h.get('attr'), h.get('code')) == VERIFY_FAILED and h.get('timestamp', 0) >= t0 - 5 for h in st['errors'])


def _minutes(state):
    """HA time sensor -> minutes, honouring its unit (ha-bambulab reports remaining time in hours)."""
    try:
        v = float(state['state'])
    except (TypeError, ValueError):
        return None
    unit = (state.get('attributes') or {}).get('unit_of_measurement', 'min')
    return round(v * {'h': 60, 'min': 1, 's': 1 / 60}.get(unit, 1), 1)


def _ha_status(name='p1s'):
    """Printer state from Home Assistant (ha-bambulab), which already holds the printer's MQTT connection.

    The P1S misbehaves with several MQTT clients (status reads hang, especially while a job starts),
    so status comes from HA whenever it is configured.
    """
    import urllib.request
    url, tok, serial = (keyring.get_password(SERVICE, k) for k in ('ha_url', 'ha_token', '%s_serial' % name))
    if not (url and tok and serial):
        return None
    pre = '%s_%s' % (name, serial.lower())

    def get(entity):
        req = urllib.request.Request('%s/api/states/%s' % (url, entity), headers={'Authorization': 'Bearer ' + tok})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    try:
        st = {'state': get('sensor.%s_print_status' % pre)['state'].upper(),
              'percent': get('sensor.%s_print_progress' % pre)['state'],
              'remaining_min': _minutes(get('sensor.%s_remaining_time' % pre)),
              'job': get('sensor.%s_task_name' % pre)['state'],
              'stage': get('sensor.%s_current_stage' % pre)['state'],
              'sd_card': get('sensor.%s_sd_card_status' % pre)['state'] == 'normal',
              'online': get('binary_sensor.%s_online' % pre)['state'] == 'on',
              'hms_errors': get('binary_sensor.%s_hms_errors' % pre)['state'] == 'on',
              'errors': [], 'source': 'home assistant'}
        trays = []
        for i in range(1, 5):                     # best effort: HA drops AMS entities until the printer re-reports them
            try:
                t = get('sensor.%s_ams_1_tray_%d' % (pre, i))
            except Exception:
                continue
            trays.append({'slot': str(i - 1), 'type': t['attributes'].get('type'),
                          'color': (t['attributes'].get('color') or '').lstrip('#').upper()})
        st['ams'] = [{'unit': '0', 'trays': trays}] if trays else []
        return st
    except Exception:
        return None


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


def _ha_snapshot(path, name, light):
    """Camera frame through Home Assistant (works for the X1C's RTSP stream and the P1S)."""
    import urllib.request
    url, tok, serial = (keyring.get_password(SERVICE, k) for k in ('ha_url', 'ha_token', '%s_serial' % name))
    if not (url and tok and serial):
        return None
    pre = '%s_%s' % (name, serial.lower())
    hdr = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}
    if light:
        try:
            req = urllib.request.Request(url + '/api/services/light/turn_on', method='POST', headers=hdr,
                                         data=json.dumps({'entity_id': 'light.%s_chamber_light' % pre}).encode())
            urllib.request.urlopen(req, timeout=10).read()
            time.sleep(1.5)
        except Exception:
            pass
    try:
        req = urllib.request.Request(url + '/api/camera_proxy/camera.%s_camera' % pre, headers=hdr)
        data = urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    return {'path': os.path.abspath(path), 'bytes': len(data), 'source': 'home assistant'}


def snapshot(path, name='p1s', light=True):
    """Save a camera frame, through Home Assistant when possible. The P1S also has a direct fallback
    (1280x720 JPEG); the X1C streams RTSP, which needs LAN Only Liveview turned on at the printer."""
    got = _ha_snapshot(path, name, light)
    if got:
        return got
    if name != 'p1s':
        raise RuntimeError('no camera frame from Home Assistant for %s; turn on LAN Only Liveview on the printer' % name)
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


def print_job(path, plate=1, confirm=False, use_ams=None, ams_slot=None, name='p1s', color=None):
    """Send one plate of a sliced .gcode.3mf to the printer.

    Without confirm=True this only returns what would be printed. Refuses files that were not sliced
    by this pipeline, failed its safety checks, or were sliced for another printer model. With no
    ams_slot given, picks the AMS slot whose colour matches `color` (e.g. "000000") or else the
    recipe's "ams_color".
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
    target = bp.resolve('machine', bs.PRINTERS[name])['printer_model']
    if model != target:
        raise RuntimeError('this file was sliced for the %s, not the %s; re-slice it with printer=%r' % (model, target, name))
    gcode = zipfile.ZipFile(path).read('Metadata/plate_%d.gcode' % plate).decode('utf-8', 'replace')
    problems = bs._check_plate(gcode, model, entry['presets']['machine'])
    if problems:
        raise RuntimeError('plate %d failed checks: %s' % (plate, problems))

    st = _ha_status(name) or status(name)
    if not st.get('ams'):                         # HA had no AMS data: read the trays straight from the printer
        try:
            st['ams'] = status(name)['ams']
        except (OSError, RuntimeError):
            pass
    if st['state'] in BUSY:
        raise RuntimeError('printer is busy (%s, %s%%)' % (st['state'], st['percent']))
    if use_ams is None:
        use_ams = bool(st['ams'])
    trays = {int(u['unit']) * 4 + int(t['slot']): t for u in st['ams'] for t in u['trays'] if t.get('type')}
    want = (color or bs.load_recipe(entry['recipe']).get('ams_color') or '').upper().lstrip('#')
    if use_ams and ams_slot is None:
        match = [i for i, t in sorted(trays.items()) if want and (t.get('color') or '').upper().startswith(want)]
        if want and not match:
            raise RuntimeError('no AMS slot holds colour %s; load it or pass ams_slot' % want)
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
    for _ in range(18):
        time.sleep(5)
        s = _ha_status(name)
        if s is None:  # no Home Assistant: fall back to a direct read
            try:
                s = status(name)
            except (OSError, RuntimeError):
                continue
            if _rejected_since(s, t0):
                raise RuntimeError('uploaded %s, but the printer rejected the start command (HMS 0500-0500-0001-0007, '
                                   'command verification failed): turn on Developer Mode on the printer' % remote)
        if s['state'] in ('PREPARE', 'RUNNING') or (s['job'] or '').startswith(entry['job_id']):
            started = s
            break
    bs._journal({'type': 'print', 'job_id': entry['job_id'], 'plate': plate, 'remote_file': remote,
                 'started': bool(started), 'time': datetime.datetime.now().isoformat(timespec='seconds')})
    if not started:
        raise RuntimeError('uploaded %s but the printer did not start within 90 s; check Developer Mode and HMS errors' % remote)
    plan.update({'started': True, 'printer': started})
    return plan


def control(action, name='p1s'):
    """pause / resume / stop the current print."""
    p = _api(name)
    try:
        return {'pause': p.pause_print, 'resume': p.resume_print, 'stop': p.stop_print}[action]()
    finally:
        p.disconnect()
