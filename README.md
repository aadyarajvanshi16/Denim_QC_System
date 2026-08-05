# Denim_QC_System

# 👖 AI-Powered Denim Quality Inspection System

An AI-assisted web application developed using **Flask**, **OpenCV**, and **RTSP Streaming** for real-time denim fabric quality inspection. The system enables automated fabric comparison, recipe extraction, live production monitoring, inspection history management, AI-generated reports, and secure admin access.

---

## 📌 Features

### 🧵 Fabric Comparison
- Upload reference and test denim images.
- Compare fabric colors using CIE LAB color space.
- Calculate Delta E (ΔE) color difference.
- Determine similarity percentage.
- Display PASS/FAIL inspection status.

### 🎨 Recipe Extraction
- Extract dominant denim shades.
- Display LAB values.
- Suggest dye recipe adjustments based on color differences.

### 🎥 Live Quality Inspection
- Real-time inspection using:
  - Laptop Camera
  - Mobile Camera via RTSP (Larix Broadcaster + MediaMTX)
- ROI (Region of Interest) selection.
- Continuous AI-based fabric analysis.
- Live dashboard showing:
  - Color Match
  - Delta E
  - LAB Values
  - AI Confidence
  - PASS / FAIL Status

### 📄 AI Reports
- Automatically generate inspection reports.
- Save reports for future reference.

### 📜 Inspection History
- Maintain previous inspection records.
- View historical inspection details.

### 🔐 Admin Panel
- Secure login authentication.
- User management.
- Page access control.
- Permission-based dashboard.

---

## 🛠️ Technologies Used

- Python
- Flask
- OpenCV
- NumPy
- Bootstrap 5
- HTML5
- CSS3
- JavaScript
- SQLite
- MediaMTX
- Larix Broadcaster

---

## 📂 Project Structure

```
app.py
config.py
templates/
static/
utils/
instance/
uploads/
saved_reports/
history.json
requirements.txt
README.md
```

---

## 🚀 Installation

1. Clone the repository

```bash
git clone <repository-url>
```

2. Navigate into the project

```bash
cd denim_qc_system
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Run the application

```bash
python app.py
```

5. Open your browser

```
http://127.0.0.1:5000
```

---

## 📱 RTSP Live Camera Setup

1. Install **Larix Broadcaster** on your mobile device.
2. Install **MediaMTX** on your computer.
3. Connect both devices to the same Wi-Fi network.
4. Start streaming from Larix.
5. Enter the RTSP URL inside the application.
6. Start Live Inspection
