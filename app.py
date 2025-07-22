from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

app = Flask(__name__)

# Use relative paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EMP_DETAILS_PATH = os.path.join(BASE_DIR, "Emp_Details.xlsx")
PF_ESIC_PATH = os.path.join(BASE_DIR, "Pf_esic_details.xlsx")
SALARY_SLIPS_FOLDER = os.path.join(BASE_DIR, "salary_slips")
PF_ESIC_CARDS_FOLDER = os.path.join(BASE_DIR, "pf_esic_cards")

REFERRAL_FORM_LINK = "https://docs.google.com/forms/d/1hWOzwy0TAEmabUXpWbbjjPr3UGBxNttwbfDrvHFsCUw"

sessions = {}

def find_emp_id(mobile):
    df = pd.read_excel(EMP_DETAILS_PATH)
    row = df[df['Mobile'] == int(mobile)]
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

@app.route("/salary_slips/<path:filename>")
def serve_salary_pdf(filename):
    return send_from_directory(SALARY_SLIPS_FOLDER, filename)

@app.route("/pf_esic_cards/<filename>")
def serve_pf_card(filename):
    return send_from_directory(PF_ESIC_CARDS_FOLDER, filename)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    phone = request.values.get("From", "").replace("whatsapp:", "")
    resp = MessagingResponse()
    msg = resp.message()

    # ✅ FIX: Use setdefault so session persists properly
    session = sessions.setdefault(phone, {})
    expecting = session.get("expecting")

    if incoming_msg.lower() in ["hi", "hello"]:
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

    elif incoming_msg == "1":
        session["expecting"] = "salary"
        msg.body("📌 Enter your Employee ID or 10-digit Mobile Number:")
        return str(resp)

    elif incoming_msg == "2":
        session["expecting"] = "pfesic"
        msg.body("📌 Enter your Employee ID or 10-digit Mobile Number:")
        return str(resp)

    elif incoming_msg == "3":
        msg.body(f"📝 Fill this referral form to earn rewards: {REFERRAL_FORM_LINK}")
        return str(resp)

    elif expecting == "salary":
        if "emp_id" not in session:
            emp_id = incoming_msg if incoming_msg.startswith("EMP") else find_emp_id(incoming_msg)
            if not emp_id:
                msg.body("❌ Employee not found. Please enter a valid Employee ID or Mobile Number.")
                return str(resp)
            session["emp_id"] = emp_id
            msg.body("📅 Enter the month (e.g., June):")
            return str(resp)
        else:
            month = incoming_msg
            emp_id = session["emp_id"]
            rel_path, abs_path = get_salary_pdf(emp_id, month)
            if abs_path:
                msg.media(request.url_root + f"salary_slips/{rel_path.replace(' ', '%20')}")
                msg.body(f"✅ Salary Slip for {month} - {emp_id}")
            else:
                msg.body("❌ Salary Slip not found for the given month.")
            sessions.pop(phone, None)
            return str(resp)

    elif expecting == "pfesic":
        emp_id = incoming_msg if incoming_msg.startswith("EMP") else find_emp_id(incoming_msg)
        filename, abs_path = get_pf_esic_pdf(emp_id)
        if not emp_id or not abs_path:
            msg.body("❌ PF/ESIC card not found or invalid employee ID.")
            sessions.pop(phone, None)
            return str(resp)
        msg.media(request.url_root + f"pf_esic_cards/{filename.replace(' ', '%20')}")
        msg.body(f"✅ PF & ESIC Card - {emp_id}")
        sessions.pop(phone, None)
        return str(resp)

    else:
        msg.body("❗ Invalid option. Please reply with 'Hi' to restart.")
        return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
