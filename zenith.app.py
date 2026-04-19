import html
import os
import time
from io import BytesIO
from pathlib import Path
import json

import google.generativeai as genai
import gspread
import streamlit as st
from google.api_core.exceptions import ResourceExhausted
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from supabase import Client, create_client

# =========================================================
# CONFIG
# =========================================================
APP_TITLE = "Zenith - FindYourDream"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

# Read from Streamlit secrets first, then fallback to environment variables
def get_secret(name: str, default: str | None = None):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
SERVICE_ACCOUNT_FILE = get_secret("SERVICE_ACCOUNT_FILE")
GOOGLE_SHEET_KEY = get_secret(
    "GOOGLE_SHEET_KEY",
    "1pH-2bpO5FU-BniYxZR5jE8FeY6YfHfSJEF8z88_fhQQ",
)
GOOGLE_SHEET_WORKSHEET = get_secret("GOOGLE_SHEET_WORKSHEET", "data")

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
SUPABASE_BUCKET = get_secret("SUPABASE_BUCKET", "zenith-pdfs")
SUPABASE_PUBLIC_BUCKET = str(get_secret("SUPABASE_PUBLIC_BUCKET", "false")).lower() == "true"

FONT_CANDIDATES = [
    "NotoSansThai.ttf",
    "assets/NotoSansThai.ttf",
]

QUESTION_MAP = {
    "q1": "1) คุณสนใจเรื่องอะไรเป็นพิเศษ หรือชอบเรียนรู้อะไร",
    "q2": "2) วิชาที่คุณคิดว่าตัวเองถนัดหรือทำได้ดีคืออะไร เพราะอะไร",
    "q3": "3) ตอนนี้มีคณะ / สาขา / อาชีพในใจไหม",
    "q4": "4) คุณเคยทำกิจกรรมอะไรที่คิดว่าสะท้อนตัวตนหรือความสามารถของคุณ",
    "q5": "5) จุดแข็งของคุณคืออะไร และมีเรื่องไหนที่อยากพัฒนาตัวเองเพิ่ม",
    "q6": "6) เป้าหมายหรือความฝันในอนาคตที่อยากไปถึงคืออะไร",
}

REFLECTION_KEYS = [
    "ฐานวิชาการ 1 : แบ่งน้ำปันใจ",
    "ฐานวิชาการ 2 : The Cellular bridge",
    "ฐานวิชาการ 3 : Unlock the outbreak",
    "ฐานวิชาการ 4 : เกมครูเพ็ญศรี",
    "ฐานวิชาการ 5 : Forensic Science Challenge",
    "ฐานกิจกรรม 1 : ตุ๊กตาขนมปัง",
    "ฐานกิจกรรม 2 : Voices in the Room",
    "ฐานกิจกรรม 3 : Odyssey Plan & Dream Bingo",
]

SELF_RATE_GROUPS = [
    {
        "group_key": "thinking",
        "group_title": "Thinking Skills",
        "skills": [
            ("critical_thinking", "Critical Thinking", ""),
            ("creativity", "Creativity", ""),
            ("problem_solving", "Problem Solving", ""),
            ("information_literacy", "Information Literacy", ""),
        ],
    },
    {
        "group_key": "social",
        "group_title": "Working With Others",
        "skills": [
            ("collaboration", "Collaboration", ""),
            ("communication", "Communication", ""),
            ("empathy", "Empathy", ""),
            ("social_awareness", "Social Awareness", ""),
        ],
    },
    {
        "group_key": "growth",
        "group_title": "Growth & Leadership",
        "skills": [
            ("innovation", "Innovation", ""),
            ("curiosity", "Curiosity", ""),
            ("initiative", "Initiative", ""),
            ("adaptability", "Adaptability", ""),
        ],
    },
]

