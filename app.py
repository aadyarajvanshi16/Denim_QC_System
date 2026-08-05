from flask import Flask, render_template, request, send_file, jsonify, Response, redirect
import os
import json
import shutil
from datetime import datetime
import config


from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from pipeline.stream_reader import StreamReader
from utils.color_analysis import analyze_images
from utils.charts import generate_charts
from utils.image_processing import select_roi, crop_roi
from utils.recipe_engine import generate_recipe
from utils.recipe_engine import extract_recipe_from_image
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ============================================
# DATABASE SETUP
# ============================================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SECRET_KEY"] = "denim-factory-secret-key-2026"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ============================================
# USER TABLE (DATABASE MODEL)
# ============================================

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)

    password_hash = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="user")  # "admin" or "user"

    # which use-cases this user can access, stored as comma-separated text
    # example: "fabric_comparison,live_quality"
    permissions = db.Column(db.String(300), default="")


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

# ============================================
# ADMIN-ONLY BOUNCER
# ============================================

from functools import wraps

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not current_user.is_authenticated or current_user.role != "admin":

            return redirect("/")

        return f(*args, **kwargs)

    return decorated_function

# ============================================
# PERMISSION-BASED BOUNCER
# ============================================

def permission_required(feature_name):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if not current_user.is_authenticated:
                return redirect("/login")

            if current_user.role == "admin":
                return f(*args, **kwargs)

            user_permissions = current_user.permissions.split(",")

            if feature_name in user_permissions:
                return f(*args, **kwargs)

            return "You don't have access to this feature. Contact your admin.", 403

        return decorated_function

    return decorator

# ============================================
# GLOBAL STREAM READER
# ============================================

stream_reader = None

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "static/results"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


# ============================================
# HOME PAGE
# ============================================

@app.route("/")
@login_required
def index():

    return render_template(
        "index.html"
    )

# ============================================
# LOGIN PAGE
# ============================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            return redirect("/")

        else:

            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html", error=None)

# ============================================
# LOGOUT
# ============================================

@app.route("/logout")
def logout():

    logout_user()

    return redirect("/login")

# ============================================
# ADMIN PANEL - VIEW ALL USERS
# ============================================

@app.route("/admin")
@login_required
@admin_required
def admin_panel():

    all_users = User.query.all()

    return render_template("admin.html", users=all_users)

# ============================================
# ADMIN PANEL - CREATE NEW USER
# ============================================

@app.route("/admin/create_user", methods=["POST"])
@login_required
@admin_required
def create_user():

    username = request.form["username"]
    password = request.form["password"]

    # get list of checked permission checkboxes
    selected_permissions = request.form.getlist("permissions")

    # turn the list into a comma-separated text, e.g. "fabric_comparison,live_quality"
    permissions_text = ",".join(selected_permissions)

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role="user",
        permissions=permissions_text
    )

    db.session.add(new_user)
    db.session.commit()

    return redirect("/admin")

# ============================================
# LIVE QUALITY INSPECTION
# ============================================

@app.route("/live_quality")
@login_required
@permission_required("live_quality")
def live_quality():
    return render_template("live_quality.html")

# ============================================
# SET RTSP CAMERA (temp)
# ============================================

@app.route("/set_rtsp", methods=["POST"])
def set_rtsp():

    global stream_reader

    config.RTSP_URL = request.form["rtsp"]

    config.CAMERA_SOURCE = "rtsp"

    # Stop previous stream if running
    if stream_reader is not None:

        stream_reader.stop()

    # Start new stream
    stream_reader = StreamReader(
        config.RTSP_URL
    ).start()

    return jsonify({

        "status": "connected"

    })

@app.route("/rtsp_status")
def rtsp_status():

    global stream_reader

    if stream_reader is None:

        return jsonify({

            "status": "No Stream"

        })

    frame = stream_reader.get_frame()

    if frame is None:

        return jsonify({

            "status": "Waiting for Frames"

        })

    return jsonify({

        "status": "Receiving Frames"

    })

# ============================================
# RTSP VIDEO STREAM
# ============================================

