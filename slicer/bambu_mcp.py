"""MCP server: slice for the Bambu Lab P1S from versioned recipes, tune settings against results,
and drive the printer over LAN (status, camera, light, guarded print start).

Starting prints needs the P1S in LAN-only + Developer Mode; status, camera and light work on Bambu Cloud too.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import MCPServer  # noqa: E402

import bambu_printer as bpr  # noqa: E402
import bambu_profiles as bp  # noqa: E402
import bambu_slice as bs  # noqa: E402

server = MCPServer(
    name='bambu',
    instructions=(
        'Slices models for the Bambu Lab P1S using recipes in slicer/recipes (three Bambu system presets '
        'plus overrides). To tune a print, read the journal, change one setting at a time with set_setting '
        '(always give the reason), re-slice, and record the real outcome with log_print_result. Never treat '
        'a slice with safe_to_print=false as printable. Never call print_plate with confirm=True or print_control '
        'without the user explicitly approving that exact action.'),
)


@server.tool()
def list_recipes() -> list[dict]:
    """List slicing recipes with their descriptions and presets."""
    out = []
    for n in bs.list_recipes():
        r = bs.load_recipe(n)
        out.append({'recipe': n, 'description': r.get('description', ''), 'bed_type': r.get('bed_type'),
                    'presets': {c: r[c] for c in bp.CATEGORIES}})
    return out


@server.tool()
def show_recipe(recipe: str) -> dict:
    """Full recipe: presets, bed type, overrides and dated changelog."""
    return bs.load_recipe(recipe)


@server.tool()
def create_recipe(recipe: str, description: str, based_on: str | None = None, machine: str | None = None,
                  process: str | None = None, filament: str | None = None, bed_type: str | None = None) -> dict:
    """Create a new recipe, optionally copying another recipe's presets and overrides.

    bed_type is one of: Cool Plate, Engineering Plate, High Temp Plate (smooth PEI), Textured PEI Plate, Supertack Plate.
    """
    if os.path.exists(bs.recipe_path(recipe)):
        raise ValueError('recipe already exists: ' + recipe)
    r = dict(bs.load_recipe(based_on)) if based_on else {'overrides': {}}
    r['description'] = description
    for cat, val in (('machine', machine), ('process', process), ('filament', filament)):
        if val:
            r[cat] = val
        if not r.get(cat):
            raise ValueError('%s preset required' % cat)
        bp.resolve(cat, r[cat])  # raises if the preset does not exist
    if bed_type:
        if bed_type not in bs.BED_TYPES:
            raise ValueError('bed_type must be one of %s' % (bs.BED_TYPES,))
        r['bed_type'] = bed_type
    r['changelog'] = ['created' + (' from %s' % based_on if based_on else '')]
    bs.save_recipe(recipe, r)
    return r


@server.tool()
def set_setting(recipe: str, category: str, key: str, value: str, reason: str) -> dict:
    """Override one setting in a recipe (category: machine, process or filament) and log the reason.

    Values use Bambu Studio's config format, e.g. "3", "15%", "monotonic", "0.15".
    """
    return bs.set_setting(recipe, category, key, value, reason)


@server.tool()
def reset_setting(recipe: str, category: str, key: str, reason: str) -> dict:
    """Remove an override so the preset's value applies again."""
    return bs.set_setting(recipe, category, key, None, reason)


@server.tool()
def get_setting(recipe: str, category: str, key: str) -> dict:
    """Preset value, override and effective value for one setting."""
    return bs.effective(recipe, category, key)


@server.tool()
def search_settings(recipe: str, pattern: str) -> list[dict]:
    """Find setting keys matching a regex (e.g. "brim|skirt", "bed_temp|plate_temp") with current values."""
    return bs.search_settings(recipe, pattern)


@server.tool()
def list_presets(category: str, contains: str = '') -> list[str]:
    """Bambu system preset names for machine, process or filament, filtered by substring (e.g. "P1S")."""
    return bp.presets(category, contains)


@server.tool()
def slice(recipe: str, models: list[str], job: str | None = None, bed_type: str | None = None) -> dict:
    """Slice 3MF/STL files (paths or globs) with a recipe. Auto-arranges across as many plates as needed.

    Returns per-plate time, filament, objects, thumbnail path and safety problems. The .gcode.3mf can be
    opened in Bambu Studio (open_in_bambu_studio) to print. bed_type overrides the recipe's plate for this
    job (Cool Plate, Engineering Plate, High Temp Plate = smooth PEI, Textured PEI Plate, Supertack Plate).
    """
    return bs.slice_models(recipe, models, job, bed_type=bed_type)


@server.tool()
def open_in_bambu_studio(path: str) -> str:
    """Open a 3MF / .gcode.3mf in the Bambu Studio GUI on this PC."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return 'opened ' + bs.open_in_studio(path)


@server.tool()
def log_print_result(job_id: str, outcome: str, notes: str = '', plate: int | None = None) -> dict:
    """Record what actually happened when a sliced job was printed (e.g. outcome "ok", "warped", "poor adhesion")."""
    return bs.log_result(job_id, outcome, notes, plate)


@server.tool()
def journal(limit: int = 20, recipe: str | None = None) -> list[dict]:
    """Recent slices and recorded print results, optionally for one recipe."""
    return bs.journal(limit, recipe)


@server.tool()
def printer_status() -> dict:
    """Live P1S status (via Home Assistant when configured, else LAN): state, progress, SD card, AMS, errors."""
    return bpr._ha_status() or bpr.status()


@server.tool()
def camera_snapshot(path: str | None = None, light_on: bool = True) -> dict:
    """Save a P1S camera frame (1280x720 JPEG) and return its path. Turns the chamber light on by default."""
    path = path or os.path.join(bs.OUT, '..', 'snapshots', 'p1s %s.jpg' % datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    return bpr.snapshot(os.path.abspath(path), light=light_on)


@server.tool()
def chamber_light(on: bool) -> bool:
    """Turn the P1S chamber light on or off."""
    return bpr.light(on)


@server.tool()
def print_plate(path: str, plate: int = 1, confirm: bool = False, use_ams: bool | None = None,
                ams_slot: int | None = None, color: str | None = None) -> dict:
    """Send one plate of a sliced .gcode.3mf to the P1S.

    Call first WITHOUT confirm to get the plan (objects, time, build plate to load). Only call with
    confirm=True after the user has explicitly approved that plan. Only files sliced by this pipeline
    that passed its safety checks are accepted. Needs LAN-only + Developer Mode on the printer.
    color (hex, e.g. "000000") picks the AMS slot holding that colour; default is the recipe's ams_color.
    """
    return bpr.print_job(path, plate, confirm, use_ams, ams_slot, color=color)


@server.tool()
def print_control(action: str) -> bool:
    """pause, resume or stop the current print. Only use when the user asks."""
    if action not in ('pause', 'resume', 'stop'):
        raise ValueError('action must be pause, resume or stop')
    return bpr.control(action)


if __name__ == '__main__':
    server.run()