SHEET_SKILL_COLUMN_MAP = {
    "critical_thinking": "critical thinking",
    "creativity": "creativity",
    "problem_solving": "problem solving",
    "collaboration": "collaboration",
    "communication": "communication",
    "empathy": "empathy",
    "innovation": "innovation",
    "information_literacy": "information literacy",
    "curiosity": "curiosity",
    "social_awareness": "social awareness",
    "initiative": "initiative",
    "adaptability": "adaptability",
}

PREPOST_SUBJECTS = [
    {
        "key": "math",
        "label_th": "คณิต",
        "pre_candidates": ["pre-test คณิต", "pretest คณิต", "คณิต pre-test", "คณิต pretest", "math pre-test", "math pretest", "math_pre", "pre_math"],
        "post_candidates": ["post-test คณิต", "posttest คณิต", "คณิต post-test", "คณิต posttest", "math post-test", "math posttest", "math_post", "post_math"],
    },
    {
        "key": "physics",
        "label_th": "ฟิสิกส์",
        "pre_candidates": ["pre-test ฟิสิกส์", "pretest ฟิสิกส์", "ฟิสิกส์ pre-test", "ฟิสิกส์ pretest", "physics pre-test", "physics pretest", "physics_pre", "pre_physics"],
        "post_candidates": ["post-test ฟิสิกส์", "posttest ฟิสิกส์", "ฟิสิกส์ post-test", "ฟิสิกส์ posttest", "physics post-test", "physics posttest", "physics_post", "post_physics"],
    },
    {
        "key": "chemistry",
        "label_th": "เคมี",
        "pre_candidates": ["pre-test เคมี", "pretest เคมี", "เคมี pre-test", "เคมี pretest", "chemistry pre-test", "chemistry pretest", "chemistry_pre", "pre_chemistry"],
        "post_candidates": ["post-test เคมี", "posttest เคมี", "เคมี post-test", "เคมี posttest", "chemistry post-test", "chemistry posttest", "chemistry_post", "post_chemistry"],
    },
    {
        "key": "biology",
        "label_th": "ชีวะ",
        "pre_candidates": ["pre-test ชีวะ", "pretest ชีวะ", "ชีวะ pre-test", "ชีวะ pretest", "biology pre-test", "biology pretest", "biology_pre", "pre_biology"],
        "post_candidates": ["post-test ชีวะ", "posttest ชีวะ", "ชีวะ post-test", "ชีวะ posttest", "biology post-test", "biology posttest", "biology_post", "post_biology"],
    },
    {
        "key": "english",
        "label_th": "อังกฤษ",
        "pre_candidates": ["pre-test อังกฤษ", "pretest อังกฤษ", "อังกฤษ pre-test", "อังกฤษ pretest", "english pre-test", "english pretest", "english_pre", "pre_english"],
        "post_candidates": ["post-test อังกฤษ", "posttest อังกฤษ", "อังกฤษ post-test", "อังกฤษ posttest", "english post-test", "english posttest", "english_post", "post_english"],
    },
]

PROFILE_EXCLUDE_KEYS = ["ID"] + REFLECTION_KEYS + list(SHEET_SKILL_COLUMN_MAP.values())

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# UTILITIES
# =========================================================
def require_config(name: str, value: str | None):
    if value:
        return

    if name == "SERVICE_ACCOUNT_FILE":
        st.error(
            "ไม่พบ SERVICE_ACCOUNT_FILE กรุณาใส่ path ของไฟล์ service account ใน Streamlit secrets หรือ environment variables"
        )
    else:
        st.error(f"ไม่พบ {name} กรุณาตรวจสอบ Streamlit secrets / environment variables")
    st.stop()


def safe_float(value, default: float = 0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sanitize_pdf_text(text: str | None) -> str:
    if text is None:
        return "-"
    sanitized = str(text)
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\r\n": "\n",
        "\n\n": "\n",
    }
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)
    return sanitized


def get_prepost_value(selected_info: dict, candidates: list[str]):
    normalized = {str(k).strip().lower(): v for k, v in selected_info.items()}
    for candidate in candidates:
        value = normalized.get(candidate.strip().lower())
        if value not in (None, ""):
            return safe_float(value, None)
    return None


