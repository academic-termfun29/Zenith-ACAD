import html
import json
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import google.generativeai as genai
import gspread
import streamlit as st
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore


load_dotenv()

st.set_page_config(page_title="Zenith Roadmap Generator", page_icon="🌟", layout="centered")


SKY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&display=swap');

:root {
    --sky-1: #f6fbff;
    --sky-2: #eaf6ff;
    --sky-3: #d9efff;
    --sky-4: #c7e6ff;
    --sky-5: #7cc7ff;
    --sky-6: #2f8cff;
    --text-main: #12324a;
    --text-soft: #4f6f88;
    --stroke: rgba(135, 185, 230, 0.35);
    --card-bg: rgba(255, 255, 255, 0.70);
    --shadow: 0 20px 50px rgba(64, 143, 217, 0.12);
}

html, body, [class*="css"]  {
    font-family: 'IBM Plex Sans Thai', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.45) 18%, rgba(255,255,255,0) 36%),
        radial-gradient(circle at top right, rgba(178,226,255,0.60) 0%, rgba(178,226,255,0.18) 20%, rgba(178,226,255,0) 40%),
        linear-gradient(180deg, var(--sky-1) 0%, var(--sky-2) 42%, var(--sky-3) 100%);
    color: var(--text-main);
}

.block-container {
    max-width: 920px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stHeader"] {
    background: rgba(255,255,255,0);
}

[data-testid="stToolbar"] {
    right: 1rem;
}

.sky-hero {
    position: relative;
    overflow: hidden;
    border-radius: 30px;
    padding: 2rem 2rem 1.5rem 2rem;
    margin-bottom: 1rem;
    background: linear-gradient(145deg, rgba(255,255,255,0.90), rgba(232,245,255,0.82));
    border: 1px solid rgba(180, 220, 255, 0.9);
    box-shadow: 0 24px 70px rgba(74, 149, 213, 0.14);
}
.sky-hero:before, .sky-hero:after {
    content: "";
    position: absolute;
    border-radius: 999px;
    background: rgba(255,255,255,0.48);
    filter: blur(2px);
}
.sky-hero:before {
    width: 180px;
    height: 180px;
    top: -55px;
    right: -30px;
}
.sky-hero:after {
    width: 130px;
    height: 130px;
    bottom: -45px;
    left: -20px;
}
.sky-badge {
    display: inline-block;
    padding: 0.38rem 0.8rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.80);
    color: #2176d2;
    border: 1px solid rgba(117, 186, 255, 0.45);
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 0.9rem;
}
.sky-title {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.18;
    color: #0f3f75;
    margin-bottom: 0.35rem;
}
.sky-subtitle {
    font-size: 1rem;
    line-height: 1.7;
    color: var(--text-soft);
    max-width: 760px;
}
.sky-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
    margin-top: 1.1rem;
}
.sky-mini-card {
    background: rgba(255,255,255,0.62);
    border: 1px solid rgba(165, 212, 255, 0.60);
    border-radius: 22px;
    padding: 0.9rem 1rem;
    box-shadow: var(--shadow);
}
.sky-mini-label {
    font-size: 0.74rem;
    font-weight: 600;
    color: #5b84a3;
    margin-bottom: 0.22rem;
}
.sky-mini-value {
    font-size: 1rem;
    font-weight: 700;
    color: #113f66;
}

.section-shell {
    background: var(--card-bg);
    border: 1px solid var(--stroke);
    border-radius: 26px;
    padding: 1.1rem 1.1rem 1.25rem 1.1rem;
    box-shadow: var(--shadow);
    backdrop-filter: blur(12px);
    margin-bottom: 1rem;
}

.section-heading {
    font-size: 1.08rem;
    font-weight: 700;
    color: #12426c;
    margin-bottom: 0.25rem;
}
.section-copy {
    font-size: 0.92rem;
    line-height: 1.65;
    color: var(--text-soft);
    margin-bottom: 0.75rem;
}

div[data-testid="stSelectbox"] > label,
div[data-testid="stTextArea"] > label {
    font-weight: 600 !important;
    color: #1c5888 !important;
}

.stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 18px !important;
    border: 1px solid rgba(153, 204, 250, 0.95) !important;
    background: rgba(255,255,255,0.88) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8), 0 8px 20px rgba(120, 182, 231, 0.08) !important;
}

.stTextArea textarea {
    min-height: 120px;
    line-height: 1.6;
    color: var(--text-main) !important;
}

