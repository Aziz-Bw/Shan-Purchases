import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(page_title="موازنة المشتريات (سحابي)", layout="wide", page_icon="☁️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 14px; color: #666; font-weight: bold; margin-bottom: 8px; }
    .metric-value { font-size: 26px; font-weight: bold; color: #034275; }
    .metric-sub { font-size: 12px; color: #27ae60; margin-top: 5px; }
    
    /* زر الحفظ */
    div.stButton > button:first-child {
        background-color: #034275;
        color: white;
        font-size: 18px;
        padding: 10px 24px;
        border-radius: 8px;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #022c4f;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. الاتصال بجوجل شيت ---
# هذا السطر السحري يقرأ المعلومات من Secrets تلقائياً
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("☁️ موازنة المشتريات ومتابعة الاستيراد")
st.caption("يتم حفظ البيانات وتزامنها تلقائياً مع Google Drive")

# --- 3. قراءة البيانات ---
try:
    # قراءة البيانات (ttl=0 يعني لا تحفظ نسخة مؤقتة، هات الجديد دائماً)
    existing_data = conn.read(worksheet="Sheet1", ttl=0)
    existing_data = existing_data.dropna(how="all") # حذف الصفوف الفارغة تماماً
    
    # التأكد من وجود الأعمدة المطلوبة (في حال كان الملف جديداً)
    required_columns = [
        "اسم الطلبية/المورد", "قيمة الطلبية (عملة)", "سعر الصرف", 
        "المدفوع (ريال)", "حالة السداد", "حالة الشحنة", "تاريخ الوصول", "ملاحظات"
    ]
    
    # إضافة الأعمدة الناقصة إن وجدت
    for col in required_columns:
        if col not in existing_data.columns:
            existing_data[col] = None

except Exception as e:
    # في حال كان الملف جديداً تماماً أو فارغاً
    st.warning("جاري تهيئة ملف البيانات لأول مرة...")
    existing_data = pd.DataFrame(columns=[
        "اسم الطلبية/المورد", "قيمة الطلبية (عملة)", "سعر الصرف", 
        "المدفوع (ريال)", "حالة السداد", "حالة الشحنة", "تاريخ الوصول", "ملاحظات"
    ])

# --- 4. منطقة العمل (الجدول التفاعلي) ---
st.subheader("📝 سجل الطلبيات (تعديل مباشر)")

edited_df = st.data_editor(
    existing_data,
    num_rows="dynamic", # يسمح بإضافة صفوف
    use_container_width=True,
    column_config={
        "اسم الطلبية/المورد": st.column_config.TextColumn(width="medium"),
        "قيمة الطلبية (عملة)": st
