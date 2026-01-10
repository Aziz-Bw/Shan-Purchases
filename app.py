import streamlit as st
import pandas as pd
from datetime import date

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="موازنة المشتريات | Shan Budget", layout="wide", page_icon="📦")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    /* كروت المؤشرات */
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 14px; color: #666; font-weight: bold; margin-bottom: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #034275; }
    
    /* تنبيهات الحالة */
    .status-ok { color: #27ae60; font-weight: bold; }
    .status-warning { color: #f39c12; font-weight: bold; }
    .status-danger { color: #c0392b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. إدارة البيانات (Load/Save) ---
if 'df_budget' not in st.session_state:
    # الهيكل الافتراضي للجدول (زي الإكسل)
    data = {
        "اسم الطلبية/المورد": ["طلبية الصين - قطع غيار", "مورد محلي - زيوت"],
        "قيمة الطلبية (عملة)": [50000.0, 15000.0],
        "سعر الصرف": [3.75, 1.0],
        "إجمالي القيمة (ريال)": [187500.0, 15000.0],
        "المدفوع (ريال)": [50000.0, 15000.0],
        "المتبقي (ريال)": [137500.0, 0.0],
        "حالة السداد": ["جاري السداد", "مدفوع بالكامل"],
        "تاريخ الوصول المتوقع": [date(2026, 2, 15), date(2026, 1, 20)],
        "حالة الشحنة": ["في البحر", "تم الاستلام"],
        "ملاحظات": ["دفعة أولى 30%", ""]
    }
    st.session_state.df_budget = pd.DataFrame(data)

# --- 3. القائمة الجانبية (للحفظ والاسترجاع) ---
with st.sidebar:
    st.header("💾 إدارة الملفات")
    st.info("بما أن هذا النظام يدوي، يرجى حفظ الملف بعد كل تعديل.")
    
    # تحميل ملف سابق
    uploaded_file = st.file_uploader("📂 فتح ملف موازنة سابق (CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            loaded_df = pd.read_csv(uploaded_file)
            # تحويل التواريخ لتظهر بشكل صحيح
            if 'تاريخ الوصول المتوقع' in loaded_df.columns:
                loaded_df['تاريخ الوصول المتوقع'] = pd.to_datetime(loaded_df['تاريخ الوصول المتوقع']).dt.date
            st.session_state.df_budget = loaded_df
            st.success("تم تحميل البيانات بنجاح!")
        except:
            st.error("فشل تحميل الملف.")

    st.markdown("---")
    
    # زر الحفظ
    csv = st.session_state.df_budget.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="💾 حفظ التعديلات (تحميل CSV)",
        data=csv,
        file_name=f"Shan_Budget_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime='text/csv',
    )

# --- 4. الصفحة الرئيسية ---
st.title("📦 موازنة المشتريات ومتابعة الاستيراد")

# --- أ. التعديل المباشر (الإكسل) ---
st.subheader("📝 سجل الطلبيات (قابل للتعديل)")

# إعدادات الجدول القابل للتعديل
edited_df = st.data_editor(
    st.session_state.df_budget,
    num_rows="dynamic", # يسمح بإضافة صفوف جديدة
    use_container_width=True,
    column_config={
        "قيمة الطلبية (عملة)": st.column_config.NumberColumn(format="%.2f"),
        "سعر الصرف": st.column_config.NumberColumn(format="%.2f", help="3.75 للدولار"),
        "إجمالي القيمة (ريال)": st.column_config.NumberColumn(format="%.2f", disabled=True), # ممنوع التعديل (محسوب)
        "المدفوع (ريال)": st.column_config.NumberColumn(format="%.2f"),
        "المتبقي (ريال)": st.column_config.NumberColumn(format="%.2f", disabled=True), # ممنوع التعديل (محسوب)
        "حالة السداد": st.column_config.SelectboxColumn(options=["مدفوع بالكامل", "جاري السداد", "لم يبدأ", "متأخر"]),
        "حالة الشحنة": st.column_config.SelectboxColumn(options=["تحت التجهيز", "في البحر", "تخليص جمركي", "تم الاستلام", "ملغي"]),
        "تاريخ الوصول المتوقع": st.column_config.DateColumn(format="DD/MM/YYYY"),
    },
    key="editor"
)

# --- ب. المنطق الحسابي (تحديث البيانات بناء على التعديل) ---
# نقوم بحساب الأعمدة المشتقة تلقائياً
if edited_df is not None:
    # 1. حساب الإجمالي بالريال (القيمة * الصرف)
    edited_df['إجمالي القيمة (ريال)'] = edited_df['قيمة الطلبية (عملة)'] * edited_df['سعر الصرف']
    
    # 2. حساب المتبقي (الإجمالي - المدفوع)
    edited_df['المتبقي (ريال)'] = edited_df['إجمالي القيمة (ريال)'] - edited_df['المدفوع (ريال)']
    
    # 3. تحديث حالة السداد تلقائياً (اختياري، أو يترك يدوي)
    # هنا نتركها يدوية كما في الإكسل، لكن نحدث المتبقي
    
    # حفظ التغييرات في الجلسة
    st.session_state.df_budget = edited_df

# --- ج. كروت التحليل (KPIs) ---
st.divider()
st.subheader("📊 ملخص الموقف المالي")

total_commitment = edited_df['إجمالي القيمة (ريال)'].sum()
total_paid = edited_df['المدفوع (ريال)'].sum()
total_remaining = edited_df['المتبقي (ريال)'].sum()
payment_progress = (total_paid / total_commitment * 100) if total_commitment > 0 else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f'<div class="metric-box"><div class="metric-title">إجمالي الالتزامات (ريال)</div><div class="metric-value">{total_commitment:,.0f}</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown(f'<div class="metric-box"><div class="metric-title">تم سداده (ريال)</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div></div>', unsafe_allow_html=True)

with c3:
    st.markdown(f'<div class="metric-box"><div class="metric-title">المتبقي للسداد (ريال)</div><div class="metric-value" style="color:#c0392b">{total_remaining:,.0f}</div></div>', unsafe_allow_html=True)

with c4:
    st.markdown(f'<div class="metric-box"><div class="metric-title">نسبة الإنجاز المالي</div><div class="metric-value">{payment_progress:.1f}%</div></div>', unsafe_allow_html=True)

# --- د. تنبيهات الوصول ---
st.divider()
c_alert1, c_alert2 = st.columns(2)

with c_alert1:
    st.subheader("🚢 شحنات في الطريق")
    incoming = edited_df[edited_df['حالة الشحنة'].isin(["في البحر", "تخليص جمركي", "تحت التجهيز"])]
    if not incoming.empty:
        st.dataframe(incoming[['اسم الطلبية/المورد', 'حالة الشحنة', 'تاريخ الوصول المتوقع']], use_container_width=True)
    else:
        st.info("لا توجد شحنات قادمة حالياً.")

with c_alert2:
    st.subheader("💰 دفعات مستحقة الانتباه")
    # الدفعات التي لم تكتمل
    unpaid = edited_df[(edited_df['المتبقي (ريال)'] > 0) & (edited_df['حالة السداد'] != "ملغي")]
    if not unpaid.empty:
        st.dataframe(unpaid[['اسم الطلبية/المورد', 'المتبقي (ريال)', 'حالة السداد']], use_container_width=True)
    else:
        st.success("جميع الطلبيات مدفوعة بالكامل.")
