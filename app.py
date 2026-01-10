import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="إدارة المشتريات (تعديل كامل)", layout="wide", page_icon="📦")

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
    
    .plan-box {
        background-color: #f8f9fa; border-right: 4px solid #27ae60;
        padding: 10px; margin-bottom: 10px; border-radius: 5px;
    }
    
    /* تحسين زر الحفظ */
    div.stButton > button:first-child {
        border-radius: 5px; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. الاتصال بجوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df.empty: return pd.DataFrame()
        
        required_cols = [
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", 
            "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"
        ]
        for col in required_cols:
            if col not in df.columns: df[col] = None
        
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame(columns=[
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", 
            "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"
        ])

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("📦 نظام إدارة المشتريات (تحكم كامل)")

# القائمة الجانبية (إضافة جديد)
with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية / الصنف")
        supplier = st.text_input("اسم المورد")
        c1, c2 = st.columns(2)
        val_usd = c1.number_input("قيمة الفاتورة ($)", min_value=0.0, step=100.0)
        rate = c2.number_input("سعر الصرف", value=3.75, step=0.01)
        st.markdown("---")
        st.markdown("###### 📊 خطة الدفع (النسب)")
        p1, p2, p3 = st.columns(3)
        pct_start = p1.number_input("اعتماد %", value=30)
        pct_ship = p2.number_input("شحن %", value=20)
        pct_arrive = p3.number_input("وصول %", value=50)
        st.markdown("---")
        arrival_date = st.date_input("تاريخ الوصول")
        status = st.selectbox("حالة الشحنة", ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"])
        notes = st.text_area("ملاحظات")
        submitted = st.form_submit_button("💾 حفظ الطلبية")
        
        if submitted:
            if order_name and val_usd > 0:
                val_sar = val_usd * rate
                new_id = 1
                if not df.empty and 'ID' in df.columns and pd.notna(df['ID'].max()):
                    new_id = int(df['ID'].max()) + 1
                
                new_row = pd.DataFrame([{
                    "ID": new_id, "الطلبية": order_name, "المورد": supplier,
                    "القيمة_دولار": val_usd, "سعر_الصرف": rate, "القيمة_ريال": val_sar,
                    "المدفوع": 0.0, "المتبقي": val_sar, "الحالة": status,
                    "تاريخ_الوصول": str(arrival_date), "ملاحظات": notes,
                    "نسبة_اعتماد": pct_start, "نسبة_شحن": pct_ship, "نسبة_وصول": pct_arrive
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("تمت الإضافة!"); st.cache_data.clear(); st.rerun()

# --- 4. مؤشرات الأداء ---
if not df.empty:
    total_commitment = df['القيمة_ريال'].sum()
    total_paid = df['المدفوع'].sum()
    total_balance = df['المتبقي'].sum()
    active_orders = len(df[df['الحالة'] != "وصلت المستودع"])
else:
    total_commitment = 0; total_paid = 0; total_balance = 0; active_orders = 0

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزامات</div><div class="metric-value">{total_commitment:,.0f}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي المحول للموردين</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_balance:,.0f}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">طلبات نشطة</div><div class="metric-value">{active_orders}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. منطقة العمل (التعديل + تسجيل الحوالات) ---
c_left, c_right = st.columns([1.5, 1])

with c_left:
    st.subheader("📋 سجل الطلبات (قابل للتعديل)")
    st.info("💡 يمكنك تعديل البيانات الأساسية هنا مباشرة (مثل الاسم، القيمة، النسب، التواريخ).")
    
    if not df.empty:
        # عرض البيانات في محرر
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
                "الطلبية": st.column_config.TextColumn(width="medium"),
                "القيمة_دولار": st.column_config.NumberColumn("قيمة ($)", format="%.2f"),
                "سعر_الصرف": st.column_config.NumberColumn("صرف", format="%.2f"),
                "القيمة_ريال": st.column_config.NumberColumn("قيمة (ريال)", format="%.0f", disabled=True), # ممنوع التعديل لأنه محسوب
                "المدفوع": st.column_config.NumberColumn(format="%.0f", disabled=True), # التعديل من النموذج الأيمن
                "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
                "الحالة": st.column_config.SelectboxColumn(options=["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"]),
                "نسبة_اعتماد": st.column_config.NumberColumn("% اعتماد", width="small"),
                "نسبة_شحن": st.column_config.NumberColumn("% شحن", width="small"),
                "نسبة_وصول": st.column_config.NumberColumn("% وصول", width="small"),
            },
            key="main_editor"
        )
        
        # زر حفظ التعديلات اليدوية
        if st.button("💾 حفظ تعديلات الجدول"):
            # إعادة حساب الأعمدة المرتبطة (في حال غيرت الدولار أو الصرف)
            edited_df['القيمة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
            edited_df['المتبقي'] = edited_df['القيمة_ريال'] - edited_df['المدفوع']
            
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("تم تحديث البيانات وإعادة الحساب بنجاح!")
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("لا توجد بيانات. ابدأ بالإضافة من اليمين.")

with c_right:
    st.subheader("💸 تسجيل الحوالات البنكية")
    st.caption("اختر الطلبية لتسجيل مبلغ تم تحويله فعلياً")
    
    if not df.empty:
        order_options = df['ID'].astype(str) + " - " + df['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            selected_id = int(str(selected_option).split(" - ")[0])
            current_order = df[df['ID'] == selected_id].iloc[0]
            
            total_val = current_order['القيمة_ريال']
            paid_val = current_order['المدفوع']
            
            # تحليل الدفعات
            amount_start = total_val * (current_order['نسبة_اعتماد'] / 100)
            amount_ship = total_val * (current_order['نسبة_شحن'] / 100)
            amount_arrive = total_val * (current_order['نسبة_وصول'] / 100)
            
            st.markdown(f"""
            <div class="plan-box">
            <b>مطلوب سداده حسب الخطة:</b><br>
            1️⃣ اعتماد: {amount_start:,.0f} ريال<br>
            2️⃣ شحن: {amount_ship:,.0f} ريال<br>
            3️⃣ وصول: {amount_arrive:,.0f} ريال<br>
            <hr>
            ✅ <b>المدفوع فعلياً: {paid_val:,.0f} ريال</b>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("payment_form"):
                new_transfer = st.number_input("مبلغ الحوالة (ريال)", min_value=0.0, step=1000.0)
                update_status_pay = st.selectbox("تحديث الحالة", ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"], index=["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"].index(current_order['الحالة']) if current_order['الحالة'] in ["تجهيز", "في البحر", "تخليص جمركي", "وصلت المستودع"] else 0)
                
                if st.form_submit_button("تسجيل الحوالة"):
                    idx = df.index[df['ID'] == selected_id][0]
                    new_total = paid_val + new_transfer
                    
                    if new_total > total_val:
                        st.error("المبلغ أكبر من قيمة الطلبية!")
                    else:
                        df.at[idx, 'المدفوع'] = new_total
                        df.at[idx, 'المتبقي'] = total_val - new_total
                        df.at[idx, 'الحالة'] = update_status_pay
                        conn.update(worksheet="Sheet1", data=df)
                        st.success("تم تسجيل الحوالة!")
                        st.cache_data.clear()
                        st.rerun()

# --- 6. التنبيهات ---
st.divider()
if not df.empty:
    upcoming = df[df['الحالة'].isin(["في البحر", "تخليص جمركي"])].sort_values('تاريخ_الوصول')
    if not upcoming.empty:
        st.subheader("📅 تقويم الوصول")
        for _, row in upcoming.iterrows():
            st.info(f"🚢 **{row['الطلبية']}** ({row['المورد']}) - الوصول المتوقع: {row['تاريخ_الوصول']}")
