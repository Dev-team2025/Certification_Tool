import streamlit as st
import hashlib
from sqlalchemy import text
from fpdf import FPDF
from PIL import Image
import pandas as pd
import io, zipfile, os
from datetime import datetime, date

# ---------------------------------------------------------
# MYSQL USER AUTHENTICATION AND SESSION MANAGEMENT
# ---------------------------------------------------------

# Hash a password using SHA-256 for secure storage
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Register a new user account and insert into MySQL database
def register_user(username, email, password):
    conn = st.connection("mysql", type="sql")
    password_hash = hash_password(password)
    try:
        with conn.session as session:
            session.execute(
                text("INSERT INTO users (username, email, password_hash) VALUES (:username, :email, :password_hash)"),
                {"username": username, "email": email, "password_hash": password_hash}
            )
            session.commit()
        st.success("Registration successful! Please log in.")
    except Exception as e:
        st.error(f"Registration failed: {e}")


# Validate user credentials against stored username and hashed password
def login_user(username, password):
    conn = st.connection("mysql", type="sql")
    password_hash = hash_password(password)
    result = conn.query(
        "SELECT * FROM users WHERE username = :username AND password_hash = :password_hash",
        params={"username": username, "password_hash": password_hash},
        ttl="0"
    )
    return len(result) > 0


# Fetch logged-in user’s ID from database using username
def get_user_id(username):
    conn = st.connection("mysql", type="sql")
    result = conn.query("SELECT id FROM users WHERE username = :username", params={"username": username})
    if not result.empty:
        return result.iloc[0]['id']
    else:
        return None


# ---------------------------------------------------------
# STATIC ASSET PATHS FOR ORGANIZATIONS AND SEALS
# ---------------------------------------------------------

# Store logo, seal, and signature paths for each organization
ORG_ASSETS = {
    "DLithe": {
        "logo": "dlithe_logo.png",
        "seal": "dlithe_seal.png",
        "signature": "dlithe_signature.jpg"
    },
    "nxtAlign": {
        "logo": "nxtalign_logo.png",
        "seal": "nxtalign_seal.png",
        "signature": "nxtalign_signature.jpg"
    }
}


# ---------------------------------------------------------
# DOMAIN SHORTFORMS (USED IN CERTIFICATE IDs)
# ---------------------------------------------------------

DOMAIN_SHORTFORMS = {
    "Python Fullstack": "PY",
    "Web Development": "WD",
    "Cybersecurity": "CS",
    "Java Full Stack": "JFSD",
    "Artificial Intelligence": "AIML",
    "Internet of Things": "IOT"
}


# ---------------------------------------------------------
# COLUMN MAPPING AND DATE PARSING UTILITIES
# ---------------------------------------------------------

# Maps variable column headers to a consistent format
EXPECTED_COLUMNS = {
    "Prefix":["Prefix","prefix"],
    "Name": ["Name", "Full Name", "Student Name"],
    "USN": ["USN", "University Serial Number", "ID"],
    "College": ["College", "Institution", "University"],
    "Email": ["Email", "Email Address", "E-mail"],
    "Phone": ["Phone", "Phone Number", "Contact"],
    "Registered": ["Registered", "Registration Date"],
    "Start Date": ["Start Date", "Internship Start", "Start"],
    "End Date": ["End Date", "Internship End", "End"],
    "Program": ["Program", "Course", "Internship Program"],
    "Mode": ["Mode", "Internship Mode"],
    "Payment Status": ["Payment Status", "Payment", "Paid"],
    "Certificate Issued Date": ["Certificate Issued Date", "Issue Date", "Cert Date"],
    "Intern ID": ["Intern ID", "ID", "Internship ID"],
    "Topic": ["Topic", "Project Topic", "Internship Topic"],
    "Certificate ID": ["Certificate ID", "Cert ID", "Certificate Number"],
    "Domain": ["Domain", "Internship Domain", "Course Domain"]
}


