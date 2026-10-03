"""One-Click Content Studio - CrewAI + Gemini (free) + DuckDuckGo + Streamlit."""
import io
import os
import sys
import time
import zipfile
import datetime as dt

try:  # Streamlit Cloud ships an old sqlite3; crewai needs a newer one
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from crew_setup import LENGTHS, MODELS, run_studio  # noqa: E402

st.set_page_config(page_title="One-Click Content Studio", page_icon="✨", layout="wide")

# ----------------------------------------------------------------- styling
st.markdown(
    """
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {background: linear-gradient(135deg,#6D5DFB 0%,#8E7BFF 45%,#22C1C3 100%);
  border-radius: 20px; padding: 34px 38px; color: #fff; margin-bottom: 22px;
  box-shadow: 0 12px 30px rgba(109,93,251,.28);}
.hero h1 {margin:0; font-size: 2.2rem; font-weight: 800; color:#fff;}
.hero p {margin: 8px 0 0; font-size: 1.05rem; opacity:.95;}
.badges span {display:inline-block; background: rgba(255,255,255,.18); padding: 4px 12px;
  border-radius: 999px; font-size:.78rem; margin: 14px 8px 0 0; backdrop-filter: blur(4px);}
.card {background:#fff; border:1px solid #E8EAF2; border-radius:16px; padding:18px 20px;
  box-shadow: 0 2px 10px rgba(20,25,50,.04);}
.pipe {display:flex; gap:10px; flex-wrap:wrap; margin: 6px 0 4px;}
.step {flex:1; min-width:150px; background:#fff; border:1px solid #E8EAF2; border-radius:14px;
  padding:12px 14px; font-size:.88rem;}
.step b {display:block; margin-bottom:2px;}
.step.done {border-color:#27AE60; background:#F0FBF4;}
.step.active {border-color:#6D5DFB; background:#F3F1FF; animation:pulse 1.3s infinite;}
.step.wait {opacity:.55;}
@keyframes pulse {0%{box-shadow:0 0 0 0 rgba(109,93,251,.35)} 100%{box-shadow:0 0 0 10px rgba(109,93,251,0)}}
.metric {background:#fff; border:1px solid #E8EAF2; border-radius:14px; padding:14px 16px; text-align:center;}
.metric .v {font-size:1.6rem; font-weight:800; color:#6D5DFB;}
.metric .l {font-size:.78rem; color:#6b7280; text-transform:uppercase; letter-spacing:.05em;}
div.stButton > button[kind="primary"] {background: linear-gradient(135deg,#6D5DFB,#22C1C3); border:none;
  border-radius: 12px; font-weight:700; padding:.65rem 1rem;}
div.stButton > button {border-radius: 10px;}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {background:#fff; border-radius:10px 10px 0 0; padding: 8px 16px;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>✨ One-Click Content Studio</h1>
  <p>Ek topic do - poora content package tayar: research, blog, LinkedIn post, Twitter thread, SEO aur fact-check.</p>
  <div class="badges"><span>🔎 Researcher</span><span>📝 Blog Writer</span><span>💼 LinkedIn</span>
  <span>🐦 Twitter/X</span><span>📈 SEO Editor</span><span>✅ Fact-Checker</span></div>
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------- state
st.session_state.setdefault("history", [])
st.session_state.setdefault("result", None)
st.session_state.setdefault("topic", "")


def get_secret(name: str) -> str:
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    default_key = get_secret("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API key", value=default_key, type="password",
                            help="Free key: aistudio.google.com/apikey")
    if not api_key:
        st.caption("🔑 [Free key yahan se banayein](https://aistudio.google.com/apikey)")
    model_label = st.selectbox("Model", list(MODELS.keys()))

    st.markdown("### 🎯 Content options")
    audience = st.text_input("Target audience", "Students & young professionals")
    tone = st.selectbox("Tone", ["Professional", "Friendly & conversational", "Inspirational",
                                 "Technical", "Persuasive", "Humorous"])
    language = st.selectbox("Language", ["English", "Urdu", "Roman Urdu", "Hindi"])
    length = st.select_slider("Blog length", options=list(LENGTHS.keys()), value="Medium (~900 words)")
    c1, c2 = st.columns(2)
    want_li = c1.toggle("LinkedIn", True)
    want_tw = c2.toggle("Twitter/X", True)

    st.markdown("### 🕘 History")
    if not st.session_state.history:
        st.caption("Abhi koi generation nahi hui.")
    for i, h in enumerate(reversed(st.session_state.history[-6:])):
        if st.button(f"{h['time']} · {h['topic'][:28]}", key=f"h{i}", use_container_width=True):
            st.session_state.result = h
            st.rerun()
    if st.session_state.history and st.button("🗑️ Clear history", use_container_width=True):
        st.session_state.history = []
        st.session_state.result = None
        st.rerun()

# ------------------------------------------------------------------- input
EXAMPLES = ["AI agents in healthcare", "Remote work productivity tips", "Beginner's guide to investing in Pakistan"]
st.markdown("#### 💡 Aapka topic")
st.text_area("Topic", key="topic", height=90, label_visibility="collapsed",
             placeholder="e.g. How small businesses can use AI to save time")
cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
    col.button(ex, key=f"ex_{ex}", use_container_width=True,
               on_click=lambda e=ex: st.session_state.update(topic=e))
keywords = st.text_input("Focus keywords (optional, comma separated)", placeholder="ai, automation, productivity")

go = st.button("🚀 Generate Content Package", type="primary", use_container_width=True)


# --------------------------------------------------------------- pipeline
def pipeline_html(labels, done, active):
    html = '<div class="pipe">'
    for i, (icon, name) in enumerate(labels):
        cls = "done" if i < done else ("active" if i == active else "wait")
        state = "Done ✓" if i < done else ("Working…" if i == active else "Waiting")
        html += f'<div class="step {cls}"><b>{icon} {name}</b>{state}</div>'
    return html + "</div>"


if go:
    topic = st.session_state.topic.strip()
    if not api_key:
        st.error("Pehle sidebar me Gemini API key daalein.")
    elif len(topic) < 5:
        st.warning("Topic thora detail me likhein (kam az kam 5 characters).")
    else:
        labels = [("🔎", "Researcher"), ("📝", "Blog Writer")]
        if want_li:
            labels.append(("💼", "LinkedIn Writer"))
        if want_tw:
            labels.append(("🐦", "Twitter Writer"))
        labels += [("📈", "SEO Editor"), ("✅", "Fact-Checker")]

        holder = st.empty()
        state = {"done": 0}
        holder.markdown(pipeline_html(labels, 0, 0), unsafe_allow_html=True)

        def on_done(_output):
            state["done"] += 1
            holder.markdown(pipeline_html(labels, state["done"], state["done"]), unsafe_allow_html=True)

        cfg = dict(topic=topic, audience=audience, tone=tone, language=language, length=length,
                   keywords=keywords, linkedin=want_li, twitter=want_tw)
        start = time.time()
        try:
            with st.spinner("Agents kaam kar rahe hain… free tier me 2-5 minute lag sakte hain."):
                                order = [MODELS[model_label]] + [m for m in MODELS.values() if m != MODELS[model_label]]
                out = None
                for n, mdl in enumerate(order):
                    state["done"] = 0
                    holder.markdown(pipeline_html(labels, 0, 0), unsafe_allow_html=True)
                    try:
                        out = run_studio(cfg, mdl, api_key, on_done)
                        break
                    except Exception as e:
                        busy = any(k in str(e) for k in ("503", "UNAVAILABLE", "high demand", "429"))
                        if busy and n < len(order) - 1:
                            st.toast("Model busy hai, dusra model try ho raha hai…")
                            time.sleep(10)
                            continue
                        raise
            out.update(topic=topic, time=dt.datetime.now().strftime("%H:%M"),
                       seconds=int(time.time() - start), agents=len(labels))
            st.session_state.result = out
            st.session_state.history.append(out)
            holder.markdown(pipeline_html(labels, len(labels), -1), unsafe_allow_html=True)
            st.toast("Content package tayar hai! 🎉")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
                    except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg:
                st.error("Gemini servers abhi busy hain. 1-2 minute baad dobara Generate dabayein.")
            elif "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                st.error("Gemini free-tier limit hit ho gayi. 1 minute ruk kar dobara try karein "
                         "ya sidebar se 'Flash-Lite' model chunein.")
            elif "API key" in msg or "401" in msg or "403" in msg or "invalid" in msg.lower():
                st.error("API key invalid lag rahi hai. Key dobara check karein.")
            else:
                st.error("Kuch masla aa gaya. Dobara try karein.")
            with st.expander("Technical details"):
                st.code(msg)

# ----------------------------------------------------------------- results
res = st.session_state.result
if res:
    st.markdown("---")
    st.markdown(f"### 📦 Result: *{res['topic']}*")
    m = st.columns(4)
    stats = [(len(res["blog"].split()), "Blog words"), (res["agents"], "Agents used"),
             (f"{res['seconds']}s", "Time taken"), (2 if res["linkedin"] and res["twitter"] else 1, "Social channels")]
    for col, (v, l) in zip(m, stats):
        col.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>',
                     unsafe_allow_html=True)
    st.write("")

    sections = [("📝 Blog", "blog"), ("💼 LinkedIn", "linkedin"), ("🐦 Twitter/X", "twitter"),
                ("📈 SEO", "seo"), ("✅ Fact-check", "factcheck"), ("🔎 Research", "research")]
    sections = [s for s in sections if res.get(s[1])]
    tabs = st.tabs([s[0] for s in sections])
    for tab, (label, key) in zip(tabs, sections):
        with tab:
            st.markdown(res[key])
            with st.expander("📋 Copy raw text"):
                st.code(res[key], language="markdown")
            st.download_button("⬇️ Download (.md)", res[key], file_name=f"{key}.md", key=f"dl_{key}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for _, key in sections:
            z.writestr(f"{key}.md", res[key])
    st.download_button("📦 Download full package (.zip)", buf.getvalue(), file_name="content_package.zip",
                       mime="application/zip", type="primary", use_container_width=True)
else:
    st.info("👆 Topic likhein aur **Generate** dabayein. Sab agents mil kar aapka content package banayenge.")
