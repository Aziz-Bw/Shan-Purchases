import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="نظام إدارة المشتريات", layout="wide", page_icon="📦")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    .metric-card {
        background-color: #fff; border: 1px solid #e0e0e0; padding: 15px; 
        border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .metric-title { font-size: 13px; color: #666; margin-bottom: 5px; font-weight: bold; }
    .metric-value { font-size: 20px; font-weight: bold; color: #034275; }
    .metric-sub { font-size: 11px; color: #27ae60; margin-top: 3px; }
    
    .plan-box {
        background-color: #f8f9fa; border-right: 4px solid #27ae60;
        padding: 10px; margin-bottom: 10px; border-radius: 5px; font-size: 13px;
    }
    
    div.stButton > button:first-child { border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- قائمة الحالات المعتمدة ---
STATUS_LIST = [
    "لم يبدأ", 
    "تم الاعتماد", 
    "جاري التجهيز", 
    "تم الشحن", 
    "تخليص جمركي", 
    "وصلت للمستودع", 
    "مسددة بالكامل"
]

# --- 2. الاتصال بجوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        columns = [
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", 
            "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"
        ]
        
        if df.empty: return pd.DataFrame(columns=columns)
        
        for col in columns:
            if col not in df.columns: df[col] = None
        
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame(columns=["ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", "القيمة_ريال", "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"])

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("📦 نظام إدارة المشتريات والاعتمادات")

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
        st.markdown("###### 📊 نسب السداد المقترحة")
        p1, p2, p3 = st.columns(3)
        pct_start = p1.number_input("اعتماد %", value=30)
        pct_ship = p2.number_input("شحن %", value=20)
        pct_arrive = p3.number_input("وصول %", value=50)
        st.markdown("---")
        arrival_date = st.date_input("تاريخ الوصول")
        status = st.selectbox("حالة الشحنة", STATUS_LIST)
        notes = st.text_area("ملاحظات")
        submitted = st.form_submit_button("💾 حفظ الطلبية")
        
        if submitted:
            if order_name and val_usd > 0:
                val_sar = val_usd * rate
                new_id = 1
                if not df.empty and 'ID' in df.columns and pd.notna(df['ID'].max()):
                    try: new_id = int(df['ID'].max()) + 1
                    except: new_id = 1
                
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

# --- 4. لوحة الإحصائيات (KPIs Dashboard) ---
if not df.empty:
    # المالي
    total_sar = df['القيمة_ريال'].sum()
    total_paid = df['المدفوع'].sum()
    total_rem = df['المتبقي'].sum()
    
    # التشغيلي (الأعداد)
    total_orders = len(df)
    cnt_approved = len(df[df['الحالة'] == "تم الاعتماد"])
    cnt_processing = len(df[df['الحالة'] == "جاري التجهيز"])
    cnt_shipped = len(df[df['الحالة'] == "تم الشحن"])
    cnt_customs = len(df[df['الحالة'] == "تخليص جمركي"])
    cnt_arrived = len(df[df['الحالة'].isin(["وصلت للمستودع", "مسددة بالكامل"])])
    
    # قيم البضاعة في الطريق (شحن + جمارك)
    val_in_transit = df[df['الحالة'].isin(["تم الشحن", "تخليص جمركي"])]['القيمة_ريال'].sum()
else:
    total_sar = 0; total_paid = 0; total_rem = 0
    total_orders = 0; cnt_approved = 0; cnt_processing = 0; cnt_shipped = 0; cnt_customs = 0; cnt_arrived = 0; val_in_transit = 0

st.markdown("### 📊 الموقف المالي والتشغيلي")

# الصف الأول: الملخص المالي العام
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزامات (الكل)</div><div class="metric-value">{total_sar:,.0f}</div><div class="metric-sub">قيمة البضاعة بالريال</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">المدفوع فعلياً</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div><div class="metric-sub">تحويلات بنكية</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_rem:,.0f}</div><div class="metric-sub">التزام قائم</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">قيمة بضاعة بالطريق</div><div class="metric-value" style="color:#e67e22">{val_in_transit:,.0f}</div><div class="metric-sub">شحن + جمارك</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# الصف الثاني: تفاصيل حالات الطلبات
s1, s2, s3, s4, s5 = st.columns(5)
s1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الطلبات</div><div class="metric-value">{total_orders}</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="metric-card"><div class="metric-title">تم الاعتماد</div><div class="metric-value">{cnt_approved}</div><div class="metric-sub">تحت الإجراء</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="metric-card"><div class="metric-title">تم الشحن</div><div class="metric-value">{cnt_shipped}</div><div class="metric-sub">في البحر/الجو</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="metric-card"><div class="metric-title">تخليص جمركي</div><div class="metric-value">{cnt_customs}</div><div class="metric-sub">في الميناء</div></div>', unsafe_allow_html=True)
s5.markdown(f'<div class="metric-card"><div class="metric-title">وصلت / انتهت</div><div class="metric-value" style="color:#27ae60">{cnt_arrived}</div><div class="metric-sub">مكتملة</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. منطقة العمل (التعديل + تسجيل الحوالات) ---
c_left, c_right = st.columns([1.6, 1])

with c_left:
    st.subheader("📋 سجل الطلبات (قابل للتعديل)")
    
    # عرض الجدول دائماً
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
            "الطلبية": st.column_config.TextColumn(width="medium"),
            "القيمة_دولار": st.column_config.NumberColumn("قيمة ($)", format="%.2f"),
            "سعر_الصرف": st.column_config.NumberColumn("صرف", format="%.2f"),
            "القيمة_ريال": st.column_config.NumberColumn("قيمة (ريال)", format="%.0f", disabled=True),
            "المدفوع": st.column_config.NumberColumn(format="%.0f", disabled=True),
            "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
            "الحالة": st.column_config.SelectboxColumn(options=STATUS_LIST),
            "نسبة_اعتماد": st.column_config.NumberColumn("% اعتماد", width="small"),
            "نسبة_شحن": st.column_config.NumberColumn("% شحن", width="small"),
            "نسبة_وصول": st.column_config.NumberColumn("% وصول", width="small"),
        },
        key="main_editor"
    )
    
    if st.button("💾 حفظ تعديلات الجدول"):
        edited_df['القيمة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
        edited_df['المتبقي'] = edited_df['القيمة_ريال'] - edited_df['المدفوع']
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("تم التحديث!")
        st.cache_data.clear()
        st.rerun()

with c_right:
    st.subheader("💸 تسجيل الحوالات وتحديث الحالة")
    
    if not df.empty:
        order_options = df['ID'].astype(str) + " - " + df['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            selected_id = int(str(selected_option).split(" - ")[0])
            current_order = df[df['ID'] == selected_id].iloc[0]
            
            total_val = current_order['القيمة_ريال']
            paid_val = current_order['المدفوع']
            curr_status = current_order['الحالة']
            
            amount_start = total_val * (current_order['نسبة_اعتماد'] / 100)
            amount_ship = total_val * (current_order['نسبة_شحن'] / 100)
            amount_arrive = total_val * (current_order['نسبة_وصول'] / 100)
            
            st.markdown(f"""
            <div class="plan-box">
            <b>تحليل الدفعات المستحقة:</b><br>
            🔸 دفعة الاعتماد ({current_order['نسبة_اعتماد']}%): <b>{amount_start:,.0f}</b><br>
            🔸 دفعة الشحن ({current_order['نسبة_شحن']}%): <b>{amount_ship:,.0f}</b><br>
            🔸 دفعة الوصول ({current_order['نسبة_وصول']}%): <b>{amount_arrive:,.0f}</b><br>
            <hr style="margin:5px 0">
            💵 <b>المدفوع فعلياً: {paid_val:,.0f}</b> | المتبقي: <b>{(total_val - paid_val):,.0f}</b>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("payment_form"):
                new_transfer = st.number_input("مبلغ الحوالة الجديدة (ريال)", min_value=0.0, step=1000.0)
                
                # تحديد الاندكس الحالي للحالة في القائمة
                try:
                    idx_status = STATUS_LIST.index(curr_status)
                except:
                    idx_status = 0
                    
                update_status_pay = st.selectbox("تحديث حالة الطلبية", STATUS_LIST, index=idx_status)
                
                if st.form_submit_button("حفظ التحديث"):
                    idx = df.index[df['ID'] == selected_id][0]
                    new_total = paid_val + new_transfer
                    
                    if new_total > total_val:
                        st.error("المبلغ أكبر من قيمة الطلبية!")
                    else:
                        df.at[idx, 'المدفوع'] = new_total
                        df.at[idx, 'المتبقي'] = total_val - new_total
                        df.at[idx, 'الحالة'] = update_status_pay
                        conn.update(worksheet="Sheet1", data=df)
                        st.success("تم تسجيل العملية!")
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("سجل طلبية أولاً لتفعيل الدفعات.")

# --- 6. التنبيهات ---
st.divider()
if not df.empty:
    # التنبيه للحالات النشطة فقط (شحن، جمارك، تجهيز)
    alert_statuses = ["تم الشحن", "تخليص جمركي", "جاري التجهيز", "تم الاعتماد"]
    upcoming = df[df['الحالة'].isin(alert_statuses)].sort_values('تاريخ_الوصول')
    
    if not upcoming.empty:
        st.subheader("📅 متابعة الوصول")
        for _, row in upcoming.iterrows():
            icon = "🚢" if row['الحالة'] == "تم الشحن" else "🛃" if row['الحالة'] == "تخليص جمركي" else "⚙️"
            st.info(f"{icon} **{row['الطلبية']}** ({row['المورد']}) - الحالة: {row['الحالة']} - متوقع: {row['تاريخ_الوصول']}")
