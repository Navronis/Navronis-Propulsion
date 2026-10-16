"""
Export engine geometry for parametric CAD tools.
=================================================
Exports the computed thrust chamber dimensions and inner-wall profile
in formats directly consumable by:

  - **CadQuery** (Python STEP/IGES generation)
  - **FreeCAD** (Python macro import)
  - **OpenSCAD** (CSV point cloud)
  - Any parametric CAD tool that reads JSON or CSV

Two export formats:

  1. **JSON** — structured parameters + full (x, r) profile array.
     Can be loaded directly into a CadQuery ``revolve()`` script.
  2. **CSV** — flat table of (x_mm, r_mm) profile points.
     Can be imported into FreeCAD's Draft Workbench or any spreadsheet.
"""

from __future__ import annotations

import csv
import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kryptonis.propulsion_equations.profile import ChamberProfile


def export_json(
    profile: "ChamberProfile",
    path: str,
    *,
    extra_metadata: dict | None = None,
    sizing_results: dict | None = None,
) -> str:
    """Export complete engine geometry as a JSON file.

    The JSON contains:
      - ``inputs``: all design input parameters
      - ``derived``: all computed dimensions (mm)
      - ``section_boundaries_mm``: axial stations
      - ``profile_points_mm``: list of [x, r] coordinate pairs
      - ``sizing_results``: optional thermal/acoustic/structural data
      - ``cadquery_usage``: example Python snippet for CadQuery import

    Parameters
    ----------
    profile
        ``ChamberProfile`` from ``generate_chamber_profile()``.
    path
        Output file path (e.g. ``"chamber_30kN.json"``).
    extra_metadata
        Optional dict merged into the top level.
    sizing_results
        Optional dict of thermal, acoustic, structural results.

    Returns
    -------
    str
        Absolute path to the written file.
    """
    data = profile.as_dict()

    # Add CadQuery usage example
    data["cadquery_usage"] = {
        "description": "Load this JSON in CadQuery to generate a STEP file",
        "example_script": (
            "import json\n"
            "import cadquery as cq\n"
            "\n"
            "with open('chamber.json') as f:\n"
            "    data = json.load(f)\n"
            "\n"
            "pts = [(x, r) for x, r in data['profile_points_mm']]\n"
            "\n"
            "# Build hollow shell polygon (wall thickness tw = 3.0 mm)\n"
            "tw = 3.0\n"
            "pts_inner = [(x, r) for x, r in data['profile_points_mm']]\n"
            "pts_outer = [(x, r + tw) for x, r in reversed(pts_inner)]\n"
            "hollow_wire = pts_inner + pts_outer\n"
            "wire = cq.Workplane('XZ').polyline(hollow_wire).close()\n"
            "solid = wire.revolve(360, (0, 0, 0), (1, 0, 0))\n"
            "\n"
            "cq.exporters.export(solid, 'chamber_hollow.step')\n"
            "print('Exported hollow 3D STEP file')\n"
        ),
    }

    data["freecad_usage"] = {
        "description": "Load this JSON in FreeCAD to create a revolution solid",
        "example_script": (
            "import json, FreeCAD, Part\n"
            "\n"
            "with open('chamber.json') as f:\n"
            "    data = json.load(f)\n"
            "\n"
            "pts = [FreeCAD.Vector(x, r, 0) for x, r in data['profile_points_mm']]\n"
            "\n"
            "# Close along centreline\n"
            "pts.append(FreeCAD.Vector(pts[-1].x, 0, 0))\n"
            "pts.append(FreeCAD.Vector(pts[0].x, 0, 0))\n"
            "pts.append(pts[0])  # close\n"
            "\n"
            "wire = Part.makePolygon(pts)\n"
            "face = Part.Face(wire)\n"
            "solid = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), 360)\n"
            "Part.show(solid)\n"
        ),
    }

    if sizing_results:
        data["sizing_results"] = sizing_results
    if extra_metadata:
        data.update(extra_metadata)

    data["_generator"] = "kryptonis-propulsion-equations v0.1.0"
    data["_format_version"] = "1.0"

    abs_path = os.path.abspath(path)
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    return abs_path


