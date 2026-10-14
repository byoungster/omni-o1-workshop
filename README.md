# Omni O1 Workshop

Photo-size blanks for UV printing, a stackable storage system for them, and the scripts that design,
slice and print it all: Autodesk Fusion driven by Claude over MCP, a Bambu Studio slicing pipeline with
versioned settings, and LAN control of a Bambu Lab P1S.

![Photo blanks 2R to 12R](docs/images/photo-blanks.png)

*Renders show the earlier labeled version; current blanks are plain.*

## What's in the repo

| Folder | Contents |
|---|---|
| `exports/blanks_1mm/` | 3MF models of the 11 standard photo sizes, plain 1 mm (no label) |
| `exports/storage_trays/` | 3MF models of stackable trays and lids (20 blanks each) for 2R to 8R |
| `exports/photo_stands/` | 3MF models of 15° slot stands in three styles (Minimal, Fluted, Rustic), plus slot-width test combs |
| `exports/o1_jigs/` | 3MF tiles of batch jigs for the xTool O1 Omni flat bed (small 330×122 and large 330×420 plates) |
| `exports/sliced/` | Print-ready `.gcode.3mf` files for a Bambu Lab P1S (0.4 nozzle), with plate previews |
| `fusion/` | Fusion API scripts that generate the blanks and trays from parameters |
| `slicer/` | Bambu Studio CLI pipeline, slicing recipes, P1S LAN control, and an MCP server for Claude |
| `docs/images/` | Renders |

## Photo blanks

All sizes are plain 1 mm slabs. There is no label: the storage trays carry the size, and a plain blank
diffuses light evenly (a debossed label thins the blank and shows through). Set `LABELS = True` in
`fusion/photo_blanks.py` to deboss the size name again.
Print them **on a smooth PEI plate**. The face against the plate comes out flat and smooth, and that is the face
you UV print the photo onto.

| Size | mm | inches | Fits a 256 mm bed (A1, P1S, P2S, X1C) |
|---|---|---|---|
| 2R (wallet) | 64 × 89 | 2.5 × 3.5 | yes |
| 3R | 89 × 127 | 3.5 × 5 | yes |
| 4R | 102 × 152 | 4 × 6 | yes |
| 5R | 127 × 178 | 5 × 7 | yes |
| 6R | 152 × 203 | 6 × 8 | yes |
| 8R | 203 × 254 | 8 × 10 | yes, edge to edge with no room for a brim |
| S8R | 203 × 305 | 8 × 12 | no (needs a ~320 mm bed) |
| 10R | 254 × 305 | 10 × 12 | no (needs a ~320 mm bed) |
| S10R | 254 × 381 | 10 × 15 | no (needs a 400 mm bed) |
| 11R | 279 × 356 | 11 × 14 | no (needs a 400 mm bed) |
| 12R | 305 × 381 | 12 × 15 | no (needs a 400 mm bed) |

Thin sheets bow more as they get bigger, so 1 mm is best suited to the smaller sizes. For 8R and up, test
1.5 to 2 mm (change `card_t` in the Fusion script) before committing to a batch.

## Storage trays

![Trays and lids](docs/images/storage-trays-and-lids.png)

- Each tray holds 20 blanks flat, with 0.75 mm clearance per side.
- Trays stack: the inset foot of one tray drops into the rim of the tray below, and a lid caps the top of a stack.
- A full-height front notch lets you lift the top blank or push the bottom one up from below. Tick marks at
  5, 10, 15 and 20 next to the notch show stock at a glance, since one blank is 1 mm of stack.
- The 8R tray and lid are split in two with a dovetail seam so each half fits a 256 mm bed. Glue the halves with CA.
- Print trays upright and lids upside down, exactly as exported. No supports are needed.

![Front of a tray with stock ticks](docs/images/tray-front-stock-ticks.png)

## Photo stands

![Slot stands and test comb](docs/images/photo-stands.png)

- A 15° slot holds the plaque by its bottom edge. Bases reach about 15% of the plaque height behind the slot so
  tall plaques don't tip. Each stand is labeled in inches on the back (2.5x3.5 up to 8x10).
- Three styles on the same footprint:
  - **Minimal**: smooth with chamfered edges.
  - **Fluted**: vertical ribs across the front.
  - **Rustic**: the minimal shape printed with fuzzy skin (Perlin noise) for a stone or weathered look; best in
    wood-fill or marble PLA. Fuzzy skin also roughens the slot, so Rustic stands have a 1.8 mm slot.
- **Print a test comb first** (1.2–1.6 mm, or 1.6–2.4 mm for Rustic). Find the slot that holds your printed blank
  snugly and set `SLOT_W` / `SLOT_W_RUSTIC` in `fusion/photo_stands.py`.
- Print upright as exported, no supports. Matte PLA hides layer lines.

![Fluted stand](docs/images/stand-fluted.png)

## Batch jigs for the xTool O1 Omni

![Photo blank jigs](docs/images/o1-photo-blank-jigs.png)

Flat-bed jigs for 1 mm photo blanks, for both O1 plates. xTool's manual calls the plates mini and standard;
its product page calls them standard and large. By size:

| Blank | Small plate, 330 × 122 mm | Large plate, 330 × 420 mm |
|---|---|---|
| 2R (2.5x3.5 in) | 4 | 18 |
| 3R (3.5x5 in) | 2 | 9 |
| 4R (4x6 in) | 2 | 6 |
| 5R (5x7 in) | - | 4 |
| 6R (6x8 in) | - | 4 |
| 8R (8x10 in) | - | 2 |

- Pockets are 0.9 mm deep, so a 1 mm blank sits 0.1 mm above the jig and the O1's height sensing lands on
  the blanks, all on one plane. 0.2 mm clearance per side, corner reliefs, and a finger notch per pocket.