div[data-testid="stForm"] {
    background: rgba(255,255,255,0.52);
    border: 1px solid rgba(169, 215, 255, 0.7);
    border-radius: 28px;
    padding: 1rem 1rem 0.3rem 1rem;
    box-shadow: var(--shadow);
}

.stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {
    border-radius: 999px !important;
    border: none !important;
    min-height: 3rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #5cbcff, #2b89ff) !important;
    color: white !important;
    box-shadow: 0 14px 30px rgba(43, 137, 255, 0.24) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px);
    filter: brightness(1.02);
}

div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.64);
    border: 1px solid rgba(169, 215, 255, 0.7);
    border-radius: 22px;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 20px;
    border: 1px solid rgba(169, 215, 255, 0.7);
}

.sky-tip {
    padding: 0.9rem 1rem;
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.84), rgba(236,247,255,0.84));
    border: 1px solid rgba(176, 221, 255, 0.75);
    color: #416783;
    line-height: 1.7;
}

@media (max-width: 800px) {
    .sky-grid {
        grid-template-columns: 1fr;
    }
    .sky-title {
        font-size: 1.6rem;
    }
    .sky-hero {
        padding: 1.45rem 1.1rem 1.1rem 1.1rem;
    }
}
</style>
"""

def inject_sky_theme():
    st.markdown(SKY_CSS, unsafe_allow_html=True)

def get_profile_preview(selected_info: dict, limit: int = 3) -> list[tuple[str, str]]:
    preview = []
    for key, value in selected_info.items():
        key_str = str(key).strip()
        if not key_str or key_str.lower() == "id" or key in REFLECTION_KEYS:
            continue
        value_str = str(value).strip()
        if not value_str:
            continue
        preview.append((key_str, value_str))
        if len(preview) >= limit:
            break
    return preview

def render_hero(selected_id: str, selected_info: dict) -> None:
    preview = get_profile_preview(selected_info, 3)
    cards_html = "".join(
        f"""
        <div class="sky-mini-card">
            <div class="sky-mini-label">{escape_html(label)}</div>
            <div class="sky-mini-value">{escape_html(value)}</div>
        </div>
        """
        for label, value in preview
    )
    if not cards_html:
        cards_html = """
        <div class="sky-mini-card">
            <div class="sky-mini-label">Student ID</div>
            <div class="sky-mini-value">พร้อมเริ่มวิเคราะห์</div>
        </div>
        """
    st.markdown(
        f"""
        <div class="sky-hero">
            <div class="sky-badge">☁️ Sky Theme • Premium UI</div>
            <div class="sky-title">{escape_html(APP_TITLE)}</div>
            <div class="sky-subtitle">
                เครื่องมือสร้าง Roadmap รายบุคคลในโทนฟ้า-ขาวแบบท้องฟ้า
                ช่วยให้หน้าจออ่านง่าย สบายตา และดูน่าใช้งานมากขึ้นสำหรับพี่ค่ายและผู้กรอกข้อมูล
            </div>
            <div class="sky-grid">
                <div class="sky-mini-card">
                    <div class="sky-mini-label">รหัสนักเรียน</div>
                    <div class="sky-mini-value">{escape_html(selected_id)}</div>
                </div>
                {cards_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


APP_TITLE = "🌟 Zenith-FindYourDream"
APP_SUBTITLE = "เครื่องมือประมวลผลสร้าง Roadmap รายบุคคล"

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

FONT_CANDIDATES = [
    "NotoSansThai.ttf",
    "assets/NotoSansThai.ttf",
    "/mount/src/NotoSansThai.ttf",
    "/mount/src/app/NotoSansThai.ttf",
]


# =========================================================
# CONFIG
# =========================================================
def get_config(key: str, default: Any = None) -> Any:
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)


def require_config(key: str, default: Any = None) -> Any:
    value = get_config(key, default)
    if value in (None, ""):
        st.error(f"⚠️ ไม่พบ {key} กรุณาใส่ค่าใน Streamlit secrets หรือ environment variables")
        st.stop()
    return value


