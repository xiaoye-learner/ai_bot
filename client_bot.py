import os
import time
import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
from openai import OpenAI
from colorama import Fore, Style, init

# ================= 配置区域 =================

# 1. DeepSeek API 配置
DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 2. GPT-SoVITS 服务端配置
TTS_API_URL = "http://127.0.0.1:9880"

REF_AUDIO_PATH = "asset/09_大厅5.mp3"  # 参考音频路径
REF_TEXT = "今日は、先生がワイルドハントにいらっしゃらないので…来ちゃいました。"
REF_LANG = "ja"
TARGET_LANG = "ja"

# 3. 硬件与录音配置
ASR_MODEL_SIZE = "large-v3"
SAMPLE_RATE = 44100
CHANNELS = 1
# ===================================================================

init(autoreset=True)

class AI_Waifu:
    def __init__(self):
        print(Fore.CYAN + "正在初始化系统...")
        
        # (DeepSeek)
        self.brain = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        
        # 设定人设
        self.history = [
            {"role": "system", "content": (
                "你不是AI助手，而是一位温柔可爱的伙伴"
                "请用日语和我进行自然的日常对话。"
                "【回答要求】"
                "1. 严禁使用列表、序号（如1. 2. 3.）或分点作答。"
                "2. 不要过于简短，多用一些语气词（如ね、よ、かな）来表现情感，像朋友一样多聊几句。"
                "3. 回答长度控制在2到4句话之间，像人类口语一样连贯。"
                "4. 即使我在问问题，也不要像百科全书一样回答，要用你的口吻表达看法。"
            )}
        ]
        
        # 1. (Whisper)
        self.ear = None 

    def load_ear(self):
        if self.ear is None:
            print(Fore.YELLOW + f"正在加载听觉模型 ({ASR_MODEL_SIZE})...")
            self.ear = WhisperModel(ASR_MODEL_SIZE, device="cuda", compute_type="float16")
        
    def record_audio(self):
        """录音模块：防手抖版"""
        print(Fore.CYAN + "\n[按回车键开始录音]...")
        input()
        
        # 清除缓冲区防止误触
        try:
            import msvcrt
            while msvcrt.kbhit(): msvcrt.getch()
        except: pass

        print(Fore.RED + "🔴 正在录音... (再次按回车键结束)")
        
        recording = []
        def callback(indata, frames, time, status):
            recording.append(indata.copy())
            
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback)
        stream.start()
        time.sleep(0.5) # 强制最少录制0.5秒
        input() 
        stream.stop()
        stream.close()
        
        print(Fore.CYAN + "录音结束，正在处理...")
        
        if not recording: return None
        
        audio_data = np.concatenate(recording, axis=0)
        temp_filename = "temp_input.wav"
        sf.write(temp_filename, audio_data, SAMPLE_RATE)
        return temp_filename

    def listen(self, audio_file):
        """听觉模块"""
        segments, info = self.ear.transcribe(audio_file, language=None) 
        text = "".join([segment.text for segment in segments])
        
        if text.strip():
            print(Fore.BLUE + f"👂 听到: {text}")
        else:
            print(Fore.YELLOW + "👂 (什么都没听到)")
        return text

    def think(self, text):
        """大脑模块"""
        if not text.strip(): return None
        
        self.history.append({"role": "user", "content": text})
        
        print(Fore.YELLOW + "🧠 思考中...")
        try:
            response = self.brain.chat.completions.create(
                model="deepseek-chat",
                messages=self.history,
                temperature=1.3,
                max_tokens=400
            )
            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            print(Fore.MAGENTA + f"🤖 回复: {reply}")
            return reply
        except Exception as e:
            print(Fore.RED + f"大脑宕机了: {e}")
            return None

    def speak(self, text):
        """嘴巴模块"""
        
        # --- 清理旧文件 ---
        output_file = "temp_output.wav"
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception as e:
                print(Fore.RED + f"无法删除旧文件: {e}")
        # ----------------------

        print(Fore.GREEN + "🔊 正在合成语音...")
        
        payload = {
            "text": text,
            "text_lang": TARGET_LANG,
            "ref_audio_path": REF_AUDIO_PATH,
            "prompt_text": REF_TEXT,
            "prompt_lang": REF_LANG,
            "text_split_method": "cut5",
            "top_k": 15,
            "top_p": 1.0,
            "temperature": 1.0,
            "speed": 1.0
        }
        
        try:
            response = requests.post(f"{TTS_API_URL}/tts", json=payload)
            
            if response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                data, fs = sf.read(output_file)
                sd.play(data, fs)
                sd.wait()
            else:
                print(Fore.RED + f"TTS 服务报错: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(Fore.RED + "无法连接到 TTS 服务。请检查 Docker 是否正在运行。")
        except Exception as e:
            print(Fore.RED + f"语音合成未知错误: {e}")

    def run(self):
        """主循环：增加模式选择"""
        print(Fore.WHITE + "\n==============================")
        print(Fore.WHITE + "请选择交互模式:")
        print(Fore.GREEN + "1. 语音模式 (Voice Mode)")
        print(Fore.YELLOW + "2. 文字模式 (Text Mode)")
        print(Fore.WHITE + "==============================")
        
        choice = input("请输入序号 (默认1): ").strip()
        
        # 如果选了语音模式，才加载 Whisper 模型
        if choice != '2':
            self.load_ear()

        print(Fore.GREEN + "\n系统就绪！(按 Ctrl+C 退出)")

        while True:
            try:
                user_text = ""
                
                # --- 分支逻辑 ---
                if choice == '2':
                    # 文字模式
                    print(Fore.CYAN + "\n请输入文本: ", end="")
                    user_text = input()
                else:
                    # 语音模式
                    audio_file = self.record_audio()
                    if not audio_file: continue
                    user_text = self.listen(audio_file)
                # ---------------

                if not user_text: continue
                
                # 3. 思考
                ai_reply = self.think(user_text)
                
                # 4. 说话
                if ai_reply:
                    self.speak(ai_reply)
                    
            except KeyboardInterrupt:
                print(Fore.CYAN + "\n程序已退出。再见！")
                break

if __name__ == "__main__":
    bot = AI_Waifu()
    bot.run()