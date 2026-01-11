import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="نظام إدارة المشتريات واللوجستيات", layout="wide", page_icon="🚢")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    .metric-card {
        background-color: #fff; border: 1px solid #e0e0e0; padding: 15px; 
        border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .metric-title { font-size: 13px; color: #333 !important; margin-bottom: 5px; font-weight: bold; }
    .metric-value { font-size: 20px; font-weight: bold; color: #034275 !important; }
    
    .plan-box {
        background-color: #f8f9fa !important; border-right: 4px solid #27ae60;
        padding: 15px; margin-bottom: 15px; border-radius: 8px; font-size: 14px;
        color: #000 !important;
    }
    
    /* تنسيق جدول الدفعات */
    .payment-table { font-size: 12px; }
    
    div.stButton > button:first-child { border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- الثوابت ---
STATUS_LIST = ["لم يبدأ", "تم الاعتماد", "جاري التجهيز", "تم الشحن", "تخليص جمركي", "وصلت للمستودع", "مسددة بالكامل"]
FEES_FACTOR = 0.744

# --- 2. الاتصال والبيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # تحميل الطلبات
        df_orders = conn.read(worksheet="Sheet1", ttl=0)
        
        # تحميل الدفعات (من الصفحة الثانية payments)
        try:
            df_payments = conn.read(worksheet="payments", ttl=0)
        except:
            df_payments = pd.DataFrame() # إذا لم توجد الصفحة

        # --- تجهيز جدول الطلبات ---
        ord_cols = [
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", 
            "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", 
            "المدفوع", "المتبقي", "الحالة", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول",
            "تاريخ_الاعتماد_الفعلي", "تاريخ_الشحن_المتوقع", 
            "تاريخ_الشحن_الفعلي", "تاريخ_الوصول_المتوقع", "تاريخ_الوصول_الفعلي"
        ]
        if df_orders.empty: df_orders = pd.DataFrame(columns=ord_cols)
        for col in ord_cols:
            if col not in df_orders.columns: df_orders[col] = None
            
        # --- تجهيز جدول الدفعات ---
        pay_cols = ["PaymentID", "OrderID", "التاريخ", "المبلغ", "البيان", "رابط_السند"]
        if df_payments.empty: df_payments = pd.DataFrame(columns=pay_cols)
        for col in pay_cols:
            if col not in df_payments.columns: df_payments[col] = None

        # تحويل الأرقام (Orders)
        num_cols = ["القيمة_دولار", "سعر_الصرف", "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in num_cols: df_orders[col] = pd.to_numeric(df_orders[col], errors='coerce').fillna(0)
        df_orders['ID'] = pd.to_numeric(df_orders['ID'], errors='coerce').fillna(0).astype(int)
        
        # تحويل الأرقام (Payments)
        df_payments['PaymentID'] = pd.to_numeric(df_payments['PaymentID'], errors='coerce').fillna(0).astype(int)
        df_payments['OrderID'] = pd.to_numeric(df_payments['OrderID'], errors='coerce').fillna(0).astype(int)
        df_payments['المبلغ'] = pd.to_numeric(df_payments['المبلغ'], errors='coerce').fillna(0)

        # تحويل التواريخ
        date_cols = ["تاريخ_الاعتماد_الفعلي", "تاريخ_الشحن_المتوقع", "تاريخ_الشحن_الفعلي", "تاريخ_الوصول_المتوقع", "تاريخ_الوصول_الفعلي"]
        for col in date_cols: df_orders[col] = pd.to_datetime(df_orders[col], errors='coerce')
        
        # *** المزامنة الذكية ***
        # نعيد حساب "المدفوع" في جدول الطلبات بناءً على مجموع الدفعات في جدول الدفعات
        # لضمان عدم وجود أخطاء في الأرصدة
        if not df_payments.empty:
            real_paid = df_payments.groupby('OrderID')['المبلغ'].sum().reset_index()
            for index, row in df_orders.iterrows():
                oid = row['ID']
                paid_amt = real_paid[real_paid['OrderID'] == oid]['المبلغ'].sum()
                df_orders.at[index, 'المدفوع'] = paid_amt
                df_orders.at[index, 'المتبقي'] = row['aجمالي_التكلفة'] - paid_amt # سيتم تصحيحه في الاسفل

        # إعادة حساب المتبقي للجميع
        df_orders['المتبقي'] = df_orders['اجمالي_التكلفة'] - df_orders['المدفوع']

        return df_orders, df_payments
    except Exception as e:
        st.error(f"خطأ في التحميل: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_orders, df_payments = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("🚢 نظام إدارة المشتريات (سجل الدفعات)")

with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية")
        supplier = st.text_input("اسم المورد")
        c1, c2 = st.columns(2)
        val_usd = c1.number_input("قيمة ($)", min_value=0.0, step=100.0)
        rate = c2.number_input("سعر الصرف", value=3.75, step=0.01)
        
        goods_sar = val_usd * rate
        fees_sar = val_usd * FEES_FACTOR
        total_sar = goods_sar + fees_sar
        st.info(f"الإجمالي: {total_sar:,.0f} ريال")
        
        st.markdown("---")
        p1, p2, p3 = st.columns(3)
        pct_start = p1.number_input("اعتماد %", value=30)
        pct_ship = p2.number_input("شحن %", value=20)
        pct_arrive = p3.number_input("وصول %", value=50)
        
        st.markdown("---")
        target_arrival = st.date_input("تاريخ الوصول المستهدف")
        status = st.selectbox("الحالة الأولية", ["لم يبدأ", "تم الاعتماد"])
        notes = st.text_area("ملاحظات")
        
        submitted = st.form_submit_button("💾 حفظ الطلبية")
        if submitted:
            if order_name and val_usd > 0:
                new_id = 1
                if not df_orders.empty and len(df_orders) > 0:
                    try: new_id = int(df_orders['ID'].max()) + 1
                    except: new_id = 1
                
                today = datetime.now()
                d_arrive_exp = str(target_arrival)
                d_conf = today if status == "تم الاعتماد" else None
                d_ship_exp = (today + timedelta(days=30)) if status == "تم الاعتماد" else None
                if status == "تم الاعتماد":
                    d_arrive_exp = (today + timedelta(days=60)).strftime("%Y-%m-%d")
                
                new_row = pd.DataFrame([{
                    "ID": new_id, "الطلبية": order_name, "المورد": supplier,
                    "القيمة_دولار": val_usd, "سعر_الصرف": rate, 
                    "قيمة_البضاعة_ريال": goods_sar, "رسوم_شحن_تخليص": fees_sar, "اجمالي_التكلفة": total_sar,
                    "المدفوع": 0.0, "المتبقي": total_sar, "الحالة": status, "ملاحظات": notes,
                    "نسبة_اعتماد": pct_start, "نسبة_شحن": pct_ship, "نسبة_وصول": pct_arrive,
                    "تاريخ_الاعتماد_الفعلي": d_conf, "تاريخ_الشحن_المتوقع": d_ship_exp,
                    "تاريخ_الشحن_الفعلي": None, "تاريخ_الوصول_المتوقع": d_arrive_exp, "تاريخ_الوصول_الفعلي": None
                }])
                updated_df = pd.concat([df_orders, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("تمت الإضافة!"); st.cache_data.clear(); st.rerun()

# --- 4. الكروت العلوية ---
if not df_orders.empty:
    total_cost_all = df_orders['اجمالي_التكلفة'].sum()
    total_paid = df_orders['المدفوع'].sum()
    total_rem = df_orders['المتبقي'].sum()
    val_in_transit = df_orders[df_orders['الحالة'].isin(["تم الشحن", "تخليص جمركي"])]['اجمالي_التكلفة'].sum()
    total_orders = len(df_orders)
    cnt_shipped = len(df_orders[df_orders['الحالة'] == "تم الشحن"])
    cnt_customs = len(df_orders[df_orders['الحالة'] == "تخليص جمركي"])
    cnt_arrived = len(df_orders[df_orders['الحالة'].isin(["وصلت للمستودع", "مسددة بالكامل"])])
else:
    total_cost_all = 0; total_paid = 0; total_rem = 0; val_in_transit = 0
    total_orders = 0; cnt_shipped = 0; cnt_customs = 0; cnt_arrived = 0

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزام</div><div class="metric-value">{total_cost_all:,.0f}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">المدفوع</div><div class="metric-value" style="color:#27ae60 !important">{total_paid:,.0f}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي</div><div class="metric-value" style="color:#c0392b !important">{total_rem:,.0f}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">بضاعة بالطريق</div><div class="metric-value" style="color:#e67e22 !important">{val_in_transit:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
s1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الطلبات</div><div class="metric-value">{total_orders}</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="metric-card"><div class="metric-title">شحنات في البحر/الجو</div><div class="metric-value">{cnt_shipped}</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="metric-card"><div class="metric-title">في الجمارك</div><div class="metric-value">{cnt_customs}</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="metric-card"><div class="metric-title">وصلت / انتهت</div><div class="metric-value" style="color:#27ae60 !important">{cnt_arrived}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. الجدول الزمني ---
st.subheader("🗓️ الجدول الزمني للطلبات")
if not df_orders.empty:
    timeline_data = []
    today = datetime.now()
    timeline_data.append(dict(Task="-- Scale --", Start=today, Finish=today + timedelta(days=365), Stage="Scale", Color="rgba(0,0,0,0)"))

    for _, row in df_orders.iterrows():
        if row['الحالة'] == "لم يبدأ":
            arrive_exp = row['تاريخ_الوصول_المتوقع']
            if pd.isna(arrive_exp): arrive_exp = today + timedelta(days=60)
            start_plan = arrive_exp - timedelta(days=60)
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_plan, Finish=arrive_exp, Stage="مخطط (60 يوم)", Color="#95a5a6"))
        elif row['الحالة'] in ["وصلت للمستودع", "مسددة بالكامل"]:
            start_actual = row['تاريخ_الاعتماد_الفعلي']
            end_actual = row['تاريخ_الوصول_الفعلي']
            if pd.isna(start_actual): start_actual = today
            if pd.isna(end_actual): end_actual = today
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_actual, Finish=end_actual, Stage="مكتملة", Color="#27ae60"))
        else:
            start_conf = row['تاريخ_الاعتماد_الفعلي']
            if pd.isna(start_conf): start_conf = today
            date_ship = row['تاريخ_الشحن_الفعلي']
            date_ship_exp = row['تاريخ_الشحن_المتوقع']
            phase1_end = date_ship if pd.notna(date_ship) else (date_ship_exp if pd.notna(date_ship_exp) else start_conf + timedelta(days=30))
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_conf, Finish=phase1_end, Stage="تجهيز (30 يوم)", Color="#3498db"))
            if row['الحالة'] in ["تم الشحن", "تخليص جمركي"]:
                arrive_exp = row['تاريخ_الوصول_المتوقع']
                calc_arrival = date_ship + timedelta(days=30) if pd.notna(date_ship) else phase1_end + timedelta(days=30)
                phase2_end = arrive_exp if pd.notna(arrive_exp) else calc_arrival
                color_phase2 = "#e67e22" if row['الحالة'] == "تم الشحن" else "#e74c3c"
                stage_label = "شحن (30 يوم)" if row['الحالة'] != "تخليص جمركي" else "جمارك"
                timeline_data.append(dict(Task=row['الطلبية'], Start=phase1_end, Finish=phase2_end, Stage=stage_label, Color=color_phase2))

    if len(timeline_data) > 0:
        df_gantt = pd.DataFrame(timeline_data)
        df_clean = df_gantt[df_gantt['Task'] != "-- Scale --"]
        fig = px.timeline(
            df_clean, x_start="Start", x_end="Finish", y="Task", color="Color",
            title="", color_discrete_map="identity",
            height=350 + (len(df_orders)*30), template="plotly_white"
        )
        fig.update_xaxes(tickformat="%b %Y", dtick="M1", ticklabelmode="period", range=[today - timedelta(days=30), today + timedelta(days=300)], side="top")
        fig.update_yaxes(autorange="reversed", title="")
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10), xaxis_gridcolor='#f0f0f0')
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 6. منطقة العمل ---
c_left, c_right = st.columns([1.8, 1])

