from downloader import download_subtitles

info = download_subtitles("https://www.youtube.com/watch?v=Tn6-PIqc4UM")
print(f"Title: {info.title}")
print(f"Duration: {info.duration // 60}m {info.duration % 60}s")
print(f"VTT file: {info.vtt_path}")