- Jigs cover the print area and are cut into tiles that fit a 256 mm printer bed, with seams placed in the walls
  between pockets where possible. Butt the tiles together on the plate (or glue them with CA).
- Print in **matte black** PLA: plain and matte so the O1's scan picks out the white blanks.
- Calibrate once: tape over the jig, print the template, measure the offset, correct it in xTool Studio.
- Plate-edge registration clips are coming once the physical plates are measured.

`fusion/o1_jigs.py` generates jigs for any flat rectangular item: add a line to `ITEMS`.

## Printing on a Bambu Lab P1S## Printing on a Bambu Lab P1S

| File | Plates | Time | PLA | Build plate |
|---|---|---|---|---|
| `Photo blanks 2R-8R 1mm.gcode.3mf` | 3 | ~3.2 h | ~170 g | Smooth PEI |
| `Storage trays _ lids.gcode.3mf` | 8 | ~15.5 h | ~831 g | Textured PEI |
| `Slot test comb.gcode.3mf` / `Slot test comb Rustic.gcode.3mf` | 1 each | ~30 min | ~17 g | Textured PEI |
| `Photo stands Minimal / Fluted / Rustic 2R-8R.gcode.3mf` | 1 each | ~3.9 / 4.7 / 4.9 h | ~225 g | Textured PEI |
| `O1 Small jig <size>.gcode.3mf` (2R, 3R, 4R) | 1 each | ~1.2 h | ~55-65 g | Textured PEI, matte black |
| `O1 Large jig <size>.gcode.3mf` (2R-8R) | 3-4 each | ~3.5-4 h | ~160-205 g | Textured PEI, matte black |

Open the file in Bambu Studio and print plate by plate. For other printers, slice the 3MF models in
`exports/` with your own profiles.

## Regenerating the models in Fusion

The scripts in `fusion/` use the Fusion API and define `run(context)`. Run them from Fusion
(Utilities → Scripts and Add-Ins → create a Python script and paste the file in) or through an MCP client
connected to Fusion's built-in MCP server.

- `photo_blanks.py` builds all 11 blanks in the active design. Every dimension is a user parameter.
- `storage_trays.py` builds every tray and lid in a new document and splits parts that exceed the bed.
- `place_blanks_in_trays.py` copies the blanks into their trays as a fit check.
- `photo_stands.py` builds the slot stands (three styles) and the slot-width test combs in a new document.
- `o1_jigs.py` builds tiled batch jigs for the xTool O1 Omni in a new document.

## Slicing pipeline and MCP server

`slicer/` slices from **recipes**: a recipe names three Bambu system presets (machine, process, filament)
and overrides individual settings, each with a dated reason in its changelog. Every slice and every recorded
print outcome is appended to a local journal, so settings can be tuned against real results.

```
cd slicer
pip install -r requirements.txt
python bambu_slice.py slice photo_blanks_1mm "../exports/blanks_1mm/5R*.3mf" --job "5R test"
python bambu_slice.py set photo_blanks_1mm process brim_type brim_ears "corners lifted on 8R"
python bambu_slice.py result "5R test" ok "flat, clean photo face"
```

**Bambu Studio CLI gotcha.** The CLI ignores `inherits` and `include` in preset files passed with
`--load-settings`. It silently falls back to built-in defaults, so you get G-code **with no printer start
sequence and no bed leveling**, zero filament density and wrong bed temperatures. `bambu_profiles.py` resolves
the system presets the way the GUI does, and every sliced plate is checked for the printer's start G-code,
G29 bed leveling and objects inside the bed before it is marked safe to print.

`bambu_mcp.py` exposes all of this to Claude as an MCP server: recipes, settings search and tuning, slicing,
the print journal, and P1S status, camera snapshots, chamber light, and a guarded print start (always a dry
run first, then an explicit confirm). Register it with Claude Code:

```
claude mcp add --scope user bambu -- <path-to-python> <path-to-repo>/slicer/bambu_mcp.py
```

Printer credentials are read from the OS keychain (Windows Credential Manager on Windows), never from files:

```
python -c "import keyring, getpass; [keyring.set_password('omni-o1', 'p1s_' + k, getpass.getpass(k + ': ') if k == 'access_code' else input(k + ': ')) for k in ('ip', 'serial', 'access_code')]"
```

Status and camera work while the printer is on Bambu Cloud. Uploading and starting prints from your own code
needs the printer in **LAN-only mode with Developer Mode on** (Bambu's 2025 authorization firmware), which
disconnects it from Bambu Cloud and Bambu Handy.

## Home Assistant

`homeassistant/blueprints/` holds automations for the [ha-bambulab](https://github.com/greghesp/ha-bambulab)
integration that you can import with one click.

**Print finished / failed: phone alert with photo.** Saves a printer camera snapshot to `/config/www` and pushes
it to your phone (Home Assistant Companion app) with the job name and filament weight.

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbyoungster%2Fomni-o1-workshop%2Fblob%2Fmain%2Fhomeassistant%2Fblueprints%2Fautomation%2Fbambu_print_alert_photo.yaml)

## Roadmap

- Home Assistant as the hub: ESP32 camera and LED status lights, more automations
- Slack bot: request a design in Slack, approve it, and get a photo back when the print finishes
- O1 plate registration clips; jigs for magnets, ornaments, badges, phone cases
- Automated plate handling

## License

- Code (`fusion/`, `slicer/`): [MIT](LICENSE)
- Models, print files and images (`exports/`, `docs/images/`): [CC BY-NC-SA 4.0](LICENSE-MODELS.txt).
  Credit this repo, no commercial use, and share changes under the same license.