def generate_rtsp_frames():

    cap = cv2.VideoCapture(config.RTSP_URL)

    while True:

        success, frame = cap.read()

        if not success:
            break

        _, buffer = cv2.imencode(".jpg", frame)

        frame = buffer.tobytes()

        yield (

            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'

        )

    cap.release()


@app.route("/video_feed")
def video_feed():

    return Response(

        generate_rtsp_frames(),

        mimetype="multipart/x-mixed-replace; boundary=frame"

    )

# ============================================
# LIVE ANALYZE
# ============================================

@app.route("/live_analyze", methods=["POST"])
def live_analyze():

    # -------------------------------
    # SAVE LIVE FRAME
    # -------------------------------

    frame = request.files["frame"]

    frame_path = os.path.join(
        "static",
        "results",
        "live_frame.jpg"
    )

    frame.save(frame_path)
    print("\n========== LIVE FRAME ==========")
    print(os.path.exists(frame_path))
    print(frame_path)   

    # -------------------------------
    # LOAD REFERENCE IMAGE
    # -------------------------------

    reference_path = os.path.join(
        "static",
        "results",
        "live_reference.jpg"
    )

    print("\n========== REFERENCE ==========")
    print(os.path.exists(reference_path))
    print(reference_path)

    # -------------------------------
    # GET SAVED ROI
    # -------------------------------

    roi = app.config.get("LIVE_REFERENCE_ROI")
    print("\n========== ROI ==========")
    print(roi)
    print(type(roi))

    if roi is None:

        return jsonify({
            "status": "Select ROI first"
        })

    # -------------------------------
    # CROP BOTH IMAGES
    # -------------------------------

    reference_roi = crop_roi(
        reference_path,
        roi
    )

    print(reference_roi)
    print(os.path.exists(reference_roi))

    import cv2

    ref = cv2.imread(reference_path)
    live = cv2.imread(frame_path)

    ref_h, ref_w = ref.shape[:2]
    live_h, live_w = live.shape[:2]

    x, y, w, h = roi

    scale_x = live_w / ref_w
    scale_y = live_h / ref_h

    scaled_roi = (
        int(x * scale_x),
        int(y * scale_y),
        int(w * scale_x),
        int(h * scale_y)
)

    live_roi = crop_roi(
        frame_path,
        scaled_roi
)

    print(live_roi)
    print(os.path.exists(live_roi))

    # -------------------------------
    # ANALYZE
    # -------------------------------

    analysis = analyze_images(
        reference_roi,
        live_roi
    )

    print("\n========== ANALYSIS ==========")
    print(analysis)

    confidence = max(
        0,
        round(
            100 - analysis["delta_e"] * 5,
            2
        )
    )

    # -------------------------------
    # RETURN RESULTS
    # -------------------------------

    return jsonify({

        "similarity": analysis["similarity"],

        "delta_e": analysis["delta_e"],

        "l": analysis["lab2"][0],

        "a": analysis["lab2"][1],

        "b": analysis["lab2"][2],

        "confidence": confidence,

        "status": analysis["status"]

    })

# ============================================
# UPLOAD LIVE REFERENCE
# ============================================

@app.route("/upload_live_reference", methods=["POST"])
def upload_live_reference():

    print("===== UPLOAD ROUTE HIT =====")

    print(request.files)

    if "reference" not in request.files:
        return jsonify({"error": "No file received"}), 400

    file = request.files["reference"]

    print("Filename:", file.filename)

    os.makedirs(
        os.path.join("static", "results"),
        exist_ok=True
    )

    save_path = os.path.join(
        "static",
        "results",
        "live_reference.jpg"
    )

    print("Saving to:", os.path.abspath(save_path))

    file.save(save_path)

    print("Exists after save:", os.path.exists(save_path))

    return jsonify({
        "message": "Reference Uploaded"
    })

# ============================================
# SELECT LIVE ROI
# ============================================

