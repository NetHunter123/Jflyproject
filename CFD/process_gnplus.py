"""Post-processing of the GN+ SimScale runs (R07g).

Input: plateaus_<run>.json, written from the SimScale force/moment plots. Each
plateau holds the mean of the last 200 iterations of that angle and the drift
(mean of the last 100 minus mean of the 100 before). Forces are in N, CAD axes
(x aft, y right wing, z up), moments about x = 0.5837 m.

Half-model runs are doubled here. Nothing is fitted to a target.

Run:  python process_gnplus.py plateaus_A_coarse.json [plateaus_A_fine.json ...]
"""
import json
import math
import sys

RHO = 1.225
S = 0.30
C = 0.2236
B = 1.3416
W = 76.0
X_REF = 0.5837
X_CG = 0.591
PROP_NP_SHIFT = 0.0056           # R07c: prop normal force moves NP forward
X_HT_C4 = 1.36626 - 0.75 * 0.10865
S_HT = 0.04698
A_HT_PER_DEG = 0.061             # Helmbold AR 4 (0.0676/deg) x 0.9 tail efficiency (estimate)
CONVERGED_FZ_DRIFT = 0.3         # N per 100 it, full aircraft: levels above this are not used for CLmax
ETA_PROP, K_BAT, E_BAT, USE = 0.84, 1.18, 583.0, 0.8


def wind(alpha, beta=0.0):
    a, b = math.radians(alpha), math.radians(beta)
    return (math.cos(a) * math.cos(b), -math.sin(b), math.sin(a) * math.cos(b))


def point(p, half):
    k = 2.0 if half else 1.0
    V, alpha, beta = p["V"], p["alpha"], p.get("beta", 0.0)
    q = 0.5 * RHO * V * V
    u = wind(alpha, beta)
    lift_dir = (-math.sin(math.radians(alpha)), 0.0, math.cos(math.radians(alpha)))
    Fp = [k * v for v in p["Fp"]]
    Fv = [k * v for v in p["Fv"]]
    F = [a + b for a, b in zip(Fp, Fv)]
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    D, Dp, Dv = dot(F, u), dot(Fp, u), dot(Fv, u)
    L = dot(F, lift_dir)
    out = dict(V=V, alpha=alpha, beta=beta, q=q, L=L, D=D, Dp=Dp, Dv=Dv, Fz=F[2],
               CL=L / (q * S), CD=D / (q * S), CN=F[2] / (q * S), LD=L / D if D else float("nan"))
    if "M" in p:
        My = k * p["M"][1]
        out["My"] = My
        out["Cm"] = My / (q * S * C)
        out["Cm_cg"] = (My + (X_CG - X_REF) * F[2]) / (q * S * C)
        if not half:
            out["Mz"] = p["M"][2]
            out["Cn"] = p["M"][2] / (q * S * B)
            out["Fy"] = F[1]
    dFx, dFz = k * p.get("drift_Fx", 0.0), k * p.get("drift_Fz", 0.0)
    out["drift_D"] = dFx * u[0] + dFz * u[2]   # projected on the flow, not body-axis Fx
    out["drift_Fz"] = dFz
    return out


def interp(xs, ys, x):
    pts = sorted(zip(xs, ys))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    (x0, y0), (x1, y1) = (pts[0], pts[1]) if x < pts[0][0] else (pts[-2], pts[-1])
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def chain(D, V):
    P_shaft = D * V / ETA_PROP
    P_bat = P_shaft * K_BAT
    return P_shaft, P_bat, USE * E_BAT / P_bat * 60.0


def one_g(points, V):
    pts = [p for p in points if abs(p["V"] - V) < 0.5 and p["beta"] == 0.0]
    if len(pts) < 2:
        return None
    Ls = [p["L"] for p in pts]
    a1 = interp(Ls, [p["alpha"] for p in pts], W)
    g = {k: interp([p["alpha"] for p in pts], [p[k] for p in pts], a1)
         for k in ("D", "Dp", "Dv", "CL", "CD", "Cm", "Cm_cg", "Fz") if all(k in p for p in pts)}
    g["alpha"] = a1
    q = 0.5 * RHO * V * V
    Di = q * S * g["CL"] ** 2 / 16.02
    g["Di_book"] = Di
    g["D_gnplus"] = Di + 1.35 * (g["D"] - Di)          # old plan formula, rejected by the audit (_Archiv/GN+-plan-do-audytu)
    g["D_friction"] = g["Dp"] + 1.35 * g["Dv"]          # live GN+.md: roughness on friction only
    for tag in ("D", "D_gnplus", "D_friction"):
        P_shaft, P_bat, minutes = chain(g[tag], V)
        g["P_shaft_" + tag], g["P_bat_" + tag], g["min_" + tag] = P_shaft, P_bat, minutes
    if "Cm_cg" in g:
        M_cg = g["Cm_cg"] * q * S * C
        F_tail = M_cg / (X_HT_C4 - X_CG)
        g["tail_trim_N"] = F_tail
        g["tail_incidence_deg"] = F_tail / (q * S_HT * A_HT_PER_DEG)
    return g


def main(paths):
    report = {}
    for path in paths:
        data = json.load(open(path, encoding="utf-8"))
        half = data.get("half", True)
        comps = {name: [point(p, half) for p in plist] for name, plist in data["components"].items()}
        total = comps[data.get("total", "total")]
        r = {"points": total, "components": {k: v for k, v in comps.items() if k != data.get("total", "total")}}
        for V in sorted({round(p["V"], 1) for p in total}):
            g = one_g(total, V)
            if g:
                r[f"1g_{V}"] = g
        lin = [p for p in total if "Cm" in p and p["beta"] == 0.0 and data.get("np_alpha", (-90, 90))[0] <= p["alpha"] <= data.get("np_alpha", (-90, 90))[1]]
        for V in sorted({round(p["V"], 1) for p in lin}):
            pv = [p for p in lin if abs(p["V"] - V) < 0.5]
            if len(pv) >= 2:
                slope, _ = fit([p["CN"] for p in pv], [p["Cm"] for p in pv])
                x_np = X_REF - C * slope
                r[f"NP_{V}"] = dict(dCm_dCN=slope, x_NP=x_np, margin=(x_np - X_CG) / C,
                                    margin_prop=(x_np - PROP_NP_SHIFT - X_CG) / C,
                                    alphas=[p["alpha"] for p in pv])
        # Highest CL of a converged level: only meaningful for a run that reaches the lift break (B).
        conv = [p for p in total if p["beta"] == 0.0 and abs(p["drift_Fz"]) <= CONVERGED_FZ_DRIFT]
        if data.get("clmax") and conv:
            top = max(conv, key=lambda p: p["CL"])
            vs = math.sqrt(2 * W / (RHO * S * top["CL"]))
            r["CL_highest_converged"] = dict(alpha=top["alpha"], CL=top["CL"], Vs=vs, launch=1.2 * vs)
        report[data["run"]] = r
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
