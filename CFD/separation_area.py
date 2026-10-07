"""Area where wall shear τx > 0, from an extracted OpenFOAM time folder.

τx is the OpenFOAM wallShearStress x-component (stress on the fluid).
Attached flow has τx < 0 when +x points downstream. Reverse flow is τx > 0.
The reported area is the surface integral of that indicator: sum of face
areas with τx > 0. Run after extract_wall_fields.py.
"""
import gzip
import os
import sys

import numpy as np

ROOT = os.environ.get("SIMSCALE_OUT") or os.path.join(os.environ["TEMP"], "gnplus-A-fine")
TIME = sys.argv[1] if len(sys.argv) > 1 else "1400"


def load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def find_one(root, name):
    for dirpath, _, files in os.walk(root):
        if name in files:
            return os.path.join(dirpath, name)
    return None


def parse_boundary(text):
    # After the FoamFile header the file is: N ( patch { type; nFaces; startFace; } ... )
    body = text.split("boundaryField", 1)[-1]
    start = body.find("(")
    patches = []
    i = start + 1
    n = len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n or body[i] == ")":
            break
        j = i
        while j < n and body[j] not in " \t\r\n{":
            j += 1
        name = body[i:j]
        k = body.find("{", j)
        depth = 0
        m = k
        while m < n:
            if body[m] == "{":
                depth += 1
            elif body[m] == "}":
                depth -= 1
                if depth == 0:
                    m += 1
                    break
            m += 1
        block = body[k:m]
        def grab(key):
            p = block.find(key)
            if p < 0:
                return None
            return block[p + len(key):].split(";", 1)[0].strip()
        patches.append({
            "name": name,
            "type": grab("type"),
            "nFaces": int(grab("nFaces")),
            "startFace": int(grab("startFace")),
        })
        i = m
    return patches


def parse_points(text):
    start = text.find("\n(")
    end = text.rfind(")")
    blob = text[start:end].replace("(", " ").replace(")", " ")
    arr = np.fromstring(blob, sep=" ")
    return arr.reshape(-1, 3)


def parse_faces(text, wanted):
    """wanted: list of (start, count) face-index ranges. Returns dict start -> (n,  vertex ids)."""
    # Faces are listed in order. Internal faces come first.
    ranges = sorted(wanted)
    out = {}
    pos = text.find("\n(")
    if pos < 0:
        pos = text.find("(")
    i = pos + 1
    n = len(text)
    face_i = 0
    ri = 0

    def skip_to(index):
        nonlocal i, face_i
        while face_i < index:
            i = text.find(")", i)
            if i < 0:
                raise EOFError("faces ended early")
            i += 1
            face_i += 1

    while ri < len(ranges):
        start, count = ranges[ri]
        skip_to(start)
        ids = []
        for _ in range(count):
            i = text.find("(", i)
            j = text.find(")", i)
            verts = [int(x) for x in text[i + 1:j].split()]
            ids.append(verts)
            i = j + 1
            face_i += 1
        out[start] = ids
        ri += 1
    return out


def face_area_centroid(pts):
    p = np.asarray(pts, float)
    if len(p) < 3:
        return 0.0, p.mean(axis=0) if len(p) else np.zeros(3)
    origin = p[0]
    acc = np.zeros(3)
    for a, b in zip(p[1:-1], p[2:]):
        acc += np.cross(a - origin, b - origin)
    area_vec = 0.5 * acc
    return float(np.linalg.norm(area_vec)), p.mean(axis=0)


def parse_patch_vectors(block):
    if "nonuniform" not in block:
        p = block.find("(")
        if p < 0:
            return None
        nums = block[p + 1:block.find(")", p)].split()
        return np.array([float(x) for x in nums], float)
    start = block.find("(", block.find("nonuniform"))
    end = block.rfind(")")
    blob = block[start:end].replace("(", " ").replace(")", " ")
    arr = np.fromstring(blob, sep=" ")
    return arr.reshape(-1, 3)


def parse_patch_scalars(block):
    if "nonuniform" not in block:
        p = block.find("value")
        if p < 0:
            return None
        tail = block[p:].split(";", 1)[0]
        nums = [float(x) for x in tail.replace("uniform", " ").split() if x[:1].isdigit() or x[:1] == "-"]
        return np.array(nums[-1:], float) if nums else None
    start = block.find("(", block.find("nonuniform"))
    end = block.rfind(")")
    blob = block[start:end].replace("(", " ").replace(")", " ")
    return np.fromstring(blob, sep=" ")