@app.route("/select_live_roi", methods=["POST"])
def select_live_roi():

    reference_path = os.path.join(

        "static",

        "results",

        "live_reference.jpg"

    )
    print(reference_path)
    print(os.path.exists(reference_path))

    roi_path, roi = select_roi(reference_path)

    app.config["LIVE_REFERENCE_ROI"] = roi

    return jsonify({

        "message": "ROI Selected"

    })

# ============================================
# FABRIC COMPARISON
# ============================================

@app.route("/compare", methods=["POST"])
def compare():

    ref_image = request.files["reference"]
    test_image = request.files["test"]

    # SAVE ORIGINAL FILES

    ref_path = os.path.join(
        UPLOAD_FOLDER,
        ref_image.filename
    )

    test_path = os.path.join(
        UPLOAD_FOLDER,
        test_image.filename
    )

    ref_image.save(ref_path)
    test_image.save(test_path)

    # ============================================
    # ROI SELECTION
    # ============================================

    ref_roi, ref_coords = select_roi(ref_path)
    test_roi, test_coords = select_roi(test_path)
    app.config["LIVE_REFERENCE_ROI"] = ref_coords

    # COPY ROI TO STATIC FOLDER

    ref_static = "static/results/ref_roi.jpg"
    test_static = "static/results/test_roi.jpg"

    shutil.copy(ref_roi, ref_static)
    shutil.copy(test_roi, test_static)

    # ============================================
    # ANALYSIS
    # ============================================

    analysis = analyze_images(
        ref_roi,
        test_roi
    )

    # ============================================
    # AI CONFIDENCE SCORE
    # ============================================

    confidence = max(
        0,
        round(
            100 - analysis["delta_e"] * 5,
            2
        )
    )

    # ============================================
    # AI RECIPE GENERATION
    # ============================================

    recipe = generate_recipe(

        analysis["lab1"],
        analysis["lab2"]

    )

    # ============================================
    # CHARTS
    # ============================================

    bar_chart, pie_chart = generate_charts(

        analysis["lab1"],
        analysis["lab2"]

    )
    # SAVE CHART NAMES GLOBALLY

    app.config["LAST_BAR_CHART"] = bar_chart
    app.config["LAST_PIE_CHART"] = pie_chart

    # ============================================
    # QC STATUS
    # ============================================

    qc_status = analysis["status"]


    comp_id = (
    "COMP-" +
    datetime.now().strftime("%Y%m%d-%H%M%S")
)

    # ============================================
    # SAVE HISTORY
    # ============================================

    history_item = {

        "comp_id":
            comp_id, 
        
        "time":
            datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),

        "reference":
            ref_image.filename,

        "test":
            test_image.filename,

        "delta_e":
            round(
                analysis["delta_e"],
                2
            ),

        "status":
            qc_status
    }

    # LOAD OLD HISTORY

    with open("history.json", "r") as file:

        history = json.load(file)

    # INSERT NEW HISTORY

    history.insert(
        0,
        history_item
    )

    # SAVE AGAIN

    with open("history.json", "w") as file:

        json.dump(
            history,
            file,
            indent=4
        )

    # ============================================
    # STORE REPORT DATA
    # ============================================

    app.config["LAST_LAB1"] = analysis["lab1"]

    app.config["LAST_LAB2"] = analysis["lab2"]

    app.config["LAST_SIMILARITY"] = analysis["similarity"]

    app.config["LAST_CONFIDENCE"] = confidence

    app.config["LAST_COMP_ID"] = comp_id

    # ============================================
    # RESULT PAGE
    # ============================================

    return render_template(

        "result.html",

        delta_e=analysis["delta_e"],

        similarity=analysis["similarity"],

        status=analysis["status"],

        lab1=analysis["lab1"],

        lab2=analysis["lab2"],

        dominant1=analysis["dominant1"],

        dominant2=analysis["dominant2"],

        ref_roi=ref_static,

        test_roi=test_static,

        bar_chart=bar_chart,

        pie_chart=pie_chart,

        confidence=confidence,

        recipe=recipe

    )


# ============================================
# SINGLE RECIPE EXTRACTION
# ============================================

