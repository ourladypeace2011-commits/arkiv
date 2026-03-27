import subprocess
import tempfile
from pathlib import Path

WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"
NO_SPEECH_THRESHOLD = 0.6
DEFAULT_LANGUAGE = "zh"  # 強制繁體中文，避免簡體/日文亂跳


def transcribe(media_path: str, language: str = DEFAULT_LANGUAGE) -> tuple[str, str]:
    """
    Transcribe audio from a media file using mlx-whisper.
    Returns (transcript_text, language). Returns ("", "") if no speech detected.
    """
    import mlx_whisper

    wav = _to_wav(media_path)
    if not wav:
        return "", ""

    try:
        result = mlx_whisper.transcribe(
            wav,
            path_or_hf_repo=WHISPER_MODEL,
            language=language,
            word_timestamps=True,
            condition_on_previous_text=True,
            no_speech_threshold=NO_SPEECH_THRESHOLD,
            compression_ratio_threshold=2.4,
            logprob_threshold=-1.0,
        )
        text = result.get("text", "").strip()
        lang = result.get("language", language)
        segments = result.get("segments", [])

        if not segments:
            return text, lang

        # ── Anti-Hallucination Guards ──

        # Guard 1: ALL segments are silence → no speech
        avg_no_speech = sum(s.get("no_speech_prob", 0) for s in segments) / len(segments)
        if avg_no_speech > NO_SPEECH_THRESHOLD:
            return "", lang

        # Guard 2: Per-segment filtering (keep good segments, drop bad ones)
        good_segments = []
        for s in segments:
            seg_text = s.get("text", "").strip()
            if not seg_text:
                continue
            # Skip segments with very high no_speech
            if s.get("no_speech_prob", 0) > 0.8:
                continue
            # Skip segments with extremely low confidence
            if s.get("avg_logprob", 0) < -1.5:
                continue
            # Skip segments with extreme compression (hallucination loops)
            if s.get("compression_ratio", 1) > 3.0:
                continue
            good_segments.append(seg_text)

        if not good_segments:
            return "", lang

        filtered_text = " ".join(good_segments).strip()

        # Guard 3: Text-level repetition (e.g. "輪輪輪輪" or "你只會你只會")
        if _is_repetitive(filtered_text):
            return "", lang

        # Guard 4: Character-level repetition (e.g. "蕭希蕭希蕭希")
        if _has_char_loops(filtered_text):
            filtered_text = _remove_char_loops(filtered_text)

        return filtered_text, lang
    finally:
        Path(wav).unlink(missing_ok=True)


def _is_repetitive(text: str, window: int = 6, threshold: float = 0.35) -> bool:
    """Detect looping/repetitive hallucination by checking n-gram repetition ratio."""
    if len(text) < window * 3:
        return False
    chunks = [text[i:i+window] for i in range(0, len(text) - window, window)]
    unique = len(set(chunks))
    return unique / len(chunks) < threshold


def _has_char_loops(text: str, min_pattern: int = 2, min_repeats: int = 3) -> bool:
    """Detect character-level loops like 蕭希蕭希蕭希."""
    import re
    # Match any 2-4 char pattern repeated 3+ times
    return bool(re.search(r'(.{2,4})\1{2,}', text))


def _remove_char_loops(text: str) -> str:
    """Remove character-level loops, keep one instance."""
    import re
    return re.sub(r'(.{2,4})\1{2,}', r'\1', text)


def _to_wav(media_path: str) -> str | None:
    out = tempfile.mktemp(suffix=".wav")
    cmd = [
        "ffmpeg", "-i", media_path,
        "-ac", "1", "-ar", "16000",
        "-map", "a:0",
        "-loglevel", "error",
        out, "-y"
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not Path(out).exists():
        return None
    return out