def blocks_by_name(text):
    key = "boundaryField"
    p = text.find(key)
    body = text[p + len(key):]
    i = body.find("{") + 1
    n = len(body)
    depth = 1
    out = {}
    while i < n and depth:
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i < n and body[i] == "}":
            break
        j = i
        while j < n and body[j] not in " \t\r\n{":
            j += 1
        name = body[i:j]
        k = body.find("{", j)
        depth2 = 0
        m = k
        while m < n:
            if body[m] == "{":
                depth2 += 1
            elif body[m] == "}":
                depth2 -= 1
                if depth2 == 0:
                    m += 1
                    break
            m += 1
        out[name] = body[k:m]
        i = m
    return out


def main():
    bpath = find_one(ROOT, "boundary") or find_one(ROOT, "boundary.gz")
    ppath = find_one(ROOT, "points") or find_one(ROOT, "points.gz")
    fpath = find_one(ROOT, "faces") or find_one(ROOT, "faces.gz")
    tdir = None
    for dirpath, _, files in os.walk(ROOT):
        if os.path.basename(dirpath) == TIME and any(f.startswith("wallShearStress") for f in files):
            tdir = dirpath
            break
    if not (bpath and ppath and fpath and tdir):
        print("missing", bpath, ppath, fpath, tdir)
        sys.exit(1)
    print("boundary", bpath)
    print("time", tdir)
    boundary = parse_boundary(load(bpath).decode("latin1"))
    walls = [p for p in boundary if p["type"] == "wall"]
    print(f"patches {len(boundary)} walls {len(walls)} wall faces {sum(p['nFaces'] for p in walls)}")
    points = parse_points(load(ppath).decode("latin1"))
    print("points", len(points))
    faces = parse_faces(load(fpath).decode("latin1"), [(p["startFace"], p["nFaces"]) for p in walls])
    shear = blocks_by_name(load(os.path.join(tdir, "wallShearStress.gz") if os.path.exists(os.path.join(tdir, "wallShearStress.gz")) else os.path.join(tdir, "wallShearStress")).decode("latin1"))
    ypath = os.path.join(tdir, "yPlus.gz")
    yplus = blocks_by_name(load(ypath).decode("latin1")) if os.path.exists(ypath) else {}

    area = rev = fx = 0.0
    y_area = y_sum = 0.0
    y_max = 0.0
    y_over1 = y_over5 = 0.0
    xs, as_, txs = [], [], []
    for p in walls:
        tau = parse_patch_vectors(shear[p["name"]])
        if tau.ndim == 1:
            tau = np.repeat(tau.reshape(1, 3), p["nFaces"], axis=0)
        ids = faces[p["startFace"]]
        yp = parse_patch_scalars(yplus[p["name"]]) if p["name"] in yplus else None
        if yp is not None and yp.size == 1:
            yp = np.repeat(yp, p["nFaces"])
        for i, verts in enumerate(ids):
            a, c = face_area_centroid(points[verts])
            tx = float(tau[i, 0])
            area += a
            fx += tx * a
            if tx > 0.0:
                rev += a
                xs.append(c[0])
                as_.append(a)
                txs.append(tx)
            if yp is not None and i < yp.size:
                y_area += a
                y_sum += float(yp[i]) * a
                y_max = max(y_max, float(yp[i]))
                if yp[i] > 1:
                    y_over1 += a
                if yp[i] > 5:
                    y_over5 += a
    print(f"wall area m2 {area:.6f}")
    print(f"reverse area m2 {rev:.6e}")
    print(f"reverse fraction {rev / area if area else 0:.6e}")
    print(f"integral tau_x N {fx:.4f}")
    if txs:
        txa = np.array(txs)
        wa = np.array(as_)
        print(f"reverse tau_x Pa  max {txa.max():.4f}  area-weighted mean {np.average(txa, weights=wa):.4f}")
        print(f"reverse force N {np.sum(txa * wa):.4f}")
        for thr in (1e-4, 1e-3, 0.01, 0.05, 0.5, 1.0):
            m = txa > thr
            print(f"  tau_x>{thr:g} Pa  area cm2 {wa[m].sum()*1e4:.3f}  force N {np.sum(txa[m]*wa[m]):.4f}")
    if xs:
        xs = np.array(xs)
        w = np.array(as_)
        print(f"reverse centroid x m {np.average(xs, weights=w):.4f}")
        edges = np.linspace(xs.min(), xs.max(), 8)
        hist, _ = np.histogram(xs, bins=edges, weights=w)
        for a, b, h in zip(edges[:-1], edges[1:], hist):
            if h > 0:
                print(f"  x {a:.3f}..{b:.3f}  {h * 1e4:.3f} cm2")
    if y_area:
        print(f"yPlus mean {y_sum / y_area:.3f} max {y_max:.2f} area y+>1 {y_over1 / y_area:.3f} y+>5 {y_over5 / y_area:.3f}")


if __name__ == "__main__":
    main()