@app.route("/single_recipe", methods=["POST"])
def single_recipe():

    from datetime import datetime
    import shutil

    image = request.files["image"]

    # ============================================
    # SAVE ORIGINAL IMAGE
    # ============================================

    image_path = os.path.join(
        UPLOAD_FOLDER,
        image.filename
    )

    image.save(image_path)

    # ============================================
    # ROI SELECTION
    # ============================================

    roi_temp_path, roi = select_roi(image_path)

    # ============================================
    # SAVE ROI INSIDE STATIC/RESULTS
    # ============================================

    final_roi_path = os.path.join(
        "static",
        "results",
        "recipe_roi.jpg"
    )

    shutil.copy(
        roi_temp_path,
        final_roi_path
    )

    # ============================================
    # ANALYZE ROI
    # ============================================

    analysis = analyze_images(
        final_roi_path,
        final_roi_path
    )

    # ============================================
    # EXTRACT RECIPE
    # ============================================

    recipe = extract_recipe_from_image(
        analysis["lab1"],
        analysis["dominant1"]
    )

    # ============================================
    # SAVE CURRENT RECIPE DATA
    # ============================================

    app.config["LAST_RECIPE"] = recipe

    app.config["LAST_LAB"] = analysis["lab1"]

    app.config["LAST_DOMINANT"] = analysis["dominant1"]

    app.config["LAST_ROI"] = final_roi_path

    app.config["LAST_RECIPE_TIME"] = datetime.now().strftime(
        "%d-%m-%Y %H:%M"
    )

    # ============================================
    # SEND IMAGE PATH TO HTML
    # ============================================

    roi_for_html = "results/recipe_roi.jpg"

    # ============================================
    # RENDER PAGE
    # ============================================

    return render_template(

        "single_recipe.html",

        recipe=recipe,

        roi=roi_for_html,

        lab=analysis["lab1"],

        dominant=analysis["dominant1"]

    )

# ============================================
# DASHBOARD PAGE
# ============================================

@app.route("/dashboard")
def dashboard():

    return render_template(
        "index.html"
    )


# ============================================
# FABRIC COMPARISON PAGE
# ============================================

@app.route("/fabric_comparison")
@login_required
@permission_required("fabric_comparison")
def fabric_comparison():

    return render_template(
        "fabric_comparison.html"
    )


# ============================================
# RECIPE EXTRACTION PAGE
# ============================================

@app.route("/recipe_extraction")
@login_required
@permission_required("recipe_extraction")
def recipe_extraction():

    return render_template(
        "recipe_extraction.html"
    )


# ============================================
# AI REPORTS PAGE
# ============================================

@app.route("/ai_reports")
@login_required
@permission_required("ai_reports")
def ai_reports():

    reports = os.listdir(

        "saved_reports"

    )

    reports.reverse()

    return render_template(

        "ai_reports.html",

        reports=reports

    )


# ============================================
# DOWNLOAD SAVED REPORT
# ============================================

@app.route("/download_saved_report/<filename>")
def download_saved_report(filename):

    path = os.path.join(

        "saved_reports",

        filename

    )

    return send_file(

        path,

        as_attachment=True

    )


# ============================================
# DELETE REPORT
# ============================================

@app.route("/delete_report/<filename>")
def delete_report(filename):

    path = os.path.join(

        "saved_reports",

        filename

    )

    if os.path.exists(path):

        os.remove(path)

    return redirect("/ai_reports")


# ============================================
# RENAME REPORT
# ============================================

@app.route("/rename_report", methods=["POST"])
def rename_report():

    old_name = request.form["old_name"]

    new_name = request.form["new_name"]

    old_path = os.path.join(

        "saved_reports",

        old_name

    )

    new_path = os.path.join(

        "saved_reports",

        new_name + ".pdf"

    )

    os.rename(

        old_path,

        new_path

    )

    return redirect("/ai_reports")

# ============================================
# HISTORY PAGE
# ============================================

