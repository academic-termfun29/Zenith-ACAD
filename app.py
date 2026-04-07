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
  client = gspread.authorize(creds)
  sheet = client.open("ACAD - Student Databse").sheet1
  return sheet
  def get_user_data(sheet, user_id):
    records = sheet.get_all_records()
    for record in record:
      if str(record['student_id']) == str(user_id):
        return record
    return None 
