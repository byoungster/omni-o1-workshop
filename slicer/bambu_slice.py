"""Slice models for the Bambu Lab P1S from versioned recipes, with safety checks and a print journal.

A recipe (recipes/<name>.json) names three Bambu system presets and overrides individual
settings on top of them. Changing a setting is a one-line, dated, diffable edit, and every slice
and every print outcome is appended to journal.jsonl, so settings can be tuned against results.

Sliced files (.gcode.3mf) stay on this PC: G-code is specific to one printer and setup. To share a job,
export_project writes a Bambu Studio project (.3mf) with the same plates and settings but no G-code,
which anyone can open, check and slice for their own printer.

Usage:
  python bambu_slice.py slice <recipe> <model.3mf|glob> [...] [--job NAME] [--bed "High Temp Plate"] [--printer x1c]
  python bambu_slice.py project <recipe> <model.3mf|glob> [...] [--job NAME] [--bed "High Temp Plate"] [--printer x1c]
  python bambu_slice.py set <recipe> <machine|process|filament> <key> <value> "<reason>"
  python bambu_slice.py result <job_id> <ok|warped|failed|...> "<notes>"
"""
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import bambu_profiles as bp

STUDIO = r'C:\Program Files\Bambu Studio\bambu-studio.exe'
HERE = os.path.dirname(os.path.abspath(__file__))
RECIPES = os.path.join(HERE, 'recipes')
JOURNAL = os.path.join(HERE, 'journal.jsonl')
CATALOG = os.path.join(HERE, 'settings_catalog.json')  # every key the slicer knows, from the last slice
OUT = os.path.join(os.path.dirname(HERE), 'exports', 'sliced')           # G-code, local only (git-ignored)
PROJECTS = os.path.join(os.path.dirname(HERE), 'exports', 'bambu_projects')  # shareable project files
BED_TYPES = ('Cool Plate', 'Engineering Plate', 'High Temp Plate', 'Textured PEI Plate', 'Supertack Plate')
PRINTERS = {'p1s': 'Bambu Lab P1S 0.4 nozzle', 'x1c': 'Bambu Lab X1 Carbon 0.4 nozzle'}
FILAMENT_TAGS = {'p1s': ('P1S 0.4 nozzle', 'P1S', 'X1C'), 'x1c': ('X1C', 'X1C 0.4 nozzle')}
# Settings every recipe gets unless the recipe overrides them itself
DEFAULTS = {'process': {'sparse_infill_pattern': 'gyroid'}}  # 2026-10-14: gyroid infill by default


def for_printer(r, printer):
    """Recipe retargeted to another printer: its machine preset and the matching filament preset."""
    if printer not in PRINTERS:
        raise ValueError('printer must be one of %s' % sorted(PRINTERS))
    r = dict(r)
    if r['machine'] == PRINTERS[printer]:
        return r
    r['machine'] = PRINTERS[printer]
    base = r['filament'].split(' @BBL ')[0]
    known = set(bp.presets('filament', base))
    for tag in FILAMENT_TAGS[printer]:
        if '%s @BBL %s' % (base, tag) in known:
            r['filament'] = '%s @BBL %s' % (base, tag)
            break
    else:
        raise KeyError('no %s filament preset for %s' % (base, printer))
    return r


# ---------------------------------------------------------------- recipes
def recipe_path(name):
    return os.path.join(RECIPES, name + '.json')


def load_recipe(name):
    with open(recipe_path(name), encoding='utf-8') as f:
        return json.load(f)


def save_recipe(name, r):
    with open(recipe_path(name), 'w', encoding='utf-8') as f:
        json.dump(r, f, indent=2)
        f.write('\n')


def list_recipes():
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(RECIPES, '*.json')))


def set_setting(name, category, key, value, reason):
    """Set (or with value=None remove) one override and record why in the recipe changelog."""
    if category not in bp.CATEGORIES:
        raise ValueError('category must be one of %s' % (bp.CATEGORIES,))
    r = load_recipe(name)
    ov = r.setdefault('overrides', {}).setdefault(category, {})
    old = ov.get(key, '(preset default)')
    if value is None:
        ov.pop(key, None)
        new = '(preset default)'
    else:
        if key not in bp.resolve(category, r[category]) and key not in _catalog():
            raise KeyError('unknown setting %s (not in preset %s or the slicer catalog)' % (key, r[category]))
        ov[key] = value
        new = value
    r.setdefault('changelog', []).append('%s  %s.%s: %s -> %s  (%s)' % (
        datetime.date.today().isoformat(), category, key, old, new, reason))
    save_recipe(name, r)
    return {'recipe': name, 'key': '%s.%s' % (category, key), 'old': old, 'new': new}


