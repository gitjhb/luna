"""
Voice Service - TTS via 豆包(火山引擎) + STT via OpenAI Whisper
"""

import os
import uuid
import base64
import httpx
from typing import Optional


class DoubaoTTSService:
    """火山引擎豆包语音合成 - 中文语音特别清晰"""

    API_URL = "https://openspeech.bytedance.com/api/v1/tts"

    # 常用音色
    VOICES = {
        "灿灿": "BV700_streaming",       # 温暖亲切女声 (默认)
        "梓梓": "BV406_streaming",       # 活泼可爱
        "燃燃": "BV407_streaming",       # 热情开朗
        "清清": "BV002_streaming",       # 清晰自然（免费）
        "云健": "BV701_streaming",       # 沉稳大气男声
        "超哥": "BV102_streaming",       # 阳光活力
        "浩宇": "BV001_streaming",       # 标准男声（免费）
    }

    def __init__(self):
        self.app_id = os.getenv("DOUBAO_APP_ID", "")
        self.access_token = os.getenv("DOUBAO_ACCESS_TOKEN", "")
        self.cluster = os.getenv("DOUBAO_CLUSTER", "volcano_tts")
        self.default_voice = os.getenv("DOUBAO_VOICE_TYPE", "BV700_streaming")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        encoding: str = "mp3",
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
        emotion: Optional[str] = None,
    ) -> bytes:
        """
        文字转语音
        
        Args:
            text: 要合成的文本 (max 1024 bytes UTF-8)
            voice: 音色名称或ID
            encoding: mp3 / wav / ogg_opus / pcm
            speed_ratio: 语速 0.2-3.0
            volume_ratio: 音量 0.1-3.0
            pitch_ratio: 音高 0.1-3.0
            emotion: 情绪 happy / sad / angry 等

        Returns:
            音频字节
        """
        # 解析音色
        voice_type = self.VOICES.get(voice, voice) if voice else self.default_voice

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.access_token,
                "cluster": self.cluster,
            },
            "user": {"uid": "ai_companion_user"},
            "audio": {
                "voice_type": voice_type,
                "encoding": encoding,
                "rate": 24000,
                "speed_ratio": speed_ratio,
                "volume_ratio": volume_ratio,
                "pitch_ratio": pitch_ratio,
                "language": "cn",
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }

        if emotion:
            payload["audio"]["emotion"] = emotion

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer;{self.access_token}",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.API_URL, json=payload, headers=headers)
            result = resp.json()

        if result.get("code") != 3000:
            raise Exception(f"TTS error {result.get('code')}: {result.get('message')}")

        return base64.b64decode(result["data"])

    async def synthesize_long(self, text: str, **kwargs) -> bytes:
        """长文本合成，自动分句"""
        chunks = self._split_text(text, max_bytes=900)
        audio_parts = []
        for chunk in chunks:
            audio = await self.synthesize(chunk, **kwargs)
            audio_parts.append(audio)
        return b"".join(audio_parts)

    @staticmethod
    def _split_text(text: str, max_bytes: int = 900) -> list:
        import re
        sentences = re.split(r'([。！？.!?\n])', text)
        chunks, current = [], ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if len((current + sentence).encode('utf-8')) > max_bytes:
                if current:
                    chunks.append(current)
                current = sentence
            else:
                current += sentence
        if current:
            chunks.append(current)
        return chunks

    def list_voices(self) -> dict:
        return self.VOICES
