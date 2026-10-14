"""Slice models for the Bambu Lab P1S from versioned recipes, with safety checks and a print journal.

A recipe (recipes/<name>.json) names three Bambu system presets and overrides individual
settings on top of them. Changing a setting is a one-line, dated, diffable edit, and every slice
and every print outcome is appended to journal.jsonl, so settings can be tuned against results.

Usage:
  python bambu_slice.py slice <recipe> <model.3mf|glob> [...] [--job NAME] [--bed "High Temp Plate"]
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
OUT = os.path.join(os.path.dirname(HERE), 'exports', 'sliced')
BED_TYPES = ('Cool Plate', 'Engineering Plate', 'High Temp Plate', 'Textured PEI Plate', 'Supertack Plate')


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


def effective(name, category, key):
    r = load_recipe(name)
    ov = r.get('overrides', {}).get(category, {})
    base = bp.resolve(category, r[category]).get(key)
    return {'preset': r[category], 'preset_value': base, 'override': ov.get(key), 'effective': ov.get(key, base)}


def search_settings(name, pattern):
    """Settings whose key matches `pattern` (regex) across the recipe's three presets."""
    r = load_recipe(name)
    hits = []
    for cat in bp.CATEGORIES:
        cfg = bp.resolve(cat, r[cat])
        ov = r.get('overrides', {}).get(cat, {})
        for k in sorted(cfg):
            if re.search(pattern, k, re.I):
                hits.append({'category': cat, 'key': k, 'preset_value': cfg[k], 'override': ov.get(k)})
    # Settings no preset defines (slicer built-in defaults, e.g. brim_type) are set via the process override
    known = {h['key'] for h in hits} | {k for cat in bp.CATEGORIES for k in bp.resolve(cat, r[cat])}
    ov = r.get('overrides', {}).get('process', {})
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


def _check_plate(gcode, printer_model):
    """Safety checks a sliced plate must pass before it is allowed near the printer."""
    problems = []
    short = printer_model.replace('Bambu Lab ', '')
    if ('machine: %s' % short) not in gcode:
        problems.append('%s start G-code missing' % printer_model)
    if not re.search(r'^; printer_model = %s\s*$' % re.escape(printer_model), gcode, re.M):
        problems.append('G-code was not sliced for %s' % printer_model)
    if not re.search(r'^G29', gcode, re.M):
        problems.append('no bed leveling (G29) in start sequence')
    return problems


def slice_models(recipe, models, job=None, arrange=True, bed_type=None):
    """bed_type overrides the recipe's plate for this job (e.g. whatever plate is loaded right now)."""
    r = load_recipe(recipe)
    if bed_type:
        if bed_type not in BED_TYPES:
            raise ValueError('bed_type must be one of %s' % (BED_TYPES,))
        r['bed_type'] = bed_type
    models = _resolve_models(models)
    job = job or '%s %s' % (recipe, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    job = re.sub(r'[^\w\- .]', '_', job)
    os.makedirs(OUT, exist_ok=True)
    ov = r.get('overrides', {})
    with tempfile.TemporaryDirectory(prefix='bambu_') as tmp:
        files = {}
        for cat in bp.CATEGORIES:
            o = dict(ov.get(cat, {}))
            if cat == 'process' and r.get('bed_type'):
                o['curr_bed_type'] = r['bed_type']
            name = None if cat == 'machine' else 'Omni %s (%s)' % (recipe, cat)
            cfg = bp.build(cat, r[cat], o, name=name)
            if cat != 'machine':
                cfg['compatible_printers'] = [r['machine']]
                cfg['compatible_printers_condition'] = ''
            files[cat] = os.path.join(tmp, cat + '.json')
            with open(files[cat], 'w', encoding='utf-8') as f:
                json.dump(cfg, f)
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
        problems = _check_plate(gcode, printer_model)
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
    if a and a[0] == 'slice':
        opt = lambda k: a[a.index(k) + 1] if k in a else None
        models = [x for i, x in enumerate(a[2:], 2) if x not in ('--job', '--bed') and a[i - 1] not in ('--job', '--bed')]
        e = slice_models(a[1], models, opt('--job'), bed_type=opt('--bed'))
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
