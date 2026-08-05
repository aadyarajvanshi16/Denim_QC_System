import cv2
import os
import uuid


ROI_FOLDER = "uploads/roi"

os.makedirs(ROI_FOLDER, exist_ok=True)


def select_roi(image_path):

    image = cv2.imread(image_path)

    clone = image.copy()

    roi = cv2.selectROI(
        "Select Fabric Area",
        image,
        fromCenter=False,
        showCrosshair=True
    )

    x, y, w, h = roi

    cropped = clone[y:y+h, x:x+w]

    roi_filename = f"roi_{uuid.uuid4().hex}.png"

    roi_path = os.path.join(ROI_FOLDER, roi_filename)

    cv2.imwrite(roi_path, cropped)

    cv2.destroyAllWindows()

    return roi_path, roi

def crop_roi(image_path, roi):

    image = cv2.imread(image_path)

    print("Image shape:", image.shape)

    x, y, w, h = roi

    print("ROI:", x, y, w, h)

    cropped = image[y:y+h, x:x+w]

    print("Cropped shape:", cropped.shape)

    roi_path = os.path.join(
        ROI_FOLDER,
        f"roi_{uuid.uuid4().hex}.png"
    )

    cv2.imwrite(
        roi_path,
        cropped
    )

    return roi_path