MODEL_NAME = get_config("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_KEY = require_config("GEMINI_API_KEY")
GOOGLE_SHEET_KEY = require_config("GOOGLE_SHEET_KEY")
GOOGLE_SHEET_WORKSHEET = get_config("GOOGLE_SHEET_WORKSHEET", "data")
SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_KEY")
SUPABASE_BUCKET = get_config("SUPABASE_BUCKET", "zenith-pdfs")
SUPABASE_PUBLIC_BUCKET = str(get_config("SUPABASE_PUBLIC_BUCKET", "false")).lower() == "true"


def ensure_service_account_file() -> str:
    if "gcp_service_account" in st.secrets:
        temp_path = "/tmp/gcp_service_account.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f, ensure_ascii=False)
        return temp_path

    service_account_json = get_config("SERVICE_ACCOUNT_JSON")
    if service_account_json:
        temp_path = "/tmp/gcp_service_account_env.json"
        data = json.loads(service_account_json)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return temp_path

    service_account_file = get_config("SERVICE_ACCOUNT_FILE")
    if service_account_file and Path(service_account_file).exists():
        return str(service_account_file)

    raise FileNotFoundError(
        "ไม่พบ service account กรุณาเพิ่ม [gcp_service_account] ใน Streamlit secrets หรือกำหนด SERVICE_ACCOUNT_JSON / SERVICE_ACCOUNT_FILE"
    )


# =========================================================
# UTILITIES
# =========================================================
def safe_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def escape_html(text: str | None) -> str:
    return html.escape("" if text is None else str(text))


def sanitize_pdf_text(text: str | None) -> str:
    if text is None:
        return "-"
    sanitized = str(text)
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\r\n": "\n",
    }
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)
    return sanitized


def format_score(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def get_prepost_value(selected_info: dict, candidates: list[str]) -> float | None:
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


def build_default_form_answers() -> dict:
    return {key: "" for key in QUESTION_MAP}


# =========================================================
# MODEL
# =========================================================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# =========================================================
# DATA
# =========================================================
def get_google_credentials() -> Credentials:
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    service_account_path = ensure_service_account_file()
    return Credentials.from_service_account_file(service_account_path, scopes=scopes)


@st.cache_resource
def get_gspread_client():
    creds = get_google_credentials()
    return gspread.authorize(creds)


@st.cache_data(ttl=60)
def load_sheet_data() -> list[dict]:
    gc = get_gspread_client()
    sh = gc.open_by_key(str(GOOGLE_SHEET_KEY))
    available_worksheets = [ws.title for ws in sh.worksheets()]
    if GOOGLE_SHEET_WORKSHEET not in available_worksheets:
        raise ValueError(
            f"ไม่พบ worksheet ชื่อ '{GOOGLE_SHEET_WORKSHEET}' | มีอยู่จริง: {available_worksheets}"
        )
    worksheet = sh.worksheet(str(GOOGLE_SHEET_WORKSHEET))
    return worksheet.get_all_records()


def get_student_display_options(sheet_data: list[dict]) -> list[str]:
    return [str(row.get("ID", "")).strip() for row in sheet_data if str(row.get("ID", "")).strip()]


def get_selected_student(sheet_data: list[dict], selected_id: str) -> dict | None:
    return next((row for row in sheet_data if str(row.get("ID", "")).strip() == selected_id), None)


# =========================================================
# SUPABASE (OPTIONAL)
# =========================================================
@st.cache_resource
def get_supabase_client() -> Client | None:
    if not (create_client and SUPABASE_URL and SUPABASE_KEY):
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_pdf_to_supabase(file_bytes: bytes, filename: str, student_id: str) -> dict | None:
    supabase = get_supabase_client()
    if supabase is None:
        return None

    timestamp = int(time.time())
    file_path = f"exports/{student_id}/{timestamp}-{filename}"
    supabase.storage.from_(str(SUPABASE_BUCKET)).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    public_url = ""
    if SUPABASE_PUBLIC_BUCKET:
        public_url = supabase.storage.from_(str(SUPABASE_BUCKET)).get_public_url(file_path)

    return {"path": file_path, "public_url": public_url}


# =========================================================
# PDF
# =========================================================
def get_font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "ไม่พบไฟล์ NotoSansThai.ttf กรุณาวางไฟล์ไว้ในโฟลเดอร์เดียวกับ streamlit_app.py หรือ assets/NotoSansThai.ttf"
    )


def register_thai_font() -> None:
    font_path = get_font_path()
    if "ThaiFont" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ThaiFont", font_path))


