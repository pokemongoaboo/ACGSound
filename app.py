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
        
        # 尝试解析 JSON 响应
        try:
            return response.json()
        except json.JSONDecodeError as json_error:
            st.error(f"无法解析 JSON 响应: {json_error}")
            st.text("原始响应内容:")
            st.code(response.text)  # 显示原始响应内容
            return None
        
    except requests.RequestException as e:
        st.error(f"请求错误: {e}")
        if hasattr(e, 'response') and e.response is not None:
            st.text("响应状态码:")
            st.code(e.response.status_code)
            st.text("响应头:")
            st.code(e.response.headers)
            st.text("响应内容:")
            st.code(e.response.text)
        return None

# 获取角色列表
data = get_character_list()

if data and isinstance(data, dict) and "spklist" in data:
    # 显示成功消息
    st.success(data.get("message", "成功获取角色列表"))
    
    # 显示角色列表
    for character, emotions in data["spklist"].items():
        st.subheader(character)
        st.write("情绪:", ", ".join(emotions))
        st.divider()
elif data is not None:
    st.error("接收到的数据格式不正确")
    st.json(data)  # 显示接收到的数据
else:
    st.error("无法获取角色列表，请查看上方的错误信息。")

# 添加页脚
st.markdown("---")
st.markdown("由Streamlit提供支持 | 数据来源: infer.acgnai.top")
