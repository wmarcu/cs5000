"""Hourly median min-RTT from SG and FR anchors to the three Pakistani anchors (anchoring mesh, free data)."""

import collections
import datetime as dt
import json
import statistics
from datetime import timezone
from pathlib import Path

import matplotlib
import requests

matplotlib.use("Agg")
import matplotlib.dates as md
import matplotlib.pyplot as plt

# Define the incident time range
U: timezone = dt.UTC
ts = lambda *a: int(dt.datetime(*a, tzinfo=U).timestamp())  # Convert to Unix timestamp
START, STOP = ts(2026, 11, 14), ts(2026, 11, 23)
EVENT = ts(2026, 11, 18, 13)

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

# Cache configuration
CACHE_DIR = Path("ripe_atlas_cache")
CACHE_DIR.mkdir(exist_ok=True)


def GetResults(msm, prbs, refresh=False):
    """Get RIPE Atlas results, using local cache when available."""

    cache_file = CACHE_DIR / f"{msm}_{'-'.join(map(str, prbs))}_{START}_{STOP}.json"

    # Use cached results if available
    if cache_file.exists() and not refresh:
        print(f"Loading cache: {cache_file}")
        with cache_file.open("r") as f:
            return json.load(f)

    # Otherwise fetch from RIPE Atlas
    print(f"Downloading measurement {msm}, probes {prbs}...")

    response = requests.get(
        f"https://atlas.ripe.net/api/v2/measurements/{msm}/results/",
        params={
            "start": START,
            "stop": STOP,
            "probe_ids": ",".join(map(str, prbs)),
        },
        timeout=300,
    )
    response.raise_for_status()
    results = response.json()

    # Save results to cache
    with cache_file.open("w") as f:
        json.dump(results, f)

    print(f"Cached: {cache_file}")
    return results


def AnalyseLatencies(results, normalise=True):
    """
    Calculate baseline-normalized hourly RTT for each
    source-destination pair.

    Returns:
        probe_id -> {
            baseline: float,
            hourly: {timestamp: normalized_rtt}
        }
    """

    # Group raw measurements by probe and hour
    hourly = collections.defaultdict(lambda: collections.defaultdict(list))

    for x in results:
        if x.get("min", -1) <= 0:
            continue

        probe = x["prb_id"]
        hour = x["timestamp"] // 3600 * 3600

        hourly[probe][hour].append(x["min"])

    # Calculate hourly median and pre-event baseline
    output = {}

    for probe, measurements in hourly.items():
        hourly_medians = {
            t: statistics.median(values) for t, values in measurements.items()
        }

        baseline = None
        if normalise:
            baseline_values = [
                value for t, value in hourly_medians.items() if START <= t < EVENT
            ]

            if not baseline_values:
                print(f"Warning: no baseline for probe {probe}")
                continue

            baseline = statistics.median(baseline_values)

            # Normalise each hourly measurement against its baseline
            hourly_medians = {
                t: value - baseline for t, value in hourly_medians.items()
            }

        output[probe] = {
            "baseline": baseline,
            "hourly": hourly_medians,
        }

    return output


def AggregateLatencies(results, normalise=True):
    """
    Aggregate baseline-normalized RTT across source probes.

    Returns:
        timestamp -> {
            median: median normalized RTT
            count: number of probes in hourly interval
        }
    """

    per_probe = AnalyseLatencies(results, normalise)

    # Group normalized RTT by hour
    hourly = collections.defaultdict(list)

    for probe_data in per_probe.values():
        for timestamp, value in probe_data["hourly"].items():
            hourly[timestamp].append(value)

    return {
        t: {
            "median": statistics.median(values),
            "count": len(values),
        }
        for t, values in hourly.items()
    }

def CheckLatencies(refresh=False, normalise=True):

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)

    for ax, (vlab, prbs) in zip(axes, VPS.items()):
        for lab, msm in MSM.items():
            results = GetResults(msm, prbs, refresh=refresh)
            aggregated = AggregateLatencies(results, normalise)

            xs = sorted(aggregated)

            ax.plot(
                [dt.datetime.fromtimestamp(t, U) for t in xs],
                [aggregated[t]["median"] for t in xs],
                label=lab,
                lw=1.3,
            )

        ax.axvline(
            dt.datetime.fromtimestamp(EVENT, U),
            color="red",
            ls="--",
            lw=1,
        )

        if normalise:
            ax.axhline(0, color="black", ls=":", lw=0.8)
            ax.set_ylabel("RTT change from baseline (ms)")
        else:
            ax.set_ylabel("median min RTT (ms)")

        ax.set_title(f"From {vlab}")
        ax.grid(alpha=0.3)

    axes[0].legend(fontsize=8, loc="upper left")
    axes[1].xaxis.set_major_formatter(md.DateFormatter("%d %b"))

    if normalise:
        title = (
            "Baseline-normalized RIPE Atlas RTT to Pakistani anchors; "
            "red line = SMW5 fault onset (~13:00 UTC 18 Nov 2026)"
        )
    else:
        title = (
            "RIPE Atlas anchoring-mesh pings to Pakistani anchors; "
            "red line = SMW5 fault onset (~13:00 UTC 18 Nov 2026)"
        )

    fig.suptitle(title)

    fig.tight_layout()
    fig.savefig("mesh_rtt_pk_anchors.png", dpi=150)
    plt.close(fig)


def main():
    CheckLatencies()
    print("Finished")


if __name__ == "__main__":
    main()