def get_prepost_scores(selected_info: dict) -> list[dict]:
    rows = []
    for subject in PREPOST_SUBJECTS:
        pre_score = get_prepost_value(selected_info, subject["pre_candidates"])
        post_score = get_prepost_value(selected_info, subject["post_candidates"])
        rows.append(
            {
                "key": subject["key"],
                "label_th": subject["label_th"],
                "pre": pre_score,
                "post": post_score,
                "delta": None if pre_score is None or post_score is None else post_score - pre_score,
            }
        )
    return rows


def format_score(value):
    return "-" if value is None else f"{value:.1f}"


def get_font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "ไม่พบไฟล์ NotoSansThai.ttf กรุณาวางไว้ที่โฟลเดอร์เดียวกับไฟล์นี้ หรือ assets/NotoSansThai.ttf"
    )


def register_thai_font():
    font_path = get_font_path()
    if "ThaiFont" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ThaiFont", font_path))


# =========================================================
# VALIDATION / MODEL
# =========================================================
require_config("GEMINI_API_KEY", GEMINI_API_KEY)
require_config("SERVICE_ACCOUNT_FILE", SERVICE_ACCOUNT_FILE)
require_config("SUPABASE_URL", SUPABASE_URL)
require_config("SUPABASE_KEY", SUPABASE_KEY)

def ensure_service_account_file() -> str:
    # ใช้จาก Streamlit secrets
    if "gcp_service_account" in st.secrets:
        temp_path = "/tmp/gcp_service_account.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f)
        return temp_path

    # fallback: ใช้ไฟล์ local (กรณีรันเครื่องตัวเอง)
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
    if service_account_file and os.path.exists(service_account_file):
        return service_account_file

    raise FileNotFoundError(
        "ไม่พบ service account ทั้งใน st.secrets และ environment variables"
    )

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# =========================================================
# GOOGLE SHEETS
# =========================================================
def get_google_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    service_account_path = ensure_service_account_file()
    return Credentials.from_service_account_file(service_account_path, scopes=scopes)


@st.cache_resource
def get_gspread_client():
    creds = get_google_credentials()
    return gspread.authorize(creds)


@st.cache_data(ttl=60)
def load_sheet_data():
    gc = get_gspread_client()
    sh = gc.open_by_key(GOOGLE_SHEET_KEY)
    available_worksheets = [ws.title for ws in sh.worksheets()]

    if GOOGLE_SHEET_WORKSHEET not in available_worksheets:
        raise ValueError(
            f"ไม่พบ worksheet ชื่อ '{GOOGLE_SHEET_WORKSHEET}' | มีอยู่จริง: {available_worksheets}"
        )

    worksheet = sh.worksheet(GOOGLE_SHEET_WORKSHEET)
    return worksheet.get_all_records()


# =========================================================
# SUPABASE
# =========================================================
@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_pdf_to_supabase(file_bytes: bytes, filename: str, student_id: str) -> dict:
    supabase = get_supabase_client()
    timestamp = int(time.time())
    file_path = f"exports/{student_id}/{timestamp}-{filename}"

    upload_response = supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=file_path,
        file=file_bytes,
        file_options={
            "content-type": "application/pdf",
            "upsert": "true",
        },
    )

    public_url = ""
    if SUPABASE_PUBLIC_BUCKET:
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_path)

    return {
        "path": file_path,
        "public_url": public_url,
        "response": upload_response,
    }


