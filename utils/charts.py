import matplotlib.pyplot as plt
import uuid


def generate_charts(lab1, lab2):

    labels = ["L", "A", "B"]

    # -------- BAR CHART --------
    plt.figure(figsize=(6, 4))

    x = range(len(labels))

    plt.bar(x, lab1, width=0.4, label="Reference")
    plt.bar([i + 0.4 for i in x], lab2, width=0.4, label="Test")

    plt.xticks([i + 0.2 for i in x], labels)

    plt.ylabel("LAB Values")
    plt.title("LAB Color Comparison")
    plt.legend()

    bar_filename = f"bar_{uuid.uuid4().hex}.png"
    bar_path = f"static/results/{bar_filename}"

    plt.savefig(bar_path)
    plt.close()

    # -------- PIE CHART --------
    diff = [abs(a - b) for a, b in zip(lab1, lab2)]

    plt.figure(figsize=(5, 5))

    plt.pie(
        diff,
        labels=labels,
        autopct='%1.1f%%'
    )

    plt.title("LAB Difference Distribution")

    pie_filename = f"pie_{uuid.uuid4().hex}.png"
    pie_path = f"static/results/{pie_filename}"

    plt.savefig(pie_path)
    plt.close()

    return bar_filename, pie_filename