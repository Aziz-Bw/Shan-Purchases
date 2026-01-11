import streamlit as st
import pandas as pd
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
    .metric-title { font-size: 13px; color: #666; margin-bottom: 5px; font-weight: bold; }
    .metric-value { font-size: 20px; font-weight: bold; color: #034275; }
    
    .plan-box {
        background-color: #f8f9fa; border-right: 4px solid #27ae60;
        padding: 10px; margin-bottom: 10px; border-radius: 5px; font-size: 13px;
    }
    
    .date-badge {
        background-color: #e3f2fd; color: #1565c0; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold;
    }
    
    div.stButton > button:first-child { border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- الثوابت ---
STATUS_LIST = ["لم يبدأ", "تم الاعتماد", "جاري التجهيز", "تم الشحن", "تخليص جمركي", "وصلت للمستودع", "مسددة بالكامل"]
FEES_FACTOR = 0.744

# --- 2. الاتصال بجوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        # الأعمدة الجديدة للتواريخ
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
        
        # تحويل الأرقام
        numeric_cols = ["القيمة_دولار", "سعر_الصرف", "قيمة_البضاعة_ريال", "رسوم_شحن_تخليص", "اجمالي_التكلفة", "المدفوع", "المتبقي", "نسبة_اعتماد", "نسبة_شحن", "نسبة_وصول"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. الواجهة الرئيسية ---
st.title("🚢 نظام إدارة المشتريات (الجدولة الذكية)")

# القائمة الجانبية (إضافة)
with st.sidebar:
    st.header("📝 تسجيل طلبية جديدة")
    with st.form("add_order_form"):
        order_name = st.text_input("اسم الطلبية / الصنف")
        supplier = st.text_input("اسم المورد")
        c1, c2 = st.columns(2)
        val_usd = c1.number_input("قيمة الفاتورة ($)", min_value=0.0, step=100.0)
        rate = c2.number_input("سعر الصرف", value=3.75, step=0.01)
        
        goods_sar = val_usd * rate
        fees_sar = val_usd * FEES_FACTOR
        total_sar = goods_sar + fees_sar
        
        st.info(f"💰 الإجمالي المقدر: {total_sar:,.0f} ريال")
        
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
                if not df.empty and 'ID' in df.columns and pd.notna(df['ID'].max()):
                    try: new_id = int(df['ID'].max()) + 1
                    except: new_id = 1
                
                # منطق التواريخ الأولي (إذا بدأ بحالة متقدمة)
                today_str = datetime.now().strftime("%Y-%m-%d")
                exp_ship = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                exp_arrive = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
                
                d_conf = today_str if status == "تم الاعتماد" else None
                d_ship_exp = exp_ship if status == "تم الاعتماد" else None
                
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

# --- 4. لوحة الإحصائيات ---
if not df.empty:
    total_cost_all = df['اجمالي_التكلفة'].sum()
    total_paid = df['المدفوع'].sum()
    total_rem = df['المتبقي'].sum()
    val_in_transit = df[df['الحالة'].isin(["تم الشحن", "تخليص جمركي"])]['اجمالي_التكلفة'].sum()
else:
    total_cost_all = 0; total_paid = 0; total_rem = 0; val_in_transit = 0

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الالتزام (بضاعة+رسوم)</div><div class="metric-value">{total_cost_all:,.0f}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-title">المدفوع فعلياً</div><div class="metric-value" style="color:#27ae60">{total_paid:,.0f}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-card"><div class="metric-title">المتبقي للسداد</div><div class="metric-value" style="color:#c0392b">{total_rem:,.0f}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-card"><div class="metric-title">التزام بضاعة في الطريق</div><div class="metric-value" style="color:#e67e22">{val_in_transit:,.0f}</div></div>', unsafe_allow_html=True)

st.divider()

# --- 5. منطقة العمل ---
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📋 سجل المشتريات والتواريخ")
    
    # عرض الأعمدة المهمة للجدولة
    col_config = {
        "ID": st.column_config.NumberColumn("#", width="small", disabled=True),
        "الطلبية": st.column_config.TextColumn(width="medium"),
        "القيمة_دولار": st.column_config.NumberColumn("$", format="%.2f"),
        "تاريخ_الشحن_المتوقع": st.column_config.DateColumn("ت. شحن (متوقع)", format="DD/MM/YYYY", disabled=True),
        "تاريخ_الوصول_المتوقع": st.column_config.DateColumn("ت. وصول (متوقع)", format="DD/MM/YYYY", disabled=True),
        "الحالة": st.column_config.SelectboxColumn(options=STATUS_LIST),
        "المتبقي": st.column_config.NumberColumn(format="%.0f", disabled=True),
    }
    
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, column_config=col_config, key="main_editor")
    
    if st.button("💾 حفظ تعديلات الجدول"):
        # إعادة حساب الرسوم
        edited_df['قيمة_البضاعة_ريال'] = edited_df['القيمة_دولار'] * edited_df['سعر_الصرف']
        edited_df['رسوم_شحن_تخليص'] = edited_df['القيمة_دولار'] * FEES_FACTOR
        edited_df['اجمالي_التكلفة'] = edited_df['قيمة_البضاعة_ريال'] + edited_df['رسوم_شحن_تخليص']
        edited_df['المتبقي'] = edited_df['اجمالي_التكلفة'] - edited_df['المدفوع']
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("تم التحديث!")
        st.cache_data.clear(); st.rerun()

with c_right:
    st.subheader("⚙️ تحديث الحالة والجدولة")
    
    if not df.empty:
        order_options = df['ID'].astype(str) + " - " + df['الطلبية']
        selected_option = st.selectbox("تحديد الطلبية:", order_options)
        
        if selected_option:
            selected_id = int(str(selected_option).split(" - ")[0])
            current_order = df[df['ID'] == selected_id].iloc[0]
            
            curr_status = current_order['الحالة']
            # عرض التواريخ الحالية
            st.markdown(f"""
            <div class="plan-box">
            📅 <b>الموقف الزمني:</b><br>
            • الاعتماد الفعلي: {current_order.get('تاريخ_الاعتماد_الفعلي') or 'غير محدد'}<br>
            • الشحن المتوقع: <b>{current_order.get('تاريخ_الشحن_المتوقع') or '--'}</b><br>
            • الوصول المتوقع: <b>{current_order.get('تاريخ_الوصول_المتوقع') or '--'}</b>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("payment_form"):
                new_transfer = st.number_input("مبلغ دفعة جديدة (ريال)", min_value=0.0, step=1000.0)
                try: idx_status = STATUS_LIST.index(curr_status)
                except: idx_status = 0
                new_status = st.selectbox("تحديث الحالة (سيحسب التواريخ تلقائياً)", STATUS_LIST, index=idx_status)
                
                if st.form_submit_button("تنفيذ التحديث"):
                    idx = df.index[df['ID'] == selected_id][0]
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # --- المنطق الذكي للتواريخ ---
                    # 1. إذا تحولت إلى "تم الاعتماد"
                    if new_status == "تم الاعتماد" and curr_status != "تم الاعتماد":
                        df.at[idx, 'تاريخ_الاعتماد_الفعلي'] = today_str
                        # شحن متوقع بعد 30 يوم
                        df.at[idx, 'تاريخ_الشحن_المتوقع'] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    
                    # 2. إذا تحولت إلى "تم الشحن"
                    if new_status == "تم الشحن" and curr_status != "تم الشحن":
                        df.at[idx, 'تاريخ_الشحن_الفعلي'] = today_str
                        # وصول متوقع بعد 30 يوم من الشحن
                        df.at[idx, 'تاريخ_الوصول_المتوقع'] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        
                    # 3. إذا تحولت إلى "وصلت"
                    if new_status in ["وصلت للمستودع", "مسددة بالكامل"] and curr_status not in ["وصلت للمستودع", "مسددة بالكامل"]:
                        df.at[idx, 'تاريخ_الوصول_الفعلي'] = today_str

                    # تحديث الماليات والحالة
                    new_total_paid = current_order['المدفوع'] + new_transfer
                    df.at[idx, 'المدفوع'] = new_total_paid
                    df.at[idx, 'المتبقي'] = current_order['اجمالي_التكلفة'] - new_total_paid
                    df.at[idx, 'الحالة'] = new_status
                    
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("تم تحديث الحالة والتواريخ والماليات!")
                    st.cache_data.clear(); st.rerun()

# --- 6. النظرة المستقبلية (Timeline) ---
st.divider()
if not df.empty:
    st.subheader("🔮 النظرة المستقبلية (القادم بالطريق)")
    
    # فلترة الشحنات التي لها تاريخ وصول متوقع ولم تصل بعد
    future = df[
        (df['تاريخ_الوصول_المتوقع'].notna()) & 
        (~df['الحالة'].isin(["وصلت للمستودع", "مسددة بالكامل"]))
    ].sort_values('تاريخ_الوصول_المتوقع')
    
    if not future.empty:
        # تحويل الجدول لبيانات للعرض
        future_display = future[['الطلبية', 'المورد', 'الحالة', 'تاريخ_الوصول_المتوقع', 'اجمالي_التكلفة', 'المتبقي']].copy()
        
        # تنسيق الجدول بالألوان (Dataframe Styling)
        st.dataframe(
            future_display,
            use_container_width=True,
            column_config={
                "تاريخ_الوصول_المتوقع": st.column_config.DateColumn("📆 متوقع الوصول", format="DD/MM/YYYY"),
                "المتبقي": st.column_config.NumberColumn("مطلوب سداده", format="%.0f"),
                "اجمالي_التكلفة": st.column_config.NumberColumn("قيمة الشحنة", format="%.0f"),
            }
        )
    else:
        st.info("لا توجد شحنات مجدولة للوصول قريباً.")
