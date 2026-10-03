"""Agents, tasks and crew for the One-Click Content Studio."""
from crewai import Agent, Crew, LLM, Process, Task

from tools import news_search, web_search

SEO_DELIMITER = "=====SEO_META====="

MODELS = {
    "Gemini 2.5 Flash (recommended, free)": "gemini/gemini-2.5-flash",
    "Gemini 2.5 Flash-Lite (fastest, free)": "gemini/gemini-2.5-flash-lite",
    "Gemini 2.0 Flash (free)": "gemini/gemini-2.0-flash",
}

LENGTHS = {"Short (~500 words)": 500, "Medium (~900 words)": 900, "Long (~1500 words)": 1500}


def build_llm(model: str, api_key: str) -> LLM:
    return LLM(model=model, api_key=api_key, temperature=0.4, max_tokens=4096)


def run_studio(cfg: dict, model: str, api_key: str, on_task_done=None) -> dict:
    """Run the full pipeline. Returns dict of section -> text."""
    llm = build_llm(model, api_key)
    topic = cfg["topic"]
    audience = cfg["audience"]
    tone = cfg["tone"]
    language = cfg["language"]
    words = LENGTHS[cfg["length"]]
    keywords = cfg.get("keywords") or "(none given - choose the best ones yourself)"

    common = dict(llm=llm, allow_delegation=False, verbose=False, max_iter=6, respect_context_window=True)

    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Collect accurate, current and well-sourced facts about '{topic}'.",
        backstory="You are a meticulous analyst. You only report what you can support with a source, "
                  "and you clearly mark anything uncertain. You never invent statistics or URLs.",
        tools=[web_search, news_search], **common)
    blogger = Agent(
        role="Expert Blog Writer",
        goal="Write an engaging, well-structured, original blog post based strictly on the research notes.",
        backstory="You are a veteran content writer who turns research into clear, useful and "
                  "human-sounding articles. You never add facts that are not in the research.",
        **common)
    linkedin = Agent(
        role="LinkedIn Content Strategist",
        goal="Create a high-performing LinkedIn post that matches the blog's facts.",
        backstory="You write scroll-stopping LinkedIn posts: strong hook, short paragraphs, "
                  "real insight, a clear call-to-action. You avoid clichés and fake claims.",
        **common)
    twitter = Agent(
        role="Twitter/X Thread Writer",
        goal="Create a punchy Twitter/X thread that matches the blog's facts.",
        backstory="You write threads that people actually finish: a sharp hook tweet, one idea per tweet, "
                  "each under 280 characters, and a strong closing tweet.",
        **common)
    seo = Agent(
        role="SEO Editor",
        goal="Polish the blog for readability and search ranking without changing the facts.",
        backstory="You are a technical SEO editor. You improve headings, keyword placement, "
                  "readability and metadata while keeping the writer's voice and the facts intact.",
        **common)
    checker = Agent(
        role="Fact-Checker",
        goal="Honestly verify every important claim in the content package against the research and the web.",
        backstory="You are a skeptical fact-checker. You flag unsupported, outdated or exaggerated claims "
                  "and never rubber-stamp content. If something is wrong you say so plainly.",
        tools=[web_search], **common)

    lang_rule = f"Write everything in {language}."

    research_t = Task(
        description=(
            f"Research the topic: '{topic}'.\nTarget audience: {audience}.\nFocus keywords: {keywords}.\n"
            "Use the search tools (3-5 searches max) to find key facts, statistics, trends, expert views "
            "and recent developments. Prefer reputable sources.\n"
            f"{lang_rule}\nDo NOT invent any data. If you cannot verify something, say so."),
        expected_output=(
            "Structured research notes in markdown: 1) Key facts & statistics (each with its source URL), "
            "2) Current trends, 3) Common questions / angles audiences care about, "
            "4) Suggested outline for an article, 5) List of sources."),
        agent=researcher)

    blog_t = Task(
        description=(
            f"Write a blog post about '{topic}' for {audience}. Tone: {tone}. Target length: about {words} words.\n"
            f"Use ONLY facts from the research notes. Naturally include these keywords: {keywords}.\n"
            "Structure: catchy title, hook intro, H2/H3 sections, short paragraphs, a conclusion with a CTA.\n"
            f"{lang_rule}"),
        expected_output="A complete blog post in markdown with title, headings and conclusion.",
        agent=blogger, context=[research_t])

    tasks = [research_t, blog_t]
    li_t = tw_t = None
    if cfg.get("linkedin", True):
        li_t = Task(
            description=(
                f"Write ONE LinkedIn post (150-250 words) promoting the blog about '{topic}'. Tone: {tone}. "
                "Start with a strong hook, use short lines, add 3-5 relevant hashtags and a call-to-action. "
                f"Use only facts from the blog/research. {lang_rule}"),
            expected_output="A ready-to-publish LinkedIn post (plain text with line breaks and hashtags).",
            agent=linkedin, context=[research_t, blog_t])
        tasks.append(li_t)
    if cfg.get("twitter", True):
        tw_t = Task(
            description=(
                f"Write a Twitter/X thread of 6-8 tweets about '{topic}'. Tone: {tone}. "
                "Number each tweet like 1/, 2/ ... Every tweet MUST be under 280 characters. "
                "First tweet = strong hook, last tweet = takeaway + CTA, max 2 hashtags overall. "
                f"Use only facts from the blog/research. {lang_rule}"),
            expected_output="A numbered Twitter/X thread, one tweet per paragraph.",
            agent=twitter, context=[research_t, blog_t])
        tasks.append(tw_t)

    seo_t = Task(
        description=(
            f"Edit the blog post for SEO and readability. Keywords: {keywords}. "
            "Improve the title, headings, keyword placement (no stuffing), intro and readability. "
            "Do NOT add new facts.\n"
            f"Output format (strict): first the FINAL polished blog in markdown, then a line containing exactly "
            f"{SEO_DELIMITER} and after it the SEO metadata: SEO title (<=60 chars), meta description (<=155 chars), "
            "URL slug, primary keyword, 5 secondary keywords, a short list of internal-link / image-alt suggestions. "
            f"{lang_rule}"),
        expected_output=f"Final blog markdown, then {SEO_DELIMITER}, then SEO metadata.",
        agent=seo, context=[blog_t])
    tasks.append(seo_t)

    check_ctx = [t for t in [research_t, seo_t, li_t, tw_t] if t is not None]
    check_t = Task(
        description=(
            "Fact-check the whole content package (blog, and social posts if present) against the research notes. "
            "List the 5-10 most important factual claims. For each one give: the claim, verdict "
            "(Verified / Unverified / Incorrect), and evidence or source. You may run up to 3 web searches for "
            "doubtful claims. Be honest - do not approve claims you cannot support.\n"
            "End with: overall reliability score out of 10, and a list of exact fixes the author should make. "
            f"{lang_rule}"),
        expected_output="A markdown fact-check report: claims table, overall score /10, required fixes.",
        agent=checker, context=check_ctx)
    tasks.append(check_t)

    agents = [researcher, blogger] + ([linkedin] if li_t else []) + ([twitter] if tw_t else []) + [seo, checker]

    crew = Crew(
        agents=agents, tasks=tasks, process=Process.sequential, verbose=False,
        memory=False, max_rpm=8,  # keeps us inside the Gemini free-tier rate limit
        task_callback=on_task_done)
    crew.kickoff()

    out = {
        "research": research_t.output.raw,
        "linkedin": li_t.output.raw if li_t else "",
        "twitter": tw_t.output.raw if tw_t else "",
        "factcheck": check_t.output.raw,
    }
    seo_raw = seo_t.output.raw
    if SEO_DELIMITER in seo_raw:
        blog, meta = seo_raw.split(SEO_DELIMITER, 1)
    else:
        blog, meta = seo_raw, "SEO metadata was not returned separately - see the blog above."
    out["blog"] = blog.strip()
    out["seo"] = meta.strip()
    return out