@app.route("/history")
@login_required
@admin_required
def history():

    with open(
        "history.json",
        "r"
    ) as file:

        history_data = json.load(file)

    return render_template(

        "history.html",

        history=history_data

    )


# ============================================
# ADVANCED PDF REPORT EXPORT
# ============================================

@app.route("/download_report")
def download_report():

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Image,
        Table,
        TableStyle,
        PageBreak
    )

    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import letter

    report_name = (

    "Denim_Report_"

    + datetime.now().strftime("%d_%m_%Y_%H_%M_%S")

    + ".pdf"

)

    pdf_path = os.path.join(

        "saved_reports",

        report_name

)

    doc = SimpleDocTemplate(
    pdf_path,
    pagesize=letter
)

    styles = getSampleStyleSheet()

    elements = []

    # ============================================
    # TITLE
    # ============================================

    title = Paragraph(

        "AI Denim Dye Inspection Report",

        styles['Title']

    )

    elements.append(title)

    elements.append(
        Spacer(1,10)
    )

    # ============================================
    # LOAD HISTORY
    # ============================================

    with open("history.json", "r") as file:

        history = json.load(file)

    latest = history[0]

    # ============================================
    # MAIN DETAILS TABLE
    # ============================================

    details = [
        ["Comparison ID", latest['comp_id']],

        ["Inspection Time", latest['time']],

        ["Reference Fabric", latest['reference']],

        ["Test Fabric", latest['test']],

        ["Delta E", str(latest['delta_e'])],

        ["QC Status", latest['status']]

    ]

    # ============================================
    # ADVANCED ANALYSIS TABLE
    # ============================================

    elements.append(

    Paragraph(

        "Detailed LAB Analysis",

        styles['Heading2']

    )

)

    elements.append(
    Spacer(1, 12)
)

    advanced_data = [

    [

        "Parameter",

        "Reference",

        "Test"

    ],

    [

        "L Value",

        str(app.config["LAST_LAB1"][0]),

        str(app.config["LAST_LAB2"][0])

    ],

    [

        "A Value",

        str(app.config["LAST_LAB1"][1]),

        str(app.config["LAST_LAB2"][1])

    ],

    [

        "B Value",

        str(app.config["LAST_LAB1"][2]),

        str(app.config["LAST_LAB2"][2])

    ],

    [

        "Similarity %",

        str(app.config["LAST_SIMILARITY"]),

        "-"

    ],

    [

        "AI Confidence",

        str(app.config["LAST_CONFIDENCE"]),

        "-"

    ]

]

    advanced_table = Table(

    advanced_data,

    colWidths=[180, 150, 150]

)

    advanced_table.setStyle(TableStyle([

    ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

    ('TEXTCOLOR', (0,0), (-1,0), colors.white),

    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

    ('GRID', (0,0), (-1,-1), 1, colors.black),

    ('BOTTOMPADDING', (0,0), (-1,0), 12),

]))

    elements.append(advanced_table)

    elements.append(
    Spacer(1,10)
)

    table = Table(

        details,

        colWidths=[180, 300]

    )

    table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0,0), (-1,0), 12),

        ('TOPPADDING', (0,0), (-1,0), 12),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTSIZE', (0,0), (-1,-1), 11)

    ]))

    elements.append(table)

    elements.append(
        Spacer(1,10)
    )

