import streamlit as st
import requests
import json

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

def main():
    st.title("角色和情绪选择器")

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

            # 保存选择为变量
            st.session_state.speaker = selected_character
            st.session_state.emotion = selected_emotion

            # 显示保存的变量
            st.write("保存的变量：")
            st.write(f"speaker = {st.session_state.speaker}")
            st.write(f"emotion = {st.session_state.emotion}")
        else:
            st.warning(f"所选角色 {selected_character} 没有可用的情绪选项。")
    else:
        st.error("无法获取角色数据，请检查 API 连接。")

if __name__ == "__main__":
    main()
