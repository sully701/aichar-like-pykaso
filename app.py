# app.py — Streamlit AI Character + Video Generator (fixed version)
import os, time, io, textwrap, requests
from pathlib import Path
from PIL import Image
import streamlit as st

# ✅ Self-install fallback for gTTS if missing
try:
    from gtts import gTTS
except ImportError:
    os.system("pip install gTTS==2.5.1")
    from gtts import gTTS

# ✅ Install moviepy only if missing (fixes build issues)
try:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
except ImportError:
    os.system("pip install moviepy==1.0.3")
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip

# ---- SETTINGS ----
st.set_page_config(page_title="AI Character Studio", page_icon="🎬", layout="centered")
st.title("🎬 AI Character Studio — Free Version")
st.write("Create AI character images, auto scripts, voice, and short videos — 100% free personal use.")

HF_IMG_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
HF_TEXT_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

# ---- Sidebar (token + settings) ----
with st.sidebar:
    st.header("🔑 Hugging Face Token")
    hf_token = st.text_input(
        "Paste your Hugging Face token here:",
        placeholder="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        type="password",
    )
    st.info("👉 Get a free token at https://huggingface.co/settings/tokens")
    st.divider()
    st.caption("If you leave it blank, it’ll use public inference (slower).")

# ---- Helper Functions ----
def hf_image(prompt, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    res = requests.post(HF_IMG_URL, headers=headers, json={"inputs": prompt}, stream=True)
    if res.status_code != 200:
        raise Exception(f"Hugging Face image failed: {res.text}")
    return res.content

def hf_text(prompt, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    res = requests.post(HF_TEXT_URL, headers=headers, json={"inputs": prompt})
    if res.status_code != 200:
        raise Exception(f"Hugging Face text failed: {res.text}")
    data = res.json()
    if isinstance(data, list) and len(data) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    return str(data)

def fallback_script(topic):
    return f"This is a short cinematic message about {topic}. Discipline beats luck. Action creates power. Keep moving forward."

def make_video(img_path, audio_path, text_overlay, duration=8, out_path="final.mp4"):
    img_clip = ImageClip(img_path).set_duration(duration)
    txt_clip = TextClip(
        text_overlay, fontsize=36, color="white", method="caption", size=(680, None)
    ).set_position(("center", 0.1)).set_duration(duration)
    audio_clip = AudioFileClip(audio_path)
    final = CompositeVideoClip([img_clip, txt_clip]).set_audio(audio_clip)
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    return out_path

# ---- Main UI ----
prompt = st.text_input(
    "🧠 Describe your character:",
    "cinematic portrait of a confident entrepreneur, golden rim light, 85mm lens",
)
topic = st.text_input("🎤 Topic for the short script:", "mindset and discipline")
duration = st.slider("🎞️ Video length (seconds):", 6, 15, 8)
lang = st.selectbox("🌎 Voice language:", ["en", "en-us", "en-uk", "es", "fr", "de"])

if st.button("🚀 Generate Character + Script + Video"):
    try:
        with st.spinner("🖼️ Creating character image..."):
            img_bytes = hf_image(prompt, hf_token)
            img_path = "tmp/character.png"
            Path("tmp").mkdir(exist_ok=True)
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            st.image(img_path, caption="Generated Character", use_column_width=True)

        with st.spinner("📝 Writing short script..."):
            try:
                script = hf_text(f"Write a short motivational monologue about {topic}.", hf_token)
            except Exception:
                script = fallback_script(topic)
            st.text_area("🎬 Generated Script:", script, height=120)

        with st.spinner("🎧 Creating voice..."):
            tts = gTTS(script, lang=lang.split("-")[0])
            audio_path = "tmp/voice.mp3"
            tts.save(audio_path)

        with st.spinner("🎥 Rendering final cinematic clip..."):
            out_path = make_video(img_path, audio_path, textwrap.fill(script, 40), duration)
            st.video(out_path)
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download MP4", f, "ai_character_clip.mp4")

        st.success("✅ Done! Your AI cinematic video is ready.")

    except Exception as e:
        st.error(f"Error: {e}")

