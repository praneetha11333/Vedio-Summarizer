# test_parser.py
from downloader import download_subtitles
from vtt_parser import parse_vtt, segments_to_transcript

info = download_subtitles("https://www.youtube.com/watch?v=Tn6-PIqc4UM")
if info.vtt_path:
    segments = parse_vtt(info.vtt_path)
    print(f"Parsed {len(segments)} segments")
    print("\nFirst 5 segments:")
    for seg in segments[:5]:
        print(f"  [{seg.start_formatted}] {seg.text}")
    print("\nFull transcript preview:")
    print(segments_to_transcript(segments[:20]))