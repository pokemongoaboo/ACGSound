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
def generate_speech(text, emotion="neutral"):
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

# 生成故事轉折重點
def generate_plot_points(character, theme):
    prompt = f"""為一個關於{character}的{theme}故事生成3到5個可能的故事轉折重點。
    每個重點應該簡短而有趣。
    請直接列出轉折重點，每個轉折點佔一行，不要加入額外的說明或編號。
    例如：
    主角遇到一個神秘的陌生人
    意外發現一個魔法物品
    朋友陷入危險需要救援
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    plot_points = response.choices[0].message.content.split('\n')
    return [point.strip() for point in plot_points if point.strip()]

# 生成故事
def generate_story(character, theme, plot_point, page_count):
    prompt = f"""
    請你角色扮演成一個暢銷的童書繪本作家，你擅長以孩童的純真眼光看這世界，製作出許多溫暖人心的作品。
    請以下列主題：{theme}發想故事，
    在{page_count}的篇幅內，
    說明一個{character}的故事，
    請在故事中包含以下情緒的段落：
    "开心_happy", 
    "难过_sad", 
    "生气_angry",
    "中立_neutral", 
    每種情緒至少出現一次，
    在故事說明中，不需要出現_happy, _sad, _angry, _neutral, 等文字,
    並注意在倒數第三頁加入{plot_point}的元素，
    最後的故事需要是溫馨、快樂的結局。
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成分頁故事
def generate_paged_story(story, page_count, character, theme, plot_point):
    prompt = f"""
    將以下故事大綱細分至預計{page_count}個跨頁的篇幅，每頁需要包括(text，image_prompt)，
    {page_count-3}(倒數第三頁)才可以出現{plot_point}，
    在這之前應該要讓{character}的{theme}世界發展故事更多元化。
    請以JSON格式回覆，格式如下：
    [
        {{"text": "第一頁的文字", "image_prompt": "第一頁的圖像提示"}},
        {{"text": "第二頁的文字", "image_prompt": "第二頁的圖像提示"}},
        ...
    ]

    故事：
    {story}
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 判斷情緒
def determine_emotion(text):
    prompt = f"""
    請判斷以下文本的主要情緒。只能從以下選項中選擇一個：
    "开心_happy", "难过_sad", "生气_angry","中立_neutral",
    如果無法確定，請選擇"中立_neutral"。
    
    文本：{text}
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# 生成風格基礎
def generate_style_base(story):
    prompt = f"""
    基於以下故事，請思考大方向上你想要呈現的視覺效果，這是你用來統一整體繪本風格的描述，請盡量精簡，使用英文撰寫：

    {story}
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成圖片
def generate_image(image_prompt, style_base):
    final_prompt = f"""
    Based on the image prompt: "{image_prompt}" and the style base: "{style_base}",
    please create a detailed image description including color scheme, background details, specific style, and scene details.
    Describe the current color, shape, and features of the main character.
    Include at least 3 effect words (lighting effects, color tones, rendering effects, visual styles) and 1 or more composition techniques.
    Set a random seed value of 42. Ensure no text appears in the image.
    """
    response = client.images.generate(
        model="dall-e-3",
        prompt=final_prompt,
        size="1024x1024",
        n=1
    )
    return response.data[0].url

# 預處理 JSON
def preprocess_json(json_string):
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'\s*```', '', json_string)
    json_string = json_string.strip()
    if not json_string.startswith('['):
        json_string = '[' + json_string
    if not json_string.endswith(']'):
        json_string = json_string + ']'
    return json_string

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
                
                # 判斷情緒
                emotion = determine_emotion(text)
                st.write("判斷的情緒：", emotion)
                
                # 生成語音
                with st.spinner(f"正在生成第 {i} 頁的語音..."):
                    speech_result = generate_speech(text, emotion.split('_')[1] if '_' in emotion else emotion)
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
