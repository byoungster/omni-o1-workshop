"""Resolve Bambu Studio system presets into complete configs the CLI can use.

The Bambu Studio CLI ignores `inherits`/`include` in --load-settings files and silently falls
back to built-in defaults (no start G-code, zero filament density, wrong bed temps). This module
walks the same chain the GUI does: parent preset first, then `include` templates, then the
preset's own keys, where a "nil" entry in a list keeps the parent's value at that index.
"""
import glob
import json
import os

SYSTEM = r'C:\Program Files\Bambu Studio\resources\profiles\BBL'
CATEGORIES = ('machine', 'process', 'filament')
_index = {}


def _scan(cat):
    if cat not in _index:
        idx = {}
        for f in glob.glob(os.path.join(SYSTEM, cat, '*.json')):
            try:
                with open(f, encoding='utf-8') as fh:
                    d = json.load(fh)
            except (OSError, ValueError):
                continue
            if d.get('name'):
                idx[d['name']] = d
        _index[cat] = idx
    return _index[cat]


def _as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith('[') and v.endswith(']'):
        try:
            return json.loads(v.replace("'", '"'))
        except ValueError:
            pass
    return [v] if v else []


def apply(base, over):
    """Overlay `over` onto `base` (both dicts), honouring "nil" placeholders in lists."""
    out = dict(base)
    for k, v in over.items():
        if k in ('inherits', 'include'):
            continue
        if isinstance(v, list) and 'nil' in v:
            parent = out.get(k) if isinstance(out.get(k), list) else []
            v = [(parent[i] if i < len(parent) else (parent[-1] if parent else 'nil')) if x == 'nil' else x
                 for i, x in enumerate(v)]
        out[k] = v
    return out


def resolve(cat, name):
    """Fully resolved system preset `name` of category `cat` (machine/process/filament)."""
    raw = _scan(cat).get(name)
    if raw is None:
        raise KeyError('%s preset not found: %s' % (cat, name))
    cfg = resolve(cat, raw['inherits']) if raw.get('inherits') else {}
    for inc in _as_list(raw.get('include')):
        cfg = apply(cfg, resolve(cat, inc))
    cfg = apply(cfg, raw)
    cfg.pop('inherits', None)
    cfg.pop('include', None)
    return cfg


def presets(cat, contains=''):
    """Instantiable system preset names, optionally filtered by substring."""
    return sorted(n for n, d in _scan(cat).items()
                  if d.get('instantiation', 'true') == 'true' and contains.lower() in n.lower())


def build(cat, base_name, overrides=None, name=None):
    """Resolved preset plus overrides, ready to write for --load-settings / --load-filaments.

    Override values are coerced to the shape of the base value: lists of strings stay lists
    (a scalar override fills every slot), scalars become strings.
    """
    cfg = resolve(cat, base_name)
    for k, v in (overrides or {}).items():
        cur = cfg.get(k)
        if isinstance(cur, list) and not isinstance(v, list):
            v = [str(v)] * max(1, len(cur))
        elif isinstance(v, list):
            v = [str(x) for x in v]
        elif isinstance(v, bool):
            v = '1' if v else '0'
        else:
            v = str(v)
        cfg[k] = v
    cfg['type'] = cat
    cfg['from'] = 'User' if name else 'system'
    cfg['name'] = name or base_name
    cfg['instantiation'] = 'true'
    return cfg
