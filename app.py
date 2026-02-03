import streamlit as st
import google.generativeai as genai
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import requests
from datetime import datetime

# --- 核心配置 ---
# 已经换上你刚才给我的新 API Key
GOOGLE_API_KEY = "AIzaSyCAdCBSfHY9FtvAQnNPSYJHqQPLygMj8S0"
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="AI 智能记账 (正式版)", layout="centered")
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

st.title("💹 AI 智能记账 (全能版)")

mode = st.radio("选择方式：", ["📷 拍照识别", "✍️ 手动录入", "🤖 智能话语"])

if mode == "📷 拍照识别":
    uploaded_file = st.file_uploader("上传收据", type=["jpg", "jpeg", "png"])
    if uploaded_file and st.button("开始 AI 识别"):
        with st.spinner("AI 正在努力看图..."):
            try:
                # 使用最标准的模型路径
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = 'Return JSON ONLY: {"date": "YYYY-MM-DD", "store": "name", "amount": number, "cat": "food/other"}'
                response = model.generate_content([prompt, Image.open(uploaded_file)])
                
                res_text = response.text
                # 强行定位 JSON 内容
                res = json.loads(res_text[res_text.find("{"):res_text.rfind("}")+1])
                
                cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                st.success(f"✅ 记账成功！折合 ￥{cny}")
            except Exception as e:
                st.error(f"识别失败，请稍后重试: {e}")

elif mode == "✍️ 手动录入":
    with st.form("manual"):
        d, s = st.columns(2)
        date = d.date_input("日期")
        store = s.text_input("店名")
        amount = st.number_input("日元金额", min_value=1)
        cat = st.selectbox("分类", ["饮食", "交通", "日用品", "娱乐", "其他"])
        if st.form_submit_button("确认存入"):
            cny = save_to_sheet(str(date), store, amount, cat)
            st.success(f"✅ 录入成功！折合 ￥{cny}")

elif mode == "🤖 智能话语":
    t = st.text_input("想记什么？", placeholder="比如：在草加松屋吃了800日元")
    if st.button("AI 解析") and t:
        with st.spinner("AI 正在思考..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f'Return JSON ONLY for: "{t}". Format: {{"date": "{datetime.now().strftime("%Y-%m-%d")}", "store": "name", "amount": number, "cat": "food/other"}}'
                response = model.generate_content(prompt)
                res_text = response.text
                res = json.loads(res_text[res_text.find("{"):res_text.rfind("}")+1])
                cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                st.success(f"🤖 AI 记下了：{res['store']} {res['amount']}日元")
            except Exception as e:
                st.error(f"解析失败: {e}")

st.divider()
if st.checkbox("🔍 查看历史"):
    try:
        st.dataframe(conn.read().sort_index(ascending=False), use_container_width=True)
    except:
        st.info("连接云端表格中...")