# =========================================================
# CONTEXT / PROMPT
# =========================================================
def build_context_text(selected_info: dict) -> str:
    context_lines = []

    for key, value in selected_info.items():
        if key in PROFILE_EXCLUDE_KEYS:
            continue
        if value in (None, ""):
            continue
        context_lines.append(f"{key}: {value}")

    reflection_lines = []
    for key in REFLECTION_KEYS:
        value = str(selected_info.get(key, "")).strip()
        if value:
            reflection_lines.append(f"- {key}: {value}")

    if reflection_lines:
        context_lines.append("Reflection จากฐานกิจกรรม:")
        context_lines.extend(reflection_lines)

    prepost_rows = get_prepost_scores(selected_info)
    if any(r["pre"] is not None or r["post"] is not None for r in prepost_rows):
        context_lines.append("คะแนน Pre-test / Post-test:")
        for row in prepost_rows:
            delta = row["delta"]
            delta_text = "-" if delta is None else f"{delta:+.1f}"
            context_lines.append(
                f"- {row['label_th']}: Pre-test {format_score(row['pre'])}, Post-test {format_score(row['post'])}, ผลต่าง {delta_text}"
            )

    context_lines.append("คะแนนทักษะจากข้อมูลในระบบ:")
    for group in SELF_RATE_GROUPS:
        for skill_key, skill_en, _ in group["skills"]:
            sheet_col = SHEET_SKILL_COLUMN_MAP.get(skill_key, "")
            context_lines.append(
                f"- {skill_en}: {safe_float(selected_info.get(sheet_col, 0), 0.0):.1f}/5"
            )

    return "\n".join(context_lines)


def build_answers_text(answers: dict) -> str:
    return f"""
คำตอบของนักเรียน:
1. ความสนใจ / สิ่งที่ชอบ:
{answers.get('q1', '')}

2. วิชาที่ถนัด:
{answers.get('q2', '')}

3. คณะ / สาขา / อาชีพที่สนใจ:
{answers.get('q3', '')}

4. กิจกรรมที่เคยทำ:
{answers.get('q4', '')}

5. จุดแข็งของคุณคืออะไร และมีเรื่องไหนที่อยากพัฒนาตัวเองเพิ่ม:
{answers.get('q5', '')}

6. เป้าหมายหรือความฝันในอนาคต:
{answers.get('q6', '')}
""".strip()


def build_analysis_prompt(context: str, answers: dict) -> str:
    answers_text = build_answers_text(answers)
    return f"""
คุณคือผู้เชี่ยวชาญด้านการศึกษา การค้นหาตัวตน การวางแผนการเตรียมตัวเกี่ยวกับการศึกษาและกิจกรรมในการเรียนต่อมหาวิทยาลัย
และการแนะแนวอาชีพสำหรับนักเรียนมัธยมปลาย

ข้อมูลจากระบบ:
{context}

{answers_text}

คำสั่งสำคัญ:
- วิเคราะห์จากทั้งข้อมูลในระบบและคำตอบของนักเรียนร่วมกัน
- ใช้คะแนนทักษะจากข้อมูลในระบบเป็นข้อมูลสนับสนุน ไม่ใช่ข้อสรุปเด็ดขาด
- ถ้าข้อมูลบางส่วนยังไม่ชัด ให้บอกอย่างระมัดระวังว่าเป็นแนวโน้ม ไม่ฟันธงเกินจริง
- ใช้ภาษาไทยสุภาพ ชัดเจน นำไปใช้ได้จริง
- น้ำเสียงเป็นมิตร สร้างแรงบันดาลใจ แต่ไม่เวอร์เกินจริง
- หลีกเลี่ยงคำตอบกว้างเกินไปหรือคลุมเครือ
- ให้ตอบเป็นภาษาไทยทั้งหมด
- ให้เน้น "Roadmap การพัฒนา" ที่ทำได้จริง
- หลีกเลี่ยงการใช้ markdown ตาราง

โปรดตอบในรูปแบบหัวข้อดังนี้:

1. ภาพรวมตัวตนและความสนใจ
2. วิเคราะห์ความถนัด
3. แนวทางคณะ / สาขา / อาชีพที่เหมาะ
4. Roadmap การพัฒนา
- ระยะสั้น (ภายใน 3 เดือน)
- ระยะกลาง (6-12 เดือน)
- ระยะยาว (การเตรียมตัวเข้ามหาวิทยาลัย)
5. ทักษะที่ควรพัฒนา
6. คำแนะนำในการเตรียมสอบและทำพอร์ต
7. ข้อความส่งท้ายให้กำลังใจ
""".strip()