# ============================================
# ROI + BAR CHART SECTION
# ============================================

    elements.append(
    Paragraph(
        "ROI Images and LAB Analysis",
        styles['Heading2']
    )
)

    elements.append(
    Spacer(1,12)
)

    ref_img = Image(
    "static/results/ref_roi.jpg",
    width=120,
    height=120
)

    test_img = Image(
    "static/results/test_roi.jpg",
    width=120,
    height=120
)

    bar_chart_path = os.path.join(
    "static/results",
    app.config["LAST_BAR_CHART"]
)

    bar_chart = Image(
    bar_chart_path,
    width=220,
    height=120
)

    combined_table = Table([
    [ref_img, test_img, bar_chart]
])

    combined_table.setStyle(TableStyle([

    ('ALIGN',(0,0),(-1,-1),'CENTER'),
    ('VALIGN',(0,0),(-1,-1),'MIDDLE'),

    ('BOX',(0,0),(-1,-1),1,colors.black),

    ('GRID',(0,0),(-1,-1),1,colors.grey),

    ('BOTTOMPADDING',(0,0),(-1,-1),10),

    ('TOPPADDING',(0,0),(-1,-1),10)

]))

    elements.append(combined_table)

    elements.append(
    Spacer(1,15)
)
    
    elements.append(PageBreak())
    
    elements.append(
    Paragraph(
        "AI Industrial Interpretation",
        styles['Heading2']
    )
)

    analysis = """

• Delta E comparison indicates overall color consistency.

• LAB values provide perceptual color measurements.

• ROI based analysis eliminates background interference.

• Computer vision identifies dominant denim shades.

• AI-assisted inspection improves repeatability and quality control.

"""

    elements.append(
    Paragraph(
        analysis,
        styles['BodyText']
    )
)

    elements.append(
    Spacer(1,15)
)
    

    elements.append(
    Paragraph(
        "Quality Assessment",
        styles['Heading2']
    )
)

    quality_text = f"""

Inspection Status : {latest['status']}<br/>

Similarity Score : {app.config['LAST_SIMILARITY']} %<br/>

AI Confidence : {app.config['LAST_CONFIDENCE']} %<br/>

Delta E Value : {latest['delta_e']}<br/>

"""

    elements.append(
    Paragraph(
        quality_text,
        styles['BodyText']
    )
)

    elements.append(
    Spacer(1,15)
)
    
    elements.append(
    Paragraph(
        "Industrial Observations",
        styles['Heading2']
    )
)

    obs = """

• Suitable for denim shade consistency evaluation.<br/>

• Helps detect dye variation between batches.<br/>

• Supports textile quality control workflows.<br/>

• Reduces manual inspection effort.<br/>

• Improves production reliability.<br/>

"""

    elements.append(
    Paragraph(
        obs,
        styles['BodyText']
    )
)

    elements.append(
    Spacer(1,15)
)
    
    elements.append(
    Paragraph(
        "Recommendation",
        styles['Heading2']
    )
)

    if latest["status"] == "APPROVED":

        recommendation = """
    AI recommends accepting this fabric sample
    for production as the color variation is
    within the acceptable tolerance range.
    """

    else:

        recommendation = """
    AI recommends rejecting this sample due to
    excessive color deviation from the reference
    fabric.
    """

    elements.append(
    Paragraph(
        recommendation,
        styles['BodyText']
    )
)

    elements.append(
    Spacer(1,15)
)
    
    elements.append(
    Paragraph(
        "Report Information",
        styles['Heading2']
    )
)

    meta = [

["Generated By",
"IOTrenetics Solutions AI Textile Intelligence System"],

["Report Type",
"Industrial Denim QC Report"],

["Generated On",
datetime.now().strftime("%d-%m-%Y %H:%M:%S")]

]

    meta_table = Table(
    meta,
    colWidths=[130,320]
)

    meta_table.setStyle(TableStyle([

('BACKGROUND',(0,0),(-1,-1),colors.whitesmoke),

('GRID',(0,0),(-1,-1),1,colors.black)

]))

    elements.append(meta_table)
    # ============================================
    # FOOTER FUNCTION
    # ============================================

    def add_footer(canvas, doc):

        canvas.saveState()

        footer_text = datetime.now().strftime(

    "%d-%m-%Y %H:%M"

)

        canvas.setFont(

            'Helvetica',

            9

        )

        canvas.drawString(

            40,

            20,

            footer_text

        )

        canvas.restoreState()



    

    # ============================================
    # FOOTER
    # ============================================

    footer = Paragraph(
        "Generated by IoTrenetics Solutions AI Textile Intelligence System",
        styles['Italic']
    )

    elements.append(footer)

    # ============================================
    # BUILD PDF
    # ============================================

    download_time = datetime.now().strftime(
    "%d-%m-%Y %H:%M:%S"
)

    elements.append(
    Spacer(1,10)
)

    elements.append(

    Paragraph(

        f"""
        <font size=10 color='grey'>
        Report Generated On:
        {download_time}
        </font>
        """,

        styles['Normal']

    )

)


    doc.build(

        elements,

        onFirstPage=add_footer,

        onLaterPages=add_footer

    )

    # ============================================
    # DOWNLOAD PDF
    # ============================================

    return send_file(

        pdf_path,

        as_attachment=True

    )

