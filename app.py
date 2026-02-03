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
# 强制使用最基础的配置
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="AI 智能记账终极版", layout="centered")

# --- 数据库连接 ---
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
    cny_val = round(float(amount) * rate, 2)
    df_existing = conn.read()
    new_data = pd.DataFrame([{"日期": date, "店名": store, "金额": amount, "分类": cat, "人民币金额": cny_val}])
    updated_df = pd.concat([df_existing, new_data], ignore_index=True)
    conn.update(data=updated_df)
    return cny_val

# --- 主界面 ---
st.title("💹 AI 智能记账 (全能版)")

mode = st.radio("选择方式：", ["📷 拍照", "✍️ 手动", "🤖 说话"])

if mode == "📷 拍照":
    uploaded_file = st.file_uploader("拍摄收据", type=["jpg", "jpeg", "png"])
    if uploaded_file and st.button("开始识别"):
        with st.spinner("AI 识别中..."):
            try:
                # 尝试用最稳妥的方式定义模型
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = 'Analyze receipt and return JSON ONLY: {"date": "YYYY-MM-DD", "store": "name", "amount": number, "cat": "food/transport/other"}'
                response = model.generate_content([prompt, Image.open(uploaded_file)])
                # 强行提取 JSON 部分
                content = response.text
                if "{" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                    res = json.loads(json_str)
                    cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                    st.success(f"✅ 记账成功！折合 ￥{cny}")
                else:
                    st.error("AI 返回内容格式不符，请重试")
            except Exception as e:
                st.error(f"识别失败: {str(e)}")

elif mode == "✍️ 手动":
    with st.form("m"):
        d = st.date_input("日期")
        s = st.text_input("店名")
        a = st.number_input("日元金额", min_value=1)
        c = st.selectbox("分类", ["饮食", "交通", "日用品", "娱乐", "其他"])
        if st.form_submit_button("确认存入"):
            cny = save_to_sheet(str(d), s, a, c)
            st.success(f"✅ 录入成功！折合 ￥{cny}")

elif mode == "🤖 说话":
    t = st.text_input("比如：在全家花了500")
    if st.button("AI 解析") and t:
        with st.spinner("思考中..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f'Return JSON ONLY for: "{t}". Format: {{"date": "{datetime.now().strftime("%Y-%m-%d")}", "store": "name", "amount": number, "cat": "category"}}'
                response = model.generate_content(prompt)
                content = response.text
                json_str = content[content.find("{"):content.rfind("}")+1]
                res = json.loads(json_str)
                cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                st.success(f"🤖 AI 已记下：{res['store']} {res['amount']}日元")
            except Exception as e:
                st.error(f"解析失败: {str(e)}")

st.divider()
if st.checkbox("🔍 查看账单"):
    try:
        st.dataframe(conn.read().sort_index(ascending=False), use_container_width=True)
    except:
        st.info("连接中...")
