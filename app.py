import streamlit as st
import pandas as pd
import plotly.express as px
import xml.etree.ElementTree as ET
from datetime import datetime

# --- 1. إعدادات الصفحة والتصميم (نفس ستايل التحصيل المعتمد) ---
st.set_page_config(page_title="مشتريات شان - التحليل الشامل", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    
    /* كروت KPI العلوية */
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-5px); }
    .kpi-title { font-size: 13px; color: #666; margin-bottom: 8px; font-weight: bold; }
    .kpi-value { font-size: 22px; font-weight: bold; color: #034275; }
    .kpi-sub { font-size: 11px; color: #888; margin-top: 5px; }
    
    /* الجداول والبطاقات */
    .main-card {
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        background-color: #ffffff;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .card-header {
        color: #034275;
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 15px;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. دوال المعالجة (مخصصة للمشتريات) ---
@st.cache_data(ttl=3600)
def load_purchase_data(file_header, file_items):
    try:
        file_header.seek(0); file_items.seek(0)
        tree_h = ET.parse(file_header); df_h = pd.DataFrame([{child.tag: child.text for child in row} for row in tree_h.getroot()])
        tree_i = ET.parse(file_items); df_i = pd.DataFrame([{child.tag: child.text for child in row} for row in tree_i.getroot()])
        
        # تنظيف البيانات
        if 'IsDelete' in df_h.columns: df_h = df_h[~df_h['IsDelete'].isin(['True', 'true', '1'])]
        df_h['Date'] = pd.to_datetime(pd.to_numeric(df_h['TransDateValue'], errors='coerce'), unit='D', origin='1899-12-30')
        
        # *** الفلتر السحري للمشتريات ***
        # نبحث عن فواتير الشراء فقط (Purchase) ونستبعد البيع
        # ونحدد المرتجعات (Debit Note / Return)
        purchase_keywords = ['purchase', 'شراء', 'مشتريات']
        return_keywords = ['debit note', 'مرتجع شراء', 'مردود مشتريات', 'return']
        
        def get_voucher_type(v_name):
            v_lower = str(v_name).lower()
            if any(k in v_lower for k in return_keywords): return 'Return'
            if any(k in v_lower for k in purchase_keywords): return 'Purchase'
            return 'Ignore'

        df_h['Type'] = df_h['VoucherName'].apply(get_voucher_type)
        df_h = df_h[df_h['Type'] != 'Ignore']

        # دمج الأصناف
        df_i['Qty'] = pd.to_numeric(df_i['TotalQty'], errors='coerce').fillna(0)
        df_i['Amount'] = pd.to_numeric(df_i.get('Amount', df_i.get('TaxbleAmount', 0)), errors='coerce').fillna(0)
        
        full_data = pd.merge(df_i, df_h[['TransCode', 'Date', 'InvoiceNo', 'LedgerName', 'Type', 'VoucherName']], on='TransCode', how='inner')
        
        # معالجة المرتجعات (بالسالب)
        full_data.loc[full_data['Type'] == 'Return', 'Amount'] *= -1
        full_data.loc[full_data['Type'] == 'Return', 'Qty'] *= -1
        
        return full_data
    except Exception as e:
        return None

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.header("📦 بيانات المشتريات")
    f1 = st.file_uploader("1. StockInvoiceDetails (Header)", type=['xml'])
    f2 = st.file_uploader("2. StockInvoiceRowItems (Items)", type=['xml'])

# --- 4. العرض والتحليل ---
if f1 and f2:
    df = load_purchase_data(f1, f2)
    
    if df is not None:
        # حسابات المؤشرات
        net_purchases = df['Amount'].sum()
        total_invoices = df[df['Type'] == 'Purchase']['InvoiceNo'].nunique()
        total_returns_count = df[df['Type'] == 'Return']['InvoiceNo'].nunique()
        total_returns_val = abs(df[df['Type'] == 'Return']['Amount'].sum())
        
        top_supplier = df.groupby('LedgerName')['Amount'].sum().idxmax()
        top_supplier_val = df.groupby('LedgerName')['Amount'].sum().max()

        # --- أ. لوحة القيادة (KPIs) ---
        st.markdown("### 📊 ملخص المشتريات والتوريد")
        k1, k2, k3, k4 = st.columns(4)
        
        with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">صافي المشتريات</div><div class="kpi-value">{net_purchases:,.0f}</div><div class="kpi-sub">بعد خصم المرتجع</div></div>', unsafe_allow_html=True)
        with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-title">عدد فواتير الشراء</div><div class="kpi-value">{total_invoices}</div><div class="kpi-sub">فاتورة مورد</div></div>', unsafe_allow_html=True)
        with k3: st.markdown(f'<div class="kpi-card"><div class="kpi-title">قيمة المرتجعات (للموردين)</div><div class="kpi-value" style="color:#c0392b">{total_returns_val:,.0f}</div><div class="kpi-sub">{total_returns_count} عملية إرجاع</div></div>', unsafe_allow_html=True)
        with k4: st.markdown(f'<div class="kpi-card"><div class="kpi-title">المورد الأكبر</div><div class="kpi-value" style="font-size:16px">{top_supplier}</div><div class="kpi-sub">{top_supplier_val:,.0f} ر.س</div></div>', unsafe_allow_html=True)

        st.divider()

        # --- ب. التحليل التفصيلي ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown('<div class="main-card"><div class="card-header">📈 المشتريات الشهرية</div>', unsafe_allow_html=True)
            monthly_trend = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum().reset_index()
            monthly_trend['Date'] = monthly_trend['Date'].astype(str)
            fig = px.bar(monthly_trend, x='Date', y='Amount', color_discrete_sequence=['#034275'])
            fig.update_layout(xaxis_title="الشهر", yaxis_title="القيمة", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<div class="main-card"><div class="card-header">🏆 أهم 5 موردين</div>', unsafe_allow_html=True)
            top_suppliers = df.groupby('LedgerName')['Amount'].sum().sort_values(ascending=False).head(5).reset_index()
            st.dataframe(top_suppliers, column_config={"LedgerName": "المورد", "Amount": st.column_config.NumberColumn("القيمة", format="%.0f")}, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- ج. جدول الأصناف الأكثر شراءً ---
        st.markdown('<div class="main-card"><div class="card-header">📦 أكثر المواد شراءً (Top Items)</div>', unsafe_allow_html=True)
        top_items = df.groupby('StockName').agg({'Qty': 'sum', 'Amount': 'sum'}).sort_values('Amount', ascending=False).head(10).reset_index()
        st.dataframe(top_items, use_container_width=True, column_config={
            "StockName": "اسم الصنف",
            "Qty": "الكمية المشتراة",
            "Amount": st.column_config.NumberColumn("إجمالي التكلفة", format="%.2f")
        })
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.warning("لم يتم العثور على بيانات مشتريات. تأكد من أن الملفات تحتوي على فواتير 'Purchase' أو 'شراء'.")
else:
    st.info("📂 الرجاء رفع ملفات الفواتير (InvoiceDetails + RowItems) للبدء.")
