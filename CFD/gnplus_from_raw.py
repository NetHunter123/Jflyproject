"""raw_plateaus.json -> plateaus_<run>.json for process_gnplus.py.

Checks the checksums written in the raw file first, so a copy error stops here.
Angle schedules are the CSVs in this folder.

Run:  python gnplus_from_raw.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = {"A_coarse": (23589.1214, 508), "A_fine": (23605.5634, 508),
         "B_fine": (23345.0179, 508), "F_full": (4353.585, 74)}
A = [(50.0, -3), (50.0, -4), (50.0, -2), (50.0, 0), (50.0, 2), (69.4, -3.5), (69.4, -4.5)]
B = [(24.4, a) for a in (2, 4, 6, 8, 10, 12, 14)]
SCHEDULE = {"A_coarse": [(v, a, 0.0) for v, a in A], "A_fine": [(v, a, 0.0) for v, a in A],
            "B_fine": [(v, a, 0.0) for v, a in B], "F_full": [(24.4, 3.5, 0.0), (24.4, 3.5, 5.0)]}


def walk(o):
    if isinstance(o, bool):
        return 0.0, 0
    if isinstance(o, (int, float)):
        return float(o), 1
    items = o.values() if isinstance(o, dict) else o if isinstance(o, list) else []
    s, n = 0.0, 0
    for x in items:
        a, b = walk(x)
        s, n = s + a, n + b
    return s, n


def plateau(f, m, i):
    g = lambda d, k: d["pl"][i][k][0]
    drift = lambda d, k: d["pl"][i][k][1]
    p = {"Fp": [g(f, "pFX"), g(f, "pFY"), g(f, "pFZ")],
         "Fv": [g(f, "vFX"), g(f, "vFY"), g(f, "vFZ")],
         "drift_Fx": drift(f, "pFX") + drift(f, "vFX"),
         "drift_Fz": drift(f, "pFZ") + drift(f, "vFZ"),
         "range_Fz": f["pl"][i]["pFZ"][2]}
    if m:
        p["M"] = [g(m, "pMX") + g(m, "vMX"), g(m, "pMY") + g(m, "vMY"), g(m, "pMZ") + g(m, "vMZ")]
    return p


def main():
    raw = json.load(open(os.path.join(HERE, "raw_plateaus.json"), encoding="utf-8"))
    for run, (s_ref, n_ref) in CHECK.items():
        s, n = walk(raw[run])
        assert n == n_ref and abs(s - s_ref) < 0.01, f"{run}: checksum {s:.4f}/{n} != {s_ref}/{n_ref}"
        print(f"{run}: checksum ok ({s:.4f}, {n})")
    for run, sched in SCHEDULE.items():
        r = raw[run]
        comps = {}
        for name, fk, mk in (("total", "ft", "mt"), ("wing", "fw", "mw")):
            if fk not in r:
                continue
            pts = []
            for i, (v, a, b) in enumerate(sched):
                p = plateau(r[fk], r.get(mk), i)
                p.update(V=v, alpha=a, beta=b)
                pts.append(p)
            comps[name] = pts
        out = {"run": run, "half": run != "F_full", "total": "total", "components": comps}
        if run.startswith("B"):
            out["np_alpha"] = [2, 8]
            out["clmax"] = True
        if run.startswith("A"):
            out["np_alpha"] = [-4, 2]
        json.dump(out, open(os.path.join(HERE, f"plateaus_{run}.json"), "w", encoding="utf-8"), indent=1)
        print("wrote", f"plateaus_{run}.json")


if __name__ == "__main__":
    main()