# Safely parse and normalize date values from CSV
def parse_date_safe(val):
    if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
        return None
    try:
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


# Map uploaded CSV columns to standardized column names and clean data
def map_and_clean_columns(df):
    mapped_df = pd.DataFrame()
    for standard_col, aliases in EXPECTED_COLUMNS.items():
        found = None
        for alias in aliases:
            if alias in df.columns:
                found = alias
                break
        mapped_df[standard_col] = df[found] if found else None

    # Clean string values and ensure dates are formatted
    mapped_df = mapped_df.where(pd.notnull(mapped_df), None)
    for col in mapped_df.columns:
        mapped_df[col] = mapped_df[col].apply(lambda x: str(x).strip() if isinstance(x, str) else x)
    for date_col in ["Start Date", "End Date", "Certificate Issued Date"]:
        if date_col in mapped_df.columns:
            mapped_df[date_col] = mapped_df[date_col].apply(parse_date_safe)
    return mapped_df


# ---------------------------------------------------------
# CERTIFICATE ID GENERATION AND TEXT UTILITIES
# ---------------------------------------------------------

# Generate certificate ID based on organization, domain, student, and date
def generate_certificate_id(domain_short, usn, date_obj, org):
    month_short = date_obj.strftime("%b").upper()
    year_short = date_obj.strftime("%y")
    if str(org).lower() == "nxtalign":
        return f"NXT{domain_short}{usn}{month_short}{year_short}"
    else:
        return f"DL{domain_short}{usn}{month_short}{year_short}"


# Clean text to replace special typographic characters
def clean_text(text):
    if not isinstance(text, str):
        return ""
    return (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
    )


# Format date values into human-readable form
def format_date(dt):
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt).date()
        except Exception:
            return dt
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime(dt.year, dt.month, dt.day)

    day = dt.day
    suffix = "th" if 4 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix} {dt:%B %Y}"


# ---------------------------------------------------------
# PDF CERTIFICATE GENERATION USING FPDF
# ---------------------------------------------------------

