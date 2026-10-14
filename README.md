# Omni O1 Workshop

Photo-size blanks for UV printing, a stackable storage system for them, and the scripts that design,
slice and print it all: Autodesk Fusion driven by Claude over MCP, a Bambu Studio slicing pipeline with
versioned settings, and LAN control of a Bambu Lab P1S.

![Photo blanks 2R to 12R](docs/images/photo-blanks.png)

## What's in the repo

| Folder | Contents |
|---|---|
| `exports/blanks_1mm/` | 3MF models of the 11 standard photo sizes, 1 mm thick, size label debossed 0.4 mm |
| `exports/storage_trays/` | 3MF models of stackable trays and lids (20 blanks each) for 2R to 8R |
| `exports/sliced/` | Print-ready `.gcode.3mf` files for a Bambu Lab P1S (0.4 nozzle), with plate previews |
| `fusion/` | Fusion API scripts that generate the blanks and trays from parameters |
| `slicer/` | Bambu Studio CLI pipeline, slicing recipes, P1S LAN control, and an MCP server for Claude |
| `docs/images/` | Renders |

## Photo blanks

All sizes are 1 mm thick with the size name debossed 0.4 mm (two layers at 0.2 mm), which leaves a 0.6 mm floor.
Print them **label side up on a smooth PEI plate**. The face against the plate comes out flat and smooth, and
that is the face you UV print the photo onto. The label ends up on the back.

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

## Printing on a Bambu Lab P1S

| File | Plates | Time | PLA | Build plate |
|---|---|---|---|---|
| `Photo blanks 2R-8R 1mm.gcode.3mf` | 3 | ~3.3 h | ~167 g | Smooth PEI |
| `Storage trays _ lids.gcode.3mf` | 8 | ~15.5 h | ~831 g | Textured PEI |

Open the file in Bambu Studio and print plate by plate. For other printers, slice the 3MF models in
`exports/` with your own profiles.

## Regenerating the models in Fusion

The scripts in `fusion/` use the Fusion API and define `run(context)`. Run them from Fusion
(Utilities → Scripts and Add-Ins → create a Python script and paste the file in) or through an MCP client
connected to Fusion's built-in MCP server.

- `photo_blanks.py` builds all 11 blanks in the active design. Every dimension is a user parameter.
- `storage_trays.py` builds every tray and lid in a new document and splits parts that exceed the bed.
- `place_blanks_in_trays.py` copies the blanks into their trays as a fit check.

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
- UV printing workflow and jigs for the xTool O1 Omni
- Automated plate handling

## License

- Code (`fusion/`, `slicer/`): [MIT](LICENSE)
- Models, print files and images (`exports/`, `docs/images/`): [CC BY-NC-SA 4.0](LICENSE-MODELS.txt).
  Credit this repo, no commercial use, and share changes under the same license.
