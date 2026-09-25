"""
Streamlit UI for the YouTube Video Summarizer.

Run with:
    uv run streamlit run app.py
"""
import sys
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from downloader import download_subtitles, download_playlist_subtitles
from vtt_parser import parse_vtt
from llm_processor import extract_topics, create_chapters, extract_qa_pairs, build_final_summary
from md_exporter import summary_to_markdown
from pipeline import is_playlist

st.set_page_config(page_title="YouTube Summarizer", page_icon="🎬", layout="centered")
st.title("🎬 YouTube Video Summarizer")
st.caption("Paste a YouTube video or playlist URL to get a structured summary.")

url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Summarize", type="primary", disabled=not url.strip()):
    urls_to_process = []

    with st.spinner("Fetching video info..."):
        try:
            if is_playlist(url):
                video_infos = download_playlist_subtitles(url, output_dir="output")
                urls_to_process = [(vi.url, vi) for vi in video_infos]
                st.info(f"Playlist detected — {len(urls_to_process)} videos found.")
            else:
                vi = download_subtitles(url, output_dir="output")
                urls_to_process = [(url, vi)]
        except Exception as e:
            st.error(f"Failed to fetch video info: {e}")
            st.stop()

    for i, (video_url, video_info) in enumerate(urls_to_process):
        if len(urls_to_process) > 1:
            st.subheader(f"Video {i+1}/{len(urls_to_process)}: {video_info.title}")

        if not video_info.vtt_path:
            st.warning(f"⚠️ No subtitles found for **{video_info.title}** — skipping.")
            continue

        progress = st.progress(0, text="Starting...")

        try:
            progress.progress(20, text="Parsing subtitles...")
            segments = parse_vtt(video_info.vtt_path)

            progress.progress(40, text="Extracting topics...")
            topic_result = extract_topics(segments, video_info.title)

            progress.progress(60, text="Creating chapters...")
            chapters = create_chapters(segments, video_info.title, topic_result.topics)

            progress.progress(80, text="Generating Q&A...")
            qa_pairs = extract_qa_pairs(segments, video_info.title, topic_result.topics)

            progress.progress(95, text="Assembling summary...")
            summary = build_final_summary(video_info, segments, topic_result, chapters, qa_pairs)
            md = summary_to_markdown(summary)

            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

        except Exception as e:
            progress.empty()
            st.error(f"Error processing **{video_info.title}**: {e}")
            continue

        # ── Display results ────────────────────────────────────────────────────
        st.success(f"✅ {video_info.title}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Duration", summary.duration_formatted)
        col2.metric("Chapters", len(chapters))
        col3.metric("Q&A Pairs", len(qa_pairs))

        st.markdown(f"**Summary:** {summary.one_line_summary}")
        st.markdown(f"**Topics:** {', '.join(f'`{t}`' for t in summary.topics)}")

        with st.expander("📖 Chapters"):
            for ch in chapters:
                st.markdown(f"**[{ch.start_time}] {ch.title}**")
                st.markdown(ch.summary)
                for point in ch.key_points:
                    st.markdown(f"- {point}")

        with st.expander("❓ Q&A"):
            for qa in qa_pairs:
                st.markdown(f"**Q: {qa.question}**")
                st.markdown(f"A: {qa.answer}")
                st.caption(f"Timestamp: {qa.timestamp}")

        st.download_button(
            label="⬇️ Download Markdown",
            data=md,
            file_name=f"{summary.video_id}.md",
            mime="text/markdown",
            key=f"dl_{summary.video_id}",
        )

        st.divider()