def generate_certificate_pdf(
    prefix, name, usn, college, start_date_str, end_date_str, topic, cert_id,
    org, logo_path=None, signature_path=None, seal_path=None, cert_type=None,
    activity_type="Internship", duration="15 Weeks"
):
    # Initialize PDF document
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_auto_page_break(False)
    pdf.add_page()

    page_width, page_height = pdf.w, pdf.h
    border_margin = 8

    # Add border
    pdf.set_line_width(0.5)
    pdf.set_draw_color(255,255,255)
    pdf.rect(border_margin, border_margin, page_width - 2*border_margin, page_height - 2*border_margin)

    # Margins
    left_margin = border_margin + 8
    right_margin = border_margin + 8
    top_margin = border_margin + 8
    pdf.set_left_margin(left_margin)
    pdf.set_right_margin(right_margin)
    current_y = top_margin

    # Add logo if found
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=left_margin, y=current_y, w=35.0)
        except Exception as e:
            st.error(f"Error loading logo image: {e}")

    # Organization-specific information text
    if org == "DLithe":
        org_name = "DLithe Consultancy Services Pvt. Ltd."
        org_cin = "CIN: U72900KA2019PTC121035"
        org_footer1 = "Registered office: #51, 1st Main, 6th Block, BSK 3rd Stage, Bengaluru -560085"
        org_footer2 = "Development Centers: Ujire | Moodabidre | Manipal | Mangaluru | Belagavi"
        org_footer3 = "M: 9008815252 | www.dlithe.com | info@dlithe.com"
        for_text = "For DLithe Consultancy Services Pvt. Ltd."
    else:
        org_name = "nxtAlign Innovation Pvt. Ltd."
        org_cin = "CIN: U73100KA2022PTC165879"
        org_footer1 = "Registered office: H No.4061/B 01, Near Chidambar Ashram, Gadag KA 582102"
        org_footer2 = "Development Centers: Ujire | AIC NITTE"
        org_footer3 = "M: 8553300781 | www.nxtalign.com | nxtalign@gmail.com"
        for_text = "For nxtAlign Innovation Pvt. Ltd."

    # Header section with organization info
    pdf.set_xy(left_margin + 40, current_y)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(page_width - left_margin - right_margin - 40, 8, org_name, align='R', ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(page_width - left_margin - right_margin - 40, 6, org_cin, align='R', ln=1)
    current_y += 18

    # Certificate ID and issue date
    pdf.set_y(current_y + 8)
    pdf.cell(0, 5, f"Certificate ID: {cert_id}", align='L')
    issued_text = f"Issued on: {end_date_str}"
    pdf.set_x(page_width - right_margin - pdf.get_string_width(issued_text))
    pdf.cell(pdf.get_string_width(issued_text), 5, issued_text, align='L')
    pdf.ln(15)

    # Add PROVISIONAL text if applicable
    if cert_type and cert_type.lower() == "provisional":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "PROVISIONAL CERTIFICATE", align='C', ln=1)
        pdf.ln(2)

    # Main certificate heading
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "TO WHOMSOEVER IT MAY CONCERN", align='C', ln=1)

    # Certificate body text
    pdf.set_font("Arial", "", 12)
    effective_width = page_width - left_margin - right_margin
    pdf.set_x(left_margin)

    # Body text for each certificate type
    if cert_type and cert_type.lower() == "provisional":
        para = (
            f"This is to certify {prefix}. {name}, from {college}, "
            f"is currently undergoing a {duration} {activity_type.lower()} starting from {start_date_str} "
            f"to {end_date_str}, under the mentorship of {org}'s development team. "
            f"{name} is working on {topic}.\n\n"
            f"During the {activity_type.lower()}, {name} demonstrated good coding skills with sound design thinking."
        )
    else:
        para = (
            f"This is to certify {prefix}. {name}, from {college}, "
            f"has successfully completed a {duration} {activity_type.lower()} on {start_date_str} "
            f"under the mentorship of {org}'s development team. "
            f"{name} has worked on {topic}.\n\n"
            f"During the {activity_type.lower()}, {name} demonstrated good coding skills with sound design thinking."
        )

    pdf.multi_cell(effective_width, 6, para, align='J')

    # Footer and signatures
    y_sign_start = page_height - 68
    pdf.set_font("Arial", "", 12)
    pdf.set_xy(page_width - right_margin - pdf.get_string_width(for_text), y_sign_start)
    pdf.cell(pdf.get_string_width(for_text), 7, for_text, align='L')

    # Add seal and signature
    if seal_path and os.path.exists(seal_path):
        pdf.image(seal_path, x=left_margin, y=y_sign_start, w=30.0)
    if signature_path and os.path.exists(signature_path):
        pdf.image(signature_path, x=page_width - right_margin - 40, y=y_sign_start + 6.0, w=40.0)
    pdf.set_font("Arial", "", 12)
    pdf.text(page_width - right_margin - 20, y_sign_start + 25.0, "Director")

    # Footer with organization details
    pdf.set_font("Arial", "", 9)
    pdf.set_y(page_height - 20)
    pdf.cell(0, 5, org_footer1, align='C', ln=1)
    pdf.cell(0, 5, org_footer2, align='C', ln=1)
    pdf.cell(0, 5, org_footer3, align='C', ln=1)

    # Return PDF as bytes
    return pdf.output(dest='S').encode('latin-1')


# ---------------------------------------------------------
# DATABASE INSERTION FOR GENERATED CERTIFICATES
# ---------------------------------------------------------

