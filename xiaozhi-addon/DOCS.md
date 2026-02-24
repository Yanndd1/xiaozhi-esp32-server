# Xiaozhi ESP32 Server - Home Assistant Add-on

## Overview

This add-on runs the Xiaozhi ESP32 AI voice assistant server directly on your Home Assistant instance. It connects Xiaozhi ESP32 hardware devices to Claude AI (Anthropic) for voice-based interactions and smart home control.

**Key features:**
- Claude AI (Opus/Sonnet/Haiku) as the LLM backbone
- Voice Activity Detection (SileroVAD, local, no cloud)
- Speech Recognition (SherpaASR, local, no cloud)
- Text-to-Speech (Edge TTS, free Microsoft voices)
- Native Home Assistant integration (lights, switches, media players)
- No PyTorch required (lightweight ONNX-based inference)

## Requirements

- Raspberry Pi 5 (8 GB recommended) or amd64 machine
- Home Assistant OS
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Xiaozhi ESP32 device

## Installation

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**
2. Click the three dots menu (top right) > **Repositories**
3. Add: `https://github.com/Yanndd1/xiaozhi-esp32-server`
4. Click **Close**, then refresh the page
5. Find "Xiaozhi ESP32 Server" and click **Install**
6. Wait for the build to complete (first build takes ~10-15 minutes on Pi 5)

## Configuration

Go to the add-on's **Configuration** tab and set:

| Option | Description | Default |
|--------|-------------|---------|
| `anthropic_api_key` | Your Anthropic API key (required) | `""` |
| `model_name` | Claude model to use | `claude-sonnet-4-6` |
| `language` | Language code (fr, en, zh) | `fr` |
| `tts_voice` | Edge TTS voice name | `fr-FR-HenriNeural` |
| `ha_devices` | List of HA devices (see below) | `[]` |
| `prompt` | System prompt for the AI assistant | Default French prompt |

### Claude Models

| Model | Best for | Cost |
|-------|----------|------|
| `claude-opus-4-6` | Brainstorming, complex reasoning | $$$ |
| `claude-sonnet-4-6` | General use, good balance | $$ |
| `claude-haiku-4-5-20251001` | Fast responses, simple tasks | $ |

### TTS Voices

Common voices by language:

- **French:** `fr-FR-HenriNeural`, `fr-FR-DeniseNeural`
- **English:** `en-US-GuyNeural`, `en-US-JennyNeural`, `en-GB-RyanNeural`
- **Chinese:** `zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`

### Home Assistant Devices

Add your devices in the format `location,device_name,entity_id`:

```yaml
ha_devices:
  - "salon,plafonnier,light.salon_ceiling"
  - "chambre,lampe,switch.bedroom_lamp"
  - "salon,tv,media_player.salon_tv"
```

Find entity IDs in HA: **Settings > Devices & Services > Entities**

## ESP32 Device Setup

1. Put your Xiaozhi ESP32 device in configuration mode (long press the button)
2. Connect to the device's WiFi hotspot
3. Set the OTA server address to: `http://YOUR_HA_IP:8003/xiaozhi/ota/`
4. Save and restart the device

The device will connect to the server via WebSocket on port 8000.

## How It Works

The add-on uses **SUPERVISOR_TOKEN** (automatically provided by Home Assistant OS) to control your smart home devices. No manual HA token configuration is needed.

Audio pipeline:
1. ESP32 captures voice via microphone
2. Audio sent to server via WebSocket (port 8000)
3. SileroVAD detects voice activity (local, ONNX)
4. SherpaASR transcribes speech to text (local, ONNX)
5. Claude processes the text and generates a response
6. Edge TTS converts response to speech
7. Audio streamed back to ESP32

## Troubleshooting

### Add-on won't start
- Check that your Anthropic API key is valid
- Look at the add-on logs for error messages

### ESP32 device can't connect
- Ensure `host_network` is enabled (default)
- Verify the ESP32 is on the same network as your HA instance
- Check that port 8000 and 8003 are not blocked by a firewall

### HA devices not responding
- Verify entity IDs are correct in the `ha_devices` configuration
- Check the add-on logs for HA API errors
- The SUPERVISOR_TOKEN is automatically provided; no manual token needed

### High memory usage
- This add-on uses ~1-2 GB RAM (ASR + VAD models)
- Pi 5 with 8 GB is recommended
- Pi 5 with 4 GB works but may be tight with other add-ons
