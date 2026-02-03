import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# --- 核心配置 ---
# 你的专属 Google Gemini API Key
GOOGLE_API_KEY = "AIzaSyDFdrO6Hx1qpZbUDXLPwkcuU3kgb3f2h0U"
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="AI 智能记账助手", layout="centered")

# --- 界面设计 ---
st.title("💹 AI 智能记账 (日本版)")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("用户设置")
    username = st.text_input("当前用户", value="Yorin")
    st.info("提示：上传日本便利店或超市收据，AI 会自动识别金额。")

# 拍照上传组件
uploaded_file = st.file_uploader("📷 点击拍照或上传收据照片", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # 展示图片预览
    image = Image.open(uploaded_file)
    st.image(image, caption="已上传的收据预览", use_container_width=True)
    
    if st.button("🚀 开始 AI 智能分析", use_container_width=True):
        with st.spinner("AI 正在阅读收据内容，请稍候..."):
            try:
                # 调用 Gemini 1.5 Flash 模型
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 提示词（针对日本收据深度优化）
                prompt = """
                你是一个专业的财务记账助手。请分析这张收据图片，并提取以下信息：
                1. 商店名称 (store_name)
                2. 总计金额 (total_amount) - 只要数字
                3. 消费日期 (date)
                4. 消费分类 (category) - 比如：饮食、日用品、交通等
                
                请严格按 JSON 格式输出，不要有任何多余的解释文字。
                格式样例如下：
                {"store_name": "LAWSON", "total_amount": 540, "date": "2026-02-01", "category": "饮食"}
                """
                
                response = model.generate_content([prompt, image])
                
                # 解析返回的 JSON
                result = json.loads(response.text.replace('```json', '').replace('```', ''))
                
                # 展示识别结果
                st.success("✅ 识别完成！")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("店名", result['store_name'])
                    st.metric("分类", result['category'])
                with col2:
                    st.metric("总金额", f"¥{result['total_amount']}")
                    st.metric("日期", result['date'])
                
                # 保存为表格展示
                df = pd.DataFrame([result])
                st.table(df)
                
            except Exception as e:
                st.error(f"识别出错啦，请重试。错误信息: {e}")

# 页脚
st.divider()
st.caption("Developed by Yorin | Powered by Gemini AI")
