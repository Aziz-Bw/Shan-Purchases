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
    .metric-title { font-size: 13px; color: #333333 !important; margin-bottom: 5px; font-weight: bold; }
    .metric-value { font-size: 20px; font-weight: bold; color: #034275 !important; }
    
    /* تنسيق النصوص داخل الصناديق */
    .plan-box {
        background-color: #f8f9fa !important; border-right: 4px solid #27ae60;
        padding: 15px; margin-bottom: 15px; border-radius: 8px; font-size: 14px;
        color: #000000 !important;
    }
    .plan-box b { color: #000000 !important; }
    
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
        df = conn.read(worksheet="Sheet1", ttl=0)
        columns = [
            "ID", "الطلبية", "المورد", "القيمة_دولار", "سعر_الصرف", 
            "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", 
            "المدفوع", "المتبقي", "الحالة", "ملاحظات",
            "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول",
            "تاريخ_الاعتماد_الفعلي", "تاريخ_الشحن_المتوقع", 
            "تاريخ_الشحن_الفعلي", "تاريخ_الوصول_المتوقع", "تاريخ_الوصول_الفعلي"
        ]
        if df.empty: return pd.DataFrame(columns=columns)
        for col in columns:
            if col not in df.columns: df[col] = None
        
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
        
        # تحويل التواريخ إلى datetime لضمان عمل المخطط
        date_cols = ["تاريخ_الاعتماد_الفعلي", "تاريخ_الشحن_المتوقع", "تاريخ_الشحن_الفعلي", "تاريخ_الوصول_المتوقع", "تاريخ_الوصول_الفعلي"]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("🚢 نظام إدارة المشتريات (اللوحة الكاملة)")

with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية / الصنف")
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
        status = st.selectbox("الحالة الأولية", STATUS_LIST)
        notes = st.text_area("ملاحظات")
        
        submitted = st.form_submit_button("💾 حفظ الطلبية")
        if submitted:
            if order_name and val_usd > 0:
                new_id = 1
                if not df.empty and len(df) > 0:
                    try: new_id = int(df['ID'].max()) + 1
                    except: new_id = 1
                
                today = datetime.now()
                d_conf = today if status == "تم الاعتماد" else None
                d_ship_exp = (today + timedelta(days=30)) if status == "تم الاعتماد" else None
                
                new_row = pd.DataFrame([{
                    "ID": new_id, "الطلبية": order_name, "المورد": supplier,
                    "القيمة_دولار": val_usd, "سعر_الصرف": rate, 
                    "قيمة_البضاعة_ريال": goods_sar, "رسوم_شحن_تخليص": fees_sar, "اجمالي_التكلفة": total_sar,
                    "المدفوع": 0.0, "المتبقي": total_sar, "الحالة": status, "ملاحظات": notes,
                    "نسبة_اعتماد": pct_start, "نسبة_شحن": pct_ship, "نسبة_وصول": pct_arrive,
                    "تاريخ_الاعتماد_الفعلي": d_conf, "تاريخ_الشحن_المتوقع": d_ship_exp,
                    "تاريخ_الشحن_الفعلي": None, "تاريخ_الوصول_المتوقع": None, "تاريخ_الوصول_الفعلي": None
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("تمت الإضافة!"); st.cache_data.clear(); st.rerun()

# --- 4. الكروت العلوية ---
if not df.empty:
    total_cost_all = df['اجمالي_التكلفة'].sum()
    total_paid = df['المدفوع'].sum()
    total_rem = df['المتبقي'].sum()
    val_in_transit = df[df['الحالة'].isin(["تم الشحن", "تخليص جمركي"])]['اجمالي_التكلفة'].sum()
    total_orders = len(df)
    cnt_shipped = len(df[df['الحالة'] == "تم الشحن"])
    cnt_customs = len(df[df['الحالة'] == "تخليص جمركي"])
    cnt_arrived = len(df[df['الحالة'].isin(["وصلت للمستودع", "مسددة بالكامل"])])
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
s2.markdown(f'<div class="metric-card"><div class="metric-title">في البحر/الجو</div><div class="metric-value">{cnt_shipped}</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="metric-card"><div class="metric-title">في الجمارك</div><div class="metric-value">{cnt_customs}</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="metric-card"><div class="metric-title">وصلت / انتهت</div><div class="metric-value" style="color:#27ae60 !important">{cnt_arrived}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. الجدول الزمني (Timeline Chart) ---
st.subheader("🗓️ الجدول الزمني للطلبات (Timeline)")

if not df.empty:
    timeline_data = []
    
    for _, row in df.iterrows():
        # تحديد التواريخ والمراحل
        start_date = row['تاريخ_الاعتماد_الفعلي']
        if pd.isna(start_date): start_date = datetime.now() # افتراضي للي ما بدأ
        
        # 1. حالة الوصول النهائي (أخضر كامل)
        if row['الحالة'] in ["وصلت للمستودع", "مسددة بالكامل"]:
            end_date = row['تاريخ_الوصول_الفعلي']
            if pd.isna(end_date): end_date = datetime.now()
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_date, Finish=end_date, Stage="مكتملة", Color="#27ae60")) # أخضر
            
        # 2. حالة لم تبدأ بعد (رمادي - توقع)
        elif row['الحالة'] == "لم يبدأ":
            end_date = start_date + timedelta(days=60) # افتراضي
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_date, Finish=end_date, Stage="مجدولة", Color="#95a5a6")) # رمادي
            
        # 3. حالات قيد التنفيذ (تقسيم المراحل)
        else:
            # مرحلة التجهيز (من الاعتماد للشحن)
            ship_date = row['تاريخ_الشحن_الفعلي']
            ship_exp = row['تاريخ_الشحن_المتوقع']
            
            # إذا لم تشحن بعد، نستخدم المتوقع
            phase1_end = ship_date if pd.notna(ship_date) else (ship_exp if pd.notna(ship_exp) else start_date + timedelta(days=30))
            
            timeline_data.append(dict(Task=row['الطلبية'], Start=start_date, Finish=phase1_end, Stage="تجهيز/تصنيع", Color="#3498db")) # أزرق
            
            # إذا شحنت، نضيف مرحلة الشحن (من الشحن للوصول المتوقع)
            if row['الحالة'] in ["تم الشحن", "تخليص جمركي"]:
                arrive_exp = row['تاريخ_الوصول_المتوقع']
                phase2_end = arrive_exp if pd.notna(arrive_exp) else phase1_end + timedelta(days=30)
                
                # لون الشحن برتقالي، التخليص أحمر فاتح
                color_phase2 = "#e67e22" if row['الحالة'] == "تم الشحن" else "#e74c3c"
                stage_name = "شحن دولي" if row['الحالة'] == "تم الشحن" else "تخليص جمركي"
                
                timeline_data.append(dict(Task=row['الطلبية'], Start=phase1_end, Finish=phase2_end, Stage=stage_name, Color=color_phase2))

    if timeline_data:
        df_gantt = pd.DataFrame(timeline_data)
        
        # رسم المخطط
        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Color",
            title="تتبع حالة الشحنات زمنياً",
            color_discrete_map="identity", # استخدام الألوان المحددة في الداتا
            height=300 + (len(df)*30) # ارتفاع ديناميكي
        )
        
        fig.update_yaxes(autorange="reversed", title="") # ترتيب من الأقدم للأحدث
        fig.update_xaxes(title="التاريخ")
        fig.update_layout(showlegend=False, xaxis_gridcolor='#eee')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("سجل تواريخ للطلبات لتظهر في الجدول الزمني.")

st.divider()

# --- 6. منطقة العمل (جدول + تحديث) ---
c_left, c_right = st.columns([1.8, 1])

with c_left:
    st.subheader("📋 البيانات التفصيلية")
    col_config = {
        "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
        "الطلبية": st.column_config.TextColumn(width="medium"),
        "القيمة_دولار": st.column_config.NumberColumn("$", format="%.2f"),
        "تاريخ_الشحن_المتوقع": st.column_config.DateColumn("ت. شحن", format="DD/MM/YYYY", disabled=True),
        "تاريخ_الوصول_المتوقع": st.column_config.DateColumn("ت. وصول", format="DD/MM/YYYY", disabled=True),
        "الحالة": st.column_config.SelectboxColumn(options=STATUS_LIST),
        "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
    }
    
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, column_config=col_config, key="main_editor")
    
    if st.button("💾 حفظ التعديلات"):
        edited_df['قيمة_البضاعة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
        edited_df['رسوم_شحن_تخليص'] = edited_df['القيمة_دولار'] * FEES_FACTOR
        edited_df['اجمالي_التكلفة'] = edited_df['قيمة_البضاعة_ريال'] + edited_df['رسوم_شحن_تخليص']
        edited_df['المتبقي'] = edited_df['اجمالي_التكلفة'] - edited_df['المدفوع']
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("تم التحديث!")
        st.cache_data.clear(); st.rerun()

with c_right:
    st.subheader("⚙️ تحديث الحالة")
    if not df.empty:
        df['ID_str'] = df['ID'].astype(str)
        order_options = df['ID_str'] + " - " + df['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            try: selected_id = int(float(selected_option.split(" - ")[0]))
            except: st.stop()

            current_order = df[df['ID'] == selected_id].iloc[0]
            
            st.markdown(f"""
            <div class="plan-box">
            <b>{current_order['الطلبية']}</b><br>
            الحالة الحالية: <b>{current_order['الحالة']}</b><br>
            المتبقي: {current_order['المتبقي']:,.0f} ريال
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("update_form"):
                new_transfer = st.number_input("تسجيل دفعة (ريال)", min_value=0.0, step=1000.0)
                try: idx_status = STATUS_LIST.index(current_order['الحالة'])
                except: idx_status = 0
                new_status = st.selectbox("تحديث الحالة", STATUS_LIST, index=idx_status)
                
                if st.form_submit_button("حفظ"):
                    idx = df.index[df['ID'] == selected_id][0]
                    today = datetime.now()
                    
                    if new_status == "تم الاعتماد" and current_order['الحالة'] != "تم الاعتماد":
                        df.at[idx, 'تاريخ_الاعتماد_الفعلي'] = today
                        df.at[idx, 'تاريخ_الشحن_المتوقع'] = today + timedelta(days=30)
                    
                    if new_status == "تم الشحن" and current_order['الحالة'] != "تم الشحن":
                        df.at[idx, 'تاريخ_الشحن_الفعلي'] = today
                        df.at[idx, 'تاريخ_الوصول_المتوقع'] = today + timedelta(days=30)
                        
                    if new_status in ["وصلت للمستودع", "مسددة بالكامل"] and current_order['الحالة'] not in ["وصلت للمستودع", "مسددة بالكامل"]:
                        df.at[idx, 'تاريخ_الوصول_الفعلي'] = today

                    df.at[idx, 'المدفوع'] = current_order['المدفوع'] + new_transfer
                    df.at[idx, 'المتبقي'] = current_order['اجمالي_التكلفة'] - (current_order['المدفوع'] + new_transfer)
                    df.at[idx, 'الحالة'] = new_status
                    
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("تم!")
                    st.cache_data.clear(); st.rerun()
