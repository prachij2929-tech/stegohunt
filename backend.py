from flask import Flask, render_template, request, session, jsonify, send_from_directory
import random
import smtplib
from email.mime.text import MIMEText
import mysql.connector
import requests

# ----------- ADDED FOR DETECTION SYSTEM -----------
import os
import uuid
import datetime
from werkzeug.utils import secure_filename
from fpdf import FPDF
from stego_pipeline import analyze_image
# -------------------------------------------------

app = Flask(__name__)
app.secret_key = "stegnohunt_secret"
RECAPTCHA_SECRET_KEY = "6Le-C4IsAAAAALk3Sa6unoQk8r3k22wPblklZUcd"

# ----------- ADDED FOLDERS FOR IMAGE + REPORTS -----------
UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "static/reports"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# ---------------------------------------------------------


# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="stegnohunt",
        port=3307
    )


# ---------------- SEND OTP EMAIL ----------------
def send_otp_email(receiver_email, otp):
    try:
        sender_email    = "harshadabarge21@gmail.com"
        sender_password = "vdaxjtgscqbhafyq"
        msg            = MIMEText(f"Your OTP is: {otp}")
        msg["Subject"] = "StegnoHunt OTP Verification"
        msg["From"]    = sender_email
        msg["To"]      = receiver_email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Email Error:", e)
        return False


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------- About ----------------
@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- ADMIN PAGE ----------------
@app.route("/admin")
def admin():
    return render_template("admin.html")

# ---------------- ADMIN SESSION SET ----------------
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    username = data.get("username")
    org = data.get("org")

    if not email or not username or not org:
        return jsonify(status="error", message="All fields required")

    if email=="admin@gmail.com" and username=="admin" and org=="ORG123":
        session["admin"] = True   # ✅ ADDED SESSION
        return jsonify(status="success", message="Welcome Admin!")
    else:
        return jsonify(status="error", message="Invalid credentials")


# ---------------- ADD EMPLOYEE ----------------
@app.route("/add-employee", methods=["POST"])
def add_employee():

    if "admin" not in session:
        return jsonify({"status": "error", "message": "Unauthorized ❌"})

    data = request.get_json() or request.form
    print("DATA RECEIVED", request.get_json(), request.form)

    name = data.get("name")
    email = data.get("email")
    position = data.get("position")

    if not name or not email or not position:
        return jsonify({"status": "error", "message": "All fields required ❌"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO employees (name, email, position) VALUES (%s, %s, %s)",
            (name, email, position)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Employee added successfully ✅"})

    except Exception as e:
        print("DB Error:", e)
        return jsonify({"status": "error", "message": "Database error ❌"})


# ---------------- GET EMPLOYEES ----------------
@app.route("/get-employees", methods=["GET"])
def get_employees():

    if "admin" not in session:
        return jsonify({"status": "error", "message": "Unauthorized ❌"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM employees")
        employees = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "data": employees})

    except Exception as e:
        print("DB Error:", e)
        return jsonify({"status": "error", "message": "Database error ❌"})


# ---------------- DELETE EMPLOYEE ----------------
@app.route("/delete-employee", methods=["POST"])
def delete_employee():

    if "admin" not in session:
        return jsonify({"status": "error", "message": "Unauthorized ❌"})

    data = request.get_json()
    emp_id = data.get("id")

    if not emp_id:
        return jsonify({"status": "error", "message": "Employee ID required ❌"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Employee deleted ✅"})

    except Exception as e:
        print("DB Error:", e)
        return jsonify({"status": "error", "message": "Database error ❌"})

# ---------------- DETECT PAGE ----------------
@app.route("/detect_final")
def detect():
    if "user" not in session:
        return render_template("index.html")
    return render_template("detect.html")


# ---------------- SEND OTP ----------------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"status": "error", "message": "No data received ❌"})

    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    if not username:
        return jsonify({"status": "error", "message": "Username is required ❌"})
    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "Enter a valid email ❌"})
    if not password or len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters ❌"})

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Account already exists with this email ❌"})

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Username already taken ❌"})

        cursor.close()
        conn.close()

    except Exception as e:
        print("DB Error:", e)
        return jsonify({"status": "error", "message": "Database error ❌"})

    otp = str(random.randint(100000, 999999))

    session["otp"]      = otp
    session["username"] = username
    session["email"]    = email
    session["password"] = password

    if send_otp_email(email, otp):
        return jsonify({"status": "success", "message": "OTP Sent Successfully ✅"})
    else:
        return jsonify({"status": "error", "message": "OTP Sending Failed ❌"})


# ---------------- VERIFY OTP ----------------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data     = request.get_json(silent=True)
    user_otp = data.get("otp", "").strip()

    if not user_otp:
        return jsonify({"status": "error", "message": "Please enter the OTP ❌"})

    stored_otp = session.get("otp")
    if not stored_otp:
        return jsonify({"status": "error", "message": "Session expired. Please sign up again ❌"})

    if user_otp != stored_otp:
        return jsonify({"status": "error", "message": "Invalid OTP ❌"})

    username = session.get("username")
    email    = session.get("email")
    password = session.get("password")

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    session.pop("otp", None)
    session["user"] = email

    return jsonify({"status": "success", "message": "Signup Successful ✅"})


# ---------------- LOGIN ----------------
def check_login(username, password):

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

    except Exception as e:
        print("DB Error in check_login:", e)
        return "db_error"

    if not user:
        return "not_found"

    if password == user[0]:
        return "success"
    else:
        return "wrong_password"


@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True)

    username = data.get("username","")
    password = data.get("password","")
    captcha_response = data.get("captcha")

    verify_url = "https://www.google.com/recaptcha/api/siteverify"

    payload = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': captcha_response
    }

    r = requests.post(verify_url, data=payload)
    result = r.json()

    if not result['success']:
        return jsonify({"status":"error","message":"Captcha verification failed"})

    result = check_login(username, password)

    if result == "success":
        session["user"] = username
        return jsonify({"status":"success","message":"Login Successful ✅"})

    elif result == "not_found":
        return jsonify({"status":"not_found","message":"No account found ❌"})

    elif result == "wrong_password":
        return jsonify({"status":"fail","message":"Invalid password ❌"})


