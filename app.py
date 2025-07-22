
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

app = Flask(__name__)

sessions = {}

# Paths for your Excel and PDF data
EMP_DETAILS_PATH = "C:\Wh Bot\Emp_Details.xlsx"
PF_ESIC_PATH = "C:\Wh Bot\Pf_esic_details.xlsx"
SALARY_SLIPS_FOLDER = "C:\Wh Bot\salary_slips"
PF_ESIC_CARDS_FOLDER = "C:\Wh Bot\pf_esic_cards"

# Referral Google Form link
REFERRAL_FORM_LINK = "https://docs.google.com/forms/d/1hWOzwy0TAEmabUXpWbbjjPr3UGBxNttwbfDrvHFsCUw"

def find_emp_id(mobile):
    df = pd.read_excel(EMP_DETAILS_PATH)
    row = df[df['Mobile'] == int(mobile)]
    return row['Emp ID'].values[0] if not row.empty else None

def find_mobile(emp_id):
    df = pd.read_excel(EMP_DETAILS_PATH)
    row = df[df['Emp ID'] == emp_id]
    return str(row['Mobile'].values[0]) if not row.empty else None

def get_salary_pdf(emp_id, month):
    month = month.strip().capitalize()
    folder_name = f"{month}_Salary"
    filename = f"{emp_id}_{month}.pdf"
    file_path = os.path.join(SALARY_SLIPS_FOLDER, "2025", folder_name, filename)
    return file_path if os.path.exists(file_path) else None

def get_pf_esic_pdf(emp_id):
    filename = f"esic_card_{emp_id}.pdf"
    file_path = os.path.join(PF_ESIC_CARDS_FOLDER, filename)
    return file_path if os.path.exists(file_path) else None

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    phone = request.values.get("From", "")
    phone = phone.replace("whatsapp:", "")

    resp = MessagingResponse()
    msg = resp.message()

    session = sessions.get(phone, {})
    expecting = session.get("expecting")

    if incoming_msg.lower() in ["hi", "hello"]:
        session.clear()
        sessions[phone] = session
        welcome_text = (
            "👋 Welcome to Commet PayrollBot!\n\n"
            "1️⃣ Salary Slip\n"
            "2️⃣ PF & ESIC Card\n"
            "3️⃣ Refer & Earn 📝\n"
            "\n📞 Contact Support:\n"
            "• EN - +91 9876543210\n"
            "• HI - +91 9876543211\n"
            "• KA - +91 9876543212\n"
            "• TA - +91 9876543213"
        )
        msg.body(welcome_text)
        return str(resp)

    elif incoming_msg == "1":
        session["expecting"] = "salary"
        sessions[phone] = session
        msg.body("📌 Enter your Employee ID or 10-digit Mobile Number:")
        return str(resp)

    elif incoming_msg == "2":
        session["expecting"] = "pfesic"
        sessions[phone] = session
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
            sessions[phone] = session
            msg.body("📅 Enter the month (e.g., June):")
            return str(resp)
        else:
            month = incoming_msg
            emp_id = session["emp_id"]
            pdf_path = get_salary_pdf(emp_id, month)
            if pdf_path:
                msg.media(request.url_root + pdf_path.replace(" ", "%20"))
                msg.body(f"✅ Salary Slip for {month} - {emp_id}")
            else:
                msg.body("❌ Salary Slip not found for the given month.")
            sessions.pop(phone, None)
            return str(resp)

    elif expecting == "pfesic":
        emp_id = incoming_msg if incoming_msg.startswith("EMP") else find_emp_id(incoming_msg)
        if not emp_id:
            msg.body("❌ Employee not found. Please enter a valid Employee ID or Mobile Number.")
            return str(resp)
        pdf_path = get_pf_esic_pdf(emp_id)
        if pdf_path:
            msg.media(request.url_root + pdf_path.replace(" ", "%20"))
            msg.body(f"✅ PF & ESIC Card - {emp_id}")
        else:
            msg.body("❌ PF/ESIC card not found.")
        sessions.pop(phone, None)
        return str(resp)

    else:
        msg.body("❗ Invalid option. Please reply with 'Hi' to restart.")
        return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