# ============================================
# DOWNLOAD RECIPE PDF REPORT
# ============================================

@app.route("/download_recipe_report")
def download_recipe_report():

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Image,
        Table,
        TableStyle
    )

    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import letter

    pdf_path = "static/results/recipe_report.pdf"

    doc = SimpleDocTemplate(

        pdf_path,

        pagesize=letter,

        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30

    )

    styles = getSampleStyleSheet()

    elements = []

    # ============================================
    # TITLE
    # ============================================

    title = Paragraph(

        "AI Dye Recipe Extraction Report",

        styles['Title']

    )

    elements.append(title)

    elements.append(
    Spacer(1,8)
)

    # ============================================
    # DETAILS TABLE
    # ============================================

    details = [

        ["Generated On",
         app.config["LAST_RECIPE_TIME"]],

        ["Inspection Type",
         "Single Fabric Recipe Extraction"],

        ["AI Engine",
         "LAB + Dominant Shade Analysis"]

    ]

    table = Table(details,
              colWidths=[150,220])
    

    table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0,0), (-1,-1), 10),

        ('TOPPADDING', (0,0), (-1,-1), 10)

    ]))

    elements.append(table)

    elements.append(
        Spacer(1,10)
    )

    # ============================================
    # ROI IMAGE
    # ============================================

    elements.append(

        Paragraph(
            "Selected ROI Fabric Region",
            styles['Heading2']
        )

    )

    elements.append(
        Spacer(1, 10)
    )

    roi_img = Image(

        app.config["LAST_ROI"],

        width=300,

        height=300

    )

    elements.append(roi_img)

    elements.append(
        Spacer(1,10)
    )

    # ============================================
    # LAB VALUES
    # ============================================

    elements.append(

        Paragraph(
            "LAB Color Analysis",
            styles['Heading2']
        )

    )

    elements.append(
        Spacer(1, 10)
    )

    lab = app.config["LAST_LAB"]

    lab_data = [

        ["Channel", "Value"],

        ["L", str(lab[0])],

        ["A", str(lab[1])],

        ["B", str(lab[2])]

    ]

    lab_table = Table(

        lab_data,

        colWidths=[200, 200]

    )

    lab_table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('BOTTOMPADDING', (0,0), (-1,-1), 10),

        ('TOPPADDING', (0,0), (-1,-1), 10)

    ]))

    elements.append(lab_table)

    elements.append(
        Spacer(1,10)
    )

    # ============================================
    # AI RECIPE TABLE
    # ============================================

    elements.append(

        Paragraph(
            "AI Dye Recipe Recommendation",
            styles['Heading2']
        )

    )

    elements.append(
        Spacer(1, 10)
    )

    recipe_data = [

        ["Action", "Dye", "Amount (%)"]

    ]

    for item in app.config["LAST_RECIPE"]:

        recipe_data.append([

            item["action"],

            item["dye"],

            str(item["amount"])

        ])

    recipe_table = Table(

        recipe_data,

        colWidths=[150, 200, 120]

    )

    recipe_table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('BOTTOMPADDING', (0,0), (-1,-1), 10),

        ('TOPPADDING', (0,0), (-1,-1), 10)

    ]))

    elements.append(recipe_table)

    elements.append(
        Spacer(1,10)
    )

    # ============================================
    # FOOTER
    # ============================================

    footer = Paragraph(

        f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}",

        styles['Normal']

    )

    elements.append(footer)

    # BUILD PDF

    doc.build(elements)

    return send_file(

        pdf_path,

        as_attachment=True

    )

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":

    app.run(debug=True)

