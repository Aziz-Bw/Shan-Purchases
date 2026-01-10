import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. إعدادات الصفحة ---
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
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("☁️ موازنة المشتريات ومتابعة الاستيراد")
st.caption("يتم حفظ البيانات وتزامنها تلقائياً مع Google Drive")

# --- 3. قراءة البيانات ---
try:
    existing_data = conn.read(worksheet="Sheet1", ttl=0)
    existing_data = existing_data.dropna(how="all")
    
    # التأكد من الأعمدة
    required_columns = [
        "اسم الطلبية/المورد", "قيمة الطلبية (عملة)", "سعر الصرف", 
        "المدفوع (ريال)", "حالة السداد", "حالة الشحنة", "تاريخ الوصول", "ملاحظات"
    ]
    
    for col in required_columns:
        if col not in existing_data.columns:
            existing_data[col] = None

except Exception as e:
    st.warning("جاري تهيئة ملف البيانات لأول مرة...")
    existing_data = pd.DataFrame(columns=[
        "اسم الطلبية/المورد", "قيمة الطلبية (عملة)", "سعر الصرف", 
        "المدفوع (ريال)", "حالة السداد", "حالة الشحنة", "تاريخ الوصول", "ملاحظات"
    ])

# --- 4. منطقة العمل (الجدول التفاعلي) ---
st.subheader("📝 سجل الطلبيات (تعديل مباشر)")

edited_df = st.data_editor(
    existing_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "اسم الطلبية/المورد": st.column_config.TextColumn(width="medium"),
        "قيمة الطلبية (عملة)": st.column_config.NumberColumn(format="%.2f", min_value=0),
        "سعر الصرف": st.column_config.NumberColumn(format="%.2f", default=3.75),
        "المدفوع (ريال)": st.column_config.NumberColumn(format="%.2f", min_value=0),
        "حالة السداد": st.column_config.SelectboxColumn(
            options=["مدفوع بالكامل", "جاري السداد", "لم يبدأ", "متأخر"],
            required=True
        ),
        "حالة الشحنة": st.column_config.SelectboxColumn(
            options=["تحت التجهيز", "في البحر", "تخليص جمركي", "تم الاستلام", "في المستودع", "ملغي"]
        ),
        "تاريخ الوصول": st.column_config.DateColumn(format="DD/MM/YYYY"),
        "ملاحظات": st.column_config.TextColumn(width="large"),
    },
    key="editor"
)

# --- 5. الحسابات والذكاء ---
# تحويل الأرقام لضمان عدم حدوث أخطاء
cols_to_numeric = ['قيمة الطلبية (عملة)', 'سعر الصرف', 'المدفوع (ريال)']
for col in cols_to_numeric:
    edited_df[col] = pd.to_numeric(edited_df[col], errors='coerce').fillna(0)

# إجراء الحسابات
edited_df['الإجمالي (ريال)'] = edited_df['قيمة الطلبية (عملة)'] * edited_df['سعر الصرف']
edited_df['المتبقي (ريال)'] = edited_df['الإجمالي (ريال)'] - edited_df['المدفوع (ريال)']

# تجميع الأرقام
total_liability = edited_df['الإجمالي (ريال)'].sum()
total_paid = edited_df['المدفوع (ريال)'].sum()
total_remaining = edited_df['المتبقي (ريال)'].sum()
incoming_shipments = len(edited_df[edited_df['حالة الشحنة'].isin(["في البحر", "تخليص جمركي"])])

# --- 6. لوحة المعلومات (KPIs) ---
st.divider()
st.subheader("📊 ملخص الموقف المالي الحالي")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f'<div class="metric-box"><div class="metric-title">إجمالي الالتزامات</div><div class="metric-value">{total_liability:,.0f}</div><div class="metric-sub">قيمة البضاعة بالريال</div></div>', unsafe_allow_html=True)

with k2:
    st.markdown(f'<div class="metric-box"><div class="metric-title">تم سداده</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div><div class="metric-sub">كاش خرج فعلياً</div></div>', unsafe_allow_html=True)

with k3:
    st.markdown(f'<div class="metric-box"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_remaining:,.0f}</div><div class="metric-sub">التزام قائم</div></div>', unsafe_allow_html=True)

with k4:
    st.markdown(f'<div class="metric-box"><div class="metric-title">شحنات في الطريق</div><div class="metric-value">{incoming_shipments}</div><div class="metric-sub">بحر / جمارك</div></div>', unsafe_allow_html=True)

# --- 7. زر الحفظ السحابي ---
st.divider()
st.markdown("### 💾 حفظ العمل")

if st.button("تحديث البيانات في Google Drive"):
    try:
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("✅ تم الحفظ بنجاح! البيانات الآن آمنة في جوجل درايف.")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"حدث خطأ أثناء الحفظ: {e}")
