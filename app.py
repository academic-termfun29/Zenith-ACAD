import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
def connect_sheet():
  creds = Credentials.from_service_account_file(
    'servie_account.json',
    scopes=['https://spreadsheets.google.com/feeds',
            'https://googleapis.com/auth/drive']
  )
  return gspred.authorize
  
def get_user_data(sheet, user_id):
  sheet1 = client.open(ACAD - Student Databse).worksheet("Student ID")
  records = sheet.get_all_records()
  for record in record:
  if str(record['student_id']) == str(user_id):
     return record
  return None

def get_exam_question(client):
  sheet2 = client.open(ACAD - Student Databse).worksheet("pre_score")
  return sheet2.get_all_records()

genai.configure(api_key=st.secrets["AIzaSyAuSBuHOzQAdRZxVZ2meF0ioqj3OUMOSto"])
model = genai.GenerativeModel('gemini-pro')

def generate_feedback(user_data, exam_data):
  analysis_data = []
for exam in exam_data:
  q_no = exam['question_no']
  analysis_data.append({
    "ข้อ": q_no
    "หมวด": exam['skill_category'],
    "ได้คะแนน": user_data.get(f'q{q_no}','N/A')
  }]
  prompt = f"""
  นักเรียน: {user_data['name']}

  คะแนนรายข้อและหมวดหมู่:
  {analysis_data}

  วิเคราะห์:
    1. สรุปคะแนนแต่ละหมวด (skill_category)
    2. จุดแข็งและจุดอ่อน
    3. ข้อแนะนำในการพัฒนาทักษะในแต่ละวิชา
    4. การเลือกเส้นทางการศึกษาและการประกอบอาชีพในอนาคต

    response = model.generate_content(prompt)
    return respone.text

st.title("ระบุข้อมูลเฉพาะบุคคล")

user_id = st.text_input("กรอกรหัสประจำตัว")

if st.button("ค้นหา"):
if user_id:
client = connect_client()
user_data = get_user_data(client, user_id)
exam_data = get_exam_questions(client)

if user_data:
st.success(f"ยินดีต้อนรับ {user_data['name']}")
with st.spinner("กำลังออกแบบแนวทางในอนาคต..."):
  feedback = generate_feedback(user_data, exam_data)
  st.write(feedback)
else:
  st.error("ไม่พบ ID นี้")
else:
  st.warning("กรุณากรอกรหัสประจำตัว")
    
