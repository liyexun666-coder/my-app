import google.generativeai as genai
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import requests  # 用于获取实时汇率

# --- 核心配置 ---
GOOGLE_API_KEY = "AIzaSyDFdrO6Hx1qpZbUDXLPwkcuU3kgb3f2h0U"
genai.configure(api_key=GOOGLE_API_KEY)

# --- 你的 Google 表格链接 ---
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1lDUp3kONA3x_-BtWqRerbv-xOhGdRTYu6Qx85J7I4BI/edit#gid=0"

st.set_page_config(page_title="AI 智能记账专业版", layout="centered")

# 初始化表格连接
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 辅助功能：获取实时汇率 (日元 -> 人民币) ---
def get_jpy_to_cny():
    try:
        # 使用免费的汇率API
        url = "https://open.er-api.com/v6/latest/JPY"
        data = requests.get(url).json()
        return data['rates']['CNY']
    except:
        return 0.048  # 如果API失效，默认一个大概的汇率

st.title("💹 AI 智能记账 (专业版)")
st.caption("支持实时日元汇率换算 & 自动同步云端账本")

# 侧边栏：清空功能
with st.sidebar:
    st.header("⚙️ 管理员工具")
    if st.button("🗑️ 一键清空所有账目", help="点击后将抹除Google表格中的所有数据"):
        # 创建空表头，这里多加一列“人民币”
        empty_df = pd.DataFrame(columns=["日期", "店名", "金额", "分类", "人民币金额"])
        conn.update(spreadsheet=spreadsheet_url, data=empty_df)
        st.success("账本已彻底清空！")
        st.rerun()

# --- 主界面 ---
uploaded_file = st.file_uploader("📷 拍摄或上传收据", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=300)
    
    if st.button("🚀 识别并存入账本", use_container_width=True):
        with st.spinner("AI 正在分析并换算汇率..."):
            try:
                # 1. AI 识别
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = """分析收据返回 JSON: {"date": "YYYY-MM-DD", "store": "店名", "amount": 数字, "cat": "分类"}"""
                response = model.generate_content([prompt, image])
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                result = json.loads(clean_json)
                
                # 2. 获取汇率并计算
                rate = get_jpy_to_cny()
                cny_amount = round(result['amount'] * rate, 2)
                
                # 3. 写入表格
                df_existing = conn.read(spreadsheet=spreadsheet_url)
                new_data = pd.DataFrame([{
                    "日期": result['date'],
                    "店名": result['store'],
                    "金额": result['amount'],
                    "分类": result['cat'],
                    "人民币金额": cny_amount
                }])
                
                updated_df = pd.concat([df_existing, new_data], ignore_index=True)
                conn.update(spreadsheet=spreadsheet_url, data=updated_df)
                
                # 4. 展示结果
                st.success(f"✅ 记账成功！")
                col1, col2 = st.columns(2)
                col1.metric("日元金额", f"¥{result['amount']}")
                col2.metric("折合人民币", f"￥{cny_amount}", delta=f"汇率:{rate:.4f}")
                st.balloons()
                
            except Exception as e:
                st.error(f"操作失败：{e}")

# 查看历史
st.divider()
if st.checkbox("查看我的云端历史账单"):
    data = conn.read(spreadsheet=spreadsheet_url)
    st.dataframe(data.sort_index(ascending=False), use_container_width=True)
