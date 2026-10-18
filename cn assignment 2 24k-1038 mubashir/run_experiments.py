#24k-1038 mubashir sikandar
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulate import run

SEED = 1038

SCENARIOS = {
    "A: reliable": dict(loss=0.0, corrupt=0.0, delay=0.0),
    "B: loss 0.10": dict(loss=0.10, corrupt=0.0, delay=0.0),
    "C: mixed": dict(loss=0.05, corrupt=0.05, delay=0.10),
}

rows = []
for name, params in SCENARIOS.items():
    for proto in ("gbn", "sr"):
        s = run(proto, packets=200, N=4, k=3, seed=SEED, **params)
        rows.append({
            "scenario": name, "protocol": proto.upper(),
            "transmitted": s["transmitted"], "retransmissions": s["retransmissions"],
            "delivered": s["delivered"], "correct_order": s["correct_order"],
            "time_s": round(s["time_ms"] / 1000, 2),
            "throughput_kbps": round(s["throughput_kbps"], 1),
        })

cols = list(rows[0].keys())
with open("results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print(" | ".join(f"{c:>15}" for c in cols))
for r in rows:
    print(" | ".join(f"{str(r[c]):>15}" for c in cols))

# graph
names = list(SCENARIOS)
x = range(len(names))
wd = 0.35
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for i, proto in enumerate(("GBN", "SR")):
    rt = [r["retransmissions"] for r in rows if r["protocol"] == proto]
    tm = [r["time_s"] for r in rows if r["protocol"] == proto]
    ax[0].bar([j + i * wd for j in x], rt, wd, label=proto)
    ax[1].bar([j + i * wd for j in x], tm, wd, label=proto)
for a, t, yl in ((ax[0], "Retransmissions", "packets"), (ax[1], "Completion time", "seconds")):
    a.set_xticks([j + wd / 2 for j in x])
    a.set_xticklabels(names)
    a.set_title(t)
    a.set_ylabel(yl)
    a.legend()
fig.suptitle("GBN vs SR (200 packets, N=4, k=3)")
plt.tight_layout()
plt.savefig("comparison.png", dpi=150)
print("saved results.csv and comparison.png")
