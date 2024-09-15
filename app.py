import streamlit as st
from openai import OpenAI
import time
import random
import json
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging
import socket

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
def create_retrying_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 检查网络连接
def check_network():
    try:
        socket.create_connection(("infer.acgnai.top", 80))
        return True
    except OSError:
        return False

# 生成语音（优化版）
def generate_speech(text, emotion="neutral", max_retries=10, initial_wait=0.5, max_wait=32):
    if not check_network():
        st.error("網絡連接出現問題，請檢查您的網絡設置。")
        return None

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
    wait_time = initial_wait

    for attempt in range(max_retries):
        try:
            with st.spinner(f"正在生成語音，第 {attempt + 1} 次嘗試..."):
                logger.debug(f"開始嘗試生成語音，文本：{text[:50]}...")
                response = session.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                logger.info(f"語音生成成功，嘗試次數：{attempt + 1}")
                return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"請求超時，嘗試 {attempt + 1}/{max_retries}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning("請求頻率過高，等待更長時間...")
                time.sleep(min(wait_time * 4, max_wait))
            else:
                logger.error(f"HTTP 錯誤：{e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"請求異常：{e}")
        
        if attempt < max_retries - 1:
            st.warning(f"語音生成失敗，正在重試（嘗試 {attempt + 1}/{max_retries}）...")
        else:
            st.error("語音生成失敗，請稍後重試。")
        
        wait_time = min(wait_time * 2, max_wait)
        time.sleep(wait_time)

    logger.error("達到最大重試次數，語音生成失敗")
    return None

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
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 判断情绪
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

# 生成风格基础
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
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'\s*```', '', json_string)
    json_string = json_string.strip()
    if not json_string.startswith('['):
        json_string = '[' + json_string
    if not json_string.endswith(']'):
        json_string = json_string + ']'
    return json_string

# 主函数
def main():
    st.sidebar.title("绘本生成设置")

    # 选择或输入主角
    story_character = st.sidebar.selectbox("选择或输入绘本主角:", story_characters + ["其他"])
    if story_character == "其他":
        story_character = st.sidebar.text_input("请输入自定义主角:")

    # 选择或输入主题
    theme = st.sidebar.selectbox("选择或输入绘本主题:", themes + ["其他"])
    if theme == "其他":
        theme = st.sidebar.text_input("请输入自定义主题:")

    # 选择页数
    page_count = st.sidebar.slider("选择绘本页数:", min_value=6, max_value=12, value=8)

    # 生成并选择故事转折重点
    if st.sidebar.button("生成故事转折重点选项"):
        with st.spinner("正在生成故事转折重点..."):
            plot_points = generate_plot_points(story_character, theme)
            if plot_points:
                st.session_state.plot_points = plot_points
                st.success("成功生成故事转折重点！")
            else:
                st.error("未能生成有效的转折重点。请重试。")

    if 'plot_points' in st.session_state:
        plot_point = st.sidebar.selectbox("选择或输入绘本故事转折重点:", 
                                          ["请选择"] + st.session_state.plot_points + ["其他"])
        if plot_point == "其他":
            plot_point = st.sidebar.text_input("请输入自定义故事转折重点:")
        elif plot_point == "请选择":
            st.sidebar.warning("请选择一个转折重点或输入自定义转折重点。")

    # 生成绘本
    if st.sidebar.button("生成绘本"):
        if not check_network():
            st.error("网络连接出现问题，请检查您的网络设置。")
            return

        if not story_character or not theme or plot_point in ["请选择", ""]:
            st.error("请确保已选择主角、主题和转折重点。")
            return

        try:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 生成故事
            status_text.text("正在生成故事...")
            story = generate_story(story_character, theme, plot_point, page_count)
            progress_bar.progress(20)
            st.write("故事大纲：", story)

            # 分页故事
            status_text.text("正在分页故事...")
            paged_story = generate_paged_story(story, page_count, story_character, theme, plot_point)
            progress_bar.progress(40)

            # 生成风格基础
            status_text.text("正在生成风格基础...")
            style_base = generate_style_base(story)
            progress_bar.progress(50)

            # 预处理 JSON 字符串
            processed_paged_story = preprocess_json(paged_story)
            pages = json.loads(processed_paged_story)

            st.success(f"成功解析故事结构。共有 {len(pages)} 页。")
            progress_bar.progress(60)

            # 创建一个容器来存放所有页面
            story_container = st.container()

            for i, page in enumerate(pages, 1):
                with story_container.expander(f"第 {i} 页", expanded=True):
                    text = page.get('text', '无文字')
                    st.write("文字：", text)
                    
                    # 判断情绪
                    emotion = determine_emotion(text)
                    st.write("判断的情绪：", emotion)
                    
                    # 生成语音
                    status_text.text(f"正在生成第 {i} 页的语音...")
                    speech_result = generate_speech(text, emotion.split('_')[1] if '_' in emotion else emotion)
                    if speech_result and 'audio' in speech_result:
                        st.audio(speech_result['audio'], format='audio/wav')
                    else:
                        st.warning("无法生成语音，将显示文本。")
                        st.text(text)
                    
                    # 生成图片
                    status_text.text(f"正在生成第 {i} 页的图片...")
                    image_prompt = page.get('image_prompt', '')
                    if image_prompt:
                        image_url = generate_image(image_prompt, style_base)
                        st.image(image_url, caption=f"第 {i} 页的插图")
                    else:
                        st.warning(f"第 {i} 页没有图像提示")
                
                progress_bar.progress(60 + (i / len(pages)) * 40)
                time.sleep(1)  # 添加短暂延迟以避免API限制

            progress_bar.progress(100)
            status_text.text("绘本生成完成！")
            st.balloons()

        except Exception as e:
            st.error(f"发生错误：{str(e)}")
            logger.error(f"绘本生成过程中发生错误：{str(e)}", exc_info=True)
            st.exception(e)

    # 添加使用说明
    st.sidebar.markdown("---")
    st.sidebar.subheader("使用说明")
    st.sidebar.markdown("""
    1. 在侧边栏选择或输入主角和主题。
    2. 选择绘本页数。
    3. 点击"生成故事转折重点选项"获取转折点建议。
    4. 选择一个转折点或输入自定义转折点。
    5. 点击"生成绘本"开始创作过程。
    6. 等待生成完成，您可以查看每一页的文字、语音和图片。
    """)

    # 添加关于部分
    st.sidebar.markdown("---")
    st.sidebar.subheader("关于")
    st.sidebar.info("""
    此应用使用 OpenAI 的 GPT-3.5 和 DALL-E 3 模型来生成故事和图片。
    语音由 GPT-SoVITS 模型生成。
    如有任何问题或建议，请联系开发团队。
    """)

if __name__ == "__main__":
    main()
