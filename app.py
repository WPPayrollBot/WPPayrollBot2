import os
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

# --- Load Secrets from Environment ---
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_FROM = os.getenv("TWILIO_FROM", "whatsapp:+14155238886")
PDF_BASE_URL = os.getenv("PDF_BASE_URL", "https://your-domain.com")
REFERRAL_FORM_URL = os.getenv("REFERRAL_FORM_URL", "https://forms.gle/your-form-link")

# --- Local Paths ---
EMP_DETAILS_PATH = os.getenv("EMP_DETAILS_PATH", r"C:\Wh Bot\Emp_Details.xlsx")
PF_ESIC_DETAILS_PATH = os.getenv("PF_ESIC_DETAILS_PATH", r"C:\Wh Bot\Pf_esic_details.xlsx")
SALARY_FOLDER = os.getenv("SALARY_FOLDER", r"C:\Wh Bot\salary_slips")
PF_ESIC_FOLDER = os.getenv("PF_ESIC_FOLDER", r"C:\Wh Bot\pf_esic_cards")

# --- Init ---
app = Flask(__name__)
client = Client(TWILIO_SID, TWILIO_AUTH)
sessions = {}

# --- Load Excel Files ---
print("📁 Loading Excel files...")
try:
    emp_df = pd.read_excel(EMP_DETAILS_PATH)
    pf_df = pd.read_excel(PF_ESIC_DETAILS_PATH)

    emp_df.columns = emp_df.columns.str.strip()
    emp_df['Emp ID'] = emp_df['Emp ID'].astype(str).str.strip().str.upper()
    emp_df['Mobile'] = emp_df['Mobile'].astype(str).str.strip()

    pf_df.columns = pf_df.columns.str.strip()
    pf_df['Emp ID'] = pf_df['Emp ID'].astype(str).str.strip().str.upper()
    pf_df['ESIC Card Filename'] = pf_df['ESIC Card Filename'].astype(str).str.strip()

    print("✅ Excel files loaded.")
    print("📌 EMP IDs:", emp_df['Emp ID'].tolist())

except Exception as e:
    print("❌ Error loading Excel files:", e)
    emp_df = pd.DataFrame()
    pf_df = pd.DataFrame()

# --- Helper Functions ---
def extract_digits(num_str):
    return ''.join(ch for ch in num_str if ch.isdigit())[-10:]

def find_emp_id(mobile):
    try:
        mobile = extract_digits(mobile)
        row = emp_df[emp_df["Mobile"].str[-10:] == mobile]
        if not row.empty:
            return row["Emp ID"].values[0]
    except Exception as e:
        print(f"[ERROR] find_emp_id failed: {e}")
    return None

def find_mobile(emp_id):
    try:
        emp_id = emp_id.strip().upper()
        row = emp_df.loc[emp_df["Emp ID"] == emp_id]
        if not row.empty:
            return str(row["Mobile"].values[0])
        else:
            print(f"[DEBUG] Emp ID '{emp_id}' not found in: {emp_df['Emp ID'].tolist()}")
    except Exception as e:
        print(f"[ERROR] find_mobile failed: {e}")
    return None

def send_pf_card(emp_id):
    try:
        row = pf_df.loc[pf_df["Emp ID"] == emp_id]
        if not row.empty:
            filename = row["ESIC Card Filename"].values[0]
            file_path = os.path.join(PF_ESIC_FOLDER, filename)
            if os.path.exists(file_path):
                link = f"{PDF_BASE_URL}/pf_esic_cards/{filename}"
                return {"reply": f"🪪 PF/ESIC Card:\n{link}"}
            else:
                print(f"[ERROR] File not found: {file_path}")
    except Exception as e:
        print(f"[ERROR] send_pf_card failed: {e}")
    return {"reply": "❌ PF/ESIC card not found. Please contact HR."}

# --- Bot Logic Handler ---
def bot_simulator(msg, phone):
    session = sessions.get(phone, {})
    m = msg.strip().lower()

    if m in ["hi", "hello", "start"]:
        sessions[phone] = {}
        return {
            "reply": (
                "👋 Welcome to Commet PayrollBot!\n\n"
                "1️⃣ Salary Slip\n"
                "2️⃣ PF & ESIC Card\n"
                "4️⃣ Refer & Earn 📝"
            )
        }

    elif m == "1":
        session["expecting"] = "salary"
        sessions[phone] = session
        return {"reply": "📌 Enter your Employee ID or 10-digit Mobile Number:"}

    elif m == "2":
        session["expecting"] = "pf"
        sessions[phone] = session
        return {"reply": "📌 Enter your Employee ID or 10-digit Mobile Number:"}

    elif m == "4":
        return {"reply": f"📝 Refer your friends!\n{REFERRAL_FORM_URL}"}

    elif m.isdigit() and len(m) == 10:
        emp_id = find_emp_id(m)
        if not emp_id:
            return {"reply": "❌ Mobile number not found."}
        session["emp_id"] = emp_id
        sessions[phone] = session
        if session.get("expecting") == "salary":
            return {"reply": "📅 Enter the month (e.g., June_2025):"}
        elif session.get("expecting") == "pf":
            return send_pf_card(emp_id)

    elif m.startswith("emp"):
        emp_id = m.upper()
        if not find_mobile(emp_id):
            return {"reply": f"❌ EMP ID {emp_id} not found."}
        session["emp_id"] = emp_id
        sessions[phone] = session
        if session.get("expecting") == "salary":
            return {"reply": "📅 Enter the month (e.g., June_2025):"}
        elif session.get("expecting") == "pf":
            return send_pf_card(emp_id)

    elif session.get("expecting") == "salary" and session.get("emp_id"):
        emp_id = session["emp_id"]
        try:
            month, year = m.split("_")
            folder = os.path.join(SALARY_FOLDER, year, f"{month}_Salary")
            file_path = os.path.join(folder, f"{emp_id}.pdf")
            if os.path.exists(file_path):
                link = f"{PDF_BASE_URL}/salary_slips/{year}/{month}_Salary/{emp_id}.pdf"
                return {"reply": f"📄 Salary Slip for {emp_id}:\n{link}"}
            else:
                return {"reply": "❌ Slip not found for that month. Try another month or contact HR."}
        except Exception as e:
            print(f"[ERROR] Invalid salary input: {e}")
            return {"reply": "❌ Invalid format. Please enter month like: June_2025"}

    return {"reply": "❌ Invalid input. Please send 'hi' to start again."}

# --- Flask Route for Twilio ---
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    body = request.form.get("Body", "")
    from_num = request.form.get("From", "")
    phone = extract_digits(from_num)

    print(f"📩 Message from {phone}: {body}")
    res = bot_simulator(body, phone)

    twiml = MessagingResponse()
    twiml.message(res["reply"])
    return str(twiml)

# --- Main Entry ---
if __name__ == "__main__":
    print("✅ Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)
