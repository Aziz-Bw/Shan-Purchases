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

# --- الثوابت ---
STATUS_LIST = ["لم يبدأ", "تم الاعتماد", "جاري التجهيز", "تم الشحن", "تخليص جمركي", "وصلت للمستودع", "مسددة بالكامل"]
FEES_FACTOR = 0.744  # معامل الشحن والجمارك

# --- 2. الاتصال بجوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        # الأعمدة المحدثة (إضافة الرسوم والاجمالي الكلي)
        columns = [
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", 
            "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", 
            "المدفوع", "المتبقي", "الحالة", "تاريخ_الوصول", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"
        ]
        
        if df.empty: return pd.DataFrame(columns=columns)
        
        for col in columns:
            if col not in df.columns: df[col] = None
        
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame() # إرجاع فارغ عند الخطأ

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("📦 نظام إدارة المشتريات (شامل الشحن والجمارك)")

# القائمة الجانبية (إضافة جديد)
with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية / الصنف")
        supplier = st.text_input("اسم المورد")
        c1, c2 = st.columns(2)
        val_usd = c1.number_input("قيمة الفاتورة ($)", min_value=0.0, step=100.0)
        rate = c2.number_input("سعر الصرف", value=3.75, step=0.01)
        
        # عرض معاينة الحسابات
        goods_sar = val_usd * rate
        fees_sar = val_usd * FEES_FACTOR
        total_sar = goods_sar + fees_sar
        
        st.info(f"""
        💰 **تحليل التكلفة المقدرة:**
        - قيمة البضاعة: {goods_sar:,.0f} ريال
        - شحن وتخليص (0.744): {fees_sar:,.0f} ريال
        - **الإجمالي الكلي: {total_sar:,.0f} ريال**
        """)
        
        st.markdown("---")
        st.markdown("###### 📊 نسب السداد")
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
                new_id = 1
                if not df.empty and 'ID' in df.columns and pd.notna(df['ID'].max()):
                    try: new_id = int(df['ID'].max()) + 1
                    except: new_id = 1
                
                new_row = pd.DataFrame([{
                    "ID": new_id, "الطلبية": order_name, "المورد": supplier,
                    "القيمة_دولار": val_usd, "سعر_الصرف": rate, 
                    "قيمة_البضاعة_ريال": goods_sar,
                    "رسوم_شحن_تخليص": fees_sar,
                    "اجمالي_التكلفة": total_sar,
                    "المدفوع": 0.0, "المتبقي": total_sar, "الحالة": status,
                    "تاريخ_الوصول": str(arrival_date), "ملاحظات": notes,
                    "نسبة_اعتماد": pct_start, "نسبة_شحن": pct_ship, "نسبة_وصول": pct_arrive
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("تمت الإضافة!"); st.cache_data.clear(); st.rerun()

# --- 4. لوحة الإحصائيات ---
if not df.empty:
    total_cost_all = df['اجمالي_التكلفة'].sum() # الالتزام الكلي (بضاعة + رسوم)
    total_paid = df['المدفوع'].sum()
    total_rem = df['المتبقي'].sum()
    total_fees = df['رسوم_شحن_تخليص'].sum() # اجمالي الرسوم فقط
    
    total_orders = len(df)
    cnt_shipped = len(df[df['الحالة'] == "تم الشحن"])
    cnt_customs = len(df[df['الحالة'] == "تخليص جمركي"])
    cnt_arrived = len(df[df['الحالة'].isin(["وصلت للمستودع", "مسددة بالكامل"])])
    
    # قيمة بضاعة بالطريق (نعتمد على اجمالي التكلفة لأننا ندفع الرسوم في الطريق عادة)
    val_in_transit = df[df['الحالة'].isin(["تم الشحن", "تخليص جمركي"])]['اجمالي_التكلفة'].sum()
else:
    total_cost_all = 0; total_paid = 0; total_rem = 0; total_fees = 0
    total_orders = 0; cnt_shipped = 0; cnt_customs = 0; cnt_arrived = 0; val_in_transit = 0

st.markdown("### 📊 الموقف المالي (شامل الشحن والجمارك)")

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزام (بضاعة+رسوم)</div><div class="metric-value">{total_cost_all:,.0f}</div><div class="metric-sub">منها {total_fees:,.0f} رسوم مقدرة</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">المدفوع فعلياً</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div><div class="metric-sub">بنوك + رسوم</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_rem:,.0f}</div><div class="metric-sub">سيولة مطلوبة</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">التزام بضاعة في الطريق</div><div class="metric-value" style="color:#e67e22">{val_in_transit:,.0f}</div><div class="metric-sub">شحن + جمارك</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
s1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الطلبات</div><div class="metric-value">{total_orders}</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="metric-card"><div class="metric-title">في البحر/الجو</div><div class="metric-value">{cnt_shipped}</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="metric-card"><div class="metric-title">في الجمارك</div><div class="metric-value">{cnt_customs}</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="metric-card"><div class="metric-title">وصلت / انتهت</div><div class="metric-value" style="color:#27ae60">{cnt_arrived}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. منطقة العمل ---
c_left, c_right = st.columns([1.8, 1])

with c_left:
    st.subheader("📋 سجل المشتريات التفصيلي")
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
            "الطلبية": st.column_config.TextColumn(width="medium"),
            "القيمة_دولار": st.column_config.NumberColumn("$ فاتورة", format="%.2f"),
            "سعر_الصرف": st.column_config.NumberColumn("صرف", format="%.2f"),
            "قيمة_البضاعة_ريال": st.column_config.NumberColumn("بضاعة (ر.س)", format="%.0f", disabled=True),
            "رسوم_شحن_تخليص": st.column_config.NumberColumn("شحن وجمارك", format="%.0f", disabled=True, help="محسوبة تلقائياً: دولار * 0.744"),
            "اجمالي_التكلفة": st.column_config.NumberColumn("الإجمالي الكلي", format="%.0f", disabled=True),
            "المدفوع": st.column_config.NumberColumn(format="%.0f", disabled=True),
            "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
            "الحالة": st.column_config.SelectboxColumn(options=STATUS_LIST),
            "نسبة_اعتماد": st.column_config.NumberColumn("% 1", width="small"),
            "نسبة_شحن": st.column_config.NumberColumn("% 2", width="small"),
            "نسبة_وصول": st.column_config.NumberColumn("% 3", width="small"),
        },
        key="main_editor"
    )
    
    if st.button("💾 حفظ وإعادة حساب الرسوم"):
        # المعادلات المحاسبية
        edited_df['قيمة_البضاعة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
        edited_df['رسوم_شحن_تخليص'] = edited_df['القيمة_دولار'] * FEES_FACTOR
        edited_df['اجمالي_التكلفة'] = edited_df['قيمة_البضاعة_ريال'] + edited_df['رسوم_شحن_تخليص']
        edited_df['المتبقي'] = edited_df['اجمالي_التكلفة'] - edited_df['المدفوع']
        
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("تم تحديث الحسابات وحفظ البيانات!")
        st.cache_data.clear()
        st.rerun()

with c_right:
    st.subheader("💸 إدارة المدفوعات")
    
    if not df.empty:
        order_options = df['ID'].astype(str) + " - " + df['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            selected_id = int(str(selected_option).split(" - ")[0])
            current_order = df[df['ID'] == selected_id].iloc[0]
            
            # تفكيك التكلفة
            goods_cost = current_order['قيمة_البضاعة_ريال']
            fees_cost = current_order['رسوم_شحن_تخليص']
            total_cost = current_order['اجمالي_التكلفة']
            paid_val = current_order['المدفوع']
            
            # حسبة الدفعات (على أساس قيمة البضاعة فقط عادة، أو الإجمالي؟)
            # هنا سنحسب النسب بناء على الإجمالي الكلي (بضاعة + رسوم) لضمان تغطية كامل المبلغ
            # أو يمكن جعل الرسوم منفصلة.. لتبسيط الموازنة سنجعل النسب من الاجمالي
            amount_start = total_cost * (current_order['نسبة_اعتماد'] / 100)
            amount_ship = total_cost * (current_order['نسبة_شحن'] / 100)
            amount_arrive = total_cost * (current_order['نسبة_وصول'] / 100)
            
            st.markdown(f"""
            <div class="plan-box">
            <b>تفاصيل التكلفة:</b><br>
            📦 بضاعة: {goods_cost:,.0f} | ⚓ رسوم: {fees_cost:,.0f}<br>
            💵 <b>الإجمالي المطلوب: {total_cost:,.0f} ريال</b>
            <hr>
            <b>خطة الدفع المقترحة (من الإجمالي):</b><br>
            1️⃣ اعتماد: {amount_start:,.0f}<br>
            2️⃣ شحن: {amount_ship:,.0f}<br>
            3️⃣ وصول: {amount_arrive:,.0f}<br>
            <hr>
            ✅ <b>المدفوع: {paid_val:,.0f}</b> | المتبقي: <b>{(total_cost - paid_val):,.0f}</b>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("payment_form"):
                new_transfer = st.number_input("تسجيل مبلغ مدفوع (ريال)", min_value=0.0, step=1000.0)
                
                try: idx_status = STATUS_LIST.index(current_order['الحالة'])
                except: idx_status = 0
                update_status_pay = st.selectbox("تحديث الحالة", STATUS_LIST, index=idx_status)
                
                if st.form_submit_button("حفظ الدفعة"):
                    idx = df.index[df['ID'] == selected_id][0]
                    new_total = paid_val + new_transfer
                    
                    if new_total > total_cost:
                        st.error("المبلغ المدفوع أكبر من إجمالي التكلفة!")
                    else:
                        df.at[idx, 'المدفوع'] = new_total
                        df.at[idx, 'المتبقي'] = total_cost - new_total
                        df.at[idx, 'الحالة'] = update_status_pay
                        conn.update(worksheet="Sheet1", data=df)
                        st.success("تم الحفظ!")
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("سجل طلبية أولاً.")

# --- 6. التنبيهات ---
st.divider()
if not df.empty:
    alert_statuses = ["تم الشحن", "تخليص جمركي", "جاري التجهيز", "تم الاعتماد"]
    upcoming = df[df['الحالة'].isin(alert_statuses)].sort_values('تاريخ_الوصول')
    if not upcoming.empty:
        st.subheader("📅 متابعة الوصول")
        for _, row in upcoming.iterrows():
            icon = "🚢" if row['الحالة'] == "تم الشحن" else "🛃" if row['الحالة'] == "تخليص جمركي" else "⚙️"
            st.info(f"{icon} **{row['الطلبية']}** ({row['المورد']}) - الحالة: {row['الحالة']} - متوقع: {row['تاريخ_الوصول']}")
