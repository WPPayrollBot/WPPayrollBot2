from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os
import logging

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)

# Session memory
sessions = {}

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMP_DETAILS_PATH = os.path.join(BASE_DIR, "Emp_Details.xlsx")
PF_ESIC_PATH = os.path.join(BASE_DIR, "Pf_esic_details.xlsx")
SALARY_SLIP_FOLDER = os.path.join(BASE_DIR, "salary_slips")
PF_ESIC_FOLDER = os.path.join(BASE_DIR, "pf_esic_cards")

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip()
    user_mobile = request.values.get('From', '').split(':')[-1][-10:]  # Last 10 digits
    resp = MessagingResponse()
    msg = resp.message()

    try:
        emp_df = pd.read_excel(EMP_DETAILS_PATH)
        row = emp_df[emp_df['Mobile'].astype(str).str[-10:] == user_mobile]
        if row.empty:
            msg.body("❌ Your number is not registered. Contact HR.")
            return str(resp)

        emp_id = row['Emp ID'].values[0]
        name = row['Name'].values[0]

        # Check if user is already in a session
        if user_mobile not in sessions:
            sessions[user_mobile] = {'stage': 'menu'}
            msg.body(f"👋 Hello {name}!\n\n1️⃣ Salary Slip\n2️⃣ PF & ESIC Card\n3️⃣ Refer & Earn 📝\n\nReply with a number.")
            return str(resp)

        stage = sessions[user_mobile]['stage']

        # Handle menu choice
        if stage == 'menu':
            if incoming_msg == '1':
                sessions[user_mobile]['stage'] = 'salary_month'
                msg.body("📅 Enter month (e.g., June or May):")
            elif incoming_msg == '2':
                # PF/ESIC Card retrieval
                pf_df = pd.read_excel(PF_ESIC_PATH)
                record = pf_df[pf_df["Emp ID"] == emp_id]

                if record.empty:
                    msg.body("❌ PF/ESIC details not found.")
                    return str(resp)

                filename = record["ESIC Card Filename"].values[0]
                pdf_path = os.path.join(PF_ESIC_FOLDER, filename)

                if not os.path.exists(pdf_path):
                    msg.body("❌ PF/ESIC card file not found.")
                    return str(resp)

                msg.media(f"https://wppayrollbot2.onrender.com/pf_esic_cards/{filename}")
                msg.body(f"📄 Your PF & ESIC Card: {filename}")
                sessions.pop(user_mobile, None)
            elif incoming_msg == '3':
                msg.body("📝 Refer & Earn form:\nhttps://docs.google.com/forms/d/1hWOzwy0TAEmabUXpWbbjjPr3UGBxNttwbfDrvHFsCUw")
                sessions.pop(user_mobile, None)
            else:
                msg.body("⚠️ Invalid option. Reply 1, 2 or 3.")
        elif stage == 'salary_month':
            month = incoming_msg.capitalize()
            salary_path = os.path.join(SALARY_SLIP_FOLDER, "2025", f"{month}_Salary", f"{emp_id}_{month}.pdf")

            if os.path.exists(salary_path):
                file_url = f"https://wppayrollbot2.onrender.com/salary_slips/2025/{month}_Salary/{emp_id}_{month}.pdf"
                msg.media(file_url)
                msg.body(f"📄 Your {month} 2025 salary slip.")
            else:
                msg.body(f"❌ Salary slip for {month} not found.")

            sessions.pop(user_mobile, None)
        else:
            msg.body("⚠️ Unknown state. Starting over.")
            sessions.pop(user_mobile, None)

    except Exception as e:
        logging.exception("Error in /whatsapp:")
        msg.body("⚠️ Server error. Contact HR.")

    return str(resp)

# Serve PDFs (Render-compatible)
@app.route("/salary_slips/2025/<month_folder>/<filename>")
def serve_salary(month_folder, filename):
    folder = os.path.join(SALARY_SLIP_FOLDER, "2025", month_folder)
    return send_from_directory(folder, filename)

@app.route("/pf_esic_cards/<filename>")
def serve_pf_esic(filename):
    return send_from_directory(PF_ESIC_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