def run_analysis(selected_info: dict, answers: dict) -> str:
    context = build_context_text(selected_info)
    prompt = build_analysis_prompt(context, answers)
    response = model.generate_content(prompt)
    return response.text if getattr(response, "parts", None) else "AI ไม่ตอบ"


# =========================================================
# PDF
# =========================================================
def create_pdf_bytes(user_id: str, profile: dict | None, answers: dict, analysis_result: str):
    register_thai_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    title_style = ParagraphStyle(
        name="Title",
        fontName="ThaiFont",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=8,
    )

    header_style = ParagraphStyle(
        name="Header",
        fontName="ThaiFont",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
        spaceBefore=8,
    )

    normal_style = ParagraphStyle(
        name="Normal",
        fontName="ThaiFont",
        fontSize=10.5,
        leading=16,
        textColor=colors.black,
        spaceAfter=4,
    )

    content = [
        Paragraph("ZENITH - Roadmap Report", title_style),
        Paragraph(f"รหัสนักเรียน: {sanitize_pdf_text(user_id)}", normal_style),
        Spacer(1, 8),
    ]

    content.append(Paragraph("ข้อมูลพื้นฐานที่ใช้ประกอบการวิเคราะห์", header_style))
    if profile:
        for key, value in profile.items():
            if key in PROFILE_EXCLUDE_KEYS:
                continue
            if value in (None, ""):
                continue
            line = f"<b>{sanitize_pdf_text(key)}:</b> {sanitize_pdf_text(value)}"
            content.append(Paragraph(line, normal_style))
    else:
        content.append(Paragraph("ไม่พบข้อมูลจากระบบ", normal_style))

    reflections = []
    if profile:
        for key in REFLECTION_KEYS:
            value = str(profile.get(key, "")).strip()
            if value:
                reflections.append((key, value))

    if reflections:
        content.append(Spacer(1, 8))
        content.append(Paragraph("Reflection จากฐานกิจกรรม", header_style))
        for key, value in reflections:
            line = f"<b>{sanitize_pdf_text(key)}:</b> {sanitize_pdf_text(value)}"
            content.append(Paragraph(line, normal_style))

    prepost_rows = get_prepost_scores(profile or {})
    if any(r["pre"] is not None or r["post"] is not None for r in prepost_rows):
        content.append(Spacer(1, 8))
        content.append(Paragraph("คะแนน Pre-test / Post-test", header_style))
        for row in prepost_rows:
            delta = row["delta"]
            delta_text = "-" if delta is None else f"{delta:+.1f}"
            score_line = (
                f"<b>{sanitize_pdf_text(row['label_th'])}:</b> "
                f"Pre-test {format_score(row['pre'])} | "
                f"Post-test {format_score(row['post'])} | "
                f"ผลต่าง {delta_text}"
            )
            content.append(Paragraph(score_line, normal_style))

    content.append(Spacer(1, 8))
    content.append(Paragraph("คำตอบของนักเรียน", header_style))
    for key, label in QUESTION_MAP.items():
        answer = sanitize_pdf_text(answers.get(key, "-"))
        content.append(Paragraph(f"<b>{sanitize_pdf_text(label)}</b>", normal_style))
        content.append(Paragraph(answer if answer.strip() else "-", normal_style))

    content.append(Spacer(1, 8))
    content.append(Paragraph("Roadmap และผลการวิเคราะห์จาก AI", header_style))
    if analysis_result:
        for line in sanitize_pdf_text(analysis_result).split("\n"):
            if line.strip():
                content.append(Paragraph(line, normal_style))
    else:
        content.append(Paragraph("ยังไม่มีผลการวิเคราะห์", normal_style))

    doc.build(content)
    buffer.seek(0)
    filename = f"{user_id}-Zenith-Roadmap.pdf"
    return buffer.getvalue(), filename


