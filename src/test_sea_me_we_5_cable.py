"""Hourly median min-RTT from SG and FR anchors to the three Pakistani anchors (anchoring mesh, free data)."""

import collections
import datetime as dt
import statistics
from datetime import timezone

import matplotlib
import requests

matplotlib.use("Agg")
import matplotlib.dates as md
import matplotlib.pyplot as plt

# Define the incident time range
U: timezone = dt.UTC
ts = lambda *a: int(dt.datetime(*a, tzinfo=U).timestamp())  # Convert to Unix timestamp
START, STOP = ts(2026, 11, 14), ts(2026, 11, 23)

# Define vantage points
VPS = {
    "Singapore anchors": [6970, 6726, 6506],
    "France anchors": [6320, 6333, 6363, 7450],
}

# Define measurements running from Pakistani anchors
MSM = {
    "7613 Z COM (AS152605, behind TWA)": 130058240,
    "7764 LUMS (AS17557, PTCL)": 179602008,
    "7812 Aero Cable (AS138910)": 214303896,
}
fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
for ax, (vlab, prbs) in zip(axes, VPS.items()):
    for lab, msm in MSM.items():
        r = requests.get(
            f"https://atlas.ripe.net/api/v2/measurements/{msm}/results/",
            params={
                "start": START,
                "stop": STOP,
                "probe_ids": ",".join(map(str, prbs)),
            },
            timeout=300,
        ).json()

        # Group the measurements by hour
        h = collections.defaultdict(list)
        for x in r:
            if x.get("min", -1) > 0:
                h[x["timestamp"] // 3600 * 3600].append(x["min"])

        xs = sorted(h)
        ax.plot(
            [dt.datetime.fromtimestamp(t, U) for t in xs],
            [statistics.median(h[t]) for t in xs],
            label=lab,
            lw=1.3,
        )
    ax.axvline(dt.datetime(2026, 11, 18, 13, tzinfo=U), color="red", ls="--", lw=1)
    ax.set_title(f"From {vlab}")
    ax.set_ylabel("median min RTT (ms)")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8, loc="upper left")
axes[1].xaxis.set_major_formatter(md.DateFormatter("%d %b"))
fig.suptitle(
    "RIPE Atlas anchoring-mesh pings to Pakistani anchors; red line = SMW5 fault onset (~13:00 UTC 18 Nov 2026)"
)
fig.tight_layout()
fig.savefig("mesh_rtt_pk_anchors.png", dpi=150)

print("Finished")