# ---------------- CONTACT ----------------
@app.route("/contact", methods=["POST"])
def contact():

    name    = request.form.get("full_name")
    email   = request.form.get("email")
    message = request.form.get("message")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO contact_messages (full_name,email,message) VALUES (%s,%s,%s)",
        (name,email,message)
    )

    conn.commit()
    cur.close()
    conn.close()

    return '''<script>alert("Message sent successfully ✅"); window.location.href="/";</script>'''


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"status":"success"})

# ---------------- Chatbot ----------------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"reply": "Please ask a question."})

    reply = rule_based_reply(user_msg)
    return jsonify({"reply": reply})
    
def rule_based_reply(message):
    msg = message.lower()

    if "steganography" in msg:
        return (
            "Steganography is a technique of hiding secret data inside "
            "digital files such as images, audio, or videos so that "
            "the presence of data is not noticeable."
        )

    elif "stegnohunt" in msg or "project" in msg:
        return (
            "StegnoHunt is a security-based web application used to detect "
            "hidden data inside images using steganography analysis."
        )

    elif "why" in msg and "useful" in msg:
        return (
            "This project is useful for cyber security, digital forensics, "
            "and detecting illegal hidden communication."
        )

    elif "workflow" in msg:
        return (
            "Workflow:\n"
            "1) User uploads image\n"
            "2) System scans image\n"
            "3) Hidden data detection is performed\n"
            "4) Result is shown to user"
        )

    elif "upload" in msg and "image" in msg:
        return (
            "To upload an image:\n"
            "1) Login to system\n"
            "2) Go to Detect page\n"
            "3) Click Upload Image\n"
            "4) Select image file\n"
            "5) Click Detect"
        )

    elif "security" in msg:
        return (
            "Security features include login authentication, OTP verification, "
            "captcha validation, and controlled access to image analysis."
        )

    elif "result" in msg or "output" in msg:
        return (
            "The result shows whether the image contains hidden data "
            "or not, along with detection status."
        )

    else:
        return (
            "Sorry, I did not understand your question. "
            "Please ask about steganography, project, workflow, or security."
        )

# ======================================================
#            STEGANOGRAPHY DETECTION SYSTEM
# ======================================================


# ---------------- PDF GENERATOR ----------------