# =========================================================
# DATA HELPERS
# =========================================================
def get_student_display_options(sheet_data: list[dict]) -> list[str]:
    return [str(row.get("ID", "")).strip() for row in sheet_data if str(row.get("ID", "")).strip()]


def get_selected_student(sheet_data: list[dict], selected_id: str) -> dict | None:
    return next(
        (row for row in sheet_data if str(row.get("ID", "")).strip() == selected_id),
        None,
    )


def answered_enough(answers: dict) -> bool:
    answered_count = sum(
        1 for key in QUESTION_MAP if str(answers.get(key, "")).strip()
    )
    return answered_count >= 3


# =========================================================
# APP
# =========================================================
st.title("🧭 Zenith - FindYourDream")
st.caption('"สร้างรากฐาน ผสานกิ่ง ส่องทางฝัน"')

try:
    sheet_data = load_sheet_data()
except Exception as exc:
    st.error(f"โหลดข้อมูลจาก Google Sheets ไม่สำเร็จ: {type(exc).__name__}: {exc}")
    st.stop()

if not sheet_data:
    st.warning("ยังไม่พบข้อมูลนักเรียนจาก Google Sheets")
    st.stop()

student_ids = get_student_display_options(sheet_data)
selected_id = st.selectbox("เลือก ID นักเรียน", student_ids)
selected_info = get_selected_student(sheet_data, selected_id)

if selected_info is None:
    st.error("ไม่พบข้อมูลของนักเรียนที่เลือก")
    st.stop()

with st.form("roadmap_export_form"):
    q1 = st.text_area(QUESTION_MAP["q1"], height=100)
    q2 = st.text_area(QUESTION_MAP["q2"], height=100)
    q3 = st.text_area(QUESTION_MAP["q3"], height=100)
    q4 = st.text_area(QUESTION_MAP["q4"], height=100)
    q5 = st.text_area(QUESTION_MAP["q5"], height=100)
    q6 = st.text_area(QUESTION_MAP["q6"], height=100)
    submitted = st.form_submit_button("สร้าง Roadmap และ Export PDF")

if submitted:
    answers = {
        "q1": q1.strip(),
        "q2": q2.strip(),
        "q3": q3.strip(),
        "q4": q4.strip(),
        "q5": q5.strip(),
        "q6": q6.strip(),
    }

    if not answered_enough(answers):
        st.warning("กรุณาตอบอย่างน้อย 3 ข้อ เพื่อให้ AI วิเคราะห์ได้มีคุณภาพมากขึ้น")
        st.stop()

    with st.spinner("กำลังประมวลผล AI และสร้างไฟล์ PDF..."):
        try:
            ai_text = run_analysis(selected_info, answers)
            pdf_bytes, pdf_name = create_pdf_bytes(
                user_id=selected_id,
                profile=selected_info,
                answers=answers,
                analysis_result=ai_text,
            )

            upload_result = upload_pdf_to_supabase(
                file_bytes=pdf_bytes,
                filename=pdf_name,
                student_id=selected_id,
            )

            st.success("สร้าง Roadmap สำเร็จ")
            st.download_button(
                "ดาวน์โหลด PDF",
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

            if upload_result.get("path"):
                st.caption(f"Supabase path: {upload_result['path']}")
            if upload_result.get("public_url"):
                st.link_button("เปิดไฟล์จาก Supabase", upload_result["public_url"])

        except ResourceExhausted:
            st.warning("ขณะนี้ quota ของโมเดลเต็ม กรุณารอสักครู่แล้วลองใหม่อีกครั้ง")
        except FileNotFoundError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"เกิดข้อผิดพลาดระหว่างประมวลผล: {type(exc).__name__}: {exc}")
