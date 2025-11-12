import os
import re
import time
from typing import Optional, Dict, Any
from google import genai
from google.genai.errors import APIError

PROMPT_TEMPLATE = (
    'Analyze the provided video. Integrate the external description. '
    'Return four sections in ENGLISH:\n'
    '1) Main Topic & Category,\n'
    '2) Onscreen Text (OCR-ish) with timestamps if possible,\n'
    '3) Full Transcript (verbatim if possible),\n'
    '4) Integrated Summary.\n'
    # 'No prose, no markdown — just pretty text.'
)

class GeminiTranscriber:
    def __init__(self, api_key: Optional[str] = None, model: str = 'gemini-2.5-flash'):
        key = api_key or os.getenv('GEMINI_API_KEY')
        if not key:
            raise ValueError('GEMINI_API_KEY not set')
        print(f"[Gemini] Using model: {model}")
        print(f"[Gemini] API key present: {bool(key)}")
        self.client = genai.Client(api_key=key)
        self.model = model

    def transcribe(self, video_path: str, description_path: Optional[str] = None) -> Dict[str, Any]:
        print(f"[Gemini] Starting transcription for: {video_path}")
        prompt = self._build_prompt(description_path)

        try:
            print("[Gemini] Uploading file…")
            f = self.client.files.upload(file=video_path)
            print(f"[Gemini] Uploaded: {f.name} (state={getattr(f, 'state', '?')})")

            print("[Gemini] Waiting for file to become ACTIVE…")
            self._wait_active(f.name)
            print("[Gemini] File is ACTIVE, sending generation request…")

            resp = self.client.models.generate_content(
                model=self.model,
                contents=[f, prompt],
            )
            print("[Gemini] Generation completed.")
            raw = getattr(resp, "text", None) or ""
            print(f"[Gemini] Response length: {len(raw)} characters")

            parsed = self._parse_sections(raw)
            print(f"[Gemini] Parsed sections: {list(parsed.keys())}")
            return {'raw': raw, **parsed}

        except Exception as e:
            print(f"[Gemini] ERROR during transcription: {e.__class__.__name__}: {e}")
            raise
        finally:
            try:
                print("[Gemini] Cleaning up remote file…")
                self.client.files.delete(name=f.name)
                print("[Gemini] File deleted.")
            except Exception as e:
                print(f"[Gemini] Cleanup warning: {e}")

    def _wait_active(self, name: str, timeout_sec: int = 180):
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                info = self.client.files.get(name=name)
                state = getattr(info, "state", None)
                print(f"[Gemini] Polling file state: {state}")
                if state == getattr(info.state, "ACTIVE", "ACTIVE"):
                    return
                if state == getattr(info.state, "FAILED", "FAILED"):
                    raise APIError('Gemini file processing failed')
            except Exception as e:
                print(f"[Gemini] Poll error: {e}")
            time.sleep(5)
        raise TimeoutError('Gemini file did not become ACTIVE in time')

    def _build_prompt(self, description_path: Optional[str]) -> str:
        desc = ''
        if description_path and os.path.exists(description_path):
            try:
                with open(description_path, 'r', encoding='utf-8') as f:
                    desc = f.read().strip()
            except Exception:
                desc = '[DESCRIPTION READ ERROR]'
        prompt = (
            PROMPT_TEMPLATE
            + '\n\n[EXTERNAL DESCRIPTION START]\n'
            + (desc or '[NO EXTERNAL DESCRIPTION]')
            + '\n[EXTERNAL DESCRIPTION END]'
        )
        print(f"[Gemini] Built prompt ({len(prompt)} chars)")
        return prompt

    def _parse_sections(self, text: str) -> Dict[str, Any]:
        """
        Parse common markdown-ish section headings in the model response.

        It tolerates:
        - numbering like '1)', '1.' or none,
        - bold markers ** **,
        - optional colon after the header,
        - any spacing/newlines,
        - and falls back to scanning with simpler heuristics.
        """
        # Normalize to make regex easier
        norm = text.replace("\r\n", "\n")

        # Build a tolerant header regex factory
        def sect(label: str) -> Optional[str]:
            # e.g. matches:
            # "1)  **Full Transcript**:\n ..." or "**Full Transcript**\n..."
            # and captures until the next numbered header or EOF
            pat = rf"""
                (?:^|\n)                           # start of text or line
                \s*(?:\d+\s*[\)\.\-]?\s*)?         # optional "1)" / "2." / "3 -"
                \*?\*?{re.escape(label)}\*?\*?     # label with optional **
                \s*:?\s*                           # optional colon
                \n+                                # newline(s)
                (.+?)                              # <-- capture section body
                (?=                                # until next header or end
                    (?:\n\s*(?:\d+\s*[\)\.\-]?\s*)?\*?\*?(?:Main Topic|Main Topic & Category|Onscreen Text|Full Transcript|Integrated Summary)\*?\*?\s*:?\s*\n)
                    | \Z
                )
            """
            m = re.search(pat, norm, flags=re.IGNORECASE | re.DOTALL | re.VERBOSE)
            return m.group(1).strip() if m else None

        topic_cat = sect("Main Topic & Category") or sect("Main Topic")
        ocr       = sect("Onscreen Text") or sect("On-screen Text") or sect("OCR")
        transcript= sect("Full Transcript") or sect("Transcript") or sect("Dialogue")
        summary   = sect("Integrated Summary") or sect("Summary") or sect("TL;DR")

        # If transcript still missing, try a coarse fallback:
        if not transcript:
            # Heuristic: everything after a line with "Full Transcript" (case/format tolerant)
            m = re.search(r"(?:^|\n).*full\s+transcript.*?\n(.*)$", norm, flags=re.IGNORECASE | re.DOTALL)
            if m:
                transcript = m.group(1).strip()

        return {
            "topic_category": topic_cat,
            "ocr": ocr,
            "transcript": transcript,
            "summary": summary,
        }