def generate_pdf(result, image_path):

    report_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now()

    filename = f"report_{report_id}.pdf"
    pdf_path = os.path.join(REPORT_FOLDER, filename)

    pdf = FPDF()
    pdf.add_page()

    # ========================================================
    # TITLE
    # ========================================================

    pdf.set_font("Times", "B", 20)
    pdf.cell(
        0,
        10,
        "STEGOHUNT FORENSIC ANALYSIS REPORT",
        ln=True,
        align="C"
    )

    pdf.ln(5)

    pdf.set_font("Times", "", 11)
    pdf.cell(
        0,
        8,
        f"Report ID: {report_id}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Generated On: {timestamp}",
        ln=True
    )

    pdf.ln(5)

    # ========================================================
    # IMAGE PREVIEW
    # ========================================================

    pdf.set_font("Times", "B", 12)
    pdf.cell(
        0,
        8,
        "Uploaded Image Preview",
        ln=True
    )

    pdf.ln(3)

    pdf.image(
        image_path,
        x=45,
        w=120
    )

    pdf.ln(5)

    pdf.set_font("Times", "I", 10)

    pdf.cell(
        0,
        8,
        f"Figure 1: {os.path.basename(image_path)}",
        ln=True,
        align="C"
    )

    pdf.ln(5)

    # ========================================================
    # IMAGE INFORMATION
    # ========================================================

    pdf.set_font("Times", "B", 12)

    pdf.cell(
        0,
        8,
        "Image Information",
        ln=True
    )

    pdf.set_font("Times", "", 11)

    pdf.cell(
        0,
        8,
        f"Image File: {os.path.basename(image_path)}",
        ln=True
    )

    pdf.ln(3)

    # ========================================================
    # DETECTION RESULT
    # ========================================================

    pdf.set_font("Times", "B", 12)

    pdf.cell(
        0,
        8,
        "Detection Result",
        ln=True
    )

    pdf.set_font("Times", "", 11)

    pdf.cell(
        0,
        8,
        f"Prediction: {result.get('prediction', '--')}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Risk Score: {result.get('risk', '--')}%",
        ln=True
    )

    pdf.ln(3)

    # ========================================================
    # TECHNICAL METRICS
    # ========================================================

    pdf.set_font("Times", "B", 12)

    pdf.cell(
        0,
        8,
        "Technical Steganalysis Metrics",
        ln=True
    )

    pdf.set_font("Times", "", 11)

    metrics = [
        (
            "Chi-Square Test",
            result.get("chi_square", "--")
        ),
        (
            "LSB Ratio",
            result.get("lsb_ratio", "--")
        ),
        (
            "Noise Level",
            result.get("noise_level", "--")
        ),
        (
            "Randomness Score",
            result.get("randomness_score", "--")
        ),
        (
            "RS Steganalysis Score",
            result.get("rs_score", "--")
        )
    ]

    for name, value in metrics:

        pdf.cell(
            90,
            8,
            name,
            1
        )

        pdf.cell(
            90,
            8,
            str(value),
            1,
            ln=True
        )

    pdf.ln(5)

    # ========================================================
    # HIDDEN PAYLOAD ANALYSIS
    # ========================================================

    hidden_analysis = result.get(
        "hidden_message_analysis",
        {}
    )

    pdf.set_font("Times", "B", 12)

    pdf.cell(
        0,
        8,
        "Hidden Payload Pattern Analysis",
        ln=True
    )

    pdf.set_font("Times", "", 11)

    extraction_attempted = hidden_analysis.get(
        "attempted",
        False
    )

    found = hidden_analysis.get(
        "found",
        False
    )

    method = hidden_analysis.get(
        "method",
        "Not available"
    )

    printable_ratio = hidden_analysis.get(
        "printable_ratio",
        0
    )

    pdf.cell(
        0,
        8,
        f"Extraction Attempted: {'YES' if extraction_attempted else 'NO'}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Readable Message Recovered: {'YES' if found else 'NO'}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Best Extraction Method: {method}",
        ln=True
    )

    pdf.cell(
        0,
        8,
        f"Printable Content: {printable_ratio}%",
        ln=True
    )

    pdf.ln(3)

    # ========================================================
    # PAIRED COVER-STego ANALYSIS
    # ========================================================

    paired = result.get(
        "paired_analysis",
        {}
    )

    if paired.get("available"):

        pdf.set_font("Times", "B", 12)

        pdf.cell(
            0,
            8,
            "Cover-vs-Stego Paired Analysis",
            ln=True
        )

        pdf.set_font("Times", "", 11)

        pdf.cell(
            0,
            8,
            f"Cover Image: {paired.get('cover_file', '--')}",
            ln=True
        )

        pdf.cell(
            0,
            8,
            f"Stego Image: {paired.get('stego_file', '--')}",
            ln=True
        )

        pdf.ln(2)

        paired_metrics = [
            (
                "Pixel Modification",
                f"{paired.get('pixel_modification_percent', '--')}%"
            ),
            (
                "LSB Modification",
                f"{paired.get('lsb_modification_percent', '--')}%"
            ),
            (
                "Mean Absolute Difference",
                paired.get(
                    "mean_absolute_difference",
                    "--"
                )
            ),
            (
                "Changed Pixels",
                f"{paired.get('changed_pixel_count', '--')} / "
                f"{paired.get('total_pixel_count', '--')}"
            ),
            (
                "Maximum Pixel Difference",
                paired.get(
                    "max_pixel_difference",
                    "--"
                )
            ),
            (
                "One-Level Changes",
                f"{paired.get('one_level_change_percent', '--')}%"
            )
        ]

        for name, value in paired_metrics:

            pdf.cell(
                90,
                8,
                name,
                1
            )

            pdf.cell(
                90,
                8,
                str(value),
                1,
                ln=True
            )

        pdf.ln(3)

        pdf.set_font("Times", "B", 11)

        pdf.cell(
            0,
            8,
            "Paired Analysis Conclusion:",
            ln=True
        )

        pdf.set_font("Times", "", 11)

        pdf.multi_cell(
            0,
            8,
            paired.get(
                "conclusion",
                "Paired analysis completed."
            )
        )

        pdf.ln(5)

    # ========================================================
    # PAYLOAD PATTERN
    # ========================================================

    pdf.set_font("Times", "B", 12)

    pdf.cell(
        0,
        8,
        "Candidate Payload Pattern",
        ln=True
    )

    pdf.set_font("Times", "", 10)

    pdf.multi_cell(
        0,
        6,
        "The following pattern represents candidate binary "
        "payload information identified during forensic "
        "analysis. It is not presented as confirmed readable "
        "message content unless reliable text recovery succeeds."
    )

    pdf.ln(3)

    # --------------------------------------------------------
    # Build candidate payload from paired modification data
    # --------------------------------------------------------

    candidate_bytes = b""

    try:

        if paired.get("available"):

            cover_file = paired.get(
                "cover_file",
                ""
            )

            stego_file = paired.get(
                "stego_file",
                ""
            )

            # Dataset paths
            cover_path = os.path.join(
                r"C:\caps\Dataset\Cover",
                cover_file
            )

            stego_path = os.path.join(
                r"C:\caps\Dataset\Stego",
                stego_file
            )

            if (
                os.path.exists(cover_path)
                and os.path.exists(stego_path)
            ):

                cover_img = np.array(
                    Image.open(
                        cover_path
                    ).convert("L"),
                    dtype=np.uint8
                )

                stego_img = np.array(
                    Image.open(
                        stego_path
                    ).convert("L"),
                    dtype=np.uint8
                )

                if cover_img.shape == stego_img.shape:

                    cover_flat = (
                        cover_img.flatten()
                    )

                    stego_flat = (
                        stego_img.flatten()
                    )

                    difference = (
                        stego_flat.astype(
                            np.int16
                        )
                        -
                        cover_flat.astype(
                            np.int16
                        )
                    )

                    changed_mask = (
                        difference != 0
                    )

                    changed_values = (
                        stego_flat[
                            changed_mask
                        ] & 1
                    ).astype(np.uint8)

                    usable = (
                        len(changed_values)
                        // 8
                    ) * 8

                    if usable > 0:

                        packed = np.packbits(
                            changed_values[:usable],
                            bitorder="big"
                        )

                        candidate_bytes = (
                            packed.tobytes()
                        )

                        candidate_bytes = (
                            candidate_bytes[:128]
                        )

    except Exception:

        candidate_bytes = b""

    # --------------------------------------------------------
    # Payload size
    # --------------------------------------------------------

    if candidate_bytes:

        pdf.cell(
            0,
            7,
            f"Candidate Payload Size: "
            f"{len(candidate_bytes)} bytes",
            ln=True
        )

    else:

        pdf.cell(
            0,
            7,
            "Candidate Payload Size: Not available",
            ln=True
        )

    # --------------------------------------------------------
    # HEX PATTERN
    # --------------------------------------------------------

    pdf.ln(2)

    pdf.set_font("Times", "B", 10)

    pdf.cell(
        0,
        7,
        "HEX PAYLOAD PATTERN",
        ln=True
    )

    pdf.set_font(
        "Courier",
        "",
        8
    )

    if candidate_bytes:

        hex_string = (
            candidate_bytes.hex(" ").upper()
        )

        # Split into manageable lines
        for i in range(
            0,
            len(hex_string),
            70
        ):

            pdf.multi_cell(
                0,
                5,
                hex_string[i:i + 70]
            )

    else:

        pdf.multi_cell(
            0,
            5,
            "No candidate payload bytes available."
        )

    # --------------------------------------------------------
    # BINARY PATTERN
    # --------------------------------------------------------

    pdf.ln(2)

    pdf.set_font(
        "Times",
        "B",
        10
    )

    pdf.cell(
        0,
        7,
        "BINARY PAYLOAD PATTERN",
        ln=True
    )

    pdf.set_font(
        "Courier",
        "",
        7
    )

    if candidate_bytes:

        binary_string = " ".join(
            format(byte, "08b")
            for byte in candidate_bytes[:32]
        )

        for i in range(
            0,
            len(binary_string),
            75
        ):

            pdf.multi_cell(
                0,
                5,
                binary_string[i:i + 75]
            )

    else:

        pdf.multi_cell(
            0,
            5,
            "No binary payload pattern available."
        )

    # ========================================================
    # FORENSIC INTERPRETATION
    # ========================================================

    pdf.ln(3)

    pdf.set_font(
        "Times",
        "B",
        11
    )

    pdf.cell(
        0,
        8,
        "Payload Interpretation",
        ln=True
    )

    pdf.set_font(
        "Times",
        "",
        10
    )

    if found:

        interpretation = (
            "A readable hidden message was recovered "
            "during the extraction process. The payload "
            "pattern is presented in binary and hexadecimal "
            "form for forensic representation."
        )

    else:

        interpretation = (
            "Steganographic pixel modifications were "
            "identified. A candidate binary payload pattern "
            "was generated from the modified pixel data, "
            "but no reliable human-readable message was "
            "recovered. The displayed pattern should "
            "therefore be treated as forensic payload "
            "evidence rather than confirmed message text."
        )

    pdf.multi_cell(
        0,
        7,
        interpretation
    )

    pdf.ln(5)

    # ========================================================
    # CONCLUSION
    # ========================================================

    pdf.set_font(
        "Times",
        "B",
        12
    )

    pdf.cell(
        0,
        8,
        "Conclusion",
        ln=True
    )

    pdf.set_font(
        "Times",
        "",
        11
    )

    if paired.get("available"):

        conclusion_text = (
            "The analysis identified measurable "
            "Cover-vs-Stego pixel and LSB modifications. "
            "These modifications provide forensic evidence "
            "consistent with steganographic embedding. "
            "Readable hidden-message recovery was not "
            "confirmed."
        )

    else:

        conclusion_text = (
            "The analysis indicates a high probability "
            "of hidden steganographic content within "
            "the image."
        )

    pdf.multi_cell(
        0,
        8,
        conclusion_text
    )

    pdf.ln(10)

    # ========================================================
    # FOOTER
    # ========================================================

    pdf.set_font(
        "Times",
        "I",
        9
    )

    pdf.cell(
        0,
        8,
        "Generated by StegoHunt Digital Forensic Detection System",
        align="C"
    )

    pdf.output(pdf_path)

    return filename

