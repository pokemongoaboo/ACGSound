import streamlit as st
import requests
import json

def call_api():
    url = "https://infer.acgnai.top/infer/spks"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": "tts",
        "brand": "gpt-sovits",
        "name": "anime"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def main():
    st.title("API调用示例")

    if st.button("调用API"):
        with st.spinner("正在调用API..."):
            result = call_api()
        
        st.success("API调用成功！")
        st.json(result)

if __name__ == "__main__":
    main()
