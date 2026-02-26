from pathlib import Path
import psutil


def spec():
    return {
        "name": "system_health",
        "description": "Report disk usage and top CPU processes.",
        "args": {"top_n": "number"},
    }


def run(*, assistant=None, wolfram_fn=None, top_n=5):
    try:
        top_n = int(top_n)
    except (TypeError, ValueError):
        top_n = 5
    top_n = max(1, min(20, top_n))

    disk = psutil.disk_usage(str(Path.cwd().anchor))
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            procs.append(p)
        except (psutil.Error, OSError):
            continue
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except (psutil.Error, OSError):
            continue
    psutil.cpu_percent(interval=0.1)
    scored = []
    for p in procs:
        try:
            scored.append((p.cpu_percent(interval=None), p.info))
        except (psutil.Error, OSError):
            continue
    scored.sort(key=lambda x: x[0], reverse=True)

    return {
        "disk": {"total_gb": round(disk.total / 1e9, 2), "free_gb": round(disk.free / 1e9, 2)},
        "top_cpu": [{"cpu": c, **info} for c, info in scored[:top_n]],
    }