def overrides(r):
    """The recipe's own overrides on top of the pipeline DEFAULTS."""
    own = r.get('overrides', {})
    return {c: {**DEFAULTS.get(c, {}), **own.get(c, {})} for c in bp.CATEGORIES if DEFAULTS.get(c) or own.get(c)}


def effective(name, category, key):
    r = load_recipe(name)
    ov = overrides(r).get(category, {})
    base = bp.resolve(category, r[category]).get(key)
    return {'preset': r[category], 'preset_value': base, 'override': ov.get(key), 'effective': ov.get(key, base)}


def search_settings(name, pattern):
    """Settings whose key matches `pattern` (regex) across the recipe's three presets."""
    r = load_recipe(name)
    hits = []
    for cat in bp.CATEGORIES:
        cfg = bp.resolve(cat, r[cat])
        ov = overrides(r).get(cat, {})
        for k in sorted(cfg):
            if re.search(pattern, k, re.I):
                hits.append({'category': cat, 'key': k, 'preset_value': cfg[k], 'override': ov.get(k)})
    # Settings no preset defines (slicer built-in defaults, e.g. brim_type) are set via the process override
    known = {h['key'] for h in hits} | {k for cat in bp.CATEGORIES for k in bp.resolve(cat, r[cat])}
    ov = overrides(r).get('process', {})
    for k, v in sorted(_catalog().items()):
        if k not in known and re.search(pattern, k, re.I):
            hits.append({'category': 'process', 'key': k, 'preset_value': v, 'override': ov.get(k),
                         'note': 'slicer default (value from last slice)'})
    return hits


