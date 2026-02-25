"""
Local TTS provider using sherpa-onnx with Piper VITS models.
Runs entirely on-device — no data leaves the machine.
"""
import os
import uuid
import wave
import numpy as np
import sherpa_onnx
from datetime import datetime
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.audio_file_type = "wav"

        model_dir = config.get("model_dir", "models/vits-piper-fr_FR-siwis-medium")
        model_file = config.get("model_file", "fr_FR-siwis-medium.onnx")
        speed = config.get("speed", 1.0)
        self.speaker_id = config.get("speaker_id", 0)

        model_path = os.path.join(model_dir, model_file)
        tokens_path = os.path.join(model_dir, "tokens.txt")
        data_dir = os.path.join(model_dir, "espeak-ng-data")

        logger.bind(tag=TAG).info(
            f"Loading local TTS: {model_file} (speed={speed})"
        )

        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=model_path,
                    tokens=tokens_path,
                    data_dir=data_dir,
                    length_scale=1.0 / speed,
                ),
                num_threads=2,
                provider="cpu",
            ),
        )
        self.tts = sherpa_onnx.OfflineTts(tts_config)
        self.sample_rate = self.tts.sample_rate
        logger.bind(tag=TAG).info(
            f"Local TTS ready (sample_rate={self.sample_rate})"
        )

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        try:
            audio = self.tts.generate(
                text, sid=self.speaker_id, speed=1.0
            )
            samples = np.array(audio.samples, dtype=np.float32)
            samples_int16 = (samples * 32767).astype(np.int16)

            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with wave.open(output_file, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(audio.sample_rate)
                    wf.writeframes(samples_int16.tobytes())
            else:
                import io
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(audio.sample_rate)
                    wf.writeframes(samples_int16.tobytes())
                return buf.getvalue()
        except Exception as e:
            error_msg = f"Local TTS failed: {e}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
