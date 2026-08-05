import cv2
import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from sklearn.cluster import KMeans


def extract_average_lab(image_path):
    

    image = cv2.imread(image_path)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    image = cv2.resize(image, (300, 300))

    pixels = image.reshape((-1, 3))

    avg_rgb = np.mean(pixels, axis=0)

    avg_rgb = avg_rgb / 255.0

    lab = rgb2lab([[avg_rgb]])[0][0]

    return lab

def extract_dominant_colors(image_path, k=3):

    image = cv2.imread(image_path)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    image = cv2.resize(image, (200, 200))

    pixels = image.reshape((-1, 3))

    kmeans = KMeans(n_clusters=k, random_state=42)

    kmeans.fit(pixels)

    colors = kmeans.cluster_centers_

    labels = kmeans.labels_

    counts = np.bincount(labels)

    percentages = counts / len(labels)

    dominant_colors = []

    for color, percent in zip(colors, percentages):

        dominant_colors.append({
            "rgb": color.astype(int).tolist(),
            "percentage": round(percent * 100, 2)
        })

    dominant_colors = sorted(
        dominant_colors,
        key=lambda x: x["percentage"],
        reverse=True
    )

    return dominant_colors


def analyze_images(img1, img2):

    lab1 = extract_average_lab(img1)
    lab2 = extract_average_lab(img2)
    dominant1 = extract_dominant_colors(img1)
    dominant2 = extract_dominant_colors(img2)

    delta_e = float(deltaE_ciede2000(lab1, lab2))

    similarity = max(0, 100 - delta_e * 10)

    status = "PASS" if delta_e < 2 else "FAIL"

    return {
    "lab1": [round(x, 2) for x in lab1],
    "lab2": [round(x, 2) for x in lab2],
    "delta_e": round(delta_e, 2),
    "similarity": round(similarity, 2),
    "status": status,
    "dominant1": dominant1,
    "dominant2": dominant2
}