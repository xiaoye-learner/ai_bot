import gradio as gr
import os
import time
import requests
import numpy as np
import soundfile as sf
import io
import re
from faster_whisper import WhisperModel
from openai import OpenAI

# ================= 配置区域 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
TTS_API_URL = os.getenv("TTS_API_URL", "http://gpt-sovits-bot:9880")
os.environ["no_proxy"] = "localhost,127.0.0.1"    # 本地不走代理

# 关键路径
REF_AUDIO_PATH = "asset/09_大厅5.mp3"
REF_TEXT = "今日は、先生がワイルドハントにいらっしゃらないので…来ちゃいました。"
REF_LANG = "ja"
TARGET_LANG = "ja"

# 硬件配置
ASR_MODEL_SIZE = "large-v3"
SAMPLE_RATE = 32000 
# ===========================================

class AI_Core:
    def __init__(self):
        print("正在初始化系统...")
        self.brain = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        self.ear = None 
        self.history = [
             {"role": "system", "content": (
                "你不是AI助手，而是一位温柔可爱的伙伴。"
                "请用日语和我进行自然的日常对话。"
                "【回答要求】"
                "1. 严禁使用列表、序号或分点作答。"
                "2. 像朋友一样聊天。"
                "3. 不必拘束，按照你的想法来，当你觉得需要长篇幅回答时就回答多一点"
            )}
        ]

    def load_ear(self):
        if self.ear is None:
            print(f"正在加载听觉模型 ({ASR_MODEL_SIZE})...")
            self.ear = WhisperModel(ASR_MODEL_SIZE, device="cuda", compute_type="float16")

    def transcribe(self, audio_path):
        """语音转文字"""
        if not audio_path: return ""
        self.load_ear()
        segments, _ = self.ear.transcribe(audio_path, language=None)
        text = "".join([segment.text for segment in segments])
        return text

    def chat(self, user_text, history):
        """大脑思考"""
        if not user_text.strip(): return history
        self.history.append({"role": "user", "content": user_text})
        try:
            response = self.brain.chat.completions.create(
                model="deepseek-chat",
                messages=self.history,
                temperature=1.3,
                max_tokens=400
            )
            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Error: {str(e)}"

    def tts(self, text, speed, temperature, top_k, top_p, pause_delay):
        """高级语音合成"""
        sentences = re.split(r'(?<=。|！|？|\.|!|\?|~|～)\s*', text)
        sentences = [s for s in sentences if s.strip()] 
        print(f"🔄 文本已拆分为 {len(sentences)} 个片段进行合成...")

        audio_segments = []
        silence_data = np.zeros(int(32000 * pause_delay)) 

        try:
            for idx, sent in enumerate(sentences):
                print(f"  -> 正在合成第 {idx+1}/{len(sentences)} 句...")
                payload = {
                    "text": sent, "text_lang": TARGET_LANG, "ref_audio_path": REF_AUDIO_PATH,
                    "prompt_text": REF_TEXT, "prompt_lang": REF_LANG, "text_split_method": "cut5",
                    "top_k": int(top_k), "top_p": float(top_p), "temperature": float(temperature), "speed": float(speed)
                }
                res = requests.post(f"{TTS_API_URL}/tts", json=payload)
                if res.status_code == 200:
                    data, samplerate = sf.read(io.BytesIO(res.content))
                    audio_segments.append(data)
                    if idx < len(sentences) - 1: audio_segments.append(silence_data)
                else:
                    print(f"TTS Error on segment {idx}: {res.text}")

            if not audio_segments: return None
            final_audio = np.concatenate(audio_segments)
            output_file = "temp_output.wav"
            if os.path.exists(output_file): os.remove(output_file)
            sf.write(output_file, final_audio, 32000) 
            return output_file
        except Exception as e:
            print(f"TTS Process Error: {e}")
            return None

core = AI_Core()

# ================= 逻辑处理函数 =================
def process_interaction(text_input, audio_input, history, speed, temp, top_k, top_p, pause_delay):
    user_msg = ""
    if audio_input is not None:
        user_msg = core.transcribe(audio_input)
    elif text_input:
        user_msg = text_input
    
    if not user_msg: return history, None, "" 

    ai_reply = core.chat(user_msg, history)
    
    if history is None: history = []
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": ai_reply})
    
    audio_path = core.tts(ai_reply, speed, temp, top_k, top_p, pause_delay)
    return history, audio_path, ""

