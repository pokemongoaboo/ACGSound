import streamlit as st
from openai import OpenAI
import time
import random
import json
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import RequestException, Timeout, ConnectionError
import os
import base64

# 设置 OpenAI 客户端
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 从 Streamlit Secrets 获取 access_token
access_token = st.secrets["access_token"]

# 主角选项
story_characters = ["貓咪", "狗狗", "花花", "小鳥", "小石頭"]

# 主题选项
themes = ["親情", "友情", "冒險", "度假", "運動比賽"]

# 页面设置
st.set_page_config(page_title="互動式繪本生成器", layout="wide")
st.title("互動式繪本生成器")

# 创建一个带有重试机制的会话
def create_retrying_session(retries=5, backoff_factor=0.5, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_api_status(url, timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except RequestException:
        return False


# 生成语音
def generate_speech(emotion, text, max_retries=10):
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
    
    if not check_api_status(url):
        st.error("API 服务器当前不可用，请稍后再试。")
        return None

    session = create_retrying_session()
    for attempt in range(max_retries):
        try:
            response = session.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if 'audio' in result:
                audio_bytes = base64.b64decode(result['audio'])
                return audio_bytes
            elif 'error' in result:
                raise ValueError(f"API 返回错误: {result['error']}")
            else:
                raise ValueError("API 响应不包含 'audio' 字段")
        except Timeout:
            st.warning(f"请求超时，正在进行第 {attempt + 2} 次尝试...")
        except ConnectionError:
            st.warning(f"网络连接错误，正在进行第 {attempt + 2} 次尝试...")
        except RequestException as e:
            st.warning(f"请求异常：{str(e)}，正在进行第 {attempt + 2} 次尝试...")
        except ValueError as e:
            st.error(f"API 错误：{str(e)}")
            return None
        
        if attempt < max_retries - 1:
            wait_time = min(30, 2 ** attempt)
            st.info(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        else:
            st.error("达到最大重试次数，语音生成失败。")
            st.error(f"请求 URL: {url}")
            st.error(f"请求头: {headers}")
            st.error(f"请求数据: {json.dumps(data, indent=2)}")
            return None





# 缓存机制
@st.cache_data
def get_cached_audio(text, emotion):
    cache_dir = "audio_cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{hash(text + emotion)}.wav")
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return f.read()
    return None

def save_cached_audio(text, emotion, audio_data):
    cache_dir = "audio_cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{hash(text + emotion)}.wav")
    with open(cache_file, "wb") as f:
        f.write(audio_data)

# 生成故事转折重点
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
        model="gpt-4o-mini",
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
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成分页故事
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
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 判断情绪
def determine_emotion(text):
    prompt = f"""
    请判断以下文本的主要情绪。只能从以下选项中选择一个：
    "开心_happy", "难过_sad", "生气_angry", "中立_neutral",
    如果无法确定，请选择"中立_neutral"。
    
    文本：{text}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# 生成风格基础
def generate_style_base(story):
    prompt = f"""
    基於以下故事，請思考大方向上你想要呈現的視覺效果，這是你用來統一整體繪本風格的描述，請盡量精簡，使用英文撰寫：

    {story}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成图片
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

# 预处理 JSON
def preprocess_json(json_string):
    # 移除可能的 Markdown 代碼塊標記
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'\s*```', '', json_string)
    
    # 移除可能的註釋
    json_string = re.sub(r'//.*', '', json_string)
    
    # 確保 JSON 數組的開始和結束
    json_string = json_string.strip()
    if not json_string.startswith('['):
        json_string = '[' + json_string
    if not json_string.endswith(']'):
        json_string = json_string + ']'
    
    # 嘗試修復常見的 JSON 錯誤
    json_string = json_string.replace("'", '"')  # 將單引號替換為雙引號
    json_string = re.sub(r',\s*}', '}', json_string)  # 移除對象末尾多餘的逗號
    json_string = re.sub(r',\s*]', ']', json_string)  # 移除數組末尾多餘的逗號

    # 嘗試解析 JSON
    try:
        json_object = json.loads(json_string)
        return json.dumps(json_object)  # 返回格式化的 JSON 字符串
    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {str(e)}")
        print(f"問題的 JSON 字符串: {json_string}")
        raise

