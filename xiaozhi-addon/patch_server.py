#!/usr/bin/env python3
"""
Patches for xiaozhi-server HAOS add-on compatibility.
Applied during Docker build after server code is copied.
"""
import pathlib

# ── Patch 1: Make modelscope import optional ─────────────────────────
# Models are pre-downloaded in the Docker image, so modelscope is not needed.
p = pathlib.Path('core/providers/asr/sherpa_onnx_local.py')
t = p.read_text(encoding='utf-8')
t = t.replace(
    'from modelscope.hub.file_download import model_file_download',
    'try:\n    from modelscope.hub.file_download import model_file_download\n'
    'except ImportError:\n    model_file_download = None'
)

# ── Patch 3: Add Whisper + Parakeet/Transducer ASR support ───────────
# sherpa_onnx_local.py only supports SenseVoice and Paraformer.
# We add Whisper (from_whisper) and NeMo Transducer (from_transducer) support.

# 3a. Store whisper_language from config for later use
t = t.replace(
    '        # 初始化模型文件路径\n'
    '        model_files = {',
    '        # 初始化模型文件路径\n'
    '        self.whisper_language = config.get("language", "fr")\n'
    '        model_files = {'
)

# 3b. Skip modelscope download for Whisper/Transducer (different file names, pre-downloaded)
t = t.replace(
    '                    logger.bind(tag=TAG).info(f"正在下载模型文件: {file_name}")\n'
    '                    model_file_download(',
    '                    if self.model_type in ("whisper", "transducer"):\n'
    '                        continue  # Different file structure, pre-downloaded\n'
    '                    logger.bind(tag=TAG).info(f"正在下载模型文件: {file_name}")\n'
    '                    model_file_download('
)

# 3c. Add Whisper + Transducer model initialization cases (before paraformer)
t = t.replace(
    '            if self.model_type == "paraformer":',
    '            if self.model_type == "transducer":\n'
    '                logger.bind(tag=TAG).info("Loading NeMo Transducer model (Parakeet V3)")\n'
    '                self.model = sherpa_onnx.OfflineRecognizer.from_transducer(\n'
    '                    encoder=os.path.join(self.model_dir, "encoder.int8.onnx"),\n'
    '                    decoder=os.path.join(self.model_dir, "decoder.int8.onnx"),\n'
    '                    joiner=os.path.join(self.model_dir, "joiner.int8.onnx"),\n'
    '                    tokens=os.path.join(self.model_dir, "tokens.txt"),\n'
    '                    num_threads=4,\n'
    '                    sample_rate=16000,\n'
    '                    feature_dim=80,\n'
    '                    decoding_method="greedy_search",\n'
    '                    model_type="nemo_transducer",\n'
    '                )\n'
    '            elif self.model_type == "whisper":\n'
    '                logger.bind(tag=TAG).info(f"Loading Whisper model for language: {self.whisper_language}")\n'
    '                self.model = sherpa_onnx.OfflineRecognizer.from_whisper(\n'
    '                    encoder=os.path.join(self.model_dir, "small-encoder.int8.onnx"),\n'
    '                    decoder=os.path.join(self.model_dir, "small-decoder.int8.onnx"),\n'
    '                    tokens=os.path.join(self.model_dir, "small-tokens.txt"),\n'
    '                    language=self.whisper_language,\n'
    '                    task="transcribe",\n'
    '                    num_threads=2,\n'
    '                )\n'
    '            elif self.model_type == "paraformer":'
)

p.write_text(t, encoding='utf-8')
print('[patch] sherpa_onnx_local.py: modelscope optional + Whisper + Transducer ASR support')

# ── Patch 2: HTTP server - request logging + routes without trailing slash ──
p = pathlib.Path('core/http_server.py')
t = p.read_text(encoding='utf-8')

# 2a. Add logging middleware
t = t.replace(
    '                app = web.Application()',
    '                @web.middleware\n'
    '                async def _log_all_requests(request, handler):\n'
    '                    self.logger.bind(tag="http").info(\n'
    '                        f"HTTP {request.method} {request.path} from {request.remote}"\n'
    '                    )\n'
    '                    return await handler(request)\n'
    '                app = web.Application(middlewares=[_log_all_requests])'
)

# 2b. Add OTA routes without trailing slash
t = t.replace(
    '                # \u6dfb\u52a0\u8def\u7531',
    '                    # Routes without trailing slash (ESP32 device compatibility)\n'
    '                    app.router.add_get("/xiaozhi/ota", self.ota_handler.handle_get)\n'
    '                    app.router.add_post("/xiaozhi/ota", self.ota_handler.handle_post)\n'
    '                    app.router.add_options("/xiaozhi/ota", self.ota_handler.handle_options)\n'
    '                # \u6dfb\u52a0\u8def\u7531'
)

p.write_text(t, encoding='utf-8')
print('[patch] http_server.py: request logging + routes without trailing slash')

# ── Patch 4: Strip accents from text sent to ESP32 display ──────────
# The ESP32 screen font doesn't support accented characters (é→□).
# We add unicodedata-based accent stripping in sendAudioHandle.py.
p = pathlib.Path('core/handle/sendAudioHandle.py')
t = p.read_text(encoding='utf-8')

# 4a. Add unicodedata import
t = t.replace(
    'import json\nimport time',
    'import json\nimport time\nimport unicodedata'
)

# 4b. Add strip_accents helper function after TAG definition
t = t.replace(
    "TAG = __name__\n"
    "# 音频帧时长（毫秒）",
    "TAG = __name__\n\n"
    "def _strip_accents(text):\n"
    "    \"\"\"Remove accents for ESP32 display (font lacks accented chars).\"\"\"\n"
    "    if not text:\n"
    "        return text\n"
    "    nfkd = unicodedata.normalize('NFKD', text)\n"
    "    return ''.join(c for c in nfkd if not unicodedata.combining(c))\n\n"
    "# 音频帧时长（毫秒）"
)

# 4c. Strip accents in send_tts_message (LLM response text on screen)
t = t.replace(
    '        message["text"] = textUtils.check_emoji(text)',
    '        message["text"] = _strip_accents(textUtils.check_emoji(text))'
)

# 4d. Strip accents in send_stt_message (ASR transcription on screen)
t = t.replace(
    '    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)\n'
    '    await conn.websocket.send(\n'
    '        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})',
    '    stt_text = _strip_accents(textUtils.get_string_no_punctuation_or_emoji(display_text))\n'
    '    await conn.websocket.send(\n'
    '        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})'
)

p.write_text(t, encoding='utf-8')
print('[patch] sendAudioHandle.py: strip accents for ESP32 display')
