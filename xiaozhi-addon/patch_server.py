#!/usr/bin/env python3
"""
Patches for xiaozhi-server HAOS add-on compatibility.
Applied during Docker build after server code is copied.
"""
import pathlib

# ── Patch 1: Make modelscope import optional ─────────────────────────
# Models are pre-downloaded in the Docker image, so modelscope is not needed.
p = pathlib.Path('core/providers/asr/sherpa_onnx_local.py')
t = p.read_text()
t = t.replace(
    'from modelscope.hub.file_download import model_file_download',
    'try:\n    from modelscope.hub.file_download import model_file_download\n'
    'except ImportError:\n    model_file_download = None'
)
p.write_text(t)
print('[patch] modelscope import made optional in sherpa_onnx_local.py')

# ── Patch 2: HTTP server - request logging + routes without trailing slash ──
# ESP32 devices may send requests to /xiaozhi/ota (without trailing slash).
# aiohttp returns 404 for unmatched paths, so we register both variants.
# Also add logging middleware to see ALL incoming HTTP requests for diagnostics.
p = pathlib.Path('core/http_server.py')
t = p.read_text()

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

# 2b. Add OTA routes without trailing slash (before the vision routes block)
t = t.replace(
    '                # \u6dfb\u52a0\u8def\u7531',
    '                    # Routes without trailing slash (ESP32 device compatibility)\n'
    '                    app.router.add_get("/xiaozhi/ota", self.ota_handler.handle_get)\n'
    '                    app.router.add_post("/xiaozhi/ota", self.ota_handler.handle_post)\n'
    '                    app.router.add_options("/xiaozhi/ota", self.ota_handler.handle_options)\n'
    '                # \u6dfb\u52a0\u8def\u7531'
)

p.write_text(t)
print('[patch] http_server.py: added request logging middleware + routes without trailing slash')