def export_csv(
    profile: "ChamberProfile",
    path: str,
) -> str:
    """Export the (x, r) profile as a CSV file.

    Columns: ``x_mm, r_mm, section``

    The ``section`` column labels each point as ``cylinder``, ``convergent``,
    ``throat``, or ``divergent`` for easy filtering in CAD tools.

    Parameters
    ----------
    profile
        ``ChamberProfile`` from ``generate_chamber_profile()``.
    path
        Output CSV file path.

    Returns
    -------
    str
        Absolute path to the written file.
    """
    abs_path = os.path.abspath(path)

    x_cyl = profile.x_cyl_end
    x_thr = profile.x_throat

    with open(abs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "r_mm", "section"])
        for xi, ri in zip(profile.x, profile.r):
            if xi <= x_cyl + 1e-9:
                section = "cylinder"
            elif xi <= x_thr + 1e-9:
                section = "convergent"
            elif abs(xi - x_thr) < 1e-6:
                section = "throat"
            else:
                section = "divergent"
            writer.writerow([f"{xi * 1e3:.4f}", f"{ri * 1e3:.4f}", section])

    return abs_path


def export_cadquery_script(
    profile: "ChamberProfile",
    path: str,
    step_output: str = "chamber.step",
    wall_thickness_mm: float = 3.0,
    hollow: bool = True,
) -> str:
    """Export a ready-to-run CadQuery Python script that generates a STEP solid.

    By default, generates a HOLLOW thrust chamber pressure vessel shell
    with realistic metal wall thickness (open injector face and open nozzle exit).

    Parameters
    ----------
    profile
        ``ChamberProfile``.
    path
        Output .py file path.
    step_output
        Filename for the generated STEP file.
    wall_thickness_mm
        Wall thickness in mm (default 3.0 mm).
    hollow
        If True (default), builds a hollow chamber with wall thickness.
        If False, revolves a solid plug of the interior gas volume.

    Returns
    -------
    str
        Absolute path to the written file.
    """
    pts = profile.points_mm()
    pts_repr = repr(pts)

    if hollow:
        body_code = [
            f'wall_thickness_mm = {wall_thickness_mm}',
            '',
            '# Build hollow shell polygon (inner contour forward + outer contour reversed)',
            'pts_inner = [(x, r) for x, r in profile_points]',
            'pts_outer = [(x, r + wall_thickness_mm) for x, r in reversed(profile_points)]',
            'hollow_polygon = pts_inner + pts_outer',
            '',
            'wire = cq.Workplane("XZ").polyline(hollow_polygon).close()',
            '',
            '# Revolve 360 deg around X-axis to create the HOLLOW axisymmetric solid',
            'solid = wire.revolve(360, (0, 0, 0), (1, 0, 0))',
        ]
    else:
        body_code = [
            '# Build solid gas core plug',
            'pts_2d = [(x, r) for x, r in profile_points]',
            'x_start = pts_2d[0][0]',
            'x_end = pts_2d[-1][0]',
            'wire = cq.Workplane("XZ").polyline(pts_2d).lineTo(x_end, 0.0).lineTo(x_start, 0.0).close()',
            'solid = wire.revolve(360, (0, 0, 0), (1, 0, 0))',
        ]

    lines = [
        '"""',
        'Auto-generated CadQuery script from Kryptonis Propulsion Equations.',
        'Run this to generate a 3D STEP solid of the rocket thrust chamber.',
        '',
        'Requirements: pip install cadquery',
        '"""',
        'import cadquery as cq',
        '',
        '# Inner wall profile points (x_mm, r_mm) from injector face to nozzle exit',
        'profile_points = ' + pts_repr,
        '',
    ] + body_code + [
        '',
        '# Export STEP and STL files',
        f'cq.exporters.export(solid, "{step_output}")',
        f'stl_output = "{step_output}".rsplit(".", 1)[0] + ".stl"',
        'try:',
        '    cq.exporters.export(solid, stl_output)',
        '    print(f"Exported STL: {stl_output}")',
        'except Exception:',
        '    pass',
        f'print("Exported STEP: {step_output}")',
        f'print(f"  Total points: {{len(profile_points)}} | Hollow: {hollow}")',
        '',
    ]
    script = "\n".join(lines) + "\n"

    abs_path = os.path.abspath(path)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(script)

    return abs_path
