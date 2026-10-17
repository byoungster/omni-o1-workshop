# Omni O1 Workshop

## FDM bindings

The `fdm` plugin holds the generic rules: the skills `design-rules`, `enclosure-design` and `durability-testing`, and the `print-engineer` agent. This section binds them to this repo.

- **CAD:** parametric Fusion API scripts in `fusion/*.py`, run through the `fusion` MCP server (`fusion_mcp_execute`, a "script" feature).
  - Each script defines `run(context)` and builds into a new document. API lengths are in cm (`MM = 0.1`).
  - Constants sit at the top of each script with a one-line reason. A superseded value stays as a comment saying what failed.
  - Models are built as printed (+Z is the build direction), unless the docstring says otherwise.
- **Exports:** 3MF to `exports/<category>/`, STEP to `cad/`. Export before any Fusion cloud save. Never publish G-code or `.f3d`.
- **Printers:** a Bambu Lab P1S and an X1 Carbon, both with 0.4 mm nozzles and 256 mm beds.
  - The P1S prints photo blanks and other jobs: white PLA on smooth PEI, with black PLA also loaded.
  - The X1C prints storage and dispenser parts and jigs: black PLA Matte on textured PEI. Black PETG is loaded but low, so prototypes stay in PLA.
- **Slicing:** the `bambu` MCP server, with recipes in `slicer/recipes/*.json`. A recipe is three system presets plus overrides, with a dated changelog.
  - Change one setting at a time, with a reason. Never treat `safe_to_print=false` as printable.
  - Gyroid infill is the pipeline default.
  - Parts whose bed-side face is a show face in white need `start_purge_extra_mm`.
- **Printing:** follow the print-start rules in memory. Run the `print-engineer` review before slicing any new or changed functional part.
- **Results:**
  - Print outcomes go to the slicing journal through `log_print_result`.
  - Strength, durability and fit tests go to `slicer/test_results.jsonl` (git-ignored) in the `durability-testing` schema. Set `print.job_id` and `print.recipe` so each test joins its slice.
  - When a test changes a setting or a design constant, cite the test id in the recipe changelog or the script comment.
- **Products:** photo blanks, storage and dispenser trays, photo stands, and O1 jigs, frames and drill guides (see `README.md`).
