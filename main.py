import os
import re
import base64
from pathlib import Path
import streamlit as st
try:
    import markdown
except ImportError:
    markdown = None
from rag import process_urls, generate_answer

st.set_page_config(
    page_title="Real Estate Research Tool",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load banner image as base64 for background
def load_banner_base64():
    banner_path = Path(__file__).parent / "resources" / "banner.jpg"
    fallback_path = Path(r"C:\Users\URV\.gemini\antigravity-ide\brain\2bacc3da-6a60-4b67-abe2-728dcb37e8ec\city_skyline_banner_1792489188987.jpg")
    for p in [banner_path, fallback_path]:
        if p.exists():
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return ""

banner_b64 = load_banner_base64()

def render_answer_html(text: str) -> str:
    """Format markdown answer into clean, accessible HTML."""
    if not text:
        return ""
    if markdown:
        return markdown.markdown(text, extensions=['extra', 'sane_lists'])
    clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<p>{clean.replace(chr(10), '<br>')}</p>"

# Custom CSS for the exact modern card-based theme
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Global background */
    .stApp {{
        background-color: #FFFFFF;
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: #F4F7FC !important;
        border-right: 1px solid #E5E9F2;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 1.5rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }}

    /* Sidebar Header */
    .sidebar-header-box {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 4px;
    }}

    .sidebar-icon-circle {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #EBF3FE;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}

    .sidebar-title {{
        font-weight: 800;
        font-size: 17px;
        color: #0F172A;
        line-height: 1.2;
    }}

    .sidebar-subtitle {{
        font-size: 12px;
        color: #64748B;
        margin-top: 2px;
    }}

    /* Sidebar Cards */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 10px 14px 12px 14px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    }}

    .url-card-title {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 13px;
        color: #1E293B;
        margin-bottom: 8px;
    }}

    /* Sidebar text input adjustments */
    [data-testid="stSidebar"] .stTextInput {{
        margin-bottom: 0px !important;
    }}

    [data-testid="stSidebar"] .stTextInput input {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #1E293B !important;
        font-size: 13px !important;
        padding: 9px 12px !important;
    }}

    [data-testid="stSidebar"] .stTextInput input:focus {{
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
    }}

    /* Process URLs Button */
    [data-testid="stSidebar"] .stButton > button {{
        width: 100% !important;
        background-color: #1A73E8 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 14.5px !important;
        padding: 11px 16px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        box-shadow: 0 2px 4px rgba(26, 115, 232, 0.25) !important;
        transition: all 0.2s ease !important;
        margin-top: 4px !important;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: #1557B0 !important;
        box-shadow: 0 4px 10px rgba(26, 115, 232, 0.35) !important;
    }}

    /* Main Container Padding */
    .block-container {{
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1150px !important;
    }}

    /* Header Banner */
    .hero-banner {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 26px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        min-height: 135px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }}

    .hero-banner-bg {{
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 55%;
        background-image: url('data:image/jpeg;base64,{banner_b64}');
        background-size: cover;
        background-position: right center;
        mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.6) 35%, rgba(0,0,0,1) 100%);
        -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.6) 35%, rgba(0,0,0,1) 100%);
        pointer-events: none;
    }}

    .hero-content {{
        position: relative;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 18px;
    }}

    .hero-icon-box {{
        width: 52px;
        height: 52px;
        border-radius: 14px;
        background: #DBEAFE;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}

    .hero-title {{
        font-weight: 800;
        font-size: 29px;
        color: #0F172A;
        letter-spacing: -0.5px;
        line-height: 1.15;
    }}

    .hero-subtitle {{
        font-size: 14px;
        color: #64748B;
        margin-top: 5px;
        font-weight: 400;
    }}

    /* Main Area Border Container for Question */
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 14px !important;
        padding: 18px 24px 18px 24px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    }}

    /* Question Header */
    .card-header-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }}

    .card-header-left {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}

    .card-icon-circle-blue {{
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #2563EB;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 14px;
    }}

    .card-title-text {{
        font-weight: 700;
        font-size: 16px;
        color: #0F172A;
    }}

    .card-header-right-hint {{
        font-size: 13px;
        color: #64748B;
        font-weight: 400;
    }}

    /* Form styling */
    [data-testid="stForm"] {{
        border: none !important;
        padding: 0 !important;
    }}

    /* Question Input */
    [data-testid="stMain"] .stTextInput input {{
        background-color: #FFFFFF !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
        font-size: 14.5px !important;
        padding: 10px 16px !important;
    }}

    [data-testid="stMain"] .stTextInput input:focus {{
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
    }}

    /* Send button */
    [data-testid="stFormSubmitButton"] > button {{
        background-color: #1A73E8 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0 !important;
        width: 46px !important;
        height: 44px !important;
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 18px !important;
        box-shadow: 0 2px 4px rgba(26, 115, 232, 0.25) !important;
        transition: all 0.2s ease !important;
    }}

    [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: #1557B0 !important;
        box-shadow: 0 4px 8px rgba(26, 115, 232, 0.35) !important;
    }}

    /* Answer Card */
    .answer-card-box {{
        background: #FFFDF7;
        border: 1px solid #FCD34D;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(217, 119, 6, 0.06);
    }}

    .answer-badge {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 2px 4px rgba(217, 119, 6, 0.25);
    }}

    .answer-title-text {{
        font-weight: 700;
        font-size: 16px;
        color: #78350F;
        letter-spacing: -0.2px;
    }}

    .answer-text {{
        color: #1E293B;
        font-size: 15px;
        line-height: 1.7;
        margin-top: 14px;
        margin-left: 42px;
    }}

    .answer-text p {{
        margin: 0 0 12px 0;
        line-height: 1.7;
        color: #1E293B;
    }}

    .answer-text p:last-child {{
        margin-bottom: 0;
    }}

    .answer-text ul, .answer-text ol {{
        margin: 10px 0 14px 22px;
        padding-left: 0;
    }}

    .answer-text li {{
        margin-bottom: 8px;
        line-height: 1.65;
        color: #334155;
    }}

    .answer-text strong {{
        color: #0F172A;
        font-weight: 700;
    }}

    .answer-text h3, .answer-text h4 {{
        color: #78350F;
        font-size: 15px;
        font-weight: 700;
        margin: 16px 0 8px 0;
    }}

    /* Sources Card */
    .sources-card-box {{
        background: #F0F7FF;
        border: 1px solid #BFDBFE;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.05);
    }}

    .sources-title-text {{
        font-weight: 700;
        font-size: 16px;
        color: #1E40AF;
        letter-spacing: -0.2px;
    }}

    .sources-badge {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: #DBEAFE;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}

    .sources-list {{
        margin-top: 14px;
        margin-left: 40px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}

    .source-row {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }}

    .source-pill {{
        background: #DBEAFE;
        color: #1E40AF;
        font-weight: 700;
        font-size: 12px;
        padding: 2px 7px;
        border-radius: 4px;
        flex-shrink: 0;
        margin-top: 2px;
    }}

    .source-anchor {{
        color: #1D4ED8;
        font-size: 14px;
        text-decoration: underline;
        word-break: break-all;
        line-height: 1.5;
    }}
    .source-anchor:hover {{
        color: #1E40AF;
    }}
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header-box">
        <div class="sidebar-icon-circle">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
        </div>
        <div>
            <div class="sidebar-title">Data Sources</div>
            <div class="sidebar-subtitle">Add real estate articles or links</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # URL 1 Card
    with st.container(border=True):
        st.markdown("""
        <div class="url-card-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
            <span>URL 1</span>
        </div>
        """, unsafe_allow_html=True)
        url1 = st.text_input("URL 1", placeholder="Enter article URL...", label_visibility="collapsed", key="url_input_1")

    # URL 2 Card
    with st.container(border=True):
        st.markdown("""
        <div class="url-card-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
            <span>URL 2</span>
        </div>
        """, unsafe_allow_html=True)
        url2 = st.text_input("URL 2", placeholder="Enter article URL...", label_visibility="collapsed", key="url_input_2")

    # URL 3 Card
    with st.container(border=True):
        st.markdown("""
        <div class="url-card-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
            <span>URL 3</span>
        </div>
        """, unsafe_allow_html=True)
        url3 = st.text_input("URL 3", placeholder="Enter article URL...", label_visibility="collapsed", key="url_input_3")

    st.write("")
    process_url_button = st.button("🗄️  Process URLs", use_container_width=True)

    status_placeholder = st.empty()

# Processing URLs logic
if process_url_button:
    urls = [url.strip() for url in (url1, url2, url3) if url.strip()]
    if len(urls) == 0:
        status_placeholder.warning("Please provide at least one valid article URL.")
    else:
        try:
            for status in process_urls(urls):
                status_placeholder.info(status)
            status_placeholder.success("Processing complete! You can now ask questions below.")
        except Exception as e:
            status_placeholder.error(f"Error processing URLs: {e}")

# ----------------- MAIN AREA -----------------

# Header Hero Banner
st.markdown("""
<div class="hero-banner">
    <div class="hero-content">
        <div class="hero-icon-box">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="#2563EB">
                <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
            </svg>
        </div>
        <div>
            <div class="hero-title">Real Estate Research Tool</div>
            <div class="hero-subtitle">Ask questions about real estate news and get AI-powered answers</div>
        </div>
    </div>
    <div class="hero-banner-bg"></div>
</div>
""", unsafe_allow_html=True)

# Question Card
with st.container(border=True):
    st.markdown("""
    <div class="card-header-row">
        <div class="card-header-left">
            <div class="card-icon-circle-blue">?</div>
            <span class="card-title-text">Question</span>
        </div>
        <div class="card-header-right-hint">Ask anything about the provided articles</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key="question_form", clear_on_submit=False):
        col_input, col_btn = st.columns([12, 1])
        with col_input:
            query = st.text_input(
                "Question Input",
                placeholder="What is the exact purchase price of Maconns Grand?",
                label_visibility="collapsed"
            )
        with col_btn:
            submitted = st.form_submit_button("➤")

# Handle Answer generation
if "answer" not in st.session_state:
    st.session_state["answer"] = None
    st.session_state["sources"] = None

if submitted and query:
    try:
        with st.spinner("Finding answer..."):
            ans, src = generate_answer(query)
            ans_str = str(ans or "").strip()
            # Clean up redundant prefix if present
            cleaned_ans = re.sub(r'^(FINAL ANSWER:\s*)+', '', ans_str, flags=re.IGNORECASE).strip()
            st.session_state["answer"] = cleaned_ans if cleaned_ans else ans_str
            st.session_state["sources"] = src
    except RuntimeError as e:
        st.warning(str(e))
    except Exception as e:
        st.error(f"Error: {e}")

# Display Answer Card if available
if st.session_state.get("answer"):
    ans_content = str(st.session_state["answer"]).strip()

    # Automatically separate any embedded sources block into the Sources section
    sources_pattern = r'(?i)\n+\s*(?:\*{0,2}SOURCES?:?\*{0,2}|REFERENCES?:?)\s*'
    if re.search(sources_pattern, ans_content):
        parts = re.split(sources_pattern, ans_content, maxsplit=1)
        ans_content = parts[0].strip()
        if len(parts) > 1 and parts[1].strip():
            found_urls = re.findall(r'https?://[^\s\]\)\}\>\"\'】]+', parts[1])
            existing_srcs = [s.strip() for s in str(st.session_state.get("sources") or "").split("\n") if s.strip()]
            for u in found_urls:
                if u not in existing_srcs:
                    existing_srcs.append(u)
            st.session_state["sources"] = "\n".join(existing_srcs)
        st.session_state["answer"] = ans_content

    html_answer = render_answer_html(ans_content)
    st.markdown(
        '<div class="answer-card-box">'
        '<div class="card-header-left">'
        '<div class="answer-badge">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
        '<polyline points="14 2 14 8 20 8"></polyline>'
        '<line x1="16" y1="13" x2="8" y2="13"></line>'
        '<line x1="16" y1="17" x2="8" y2="17"></line>'
        '<polyline points="10 9 9 9 8 9"></polyline>'
        '</svg>'
        '</div>'
        '<span class="answer-title-text">Answer</span>'
        '</div>'
        f'<div class="answer-text">{html_answer}</div>'
        '</div>',
        unsafe_allow_html=True
    )

# Display Sources Card in a separate, dedicated section if available
if st.session_state.get("sources"):
    raw_sources = [s.strip() for s in str(st.session_state["sources"]).split("\n") if s.strip()]
    if raw_sources:
        source_rows = []
        for i, src in enumerate(raw_sources, start=1):
            source_rows.append(
                f'<div class="source-row">'
                f'<span class="source-pill">{i}</span>'
                f'<a href="{src}" target="_blank" class="source-anchor">{src}</a>'
                f'</div>'
            )
        inner_html = "".join(source_rows)

        st.markdown(
            '<div class="sources-card-box">'
            '<div class="card-header-left">'
            '<div class="sources-badge">'
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>'
            '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>'
            '</svg>'
            '</div>'
            '<span class="sources-title-text">Sources</span>'
            '</div>'
            f'<div class="sources-list">{inner_html}</div>'
            '</div>',
            unsafe_allow_html=True
        )