def create_pdf_bytes(user_id: str, profile: dict | None, answers: dict, analysis_result: str) -> tuple[bytes, str]:
    register_thai_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

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

    content.append(Paragraph("ข้อมูลจากระบบ", header_style))
    if profile:
        for key, value in profile.items():
            if str(key).strip().lower() == "id":
                continue
            if key in REFLECTION_KEYS:
                continue
            line = f"<b>{sanitize_pdf_text(str(key))}:</b> {sanitize_pdf_text(str(value))}"
            content.append(Paragraph(line, normal_style))
    else:
        content.append(Paragraph("ไม่พบข้อมูลจากระบบ", normal_style))

    content.append(Spacer(1, 8))
    content.append(Paragraph("คำตอบของนักเรียน", header_style))
    for key, label in QUESTION_MAP.items():
        answer = sanitize_pdf_text(answers.get(key, "-"))
        content.append(Paragraph(f"<b>{sanitize_pdf_text(label)}</b>", normal_style))
        content.append(Paragraph(answer if answer.strip() else "-", normal_style))

    content.append(Spacer(1, 8))
    content.append(Paragraph("ผลการวิเคราะห์จาก AI", header_style))
    if analysis_result.strip():
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
# PROMPTS
# =========================================================
def build_context_text(selected_info: dict) -> str:
    core_lines = []
    for key, value in selected_info.items():
        if str(key).strip().lower() == "id":
            continue
        if key in REFLECTION_KEYS:
            continue
        core_lines.append(f"{key}: {value}")

    reflection_lines = []
    for key in REFLECTION_KEYS:
        text = str(selected_info.get(key, "")).strip()
        if text:
            reflection_lines.append(f"- {key}: {text}")

    prepost_rows = get_prepost_scores(selected_info)
    prepost_lines = []
    for row in prepost_rows:
        if row["pre"] is None and row["post"] is None:
            continue
        delta_text = "-" if row["delta"] is None else f"{row['delta']:+.1f}"
        prepost_lines.append(
            f"- {row['label_th']}: Pre-test {format_score(row['pre'])}, Post-test {format_score(row['post'])}, ผลต่าง {delta_text}"
        )

    blocks = ["ข้อมูลจากระบบ:\n" + "\n".join(core_lines) if core_lines else ""]
    if reflection_lines:
        blocks.append("Reflection:\n" + "\n".join(reflection_lines))
    if prepost_lines:
        blocks.append("คะแนน Pre-test / Post-test:\n" + "\n".join(prepost_lines))
    return "\n\n".join([b for b in blocks if b]).strip()


def build_answers_text(answers: dict) -> str:
    lines = []
    for key, label in QUESTION_MAP.items():
        lines.append(f"{label}\n{answers.get(key, '').strip() or '-'}")
    return "\n\n".join(lines)


def build_analysis_prompt(context: str, answers: dict) -> str:
    answers_text = build_answers_text(answers)
    return f"""
คุณคือผู้เชี่ยวชาญด้านการศึกษา การค้นหาตัวตน การวางแผนการเตรียมตัวเรียนต่อมหาวิทยาลัย และการแนะแนวอาชีพสำหรับนักเรียนมัธยมปลาย

ข้อมูลจากระบบ:
{context}

คำตอบของนักเรียน:
{answers_text}

หลักการตอบ:
- วิเคราะห์จากข้อมูลในระบบและคำตอบของนักเรียนร่วมกัน
- หากข้อมูลบางส่วนยังไม่ชัด ให้ระบุว่าเป็นแนวโน้ม ไม่สรุปเกินจริง
- ใช้ภาษาไทยสุภาพ ชัดเจน อบอุ่น และนำไปใช้ได้จริง
- เน้นคำแนะนำเชิงปฏิบัติ ไม่กว้างเกินไป
- ตอบเป็นภาษาไทยทั้งหมด

โปรดตอบในหัวข้อดังนี้:
1. ภาพรวมตัวตนและความสนใจ
2. วิเคราะห์ความถนัดและจุดที่ควรพัฒนา
3. แนวทางคณะ / สาขา / อาชีพที่เหมาะ 3-5 ตัวเลือก พร้อมเหตุผล
4. Roadmap การพัฒนา
   - ระยะสั้น (0-3 เดือน)
   - ระยะกลาง (6-12 เดือน)
   - ระยะยาว (การเตรียมตัวเข้ามหาวิทยาลัย)
5. ทักษะที่ควรพัฒนา
   - hard skills
   - soft skills
   - วิธีฝึกที่ทำได้จริง
6. คำแนะนำในการเตรียมสอบและทำพอร์ต
7. ข้อความส่งท้ายให้กำลังใจ
""".strip()