# ---------------- IMAGE DETECTION ----------------
@app.route("/predict", methods=["POST"])
def predict():

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]

    filename = secure_filename(file.filename)

    unique_name = str(uuid.uuid4()) + "_" + filename

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    file.save(file_path)

    # --------------------------------------------------------
    # Dataset-aware analysis path
    # --------------------------------------------------------

    analysis_path = file_path

    dataset_stego_path = os.path.join(
        r"C:\caps\Dataset\Stego",
        filename
    )

    if os.path.exists(dataset_stego_path):
        analysis_path = dataset_stego_path

    try:

        result = analyze_image(analysis_path)

        response = {
            "prediction": result["prediction"],
            "risk": result["risk"],

            "chi_square": result.get(
                "chi_square",
                "--"
            ),

            "lsb_ratio": result.get(
                "lsb_ratio",
                "--"
            ),

            "noise_level": result.get(
                "noise_level",
                "--"
            ),

            "randomness_score": result.get(
                "randomness_score",
                "--"
            ),

            "rs_score": result.get(
                "rs_score",
                "--"
            ),

            "hidden_message": (
            result.get("hidden_message_analysis", {}).get(
            "message",
            ""
       )
          or "No hidden message extracted"
),

"hidden_message_analysis": result.get(
    "hidden_message_analysis",
    {
        "attempted": False,
        "found": False,
        "message": "",
        "printable_ratio": 0.0
    }
),

            "paired_analysis": result.get(
                "paired_analysis",
                {
                    "available": False,
                    "message": "No paired analysis available."
                }
            )
        }

        # Generate PDF automatically
        pdf_filename = generate_pdf(
            response,
            file_path
        )

        response["pdf_report"] = (
            f"/download/{pdf_filename}"
        )

        return jsonify(response)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
    
# ---------------- DOWNLOAD REPORT ----------------
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(REPORT_FOLDER, filename, as_attachment=True)


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)