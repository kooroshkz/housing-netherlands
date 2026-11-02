"""Build data/map.json (simplified province outlines as SVG paths) from CBS/PDOK open data.

    python scripts/make_map.py            # downloads the 2025 generalised provinces from PDOK
    python scripts/make_map.py file.json  # or uses a local GeoJSON

Source: CBS gebiedsindelingen via PDOK, CC BY 4.0.
"""
from __future__ import annotations

import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDOK = ("https://service.pdok.nl/cbs/gebiedsindelingen/2025/wfs/v1_0?request=GetFeature&service=WFS"
        "&version=2.0.0&typeName=gebiedsindelingen:provincie_gegeneraliseerd&outputFormat=json&srsName=EPSG:4326")

LAT0 = 52.15                      # projection centre
KX = math.cos(math.radians(LAT0))
SCALE = 160                       # pixels per degree of latitude
TOLERANCE = 0.0045                # simplification in degrees
MIN_RING_AREA = 0.0006            # drop tiny islands (deg²)


def project(lon: float, lat: float, box: tuple) -> tuple[float, float]:
    lon_min, lat_max = box
    return (lon - lon_min) * KX * SCALE, (lat_max - lat) * SCALE


def simplify(points: list, tol: float) -> list:
    """Douglas-Peucker."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    idx, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        x0, y0 = points[i]
        d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            idx, dmax = i, d
    if dmax > tol:
        return simplify(points[:idx + 1], tol)[:-1] + simplify(points[idx:], tol)
    return [points[0], points[-1]]


def simplify_ring(ring: list, tol: float) -> list:
    """A closed ring starts and ends on the same point, so split it at the farthest point first."""
    x0, y0 = ring[0]
    far = max(range(len(ring)), key=lambda i: (ring[i][0] - x0) ** 2 + (ring[i][1] - y0) ** 2)
    return simplify(ring[:far + 1], tol)[:-1] + simplify(ring[far:], tol)


def area(ring: list) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def main() -> None:
    if len(sys.argv) > 1:
        geo = json.loads(Path(sys.argv[1]).read_text())
    else:
        with urllib.request.urlopen(PDOK, timeout=60) as r:
            geo = json.load(r)
    rings_all = []
    for f in geo["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings_all.append((f["properties"]["statnaam"], [p[0] for p in polys]))
    lons = [x for _, rings in rings_all for ring in rings for x, _ in ring]
    lats = [y for _, rings in rings_all for ring in rings for _, y in ring]
    box = (min(lons), max(lats))
    width = (max(lons) - min(lons)) * KX * SCALE
    height = (max(lats) - min(lats)) * SCALE
    provinces = []
    for name, rings in rings_all:
        parts = []
        for ring in rings:
            if area(ring) < MIN_RING_AREA:
                continue
            pts = simplify_ring(ring, TOLERANCE)
            if len(pts) < 4:
                continue
            xy = [project(lon, lat, box) for lon, lat in pts]
            parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in xy) + "Z")
        provinces.append({"name": name, "d": "".join(parts)})
    out = {
        "source": "CBS gebiedsindelingen 2025 via PDOK (CC BY 4.0)",
        "viewBox": f"0 0 {width:.0f} {height:.0f}",
        "projection": {"lon_min": box[0], "lat_max": box[1], "kx": KX, "scale": SCALE},
        "provinces": provinces,
    }
    path = ROOT / "data" / "map.json"
    path.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{path}: {len(provinces)} provinces, {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
