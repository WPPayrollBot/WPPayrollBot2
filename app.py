from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.INFO)

# Sessions stored per WhatsApp number
sessions = {}

# Define all necessary paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMP_DETAILS_PATH = os.path.join(BASE_DIR, "Emp_Details.xlsx")
PF_ESIC_PATH = os.path.join(BASE_DIR, "Pf_esic_details.xlsx")
SALARY_SLIPS_FOLDER = os.path.join(BASE_DIR, "salary_slips")
PF_ESIC_FOLDER = os.path.join(BASE_DIR, "pf_esic_cards")

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip()
    user_mobile = request.values.get('From', '').split(':')[-1]
    logging.info(f"[FROM: {user_mobile}] Message: {incoming_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    # Track user session
    session = sessions.setdefault(user_mobile, {})
    expecting = session.get("expecting")

    # Normalize input
    normalized = incoming_msg.lower().strip()
    normalized = (
        normalized.replace("1️⃣", "1")
        .replace("2️⃣", "2")
        .replace("3️⃣", "3")
        .replace("one", "1")
        .replace("two", "2")
        .replace("three", "3")
    )

    # Welcome menu
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

    if normalized in ["hi", "hello"]:
        session.clear()
        msg.body(welcome_text)
        return str(resp)

    elif normalized == "1":
        session["expecting"] = "salary"
        msg.body("📌 Enter your *Employee ID* or *Registered 10-digit Mobile Number* for salary slip:")
        return str(resp)

    elif normalized == "2":
        session["expecting"] = "pf_esic"
        msg.body("📌 Enter your *Employee ID* or *Registered 10-digit Mobile Number* for PF/ESIC card:")
        return str(resp)

    elif normalized == "3":
        msg.body("🔗 Here is the referral form:\nhttps://docs.google.com/forms/d/1hWOzwy0TAEmabUXpWbbjjPr3UGBxNttwbfDrvHFsCUw")
        return str(resp)

    elif expecting in ["salary", "pf_esic"]:
        user_input = incoming_msg.strip()
        try:
            file_path = EMP_DETAILS_PATH if expecting == "salary" else PF_ESIC_PATH
            df = pd.read_excel(file_path)

            emp_row = df[
                (df['Emp ID'].astype(str).str.upper() == user_input.upper()) |
                (df['Mobile'].astype(str) == user_input)
            ]

            if emp_row.empty:
                msg.body("❌ Employee not found. Please check the ID or mobile number.")
                return str(resp)

            emp_data = emp_row.iloc[0]
            emp_id = emp_data['Emp ID']
            registered_mobile = str(emp_data['Mobile'])

            if user_mobile != registered_mobile:
                logging.warning(f"[ACCESS BLOCKED] {user_mobile} tried accessing {emp_id}")
                msg.body("🔒 Access denied. You can only view your own records from your registered mobile number.")
                return str(resp)

            session["emp_id"] = emp_id
            session["emp_name"] = emp_data.get('Name', '')
            logging.info(f"[VALID ACCESS] {emp_id} accessed by {user_mobile} for {expecting}")

            if expecting == "salary":
                session["expecting"] = "month"
                msg.body("📅 Enter the month name (e.g., June):")
            else:
                session.clear()
                pdf_path = os.path.join(PF_ESIC_FOLDER, f"{emp_id}_pf_esic.pdf")
                if os.path.exists(pdf_path):
                    base_url = request.url_root.rstrip('/')
                    msg.media(f"{base_url}/download/pf_esic/{emp_id}_pf_esic.pdf")
                    msg.body(f"📄 Here's your PF/ESIC card, {emp_id}.")
                else:
                    msg.body("❌ PF/ESIC card not found.")
            return str(resp)

        except Exception as e:
            logging.error(f"Error while processing employee data: {e}")
            msg.body("⚠️ An error occurred. Please try again.")
            return str(resp)

    elif expecting == "month":
        month = incoming_msg.strip().capitalize()
        emp_id = session.get("emp_id")

        pdf_path = os.path.join(SALARY_SLIPS_FOLDER, "2025", f"{month}_Salary", f"{emp_id}_{month}.pdf")

        if os.path.exists(pdf_path):
            session.clear()
            base_url = request.url_root.rstrip('/')
            msg.media(f"{base_url}/download/salary/{month}/{emp_id}_{month}.pdf")
            msg.body(f"📄 Here's your {month} salary slip, {emp_id}.")
        else:
            msg.body(f"❌ Salary slip for {month} not found.")
        return str(resp)

    else:
        msg.body(
            "❓ I didn’t understand that. Please choose:\n"
            "1️⃣ Salary Slip\n"
            "2️⃣ PF & ESIC Card\n"
            "3️⃣ Refer & Earn 📝\n"
            "Or reply with 'hi' to see the menu again."
        )
        return str(resp)

@app.route("/download/salary/<month>/<filename>")
def download_salary(month, filename):
    folder = os.path.join(SALARY_SLIPS_FOLDER, "2025", f"{secure_filename(month)}_Salary")
    return send_from_directory(folder, secure_filename(filename))

@app.route("/download/pf_esic/<filename>")
def download_pf_esic(filename):
    return send_from_directory(PF_ESIC_FOLDER, secure_filename(filename))

if __name__ == "__main__":
    # Required for deployment on Render or cloud servers
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