# Insert each generated certificate’s metadata into the MySQL table
def insert_certificate_data(user_id, row, org):
    conn = st.connection("mysql", type="sql")
    table = f"certificate_data_{org}"
    with conn.session as session:
        session.execute(
            text(f"""
                INSERT INTO {table} (
                    user_id, prefix, name, usn, college, email,
                    phone, registered, start_date, end_date,
                    program, mode, payment_status, certificate_issued_date,
                    topic, domain, certificate_id, status
                ) VALUES (
                    :user_id, :prefix, :name, :usn, :college, :email,
                    :phone, :registered, :start_date, :end_date,
                    :program, :mode, :payment_status, :certificate_issued_date,
                    :topic, :domain, :certificate_id, 'pending_review'
                )
            """),
            {
                "user_id": user_id,
                "prefix": row["Prefix"],
                "name": row["Name"],
                "usn": row["USN"],
                "college": row["College"],
                "email": row["Email"],
                "phone": row["Phone"],
                "registered": row["Registered"],
                "start_date": row["Start Date"],
                "end_date": row["End Date"],
                "program": row["Program"],
                "mode": row["Mode"],
                "payment_status": row["Payment Status"],
                "certificate_issued_date": row["Certificate Issued Date"],
                "topic": row["Topic"],
                "domain": row.get("Domain", ""),
                "certificate_id": row["Certificate ID"]
            }
        )
        session.commit()


# ---------------------------------------------------------
# STREAMLIT UI COMPONENTS AND FUNCTIONALITY
# ---------------------------------------------------------

# Organization selector dropdown
def org_dropdown(label="Organization"):
    return st.selectbox(label, list(ORG_ASSETS.keys()))


# Domain selector dropdown
def domain_dropdown(label="Domain"):
    return st.selectbox(label, list(DOMAIN_SHORTFORMS.keys()))


# Generate and download ZIP of approved certificates
def generate_certificates_for_approved(user_id, org, sig_path, seal_path, logo_path):
    conn = st.connection("mysql", type="sql")
    table = f"certificate_data_{org}"
    results = conn.query(
        f"SELECT * FROM {table} WHERE user_id = :user_id AND status = 'Review_Completed'",
        params={"user_id": user_id}
    )
    if results.empty:
        st.warning("No approved certificates to generate.")
        return

    # Add all certificates to a ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for _, row in results.iterrows():
            pdf_bytes = generate_certificate_pdf(
                prefix=row["prefix"],
                name=row["name"],
                usn=row["usn"],
                college=row["college"],
                start_date_str=format_date(row["start_date"]),
                end_date_str=format_date(row["end_date"]),
                topic=row["topic"],
                cert_id=row["cert_id"],
                org=org,
                logo_path=logo_path,
                signature_path=sig_path,
                seal_path=seal_path,
                cert_type="Final"
            )
            pdf_filename = f"{row['name'].replace(' ', '_')}_{row['cert_id']}.pdf"
            zipf.writestr(pdf_filename, pdf_bytes)

    # Offer ZIP file download
    zip_buffer.seek(0)
    st.download_button(
        label="Download Approved Certificates ZIP",
        data=zip_buffer,
        file_name="approved_certificates.zip",
        mime="application/zip"
    )


# ---------------------------------------------------------
# MAIN STREAMLIT APP LOGIC
# ---------------------------------------------------------

