import streamlit as st
import requests
import json

# 从 Streamlit Secrets 获取 access_token
access_token = st.secrets["access_token"]

def get_character_data():
    url = "https://infer.acgnai.top/infer/spks"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "type": "tts",
        "brand": "gpt-sovits",
        "name": "anime"
    }
    
    try:
        response = requests.get(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()['spklist']
    except requests.exceptions.RequestException as e:
        st.error(f"API 调用失败：{str(e)}")
        return None

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
    st.title("角色选择和文字转语音生成器")

    # 获取角色数据
    character_data = get_character_data()

    if character_data:
        # 创建角色选择下拉菜单
        characters = list(character_data.keys())
        selected_character = st.selectbox("选择角色", characters)

        # 获取所选角色的情绪列表
        emotions = character_data[selected_character]
        
        if emotions:
            # 创建情绪选择下拉菜单
            selected_emotion = st.selectbox("选择情绪", emotions)

            # 显示选择结果
            st.write(f"您选择的角色是：{selected_character}")
            st.write(f"您选择的情绪是：{selected_emotion}")

            # 文本输入
            text = st.text_area("请输入要转换为语音的文本：", "你好，这是一个测试。")

            if st.button("生成语音"):
                with st.spinner("正在生成语音..."):
                    result = generate_speech(selected_character, selected_emotion, text)
                
                if result and 'audio' in result:
                    st.success("语音生成成功！")
                    st.audio(result['audio'])
                else:
                    st.error("语音生成失败，请重试。")
        else:
            st.warning(f"所选角色 {selected_character} 没有可用的情绪选项。")
    else:
        st.error("无法获取角色数据，请检查 API 连接。")

if __name__ == "__main__":
    main()
