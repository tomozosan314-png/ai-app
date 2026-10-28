"""Gemini API の薄いラッパー。"""

import time
from collections.abc import Iterator

from google import genai
from google.genai import errors, types

# 混雑（503）やレート制限（429）は少し待てば通ることが多いので自動で再試行する
RETRY_CODES = {429, 500, 503}
RETRY_WAITS = [2, 5, 10]  # 秒


class GeminiWriter:
    def __init__(self, api_key: str, model: str, temperature: float = 0.7):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    @staticmethod
    def list_models(api_key: str) -> list[str]:
        """この API キーで文章生成に使える Gemini モデル名の一覧（新しい順）。"""
        client = genai.Client(api_key=api_key)
        names = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "generateContent" in (m.supported_actions or [])
            and m.name.startswith("models/gemini")
            and not any(x in m.name for x in ("embedding", "tts", "image", "audio", "live"))
        ]
        return sorted(names, reverse=True)

    def stream(self, system_prompt: str, contents: list[dict]) -> Iterator[str]:
        """contents は [{"role": "user"|"model", "text": "..."}] 形式の会話履歴。"""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
        )
        payload = [
            types.Content(role=m["role"], parts=[types.Part(text=m["text"])])
            for m in contents
        ]
        for attempt in range(len(RETRY_WAITS) + 1):
            started = False
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=self.model, contents=payload, config=config
                ):
                    if chunk.text:
                        started = True
                        yield chunk.text
                return
            except errors.APIError as e:
                # 途中まで出力済みなら再試行すると文章が重複するので諦める
                if started or e.code not in RETRY_CODES or attempt == len(RETRY_WAITS):
                    raise
                time.sleep(RETRY_WAITS[attempt])