with c_left:
    st.subheader("📋 سجل البيانات التفصيلي")
    col_config = {
        "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
        "الطلبية": st.column_config.TextColumn(width="medium"),
        "القيمة_دولار": st.column_config.NumberColumn("$", format="%.2f"),
        "تاريخ_الشحن_المتوقع": st.column_config.DateColumn("ت. شحن", format="YYYY-MM-DD", disabled=False),
        "تاريخ_الوصول_المتوقع": st.column_config.DateColumn("ت. وصول", format="YYYY-MM-DD", disabled=False),
        "الحالة": st.column_config.SelectboxColumn(options=STATUS_LIST),
        "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
    }
    
    edited_df = st.data_editor(df_orders, num_rows="dynamic", use_container_width=True, column_config=col_config, key="main_editor")
    
    if st.button("💾 حفظ التعديلات"):
        edited_df['قيمة_البضاعة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
        edited_df['رسوم_شحن_تخليص'] = edited_df['القيمة_دولار'] * FEES_FACTOR
        edited_df['اجمالي_التكلفة'] = edited_df['قيمة_البضاعة_ريال'] + edited_df['رسوم_شحن_تخليص']
        edited_df['المتبقي'] = edited_df['اجمالي_التكلفة'] - edited_df['المدفوع']
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("تم التحديث!")
        st.cache_data.clear(); st.rerun()

with c_right:
    st.subheader("💳 إدارة الدفعات (سجل تاريخي)")
    
    if not df_orders.empty:
        df_orders['ID_str'] = df_orders['ID'].astype(str)
        order_options = df_orders['ID_str'] + " - " + df_orders['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            try: selected_id = int(float(selected_option.split(" - ")[0]))
            except: st.stop()

            current_order = df_orders[df_orders['ID'] == selected_id].iloc[0]
            
            # --- 1. عرض ملخص الطلب ---
            st.markdown(f"""
            <div class="plan-box">
            <b>{current_order['الطلبية']}</b> (الحالة: {current_order['الحالة']})<br>
            المطلوب: {current_order['اجمالي_التكلفة']:,.0f} | <b>المدفوع: {current_order['المدفوع']:,.0f}</b>
            </div>
            """, unsafe_allow_html=True)
            
            # --- 2. عرض سجل الدفعات السابقة (History) ---
            if not df_payments.empty:
                history = df_payments[df_payments['OrderID'] == selected_id]
                if not history.empty:
                    st.markdown("🔹 **سجل العمليات السابقة:**")
                    st.dataframe(
                        history[['التاريخ', 'المبلغ', 'البيان', 'رابط_السند']], 
                        use_container_width=True, hide_index=True,
                        column_config={
                            "رابط_السند": st.column_config.LinkColumn("السند"),
                            "المبلغ": st.column_config.NumberColumn(format="%.0f")
                        }
                    )
            
            # --- 3. نموذج إضافة دفعة جديدة ---
            st.markdown("---")
            st.markdown("##### ➕ تسجيل عملية جديدة")
            
            with st.form("new_payment_form"):
                pay_date = st.date_input("تاريخ التحويل", value=datetime.now())
                pay_amount = st.number_input("المبلغ (ريال)", min_value=0.0, step=1000.0)
                pay_note = st.text_input("البيان / الوصف (مثلاً: دفعة مقدمة)")
                pay_link = st.text_input("رابط السند (Google Drive Link)")
                
                # تحديث الحالة أيضاً
                try: idx_status = STATUS_LIST.index(current_order['الحالة'])
                except: idx_status = 0
                new_status = st.selectbox("تحديث حالة الطلب بالمرة؟", STATUS_LIST, index=idx_status)
                
                if st.form_submit_button("💾 حفظ الدفعة وتحديث الحالة"):
                    # 1. إضافة الدفعة لجدول الدفعات
                    new_pid = 1
                    if not df_payments.empty and 'PaymentID' in df_payments.columns and len(df_payments) > 0:
                        try: new_pid = int(df_payments['PaymentID'].max()) + 1
                        except: new_pid = 1
                        
                    new_payment_row = pd.DataFrame([{
                        "PaymentID": new_pid, "OrderID": selected_id,
                        "التاريخ": str(pay_date), "المبلغ": pay_amount, 
                        "البيان": pay_note, "رابط_السند": pay_link
                    }])
                    
                    updated_payments = pd.concat([df_payments, new_payment_row], ignore_index=True)
                    conn.update(worksheet="payments", data=updated_payments)
                    
                    # 2. تحديث حالة الطلبية والتواريخ (Logic)
                    idx = df_orders.index[df_orders['ID'] == selected_id][0]
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # منطق التواريخ (نفس السابق)
                    if new_status == "تم الاعتماد" and current_order['الحالة'] != "تم الاعتماد":
                        df_orders.at[idx, 'تاريخ_الاعتماد_الفعلي'] = today_str
                        df_orders.at[idx, 'تاريخ_الشحن_المتوقع'] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        df_orders.at[idx, 'تاريخ_الوصول_المتوقع'] = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
                    
                    if new_status == "تم الشحن" and current_order['الحالة'] != "تم الشحن":
                        df_orders.at[idx, 'تاريخ_الشحن_الفعلي'] = today_str
                        df_orders.at[idx, 'تاريخ_الوصول_المتوقع'] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        
                    if new_status in ["وصلت للمستودع", "مسددة بالكامل"] and current_order['الحالة'] not in ["وصلت للمستودع", "مسددة بالكامل"]:
                        df_orders.at[idx, 'تاريخ_الوصول_الفعلي'] = today_str

                    # لا نحدث المدفوع هنا يدوياً، لأن load_data سيجمعه تلقائياً في التحديث القادم
                    df_orders.at[idx, 'الحالة'] = new_status
                    
                    conn.update(worksheet="Sheet1", data=df_orders)
                    
                    st.success("تم تسجيل الدفعة وتحديث الحالة!")
                    st.cache_data.clear(); st.rerun()