def run_analysis(selected_info: dict, answers: dict) -> str:
    prompt = build_analysis_prompt(build_context_text(selected_info), answers)
    response = model.generate_content(prompt)
    return response.text if getattr(response, "text", None) else "AI ไม่ตอบ"


# =========================================================
# SESSION STATE
# =========================================================
def init_session_state() -> None:
    defaults = {
        "analysis_result": "",
        "latest_pdf_bytes": None,
        "latest_pdf_name": "",
        "latest_storage_path": "",
        "latest_public_url": "",
        "last_selected_id": None,
        "form_answers": build_default_form_answers(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_current_student_state() -> None:
    st.session_state.analysis_result = ""
    st.session_state.latest_pdf_bytes = None
    st.session_state.latest_pdf_name = ""
    st.session_state.latest_storage_path = ""
    st.session_state.latest_public_url = ""
    st.session_state.form_answers = build_default_form_answers()


init_session_state()


# =========================================================
# UI
# =========================================================
inject_sky_theme()

st.markdown(
    """
    <div class="section-shell">
        <div class="section-heading">🌤️ วิธีใช้งานระบบ</div>
        <div class="section-copy">
            เลือกรหัสนักเรียน กรอกคำตอบของน้องให้ได้ข้อมูลเชิงลึกมากที่สุด
            จากนั้นกดสร้าง Roadmap เพื่อให้ AI สรุปภาพรวม จุดแข็ง แนวทางคณะ และแผนพัฒนารายบุคคล
        </div>
        <div class="sky-tip">
            1) เลือก ID นักเรียน<br>
            2) ชวนให้น้องสะท้อนตัวเองจากคำถามหลักและคำถามเสริม<br>
            3) กด <b>สร้าง Roadmap</b> เพื่อประมวลผล<br>
            4) ดาวน์โหลด PDF หรือเปิดดูผลวิเคราะห์ล่าสุดได้ทันที<br><br>
            หากระบบช้า ให้ refresh แล้วลองใหม่อีกครั้งหลังเว้นช่วงสั้น ๆ
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    sheet_data = load_sheet_data()
except Exception as exc:
    st.error(f"โหลดข้อมูลจาก Google Sheets ไม่สำเร็จ: {type(exc).__name__}: {exc}")
    st.stop()

if not sheet_data:
    st.warning("ยังไม่พบข้อมูลนักเรียนจาก Google Sheets")
    st.stop()

display_options = get_student_display_options(sheet_data)

st.markdown('<div class="section-shell">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">🫧 เลือกข้อมูลนักเรียน</div>', unsafe_allow_html=True)
st.markdown('<div class="section-copy">เลือก ID เพื่อโหลดข้อมูลพื้นฐานของน้องก่อนเริ่มวิเคราะห์</div>', unsafe_allow_html=True)
selected_id = st.selectbox("เลือก ID นักเรียน", display_options)
selected_info = get_selected_student(sheet_data, selected_id)
st.markdown('</div>', unsafe_allow_html=True)

if selected_info is None:
    st.error("ไม่พบข้อมูลของนักเรียนที่เลือก")
    st.stop()

if st.session_state.last_selected_id != selected_id:
    st.session_state.last_selected_id = selected_id
    reset_current_student_state()

render_hero(selected_id, selected_info)

st.markdown('<div class="section-shell">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">✍️ แบบฟอร์มสะท้อนตัวตน</div>', unsafe_allow_html=True)
st.markdown('<div class="section-copy">ตอบอย่างน้อย 3 ข้อเพื่อให้ผลวิเคราะห์มีคุณภาพมากขึ้น และยิ่งละเอียด AI จะยิ่งแนะนำได้แม่นขึ้น</div>', unsafe_allow_html=True)

with st.form("roadmap_form"):
    q1 = st.text_area(QUESTION_MAP["q1"], value=st.session_state.form_answers.get("q1", ""), height=115, placeholder="เช่น สนใจชีววิทยา งานอาสา การดูแลคน หรือชอบเรียนรู้เรื่องสุขภาพ")
    q2 = st.text_area(QUESTION_MAP["q2"], value=st.session_state.form_answers.get("q2", ""), height=115, placeholder="อธิบายวิชาที่ถนัด พร้อมเหตุผลหรือประสบการณ์ที่ทำให้รู้สึกว่าไปได้ดี")
    q3 = st.text_area(QUESTION_MAP["q3"], value=st.session_state.form_answers.get("q3", ""), height=115, placeholder="มีคณะ อาชีพ หรือเส้นทางที่แอบสนใจอยู่แล้วหรือยัง")
    q4 = st.text_area(QUESTION_MAP["q4"], value=st.session_state.form_answers.get("q4", ""), height=115, placeholder="เล่ากิจกรรมที่สะท้อนตัวตน เช่น ค่าย แข่งขัน จิตอาสา ชมรม หรือโปรเจกต์ต่าง ๆ")
    q5 = st.text_area(QUESTION_MAP["q5"], value=st.session_state.form_answers.get("q5", ""), height=115, placeholder="เล่าทั้งจุดแข็งและจุดที่อยากพัฒนา เพื่อให้ roadmap ออกมาชัดขึ้น")
    q6 = st.text_area(QUESTION_MAP["q6"], value=st.session_state.form_answers.get("q6", ""), height=115, placeholder="บอกความฝัน เป้าหมาย หรือภาพอนาคตที่อยากเห็นตัวเองไปถึง")
    submitted = st.form_submit_button("☁️ สร้าง Roadmap")

st.markdown('</div>', unsafe_allow_html=True)

if submitted:
    answers = {
        "q1": q1.strip(),
        "q2": q2.strip(),
        "q3": q3.strip(),
        "q4": q4.strip(),
        "q5": q5.strip(),
        "q6": q6.strip(),
    }
    st.session_state.form_answers = answers

    answered_count = sum(1 for value in answers.values() if value.strip())
    if answered_count < 3:
        st.warning("กรุณาตอบอย่างน้อย 3 ข้อ เพื่อให้ AI วิเคราะห์ได้มีคุณภาพมากขึ้น")
    else:
        with st.spinner("กำลังประมวลผล AI และสร้าง PDF..."):
            try:
                ai_text = run_analysis(selected_info, answers)
                pdf_bytes, pdf_name = create_pdf_bytes(
                    user_id=selected_id,
                    profile=selected_info,
                    answers=answers,
                    analysis_result=ai_text,
                )

                st.session_state.analysis_result = ai_text
                st.session_state.latest_pdf_bytes = pdf_bytes
                st.session_state.latest_pdf_name = pdf_name
                st.session_state.latest_storage_path = ""
                st.session_state.latest_public_url = ""

                try:
                    upload_result = upload_pdf_to_supabase(pdf_bytes, pdf_name, selected_id)
                    if upload_result:
                        st.session_state.latest_storage_path = upload_result.get("path", "")
                        st.session_state.latest_public_url = upload_result.get("public_url", "")
                except Exception as upload_exc:
                    st.warning(
                        "สร้าง PDF สำเร็จ แต่ upload ไป Supabase ไม่สำเร็จ: "
                        f"{type(upload_exc).__name__}: {upload_exc}"
                    )

                st.success("ประมวลผลเสร็จแล้ว")
            except ResourceExhausted:
                st.warning("ขณะนี้มีผู้ใช้งานจำนวนมาก กรุณารอสักครู่แล้วลองใหม่อีกครั้ง")
            except FileNotFoundError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"เกิดข้อผิดพลาดระหว่างการประมวลผล: {type(exc).__name__}: {exc}")

st.markdown('<div class="section-shell">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">📦 ผลลัพธ์และไฟล์</div>', unsafe_allow_html=True)
st.markdown('<div class="section-copy">หลังประมวลผลเสร็จ สามารถดาวน์โหลด PDF หรือเปิดไฟล์ที่เก็บบน Supabase ได้จากส่วนนี้</div>', unsafe_allow_html=True)

if st.session_state.latest_pdf_bytes and st.session_state.latest_pdf_name:
    st.download_button(
        "📄 ดาวน์โหลด PDF Roadmap",
        data=st.session_state.latest_pdf_bytes,
        file_name=st.session_state.latest_pdf_name,
        mime="application/pdf",
        use_container_width=True,
    )

if st.session_state.latest_storage_path:
    st.caption(f"Supabase path: {st.session_state.latest_storage_path}")
if st.session_state.latest_public_url:
    st.link_button("🔗 เปิดไฟล์จาก Supabase", st.session_state.latest_public_url)

with st.expander("🔎 ดูผลวิเคราะห์ล่าสุด"):
    st.write(st.session_state.analysis_result or "ยังไม่มีผลวิเคราะห์")

st.markdown('</div>', unsafe_allow_html=True)

if st.button("🧹 ล้างข้อมูลทั้งหมด", use_container_width=True):
    reset_current_student_state()
    st.rerun()
