import streamlit as st
import google.generativeai as genai
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import requests
from datetime import datetime

# --- 核心配置 ---
# 你的 Gemini API Key
GOOGLE_API_KEY = "AIzaSyDFdrO6Hx1qpZbUDXLPwkcuU3kgb3f2h0U"
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="AI 智能记账全能版", layout="centered")

# --- 数据库连接 ---
# 自动读取 Streamlit Secrets 里的 [connections.gsheets] 配置
conn = st.connection("gsheets", type=GSheetsConnection)

def get_jpy_to_cny():
    """获取实时日元兑人民币汇率"""
    try:
        url = "https://open.er-api.com/v6/latest/JPY"
        data = requests.get(url, timeout=5).json()
        return data['rates']['CNY']
    except:
        return 0.048  # 备用汇率

def save_to_sheet(date, store, amount, cat):
    """保存数据到 Google Sheets"""
    rate = get_jpy_to_cny()
    cny_val = round(float(amount) * rate, 2)
    
    # 1. 读取现有数据
    df_existing = conn.read()
    
    # 2. 准备新行
    new_data = pd.DataFrame([{
        "日期": date, 
        "店名": store, 
        "金额": amount, 
        "分类": cat, 
        "人民币金额": cny_val
    }])
    
    # 3. 合并并更新云端表格
    updated_df = pd.concat([df_existing, new_data], ignore_index=True)
    conn.update(data=updated_df)
    return cny_val

# --- 侧边栏：管理员工具 ---
with st.sidebar:
    st.header("⚙️ 管理员工具")
    if st.button("🗑️ 一键清空所有账目"):
        # 创建空表头
        empty_df = pd.DataFrame(columns=["日期", "店名", "金额", "分类", "人民币金额"])
        conn.update(data=empty_df)
        st.success("账本已清空！")
        st.rerun()
    st.info("提示：请确保 Google 表格已分享给 Service Account 邮箱并设为『编辑器』。")

st.title("💹 AI 智能记账 (全能版)")

# --- 模式选择 ---
mode = st.radio("选择记账方式：", ["📷 拍照识别", "✍️ 手动录入", "🤖 智能话语"])

# 1. 拍照识别模式
if mode == "📷 拍照识别":
    uploaded_file = st.file_uploader("拍摄收据", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, width=250, caption="收据预览")
        if st.button("开始 AI 智能识别"):
            with st.spinner("AI 正在分析并换算汇率..."):
                try:
                    # 使用最新的模型名称以避免 404 错误
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    prompt = '分析收据内容并返回 JSON: {"date": "YYYY-MM-DD", "store": "店名", "amount": 数字, "cat": "分类"}'
                    response = model.generate_content([prompt, image])
                    
                    # 清理并解析 JSON
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    res = json.loads(clean_json)
                    
                    cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                    st.success(f"✅ 记账成功！折合人民币 ￥{cny}")
                    st.balloons()
                except Exception as e:
                    st.error(f"识别或保存失败: {e}")

# 2. 手动录入模式
elif mode == "✍️ 手动录入":
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        m_date = col1.date_input("消费日期", datetime.now())
        m_store = col2.text_input("店名/场所", placeholder="例如：罗森")
        m_amount = col1.number_input("金额 (日元)", min_value=1, step=1)
        m_cat = col2.selectbox("分类", ["饮食", "交通", "日用品", "娱乐", "其他"])
        
        if st.form_submit_button("确认存入账本"):
            try:
                cny = save_to_sheet(str(m_date), m_store, m_amount, m_cat)
                st.success(f"✅ 手动记录成功！折合 ￥{cny}")
            except Exception as e:
                st.error(f"保存失败，请检查 Secrets 配置: {e}")

# 3. 智能话语模式
elif mode == "🤖 智能话语":
    user_text = st.text_input("用中文说一句你的消费", placeholder="例如：刚才在松屋吃了500日元牛丼")
    if st.button("AI 自动解析并存入"):
        if user_text:
            with st.spinner("AI 正在理解你的话..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    prompt = f'从这段话提取信息并返回JSON: "{user_text}"。格式: {{"date": "{datetime.now().strftime("%Y-%m-%d")}", "store": "店名", "amount": 数字, "cat": "分类"}}'
                    response = model.generate_content(prompt)
                    
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    res = json.loads(clean_json)
                    
                    cny = save_to_sheet(res['date'], res['store'], res['amount'], res['cat'])
                    st.success(f"🤖 AI 听懂了！已记录：{res['store']} {res['amount']}日元")
                except Exception as e:
                    st.error(f"解析失败: {e}")

# --- 历史数据查询 ---
st.divider()
if st.checkbox("🔍 查看云端历史账单"):
    try:
        with st.spinner("正在同步云端数据..."):
            data = conn.read()
            st.dataframe(data.sort_index(ascending=False), use_container_width=True)
    except:
        st.info("目前账本为空或正在连接中...")
