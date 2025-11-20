# Certificate Generator – Streamlit Web Application

Certificate Generator is a robust web application built with [Streamlit](https://streamlit.io/) and Python, designed to automate and manage the creation and distribution of internship and training certificates for multiple organizations. With secure user authentication, dynamic data mapping, and branded PDF generation, this tool streamlines administrative tasks for educational and corporate teams.

---

## 🌐 Live Demo

http://143.110.185.65:8501

---

## 📌 Features

- **User Authentication** – Secure registration and login with hashed passwords.
- **Multi-Organization Support** – Generate certificates for multiple organizations, each with their unique logo, seal, and signature.
- **Flexible Data Mapping** – Upload CSVs regardless of column naming conventions and still map fields accurately.
- **Batch Certificate Generation** – Create and download certificates for an entire batch in ZIP format.
- **Branded PDF Output** – Every certificate is generated as a PDF, including official logos, seals, and director signatures.
- **MySQL Database Integration** – Stores user data and certificate records securely.
- **Approved Certificate Download** – Easily download only reviewed/approved certificates.
- **Customizable Fields** – Select domain, activity type, and duration with flexible drop-downs.
- **Responsive UI** – Easily accessible on desktop or browser.
- **Error Handling & Validation** – In-app feedback for uploads and generation issues.

---

## 🛠️ Tech Stack

**Frontend & UI:**
- [Streamlit](https://streamlit.io/)
- [Pandas](https://pandas.pydata.org/) – data cleaning & mapping
- [FPDF](https://pypi.org/project/fpdf/) – PDF creation
- [Pillow](https://python-pillow.org/) – image handling

**Backend & Database:**
- Python 3.x
- MySQL (for user/certificate storage)
- SQLAlchemy (DB interactions)

**Other Tools:**
- CSV upload and validation
- GitHub (version control and CI/CD)
- io/zipfile (file downloads)

---

## 📂 Folder Structure

project-root/
├── app.py # Main Streamlit application
├── requirements.txt
├── assets/
│ ├── dlithe_logo.png
│ ├── dlithe_seal.png
│ ├── dlithe_signature.jpg
│ ├── nxtalign_logo.png
│ ├── nxtalign_seal.png
│ └── nxtalign_signature.jpg
├── README.md
└── ...


---

## 📦 Installation & Setup

**1. Clone the repository:**
git clone https://github.com/your-username/certificate-generator.git
cd certificate-generator

text

**2. Install dependencies:**
pip install -r requirements.txt

text

**3. Configure MySQL database:**
- Create `users` and per-organization certificate tables as described in the documentation or in `app.py`.
- Update DB connection settings in your Streamlit app.

**4. Place organization assets:**
- Logos, seals, signatures go under `assets/` directory.

**5. Run the application:**
streamlit run app.py



---

## 🔌 Usage

1. **Register** a new user or log in with existing credentials.
2. Select your organization, domain, activity type, and certificate type.
3. **Upload a batch CSV** of student/intern details.
4. Review mapped data, generate certificates, and download as ZIP.
5. Download approved certificates after internal review.

---

## 🙋‍♂️ Author

**Kaveri SB**  
✉️ Email: kaveri@dlithe.com(mailto:kaveri@dlithe.com)  
