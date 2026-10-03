# ✨ One-Click Content Studio

Topic do → CrewAI agents poora content package banate hain.

**Agents:** Researcher · Blog Writer · LinkedIn Writer · Twitter/X Writer · SEO Editor · Fact-Checker  
**Stack:** CrewAI · Google Gemini (free tier) · DuckDuckGo search · Streamlit

## Local run
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # .env me GEMINI_API_KEY daalein
streamlit run app.py
```
Free API key: https://aistudio.google.com/apikey  (Python 3.10 - 3.12 recommended)

## Streamlit Cloud deploy
1. Code GitHub repo me push karein.
2. share.streamlit.io → New app → `app.py` select karein (Advanced settings me Python 3.11).
3. Settings → Secrets me paste karein: `GEMINI_API_KEY = "your_key"`
4. Deploy.

## Structure
```
app.py          # Streamlit UI
crew_setup.py   # agents, tasks, crew
tools.py        # DuckDuckGo search tools
```
Note: Gemini free tier me rate limits hain; app `max_rpm=8` use karti hai. Limit aaye to 1 min ruk kar retry karein.
