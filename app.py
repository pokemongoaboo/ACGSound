import streamlit as st
import requests
import json

# 设置页面标题
st.set_page_config(page_title="角色列表", page_icon="🎭")

# 标题
st.title("角色列表")

# 函数：获取角色列表
def get_character_list():
    url = "https://infer.acgnai.top/infer/spks"
    headers = {
        "content-type": "application/json"
    }
    params = {
        "type": "tts",
        "brand": "gpt-sovits",
        "name": "anime"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # 如果请求不成功，将引发异常
        return response.json()
    except requests.RequestException as e:
        st.error(f"获取角色列表时出错: {e}")
        return None

# 获取角色列表
data = get_character_list()

if data and "spklist" in data:
    # 显示成功消息
    st.success(data["message"])
    
    # 显示角色列表
    for character, emotions in data["spklist"].items():
        st.subheader(character)
        st.write("情绪:", ", ".join(emotions))
        st.divider()
else:
    st.error("无法获取角色列表，请稍后再试。")

# 添加页脚
st.markdown("---")
st.markdown("由Streamlit提供支持 | 数据来源: infer.acgnai.top")