def change_tab(tab_name):
    """
    切换页面逻辑：
    1. 控制 Content 的 visible
    2. 控制 Button 的 variant (primary=高亮, secondary=灰色)
    """
    # 定义高亮状态
    is_chat = (tab_name == "chat")
    is_hist = (tab_name == "history")
    is_sett = (tab_name == "settings")

    return (
        # 页面可见性
        gr.update(visible=is_chat),
        gr.update(visible=is_hist),
        gr.update(visible=is_sett),
        
        # 按钮样式 
        gr.update(variant="primary" if is_chat else "secondary"),
        gr.update(variant="primary" if is_hist else "secondary"),
        gr.update(variant="primary" if is_sett else "secondary")
    )
# ================= UI 构建 =================
with gr.Blocks(title="AI Waifu WebUI") as demo:
    
    state_history = gr.State([])

    with gr.Row(equal_height=False):
        
        # --- 左侧导航栏 ---
        with gr.Column(scale=1, min_width=150):
            gr.Markdown("### 🤖 导航")
            btn_chat = gr.Button("💬 聊天模式", variant="primary")
            btn_history = gr.Button("📜 历史记录", variant="secondary")
            btn_settings = gr.Button("⚙️ 系统设置", variant="secondary")
            
            gr.Markdown("---")
            gr.Markdown("**状态监控**")
            gr.Markdown("🟢 DeepSeek: Ready")
            gr.Markdown("🟢 GPT-SoVITS: Ready")

        # --- 右侧内容区 ---
        with gr.Column(scale=5):
            
            # === 聊天页面 (默认显示) ===
            with gr.Column(visible=True) as tab_chat:
                chatbot = gr.Chatbot(
                    height=750, 
                    label="Terminal / Chat Log", 
                    avatar_images=(None, "avatar.png"),
                )
                
                # 输入区
                with gr.Row():
                    with gr.Column(scale=4):
                        with gr.Tabs():
                            with gr.TabItem("⌨️ 文字输入"):
                                txt_input = gr.Textbox(show_label=False, placeholder="输入文字，按回车发送...", lines=2)
                            with gr.TabItem("🎤 语音输入"):
                                mic_input = gr.Audio(sources=["microphone"], type="filepath", label="点击录音")
                    
                    with gr.Column(scale=1):
                        audio_output = gr.Audio(label="AI 回复", autoplay=True, interactive=False)

                # 参数区
                with gr.Accordion("🎛️ 语音调教参数 (Voice Settings)", open=True):
                    with gr.Row():
                        slider_speed = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="语速 (Speed)")
                        slider_temp = gr.Slider(0.1, 2.0, value=1.0, step=0.1, label="情感波动 (Temperature)")
                        slider_pause = gr.Slider(0.1, 2.0, value=0.6, step=0.1, label="句间停顿 (Pause Delay)")
                        slider_top_k = gr.Slider(1, 50, value=15, step=1, label="Top K")
                        slider_top_p = gr.Slider(0.1, 1.0, value=1.0, step=0.05, label="Top P")
                
                btn_send = gr.Button("发送 (Send)", variant="primary")

            # === 历史记录 (默认隐藏) ===
            with gr.Column(visible=False) as tab_history:
                gr.Markdown("## 📜 历史对话记录")
                gr.Markdown("> 这里的记录功能暂未连接数据库。")
                gr.JSON(label="Debug Data", value={"status": "Not implemented yet"})

            # === 置页面 (默认隐藏) ===
            with gr.Column(visible=False) as tab_settings:
                gr.Markdown("## ⚙️ 系统设置")
                gr.Textbox(label="DeepSeek API Key", value=DEEPSEEK_API_KEY, type="password")
                gr.Textbox(label="参考音频路径", value=REF_AUDIO_PATH)
                gr.Button("保存配置 (模拟)")

    # ================= 事件绑定 =================

    # 导航栏逻辑需要的输出组件列表 
    nav_outputs = [
        tab_chat, tab_history, tab_settings,  # 页面 Column
        btn_chat, btn_history, btn_settings   # 按钮 Button
    ]
    
    # 1. 导航栏点击切换
    btn_chat.click(lambda: change_tab("chat"), outputs=nav_outputs, show_progress="hidden")
    btn_history.click(lambda: change_tab("history"), outputs=nav_outputs, show_progress="hidden")
    btn_settings.click(lambda: change_tab("settings"), outputs=nav_outputs, show_progress="hidden")

    # 2. 聊天交互绑定
    input_components = [txt_input, mic_input, state_history, slider_speed, slider_temp, slider_top_k, slider_top_p, slider_pause]
    output_components = [chatbot, audio_output, txt_input]

    txt_input.submit(process_interaction, inputs=input_components, outputs=output_components)
    btn_send.click(process_interaction, inputs=input_components, outputs=output_components)
    mic_input.stop_recording(process_interaction, inputs=input_components, outputs=output_components)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=False)
