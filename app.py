import streamlit as st
import google.generativeai as genai
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import requests
from datetime import datetime

# --- 核心配置 ---
GOOGLE_API_KEY = "AIzaSyDFdrO6Hx1qpZbUDXLPwkcuU3kgb3f2h0U"
genai.configure(api_key=GOOGLE_API_KEY)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1lDUp3kONA3x_-BtWqRerbv-xOhGdRTYu6Qx85J7I4BI/edit#gid=0"

st.set_page_config(page_title="AI 智能记账全能版", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_jpy_to_cny():
    try:
        url = "https://open.er-api.com/v6/latest/JPY"
        data = requests.get(url, timeout=5).json()
        return data['rates']['CNY']
    except:
        return 0.048

def save_to_sheet(date, store, amount, cat):
    rate = get_jpy_to_cny()
    cny_val = round(amount * rate, 2)
    df_existing = conn.read(spreadsheet=spreadsheet_url)
    new_data = pd.DataFrame([{"日期": date, "店名": store, "金额": amount, "分类": cat, "人民币金额": cny_val}])
    updated_df = pd.concat([df_existing, new_data], ignore_index=True)
    conn.update(spreadsheet=spreadsheet_url, data=updated_df)
    return cny_val

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 管理员工具")
    if st.button("🗑️ 一键清空所有账目"):
        empty_df = pd.DataFrame(columns=["日期", "店名", "金额", "分类", "人民币金额"])
        conn.update(spreadsheet=spreadsheet_url, data=empty_df)
        st.success("账本已清空！")
        st.rerun()

st.title("💹 AI 智能记账 (全能版)")

# --- 模式选择 ---
mode = st.radio("选择记账方式：", ["📷 拍照识别", "✍️ 手动录入", "🤖 智能话语"])

if mode == "📷 拍照识别":
    uploaded_file = st.file_uploader("拍摄收据", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, width=200)
        if st.button("开始 AI 识别"):
            with st.spinner("AI 分析中..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = '分析收据返回 JSON: {"date": "YYYY-MM-DD", "store": "店名", "amount": 数字, "cat": "分类"}'
                response = model.generate_content([prompt, image])
                res = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                st.success(f"已存入！折合人民币 ￥{cny}")

elif mode == "✍️ 手动录入":
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        m_date = col1.date_input("日期", datetime.now())
        m_store = col2.text_input("店名", "例如：罗森")
        m_amount = col1.number_input("金额 (日元)", min_value=1, step=1)
        m_cat = col2.selectbox("分类", ["饮食", "交通", "日用品", "娱乐", "其他"])
        if st.form_submit_button("确认存入"):
            cny = save_to_sheet(str(m_date), m_store, m_amount, m_cat)
            st.success(f"手动记账成功！折合 ￥{cny}")

elif mode == "🤖 智能话语":
    user_text = st.text_input("输入一句话记账", placeholder="例如：刚才在松屋吃了500")
    if st.button("AI 自动解析"):
        if user_text:
            with st.spinner("AI 理解中..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f'从这段话提取信息并返回JSON: "{user_text}"。格式: {{"date": "{datetime.now().strftime("%Y-%m-%d")}", "store": "店名", "amount": 数字, "cat": "分类"}}'
                response = model.generate_content(prompt)
                res = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                st.success(f"AI 听懂了！已存入：{res['store']} {res['amount']}日元")

st.divider()
if st.checkbox("查看云端历史记录"):
    data = conn.read(spreadsheet=spreadsheet_url)
    st.dataframe(data.sort_index(ascending=False), use_container_width=True)
