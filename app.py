# app.py
import streamlit as st
import requests, os, io, time, textwrap
from PIL import Image
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
from pathlib import Path

st.set_page_config(page_title="AI Studio — Starter", page_icon="🎬", layout="centered")
st.title("🎬 AI Studio — Character → Script → Voice → Video (Starter)")
st.write("Generate a cinematic character image, auto-generate a short script, add TTS voice, and render a short cinematic video — free to run for personal use.")

# ---- SETTINGS ----
HF_API_URL_IMG = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
HF_API_URL_TEXT = "https://api-inference.huggingface.co/models/google/flan-t5-base"
DEFAULT_DURATION = 10  # seconds for the final clip

# Helpers
def call_hf_inference_image(prompt, hf_token):
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    payload = {"inputs": prompt}
    # Hugging Face inference returns bytes for many image models
    res = requests.post(HF_API_URL_IMG, headers=headers, json=payload, stream=True, timeout=120)
    if res.status_code != 200:
        raise Exception(f"Hugging Face image inference failed: {res.status_code} {res.text}")
    return res.content

def call_hf_text_gen(prompt, hf_token):
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    payload = {"inputs": prompt}
    res = requests.post(HF_API_URL_TEXT, headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise Exception(f"Hugging Face text inference failed: {res.status_code} {res.text}")
    data = res.json()
    # try several common response shapes
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    if isinstance(data, list) and len(data) and isinstance(data[0], dict) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    return str(data)

def generate_script_from_template(topic):
    lines = [
        f"This is a short piece about {topic}.",
        "Listen closely — the moment you decide to act, everything changes.",
        "Discipline beats talent when talent won't show up. Believe it.",
        "Now choose: will you move, or will you watch others move instead?",
    ]
    return " ".join(lines)

def save_bytes_to_file(b, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b)

def make_video_from_image(img_path, audio_path, text_overlay, duration=DEFAULT_DURATION, out_path="output.mp4"):
    # Simple cinematic pan/zoom + overlay + audio
    img = Image.open(img_path)
    # target mobile-friendly resolution
    target_w, target_h = 720, 1280
    clip = ImageClip(img_path).set_duration(duration).resize(height=target_h)
    txt = TextClip(text_overlay, fontsize=36, font='Arial', color='white', method='caption', size=(target_w - 80, None))
    txt = txt.set_position(("center", 0.08 * target_h)).set_duration(duration)
    audio_clip = AudioFileClip(audio_path)
    if audio_clip.duration > duration:
        audio_clip = audio_clip.subclip(0, duration)
    final = CompositeVideoClip([clip, txt]).set_audio(audio_clip).set_duration(duration)
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    return out_path

# UI
with st.sidebar:
    st.header("Settings")
    st.write("Add your Hugging Face token (recommended for speed/reliability).")
    hf_token = st.text_input("Hugging Face API token (optional)", type="password")
    st.info("If you don't add a token, the app will still use fallback text generation and may be slower due to public queues. Get one (free) at https://huggingface.co/settings/tokens")

prompt = st.text_input("Describe your character (e.g., 'cinematic portrait of a confident entrepreneur, golden rim light, filmic')", value="cinematic portrait of a confident entrepreneur, golden rim light, filmic")
topic = st.text_input("What is the short script topic? (e.g., 'mindset and hustle')", value="mindset and hustle")
duration = st.slider("Final video length (seconds)", min_value=6, max_value=20, value=10, step=1)
voice_lang = st.selectbox("Voice language (gTTS)", options=["en","en-us","en-uk","es","fr","de"], index=0)

if st.button("Create character image + script + video"):
    if not prompt:
        st.error("Please describe the character.")
    else:
        try:
            with st.spinner("Generating character image..."):
                img_bytes = call_hf_inference_image(prompt, hf_token)
                img_path = "tmp/generated_character.png"
                save_bytes_to_file(img_bytes, img_path)
                st.image(img_path, caption="Generated character", use_column_width=True)

            with st.spinner("Generating short script..."):
                try:
                    if hf_token:
                        text_prompt = f"Write a short cinematic motivational script about: {topic}. Keep it punchy, ~30-60 words."
                        script = call_hf_text_gen(text_prompt, hf_token)
                    else:
                        script = generate_script_from_template(topic)
                except Exception:
                    script = generate_script_from_template(topic)
                st.markdown("**Script (editable):**")
                script = st.text_area("Script", value=script, height=130)

            with st.spinner("Generating voice (gTTS)..."):
                tts = gTTS(script, lang=voice_lang.split("-")[0])
                audio_path = "tmp/tts_audio.mp3"
                Path("tmp").mkdir(parents=True, exist_ok=True)
                tts.save(audio_path)

            with st.spinner("Rendering cinematic video (moviepy)... This may take ~20-60s on Streamlit Cloud"):
                out_path = f"tmp/final_{int(time.time())}.mp4"
                make_video_from_image(img_path, audio_path, textwrap.fill(script, width=40), duration=duration, out_path=out_path)
                st.success("Video ready!")
                with open(out_path, "rb") as f:
                    video_bytes = f.read()
                st.video(video_bytes)
                st.download_button("Download MP4", data=video_bytes, file_name="ai_character_clip.mp4", mime="video/mp4")
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
            st.exception(exc)
