import streamlit as st
from openai import OpenAI
import time
import random
import json
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 設置 OpenAI 客戶端
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 從 Streamlit Secrets 獲取 access_token
access_token = st.secrets["access_token"]

# 主角選項
story_characters = ["貓咪", "狗狗", "花花", "小鳥", "小石頭"]

# 主題選項
themes = ["親情", "友情", "冒險", "度假", "運動比賽"]

# 頁面設置
st.set_page_config(page_title="互動式繪本生成器", layout="wide")
st.title("互動式繪本生成器")

# 創建一個帶有重試機制的會話
def create_retrying_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 生成語音
def generate_speech(text):
    url = "https://infer.acgnai.top/infer/gen"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "access_token": access_token,
        "type": "tts",
        "brand": "gpt-sovits",
        "name": "anime",
        "method": "api",
        "prarm": {
            "speaker": "派蒙【原神】",
            "emotion": "happy",  # 默認情緒，可以根據需要調整
            "text": text,
            "text_language": "中文",
            "text_split_method": "按标点符号切",
            "fragment_interval": 0.3,
            "batch_size": 1,
            "batch_threshold": 0.75,
            "parallel_infer": True,
            "split_bucket": True,
            "top_k": 10,
            "top_p": 1.0,
            "temperature": 1.0,
            "speed_factor": 1.0
        }
    }
    
    session = create_retrying_session()
    try:
        response = session.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if response.status_code == 404:
            st.warning("語音生成服務暫時不可用，請稍後再試。")
        else:
            st.error(f"語音生成 API 調用失敗：{str(e)}")
        st.error(f"請求 URL: {url}")
        st.error(f"請求頭: {headers}")
        st.error(f"請求數據: {json.dumps(data, indent=2)}")
        return None

# 主函數
def main():
    # 選擇或輸入主角
    story_character = st.selectbox("選擇或輸入繪本主角:", story_characters + ["其他"])
    if story_character == "其他":
        story_character = st.text_input("請輸入自定義主角:")

    # 選擇或輸入主題
    theme = st.selectbox("選擇或輸入繪本主題:", themes + ["其他"])
    if theme == "其他":
        theme = st.text_input("請輸入自定義主題:")

    # 選擇頁數
    page_count = st.slider("選擇繪本頁數:", min_value=6, max_value=12, value=8)

    # 生成並選擇故事轉折重點
    if st.button("生成故事轉折重點選項"):
        plot_points = generate_plot_points(story_character, theme)
        if plot_points:
            st.session_state.plot_points = plot_points
        else:
            st.error("未能生成有效的轉折重點。請重試。")

    if 'plot_points' in st.session_state:
        plot_point = st.selectbox("選擇或輸入繪本故事轉折重點:", 
                                  ["請選擇"] + st.session_state.plot_points + ["其他"])
        if plot_point == "其他":
            plot_point = st.text_input("請輸入自定義故事轉折重點:")
        elif plot_point == "請選擇":
            st.warning("請選擇一個轉折重點或輸入自定義轉折重點。")

    # 生成繪本
    if st.button("生成繪本"):
        try:
            with st.spinner("正在生成故事..."):
                story = generate_story(story_character, theme, plot_point, page_count)
                st.write("故事大綱：", story)

            with st.spinner("正在分頁故事..."):
                paged_story = generate_paged_story(story, page_count, story_character, theme, plot_point)

            with st.spinner("正在生成風格基礎..."):
                style_base = generate_style_base(story)

            # 預處理 JSON 字符串
            processed_paged_story = preprocess_json(paged_story)
            pages = json.loads(processed_paged_story)

            st.success(f"成功解析 JSON。共有 {len(pages)} 頁。")

            for i, page in enumerate(pages, 1):
                st.write(f"第 {i} 頁")
                text = page.get('text', '無文字')
                st.write("文字：", text)
                
                # 生成語音
                with st.spinner(f"正在生成第 {i} 頁的語音..."):
                    speech_result = generate_speech(text)
                    if speech_result and 'audio' in speech_result:
                        st.audio(speech_result['audio'], format='audio/wav')
                    else:
                        st.warning(f"第 {i} 頁語音生成失敗")
                
                with st.spinner(f"正在生成第 {i} 頁的圖片..."):
                    image_prompt = page.get('image_prompt', '')
                    if image_prompt:
                        image_url = generate_image(image_prompt, style_base)
                        st.image(image_url, caption=f"第 {i} 頁的插圖")
                    else:
                        st.warning(f"第 {i} 頁沒有圖像提示")
                time.sleep(5)  # 添加延遲以避免API限制

        except Exception as e:
            st.error(f"發生錯誤：{str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
