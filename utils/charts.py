"""
LAB comparison charts. Uses the 'Agg' (non-interactive) matplotlib
backend explicitly — the default backend can try to open a GUI window
and crash/hang under a WSGI server the same way cv2.selectROI did.
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import matplotlib

matplotlib.use("Agg")  # must happen before pyplot is imported
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

LABELS = ["L", "A", "B"]


def generate_charts(lab1, lab2, result_folder: str) -> tuple[str, str]:
    os.makedirs(result_folder, exist_ok=True)

    # -------- BAR CHART --------
    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(LABELS))
    ax.bar(x, lab1, width=0.4, label="Reference")
    ax.bar([i + 0.4 for i in x], lab2, width=0.4, label="Test")
    ax.set_xticks([i + 0.2 for i in x])
    ax.set_xticklabels(LABELS)
    ax.set_ylabel("LAB Values")
    ax.set_title("LAB Color Comparison")
    ax.legend()

    bar_filename = f"bar_{uuid.uuid4().hex}.png"
    fig.savefig(os.path.join(result_folder, bar_filename))
    plt.close(fig)

    # -------- PIE CHART --------
    diff = [abs(a - b) for a, b in zip(lab1, lab2)]
    if sum(diff) == 0:
        diff = [1, 1, 1]  # avoid an all-zero pie chart raising in matplotlib

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(diff, labels=LABELS, autopct="%1.1f%%")
    ax.set_title("LAB Difference Distribution")

    pie_filename = f"pie_{uuid.uuid4().hex}.png"
    fig.savefig(os.path.join(result_folder, pie_filename))
    plt.close(fig)

    return bar_filename, pie_filename


def cleanup_old_charts(result_folder: str, max_age_seconds: int = 24 * 3600) -> None:
    """
    Every chart is written with a unique filename and never overwritten,
    so the results folder grows forever. Call this periodically (e.g.
    from a scheduled task or at the top of the dashboard route) to
    delete charts older than max_age_seconds.
    """
    if not os.path.isdir(result_folder):
        return
    now = time.time()
    for name in os.listdir(result_folder):
        if not (name.startswith("bar_") or name.startswith("pie_")):
            continue
        path = os.path.join(result_folder, name)
        try:
            if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
                os.remove(path)
        except OSError as exc:
            logger.warning("Could not clean up chart %s: %s", path, exc)