# 主函数
def main():
    # 选择或输入主角
    story_character = st.selectbox("选择或输入绘本主角:", story_characters + ["其他"])
    if story_character == "其他":
        story_character = st.text_input("请输入自定义主角:")

    # 选择或输入主题
    theme = st.selectbox("选择或输入绘本主题:", themes + ["其他"])
    if theme == "其他":
        theme = st.text_input("请输入自定义主题:")

    # 选择页数
    page_count = st.slider("选择绘本页数:", min_value=6, max_value=12, value=8)

    # 生成并选择故事转折重点
    if st.button("生成故事转折重点选项"):
        plot_points = generate_plot_points(story_character, theme)
        if plot_points:
            st.session_state.plot_points = plot_points
        else:
            st.error("未能生成有效的转折重点。请重试。")

    if 'plot_points' in st.session_state:
        plot_point = st.selectbox("选择或输入绘本故事转折重点:", 
                                  ["请选择"] + st.session_state.plot_points + ["其他"])
        if plot_point == "其他":
            plot_point = st.text_input("请输入自定义故事转折重点:")
        elif plot_point == "请选择":
            st.warning("请选择一个转折重点或输入自定义转折重点。")

    # 生成绘本
    if st.button("生成绘本"):
        try:
            with st.spinner("正在生成故事..."):
                story = generate_story(story_character, theme, plot_point, page_count)
                st.write("故事大纲：", story)

            with st.spinner("正在分页故事..."):
                paged_story = generate_paged_story(story, page_count, story_character, theme, plot_point)

            with st.spinner("正在生成风格基础..."):
                style_base = generate_style_base(story)

            # 預處理和解析 JSON 字符串
            try:
                processed_paged_story = preprocess_json(paged_story)
                pages = json.loads(processed_paged_story)
                st.success(f"成功解析 JSON。共有 {len(pages)} 頁。")
            except json.JSONDecodeError as e:
                st.error(f"JSON 解析錯誤: {str(e)}")
                st.error("無法解析生成的故事頁面。請重試或聯繫支持。")
                st.code(paged_story)  # 顯示原始的 paged_story 以便調試
                return  # 如果 JSON 解析失敗，提前退出函數

            for i, page in enumerate(pages, 1):
                st.write(f"第 {i} 页")
                text = page.get('text', '无文字')
                st.write("文字：", text)
                
                # 判断情绪
                emotion = determine_emotion(text)
                st.write("判断的情绪：", emotion)
                
                # 生成语音
                with st.spinner(f"正在生成第 {i} 页的语音..."):
                    cached_audio = get_cached_audio(text, emotion)
                    if cached_audio:
                        st.audio(cached_audio, format='audio/wav')
                        st.info("使用缓存的音频")
                    else:
                        audio_data = generate_speech(emotion, text)
                        if audio_data:
                            st.audio(audio_data, format='audio/wav')
                            save_cached_audio(text, emotion, audio_data)
                        else:
                            st.warning(f"第 {i} 页语音生成失败")
                            st.warning("使用备用文本到语音服务...")
                            # 这里可以实现备用的文本到语音服务
                
                # 生成图片
                with st.spinner(f"正在生成第 {i} 页的图片..."):
                    image_prompt = page.get('image_prompt', '')
                    if image_prompt:
                        image_url = generate_image(image_prompt, style_base)
                        st.image(image_url, caption=f"第 {i} 页的插图")
                    else:
                        st.warning(f"第 {i} 页没有图像提示")
                
                # 添加延迟以避免API限制
                time.sleep(15)  # 增加延迟时间到15秒

        except Exception as e:
            st.error(f"发生错误：{str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
