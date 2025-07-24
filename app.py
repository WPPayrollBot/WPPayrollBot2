from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

app = Flask(__name__)

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMP_DETAILS_PATH = os.path.join(BASE_DIR, "Emp_Details.xlsx")
PF_ESIC_PATH = os.path.join(BASE_DIR, "Pf_esic_details.xlsx")
SALARY_SLIPS_FOLDER = os.path.join(BASE_DIR, "salary_slips")
PF_ESIC_CARDS_FOLDER = os.path.join(BASE_DIR, "pf_esic_cards")

# External links
REFERRAL_FORM_LINK = "https://docs.google.com/forms/d/1hWOzwy0TAEmabUXpWbbjjPr3UGBxNttwbfDrvHFsCUw"
BASE_URL = "https://comett-10.onrender.com"

# In-memory session store
sessions = {}

# Render live check
@app.route("/", methods=["GET"])
def home():
    return "✅ Comett Payroll Bot is live!"

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

# --- Helpers ---
def find_emp_row(mobile):
    df = pd.read_excel(EMP_DETAILS_PATH)
    row = df[df['Mobile'] == int(mobile)]
    return row.iloc[0] if not row.empty else None

def find_emp_id(input_val):
    df = pd.read_excel(EMP_DETAILS_PATH)
    if input_val.startswith("EMP"):
        row = df[df['Emp ID'] == input_val]
    else:
        row = df[df['Mobile'] == int(input_val)]
    return row['Emp ID'].values[0] if not row.empty else None

def get_salary_pdf(emp_id, month):
    month = month.strip().capitalize()
    folder_name = f"{month}_Salary"
    filename = f"{emp_id}_{month}.pdf"
    rel_path = os.path.join("2025", folder_name, filename)
    abs_path = os.path.join(SALARY_SLIPS_FOLDER, rel_path)
    return (rel_path, abs_path) if os.path.exists(abs_path) else (None, None)

def get_pf_esic_pdf(emp_id):
    filename = f"esic_card_{emp_id}.pdf"
    abs_path = os.path.join(PF_ESIC_CARDS_FOLDER, filename)
    return (filename, abs_path) if os.path.exists(abs_path) else (None, None)

# --- File Serving ---
@app.route("/salary_slips/<path:filename>")
def serve_salary_pdf(filename):
    if ".." in filename or filename.startswith("/"):
        return "❌ Invalid filename", 400
    return send_from_directory(SALARY_SLIPS_FOLDER, filename)

@app.route("/pf_esic_cards/<filename>")
def serve_pf_card(filename):
    if ".." in filename or filename.startswith("/"):
        return "❌ Invalid filename", 400
    return send_from_directory(PF_ESIC_CARDS_FOLDER, filename)

# --- WhatsApp Bot ---
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    phone = request.values.get("From", "").replace("whatsapp:", "")
    user_mobile = phone[-10:]
    print(f"[From {phone}] User sent: {repr(incoming_msg)}")

    normalized = incoming_msg.replace("⿡", "1").replace("⿢", "2").replace("⿤", "3")
    normalized = normalized.replace("1️⃣", "1").replace("2️⃣", "2").replace("3️⃣", "3")

    resp = MessagingResponse()
    msg = resp.message()

    session = sessions.setdefault(phone, {})
    expecting = session.get("expecting")

    if incoming_msg.lower() in ["hi", "hello"]:
        try:
            df = pd.read_excel(EMP_DETAILS_PATH)
            registered_numbers = df["Mobile"].astype(str).str[-10:].tolist()
        except Exception as e:
            msg.body("❌ Error reading employee database.")
            print("Excel load error:", e)
            return str(resp)

        if user_mobile not in registered_numbers:
            msg.body("❌ Your number is not registered with us. Please contact HR.")
            return str(resp)

        session.clear()
        msg.body(
            "👋 Welcome to Commet PayrollBot!\n\n"
            "1️⃣ Salary Slip\n"
            "2️⃣ PF & ESIC Card\n"
            "3️⃣ Refer & Earn 📝\n\n"
            "📞 Contact Support:\n"
            "• EN - +91 9876543210\n"
            "• HI - +91 9876543211\n"
            "• KA - +91 9876543212\n"
            "• TA - +91 9876543213"
        )
        return str(resp)

    elif normalized == "1":
        session["expecting"] = "salary"
        msg.body("📌 Enter your Employee ID or 10-digit Mobile Number:")
        return str(resp)

    elif normalized == "2":
        session["expecting"] = "pfesic"
        msg.body("📌 Enter your Employee ID or 10-digit Mobile Number:")
        return str(resp)

    elif normalized == "3":
        msg.body(f"📝 Fill this referral form to earn rewards: {REFERRAL_FORM_LINK}")
        return str(resp)

    elif expecting == "salary":
        if "emp_id" not in session:
            emp_row = find_emp_row(user_mobile)
            if not emp_row:
                msg.body("❌ Mobile number not found in employee records.")
                return str(resp)

            user_input = incoming_msg.strip()
            emp_id = user_input if user_input.startswith("EMP") else find_emp_id(user_input)

            if emp_id != emp_row["Emp ID"]:
                msg.body("❌ Access denied. You can only access your own data.")
                return str(resp)

            session["emp_id"] = emp_id
            msg.body("📅 Enter the month (e.g., June):")
            return str(resp)
        else:
            month = incoming_msg.strip()
            emp_id = session["emp_id"]
            rel_path, abs_path = get_salary_pdf(emp_id, month)
            if abs_path:
                media_url = f"{BASE_URL}/salary_slips/{rel_path.replace(' ', '%20')}"
                msg.media(media_url)
                msg.body(f"✅ Salary Slip for {month} - {emp_id}")
            else:
                msg.body("❌ Salary Slip not found for the given month.")
            sessions.pop(phone, None)
            return str(resp)

    elif expecting == "pfesic":
        emp_row = find_emp_row(user_mobile)
        if not emp_row:
            msg.body("❌ Mobile number not found in employee records.")
            sessions.pop(phone, None)
            return str(resp)

        user_input = incoming_msg.strip()
        emp_id = user_input if user_input.startswith("EMP") else find_emp_id(user_input)

        if emp_id != emp_row["Emp ID"]:
            msg.body("❌ Access denied. You can only access your own data.")
            sessions.pop(phone, None)
            return str(resp)

        filename, abs_path = get_pf_esic_pdf(emp_id)
        if not abs_path:
            msg.body("❌ PF/ESIC card not found for your ID.")
            sessions.pop(phone, None)
            return str(resp)

        media_url = f"{BASE_URL}/pf_esic_cards/{filename.replace(' ', '%20')}"
        msg.media(media_url)
        msg.body(f"✅ PF & ESIC Card - {emp_id}")
        sessions.pop(phone, None)
        return str(resp)

    else:
        msg.body("❗ Invalid option. Please reply with 'Hi' to restart.")
        return str(resp)

if __name__ == "__main__":
    app.run(debug=True)


