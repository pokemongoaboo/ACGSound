import streamlit as st
import requests
import json

# 从 Streamlit Secrets 获取 access_token
access_token = st.secrets["access_token"]

def generate_speech(speaker, emotion, text):
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
            "speaker": speaker,
            "emotion": emotion,
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
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 调用失败：{str(e)}")
        return None

def main():
    st.title("文字转语音生成器")

    # 检查是否有保存的角色和情绪
    if 'speaker' not in st.session_state or 'emotion' not in st.session_state:
        st.error("请先选择角色和情绪！")
        return

    # 显示当前选择的角色和情绪
    st.write(f"当前选择的角色：{st.session_state.speaker}")
    st.write(f"当前选择的情绪：{st.session_state.emotion}")

    # 文本输入
    text = st.text_area("请输入要转换为语音的文本：", "你好，这是一个测试。")

    if st.button("生成语音"):
        with st.spinner("正在生成语音..."):
            result = generate_speech(st.session_state.speaker, st.session_state.emotion, text)
        
        if result and 'audio' in result:
            st.success("语音生成成功！")
            st.audio(result['audio'])
        else:
            st.error("语音生成失败，请重试。")

if __name__ == "__main__":
    main()
