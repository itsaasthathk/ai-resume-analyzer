from flask import Flask, render_template, request
import os
import re
import PyPDF2

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

SKILLS = [
    "python","java","c","c++","html","css","javascript",
    "react","node","flask","django","sql","mysql",
    "mongodb","git","github","excel","power bi",
    "machine learning","deep learning",
    "artificial intelligence","nlp",
    "tensorflow","pytorch","docker",
    "aws","azure","linux","rest api"
]

# ---------------- PDF Reader ---------------- #

def read_pdf(path):

    text = ""

    try:

        with open(path, "rb") as f:

            reader = PyPDF2.PdfReader(f)

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    text += page_text

    except Exception as e:

        print(e)

    return text.lower()


# ---------------- Candidate Details ---------------- #

def get_email(text):

    m = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return m.group() if m else "Not Found"


def get_phone(text):

    m = re.search(r"\d{10}", text.replace(" ", ""))

    return m.group() if m else "Not Found"
def get_name(text):

    lines = text.split("\n")

    for line in lines[:10]:

        line = line.strip()

        if (
            len(line.split()) >= 2
            and len(line.split()) <= 4
            and "@" not in line
            and not any(ch.isdigit() for ch in line)
        ):
            return line.title()

    return "Not Found"


def get_github(text):

    m = re.search(r"github\.com/\S+", text)

    return m.group() if m else "Not Found"


def get_linkedin(text):

    m = re.search(r"linkedin\.com/\S+", text)

    return m.group() if m else "Not Found"


# ---------------- Skills ---------------- #

def extract_skills(text):

    found = []

    for skill in SKILLS:

        if skill in text:

            found.append(skill)

    return sorted(list(set(found)))


def missing_skills(found):

    return [x for x in SKILLS if x not in found]


# ---------------- Resume Stats ---------------- #

def resume_stats(text):

    return {

        "words": len(text.split()),

        "pages": 1,

        "email": get_email(text) != "Not Found",

        "phone": get_phone(text) != "Not Found"

    }


# ---------------- ATS Score ---------------- #

def ats_score(text, skills):

    score = 0

    if get_email(text) != "Not Found":
        score += 10

    if get_phone(text) != "Not Found":
        score += 10

    if len(text.split()) >= 250:
        score += 10

    score += min(len(skills) * 3, 40)

    if any(x in text for x in [
        "b.tech",
        "btech",
        "mba",
        "bca",
        "mca",
        "degree",
        "university"
    ]):
        score += 10

    if "project" in text:
        score += 10

    if "experience" in text or "intern" in text:
        score += 10

    return min(score, 100)
# ---------------- AI Suggestions ---------------- #

def ai_suggestions(text, score):

    text = text.lower()

    tips = []

    if score < 60:
        tips.append("Add more technical skills.")

    if "project" not in text:
        tips.append("Add at least 2 projects.")

    if "intern" not in text and "experience" not in text:
        tips.append("Add internship or work experience.")

    if "certificate" not in text and "certification" not in text:
        tips.append("Add certifications.")

    if "github" not in text:
        tips.append("Add GitHub profile.")

    if "linkedin" not in text:
        tips.append("Add LinkedIn profile.")

    if not tips:
        tips.append("Excellent Resume! No major improvements needed.")

    return tips


# ---------------- JD Match ---------------- #

def jd_match(resume, jd):

    jd = jd.lower()

    jd_skills = [x for x in SKILLS if x in jd]

    matched = [x for x in jd_skills if x in resume]

    missing = [x for x in jd_skills if x not in resume]

    score = int(len(matched) / len(jd_skills) * 100) if jd_skills else 0

    return score, matched, missing

def section_scores(text, skills):

    scores = {}

    # Skills
    scores["skills"] = min(len(skills) * 8, 100)

    # Projects
    scores["projects"] = 100 if "project" in text else 30

    # Education
    education_keywords = [
        "b.tech", "btech", "mba", "bca", "mca",
        "degree", "university", "college"
    ]

    scores["education"] = (
        100 if any(x in text for x in education_keywords) else 40
    )

    # Experience
    experience_keywords = [
        "experience", "intern", "internship"
    ]

    scores["experience"] = (
        100 if any(x in text for x in experience_keywords) else 30
    )

    # Formatting (simple heuristic)
    words = len(text.split())

    if words >= 250:
        scores["formatting"] = 90
    elif words >= 150:
        scores["formatting"] = 70
    else:
        scores["formatting"] = 50

    return scores
# ---------------- Routes ---------------- #
@app.route("/")
def home():
    return render_template("index.html")

def highlight_text(text, skills, missing):

    for skill in skills:
        text = re.sub(
            rf"\b({re.escape(skill)})\b",
            r"<span class='found'>\1</span>",
            text,
            flags=re.IGNORECASE
        )

    for skill in missing:
        text = re.sub(
            rf"\b({re.escape(skill)})\b",
            r"<span class='missing'>\1</span>",
            text,
            flags=re.IGNORECASE
        )

    return text
@app.route("/analyze", methods=["POST"])
def analyze():

    if "resume" not in request.files:
        return "Please upload a PDF."

    file = request.files["resume"]

    if file.filename == "":
        return "No file selected."

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    file.save(filepath)

    text = read_pdf(filepath)

    skills = extract_skills(text)

    missing = missing_skills(skills)

    score = ats_score(text, skills)

    stats = resume_stats(text)
    section = section_scores(text, skills)

    jd = request.form.get("job_description", "")

    match_score, matched, missing_jd = jd_match(text, jd)

    candidate = {
        "name": get_name(text),
        "email": get_email(text),
        "phone": get_phone(text),
        "github": get_github(text),
        "linkedin": get_linkedin(text)
    }

    return render_template(
        "result.html",
        candidate=candidate,
        score=score,
        stats=stats,
        section=section,
        skills=skills,
        missing=missing,
        matched=matched,
        missing_jd=missing_jd,
        match_score=match_score,
        suggestions=ai_suggestions(text, score),
        preview = highlight_text(text[:2000], skills, missing)
    )


if __name__ == "__main__":
    app.run(debug=True)