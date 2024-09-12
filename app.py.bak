import streamlit as st
import requests
import json

def call_api():
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
        # 使用 GET 方法，同时包含 headers 和 data
        response = requests.get(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # 如果响应状态码不是 200，这将引发异常
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    st.title("API调用示例")

    if st.button("调用API"):
        with st.spinner("正在调用API..."):
            result = call_api()
        
        if "error" in result:
            st.error(f"API调用失败：{result['error']}")
        else:
            st.success("API调用成功！")
            st.json(result)

if __name__ == "__main__":
    main()