def main():
    st.title("Certificate Generator")

    # Initialize login state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # --- Login and Register Menu ---
    if not st.session_state['logged_in']:
        menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

        # Registration page
        if menu == "Register":
            st.subheader("Create New Account")
            username = st.text_input("Username", key="reg_user")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Register"):
                register_user(username, email, password)

        # Login page
        elif menu == "Login":
            st.subheader("Login to Your Account")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                if login_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        return

    # --- Logged-in Menu Options ---
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    menu = st.sidebar.radio("Actions", ["Upload & Generate Certificates", "Download Approved Certificates", "Logout"])

    # Logout
    if menu == "Logout":
        st.session_state['logged_in'] = False
        st.rerun()
        return

    user_id = get_user_id(st.session_state['username'])

    # -------------------------------------------------
    # UPLOAD & GENERATE CERTIFICATES
    # -------------------------------------------------
    if menu == "Upload & Generate Certificates":
        st.header("Batch Upload & Certificate Generation")

        cert_type = st.radio("Certificate Type", ["Provisional", "Final"])
        org = org_dropdown()
        domain = domain_dropdown()

        # Choose activity type
        activity_options = [
            "Internship", "Bootcamp", "Certification Course", "Workshop",
            "Hackathon", "Ideathon", "Faculty Development Program",
            "Skill Development Program", "Employability Enhancement Program", "Other"
        ]
        activity_type = st.selectbox("Type of Activity", activity_options)
        if activity_type == "Other":
            activity_type = st.text_input("Enter custom activity type")

        # Choose duration
        duration_options = ["15 Weeks", "1 Month", "2 Months", "3 Months", "4 Months", "Other"]
        duration = st.selectbox("Duration", duration_options)
        if duration == "Other":
            duration = st.text_input("Enter custom duration")

        # Upload student CSV data
        uploaded_file = st.file_uploader("Upload Student Data (CSV)", type="csv")

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            cleaned_df = map_and_clean_columns(df)
            cleaned_df["Domain"] = domain
            st.write("Mapped Data Preview:", cleaned_df.head())

            # Generate certificates
            if st.button("Generate Certificates"):
                logo_path = ORG_ASSETS[org]["logo"]
                sig_path = ORG_ASSETS[org]["signature"]
                seal_path = ORG_ASSETS[org]["seal"]

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
                    for _, row in cleaned_df.iterrows():
                        try:
                            # Generate unique certificate ID
                            cert_id = generate_certificate_id(
                                DOMAIN_SHORTFORMS[domain],
                                row["USN"],
                                pd.to_datetime(row["End Date"]),
                                org
                            )

                            # Generate individual PDF
                            pdf_bytes = generate_certificate_pdf(
                                prefix=row["Prefix"],
                                name=row["Name"],
                                usn=row["USN"],
                                college=row["College"],
                                start_date_str=format_date(row["Start Date"]),
                                end_date_str=format_date(row["End Date"]),
                                topic=row["Topic"],
                                cert_id=cert_id,
                                org=org,
                                logo_path=logo_path,
                                signature_path=sig_path,
                                seal_path=seal_path,
                                cert_type=cert_type,
                                activity_type=activity_type,
                                duration=duration
                            )

                            # Save into ZIP and database
                            pdf_filename = f"{row['Name'].replace(' ', '_')}_{cert_id}.pdf"
                            zipf.writestr(pdf_filename, pdf_bytes)
                            row["Certificate ID"] = cert_id
                            insert_certificate_data(user_id, row, org)

                        except Exception as e:
                            st.error(f"Error generating certificate for {row['Name']}: {str(e)}")

                # Final ZIP download
                zip_buffer.seek(0)
                program_name = str(cleaned_df["Program"].iloc[0]) if "Program" in cleaned_df.columns and not cleaned_df["Program"].isnull().all() else "Certificates"
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_filename = f"{org}_{program_name}_{now_str}.zip".replace(" ", "_")

                st.session_state['zip_buffer'] = zip_buffer.getvalue()
                st.session_state['zip_filename'] = zip_filename
                st.success("Certificates generated successfully!")

            # Download button for ZIP file
            if 'zip_buffer' in st.session_state and st.session_state['zip_buffer']:
                st.download_button(
                    label="Download Certificates ZIP",
                    data=st.session_state['zip_buffer'],
                    file_name=st.session_state['zip_filename'],
                    mime="application/zip"
                )

    # -------------------------------------------------
    # DOWNLOAD APPROVED CERTIFICATES
    # -------------------------------------------------
    elif menu == "Download Approved Certificates":
        st.header("Download Approved Certificates")
        org = org_dropdown()
        logo_path = ORG_ASSETS[org]["logo"]
        sig_path = ORG_ASSETS[org]["signature"]
        seal_path = ORG_ASSETS[org]["seal"]
        generate_certificates_for_approved(user_id, org, sig_path, seal_path, logo_path)


# Entry point of the application
if __name__ == "__main__":
    main()
