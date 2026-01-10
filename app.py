import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="نظام إدارة المشتريات", layout="wide", page_icon="📦")

# تنسيق CSS احترافي
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    .metric-card {
        background-color: #fff; border: 1px solid #eee; padding: 15px; 
        border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 14px; color: #666; margin-bottom: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #034275; }
    
    /* تحسين شكل النماذج */
    .stTextInput > div > div > input { text-align: right; }
    .stNumberInput > div > div > input { text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. الاتصال بجوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

# تحميل البيانات (مع التعامل مع الملفات الفارغة)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(how="all")
        # ضمان وجود الأعمدة الأساسية
        required_cols = ["ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات"]
        for col in required_cols:
            if col not in df.columns: df[col] = None
        
        # تحويل الأرقام
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame(columns=["ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات"])

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("📦 نظام إدارة المشتريات والاستيراد")

# تقسيم الشاشة: قائمة جانبية للإضافة، ووسط للعرض
with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية / الصنف")
        supplier = st.text_input("اسم المورد")
        
        c1, c2 = st.columns(2)
        val_usd = c1.number_input("قيمة الفاتورة ($)", min_value=0.0, step=100.0)
        rate = c2.number_input("سعر الصرف", value=3.75, step=0.01)
        
        arrival_date = st.date_input("تاريخ الوصول المتوقع")
        status = st.selectbox("حالة الشحنة", ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"])
        notes = st.text_area("ملاحظات إضافية")
        
        submitted = st.form_submit_button("💾 حفظ الطلبية")
        
        if submitted:
            if order_name and val_usd > 0:
                # الحسابات الخلفية
                val_sar = val_usd * rate
                new_id = len(df) + 1 if not df.empty else 1
                
                new_row = pd.DataFrame([{
                    "ID": new_id,
                    "الطلبية": order_name,
                    "المورد": supplier,
                    "القيمة_دولار": val_usd,
                    "سعر_الصرف": rate,
                    "القيمة_ريال": val_sar,
                    "المدفوع": 0.0, # جديد دائماً صفر
                    "المتبقي": val_sar,
                    "الحالة": status,
                    "تاريخ_الوصول": str(arrival_date),
                    "ملاحظات": notes
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("تمت الإضافة بنجاح!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("الرجاء إدخال اسم الطلبية والقيمة.")

# --- 4. لوحة المعلومات (KPIs) ---
total_commitment = df['القيمة_ريال'].sum()
total_paid = df['المدفوع'].sum()
total_balance = df['المتبقي'].sum()
active_orders = len(df[df['الحالة'] != "وصلت المستودع"])

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزامات</div><div class="metric-value">{total_commitment:,.0f}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">تم سداده</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_balance:,.0f}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">طلبات نشطة</div><div class="metric-value">{active_orders}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. إدارة الطلبات (تسجيل دفعات) ---
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📋 سجل الطلبات الحالي")
    
    # عرض جدول نظيف للقراءة فقط
    display_df = df[['ID', 'الطلبية', 'المورد', 'القيمة_ريال', 'المدفوع', 'المتبقي', 'الحالة', 'تاريخ_الوصول']].copy()
    # تنسيق الأرقام للعرض
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("#", width="small"),
            "القيمة_ريال": st.column_config.ProgressColumn("القيمة (ريال)", format="%.0f", min_value=0, max_value=max(df['القيمة_ريال'].max(), 1000)),
            "المدفوع": st.column_config.NumberColumn(format="%.0f"),
            "المتبقي": st.column_config.NumberColumn(format="%.0f"),
        }
    )

with c_right:
    st.subheader("💰 تسجيل دفعة / تحديث")
    
    # اختيار طلبية للتعديل
    if not df.empty:
        order_options = df['ID'].astype(str) + " - " + df['الطلبية']
        selected_option = st.selectbox("اختر الطلبية:", order_options)
        selected_id = int(selected_option.split(" - ")[0])
        
        # جلب بيانات الطلبية المختارة
        current_order = df[df['ID'] == selected_id].iloc[0]
        
        st.info(f"المتبقي الحالي: {current_order['المتبقي']:,.0f} ريال")
        
        with st.form("payment_form"):
            new_payment = st.number_input("مبلغ الدفعة الجديدة (ريال)", min_value=0.0, step=1000.0)
            update_status = st.selectbox("تحديث الحالة", ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"], index=["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"].index(current_order['الحالة']) if current_order['الحالة'] in ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"] else 0)
            
            confirm_pay = st.form_submit_button("تحديث البيانات")
            
            if confirm_pay:
                # تحديث البيانات في الداتا فريم
                idx = df.index[df['ID'] == selected_id][0]
                
                # تحديث المدفوع والمتبقي
                current_paid = df.at[idx, 'المدفوع']
                total_val = df.at[idx, 'القيمة_ريال']
                
                new_total_paid = current_paid + new_payment
                
                if new_total_paid > total_val:
                    st.error("خطأ: المبلغ المدفوع أكبر من قيمة الطلبية!")
                else:
                    df.at[idx, 'المدفوع'] = new_total_paid
                    df.at[idx, 'المتبقي'] = total_val - new_total_paid
                    df.at[idx, 'الحالة'] = update_status
                    
                    # الحفظ في جوجل
                    conn.update(worksheet="Sheet1", data=df)
                    st.success(f"تم تسجيل دفعة بقيمة {new_payment:,.0f} ريال بنجاح!")
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("لا توجد طلبات. ابدأ بإضافة طلبية من القائمة الجانبية.")

# --- 6. تنبيهات الوصول ---
st.divider()
st.subheader("📅 تقويم الوصول")
upcoming = df[df['الحالة'].isin(["في البحر", "تخليص جمركي"])].sort_values('تاريخ_الوصول')

if not upcoming.empty:
    for _, row in upcoming.iterrows():
        st.warning(f"🚢 **{row['الطلبية']}** ({row['المورد']}) - متوقع الوصول: {row['تاريخ_الوصول']} - الحالة: {row['الحالة']}")
else:
    st.success("لا توجد شحنات معلقة حالياً.")