def _catalog():
    try:
        with open(CATALOG, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- slicing
def _resolve_models(models):
    paths = []
    for m in models:
        found = sorted(glob.glob(m)) if any(c in m for c in '*?[') else [m]
        for p in found:
            if not os.path.isfile(p):
                raise FileNotFoundError(p)
            paths.append(os.path.abspath(p))
    if not paths:
        raise FileNotFoundError('no model files matched %s' % models)
    return paths


def start_marker(machine):
    """The '===== machine: ...' header of a machine preset's start G-code (e.g. 'P1S-0.4', 'X1-0.4')."""
    first = (bp.resolve('machine', machine).get('machine_start_gcode') or '').splitlines()[:1]
    m = re.match(r'^;=+ *machine: *([^=]+?) *=*\s*$', first[0]) if first else None
    return m.group(1) if m else None


def _check_plate(gcode, printer_model, machine):
    """Safety checks a sliced plate must pass before it is allowed near the printer."""
    problems = []
    marker = start_marker(machine)
    if not marker or not re.search(r'^;=+ *machine: *%s *=*' % re.escape(marker), gcode, re.M):
        problems.append('%s start G-code missing' % printer_model)
    if not re.search(r'^; printer_model = %s\s*$' % re.escape(printer_model), gcode, re.M):
        problems.append('G-code was not sliced for %s' % printer_model)
    if not re.search(r'^G29', gcode, re.M):
        problems.append('no bed leveling (G29) in start sequence')
    return problems


def _job(recipe, job, bed_type, printer):
    """Recipe for one job, retargeted to a printer and plate if asked, plus a file-safe job name."""
    r = load_recipe(recipe)
    if printer:
        r = for_printer(r, printer)
    if bed_type:
        if bed_type not in BED_TYPES:
            raise ValueError('bed_type must be one of %s' % (BED_TYPES,))
        r['bed_type'] = bed_type
    job = job or '%s %s' % (recipe, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    return r, re.sub(r'[^\w\- .]', '_', job)


PURGE_ANCHOR = 'M106 P1 S255\nG92 E0\nG1 E5 F300'   # P1S start G-code: right after its two 50 mm purges


def extra_start_purge(gcode, mm, step=50):
    """Push `mm` more filament through the nozzle over the purge chute at print start, in rounds of `step` mm with a
    cool-down and a shake between them (as Bambu's own filament-change flush does), so nothing of the previous colour
    is left. For prints whose first layer is the show face, e.g. white photo blanks after a black print: the stock P1S
    start purges only 105 mm (~250 mm3), and black to white needs ~600 mm3 or more."""
    if gcode.count(PURGE_ANCHOR) != 1:
        raise RuntimeError('start G-code purge block not found: extra purge is written for the P1S start G-code')
    rounds, left = [], mm
    while left > 0:
        e = min(step, left)
        rounds.append('M106 P1 S255\nM400 S3\nG1 X70 F9000\nG1 X76 F15000\nG1 X65 F15000\nG1 X76 F15000\n'
                      'G1 X65 F15000 ; shake off the purged filament\nG1 X54 F9000\nM106 P1 S0\n'
                      'G92 E0\nG1 E%g F200\nM400\n' % e)
        left -= e
    block = '; extra purge %g mm (recipe start_purge_extra_mm)\n%s' % (mm, ''.join(rounds))
    return gcode.replace(PURGE_ANCHOR, block + PURGE_ANCHOR)


def _settings_files(r, recipe, tmp):
    """Fully resolved machine/process/filament settings files (the CLI ignores preset inheritance)."""
    ov, files = overrides(r), {}
    for cat in bp.CATEGORIES:
        o = dict(ov.get(cat, {}))
        if cat == 'process' and r.get('bed_type'):
            o['curr_bed_type'] = r['bed_type']
        name = None if cat == 'machine' else 'Omni %s (%s)' % (recipe, cat)
        cfg = bp.build(cat, r[cat], o, name=name)
        if cat == 'machine' and r.get('start_purge_extra_mm'):
            cfg['machine_start_gcode'] = extra_start_purge(cfg['machine_start_gcode'], r['start_purge_extra_mm'])
        if cat != 'machine':
            cfg['compatible_printers'] = [r['machine']]
            cfg['compatible_printers_condition'] = ''
        files[cat] = os.path.join(tmp, cat + '.json')
        with open(files[cat], 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
    return files


def export_project(recipe, models, job=None, bed_type=None, printer=None):
    """Bambu Studio project (.3mf) with the recipe's settings and auto-arranged plates, but no G-code.
    Safe to share: it opens in Bambu Studio and is sliced there for whatever printer loads it."""
    r, job = _job(recipe, job, bed_type, printer)
    models = _resolve_models(models)
    os.makedirs(PROJECTS, exist_ok=True)
    out = os.path.join(PROJECTS, job + '.3mf')
    with tempfile.TemporaryDirectory(prefix='bambu_') as tmp:
        files = _settings_files(r, recipe, tmp)
        cmd = [STUDIO, '--arrange', '1', '--orient', '0',
               '--load-settings', files['machine'] + ';' + files['process'],
               '--load-filaments', files['filament'],
               '--outputdir', tmp, '--export-3mf', job + '.3mf']
        proc = subprocess.run(cmd + models, capture_output=True, text=True, timeout=1800)
        made = os.path.join(tmp, job + '.3mf')
        if not os.path.exists(made):
            raise RuntimeError('project export failed (exit %s): %s' % (proc.returncode, proc.stdout[-500:]))
        with zipfile.ZipFile(made) as z:
            names = z.namelist()
        gcode = [n for n in names if n.endswith('.gcode')]
        if gcode:
            raise RuntimeError('project unexpectedly contains G-code: %s' % gcode)
        os.replace(made, out)
    return {'project': out, 'recipe': recipe, 'printer': next((k for k, v in PRINTERS.items() if v == r['machine']), None),
            'bed_type': r.get('bed_type'), 'models': [os.path.basename(m) for m in models],
            'plates': len([n for n in names if re.match(r'Metadata/plate_\d+\.png$', n)]) or None}


def slice_models(recipe, models, job=None, arrange=True, bed_type=None, printer=None):
    """bed_type overrides the recipe's plate for this job (e.g. whatever plate is loaded right now);
    printer ('p1s', 'x1c') retargets the recipe to that printer's machine and filament presets."""
    r, job = _job(recipe, job, bed_type, printer)
    models = _resolve_models(models)
    os.makedirs(OUT, exist_ok=True)
    ov = overrides(r)
    with tempfile.TemporaryDirectory(prefix='bambu_') as tmp:
        files = _settings_files(r, recipe, tmp)
        out_name = job + '.gcode.3mf'
        cmd = [STUDIO, '--slice', '0', '--orient', '0',
               '--load-settings', files['machine'] + ';' + files['process'],
               '--load-filaments', files['filament'],
               '--outputdir', OUT, '--export-3mf', out_name]
        if arrange:
            cmd[3:3] = ['--arrange', '1']
        proc = subprocess.run(cmd + models, capture_output=True, text=True, timeout=1800)
        res_path = os.path.join(OUT, 'result.json')
        res = json.load(open(res_path, encoding='utf-8')) if os.path.exists(res_path) else {}
        for junk in [res_path] + glob.glob(os.path.join(OUT, 'plate_*.gcode')):
            os.remove(junk)
    out = os.path.join(OUT, out_name)
    if res.get('return_code', proc.returncode) != 0 or not os.path.exists(out):
        raise RuntimeError('slicing failed: %s (exit %s)' % (res.get('error_string', '?'), proc.returncode))

    printer_model = bp.resolve('machine', r['machine'])['printer_model']
    z = zipfile.ZipFile(out)
    with open(CATALOG, 'w', encoding='utf-8') as f:
        json.dump(json.loads(z.read('Metadata/project_settings.config')), f, indent=0, sort_keys=True)
    info = z.read('Metadata/slice_info.config').decode('utf-8')
    plates, all_problems = [], []
    for block in re.findall(r'<plate>(.*?)</plate>', info, re.S):
        meta = dict(re.findall(r'<metadata key="([^"]+)" value="([^"]*)"', block))
        idx = int(meta['index'])
        gcode = z.read('Metadata/plate_%d.gcode' % idx).decode('utf-8', 'replace')
        problems = _check_plate(gcode, printer_model, r['machine'])
        if meta.get('outside') == 'true':
            problems.append('object outside the printable area')
        thumb = os.path.join(OUT, '%s plate %d.png' % (job, idx))
        with open(thumb, 'wb') as f:
            f.write(z.read('Metadata/plate_%d.png' % idx))
        plates.append({'plate': idx, 'minutes': round(int(meta.get('prediction') or 0) / 60, 1),
                       'grams': float(meta.get('weight') or 0),
                       'objects': re.findall(r'<object [^>]*name="([^"]+)"', block),
                       'thumbnail': thumb, 'problems': problems})
        all_problems += ['plate %d: %s' % (idx, p) for p in problems]
    plates.sort(key=lambda p: p['plate'])
    entry = {
        'type': 'slice', 'job_id': job, 'time': datetime.datetime.now().isoformat(timespec='seconds'),
        'recipe': recipe, 'recipe_sha': hashlib.sha1(json.dumps(r, sort_keys=True).encode()).hexdigest()[:10],
        'presets': {c: r[c] for c in bp.CATEGORIES}, 'bed_type': r.get('bed_type'), 'overrides': ov,
        'printer': next((k for k, v in PRINTERS.items() if v == r['machine']), None),
        'models': [os.path.basename(m) for m in models], 'output': out,
        'plates': [{k: p[k] for k in ('plate', 'minutes', 'grams', 'objects')} for p in plates],
        'total_minutes': round(sum(p['minutes'] for p in plates), 1),
        'total_grams': round(sum(p['grams'] for p in plates), 1),
        'safe_to_print': not all_problems, 'problems': all_problems,
        'slicer_warning': ' | '.join(p.get('warning_message', '') for p in res.get('sliced_plates', []) if p.get('warning_message')),
    }
    _journal(entry)
    entry['plates'] = plates
    return entry


# ---------------------------------------------------------------- journal
def _journal(entry):
    with open(JOURNAL, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def log_result(job_id, outcome, notes='', plate=None):
    entry = {'type': 'result', 'job_id': job_id, 'plate': plate, 'outcome': outcome, 'notes': notes,
             'time': datetime.datetime.now().isoformat(timespec='seconds')}
    _journal(entry)
    return entry


def journal(limit=20, recipe=None):
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, encoding='utf-8') as f:
        rows = [json.loads(l) for l in f if l.strip()]
    if recipe:
        jobs = {e['job_id'] for e in rows if e.get('recipe') == recipe}
        rows = [e for e in rows if e.get('job_id') in jobs]
    return rows[-limit:]


def open_in_studio(path):
    subprocess.Popen([STUDIO, os.path.abspath(path)], close_fds=True)
    return path


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    flags = ('--job', '--bed', '--printer')
    models = [x for i, x in enumerate(a[2:], 2) if x not in flags and a[i - 1] not in flags]
    if a and a[0] == 'project':
        print(json.dumps(export_project(a[1], models, opt('--job'), bed_type=opt('--bed'), printer=opt('--printer')), indent=1))
    elif a and a[0] == 'slice':
        e = slice_models(a[1], models, opt('--job'), bed_type=opt('--bed'), printer=opt('--printer'))
        print(json.dumps({k: e[k] for k in ('job_id', 'output', 'total_minutes', 'total_grams', 'safe_to_print', 'problems')}, indent=1))
        for p in e['plates']:
            print('  plate %d: %6.1f min %6.1f g  %s%s' % (p['plate'], p['minutes'], p['grams'], ', '.join(p['objects']),
                                                       ('  !! ' + '; '.join(p['problems'])) if p['problems'] else ''))
    elif a and a[0] == 'set':
        print(set_setting(a[1], a[2], a[3], a[4], a[5]))
    elif a and a[0] == 'result':
        print(log_result(a[1], a[2], a[3] if len(a) > 3 else ''))
    else:
        print(__doc__)
