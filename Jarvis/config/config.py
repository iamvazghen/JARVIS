import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    # Load project-level .env automatically so runtime behavior matches configured values.
    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env", override=False)


# WolframAlpha
wolframalpha_id = os.getenv("JIVAN_WOLFRAMALPHA_ID", "")


# OpenWeatherMap
weather_api_key = os.getenv("JIVAN_OPENWEATHER_API_KEY", "")
imgflip_username = os.getenv("JIVAN_IMGFLIP_USERNAME", "")
imgflip_password = os.getenv("JIVAN_IMGFLIP_PASSWORD", "")


# AI brain (OpenAI-compatible Chat Completions API)
#
# Providers you can use include:
# - OpenAI: base_url="https://api.openai.com/v1"
# - Groq:   base_url="https://api.groq.com/openai/v1"
# - Moonshot (Kimi): base_url="https://api.moonshot.ai/v1"
llm_api_key = os.getenv("JIVAN_LLM_API_KEY", "")
llm_base_url = os.getenv("JIVAN_LLM_BASE_URL", "https://api.moonshot.ai/v1")
llm_model = os.getenv("JIVAN_LLM_MODEL", "kimi-k2.5")


# Speech stack (multilingual EN/RU/AM)
# Providers:
# - STT: openai (best), google (fallback)
# - TTS: azure (best neural voices), openai (fallback), local pyttsx3 (final fallback)
speech_stt_provider = os.getenv("JIVAN_SPEECH_STT_PROVIDER", "openai")
speech_stt_mode = os.getenv("JIVAN_SPEECH_STT_MODE", "balanced")  # latency | balanced | accuracy
speech_tts_provider = os.getenv("JIVAN_SPEECH_TTS_PROVIDER", "azure")
speech_tts_fallback_order = os.getenv(
    "JIVAN_SPEECH_TTS_FALLBACK_ORDER",
    "cartesia,elevenlabs,azure,openai,local",
)

# Default interaction language; "en", "ru", "de". Auto detection still applies.
speech_default_language = os.getenv("JIVAN_SPEECH_DEFAULT_LANGUAGE", "en")
speech_google_fallback_languages = os.getenv(
    "JIVAN_SPEECH_GOOGLE_FALLBACK_LANGS",
    "en-US,ru-RU,de-DE",
)

# OpenAI speech settings (used for STT and/or TTS fallback).
speech_openai_api_key = os.getenv("JIVAN_SPEECH_OPENAI_API_KEY", llm_api_key)
speech_openai_base_url = os.getenv("JIVAN_SPEECH_OPENAI_BASE_URL", "https://api.openai.com/v1")
speech_openai_stt_model = os.getenv("JIVAN_SPEECH_OPENAI_STT_MODEL", "whisper-1")
speech_openai_tts_model = os.getenv("JIVAN_SPEECH_OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
speech_tts_voice_en = os.getenv("JIVAN_SPEECH_TTS_VOICE_EN", "alloy")
speech_tts_voice_ru = os.getenv("JIVAN_SPEECH_TTS_VOICE_RU", "alloy")
speech_tts_voice_de = os.getenv("JIVAN_SPEECH_TTS_VOICE_DE", "alloy")

# Azure speech (recommended for most human-like multilingual neural TTS).
speech_azure_key = os.getenv("JIVAN_SPEECH_AZURE_KEY", "")
speech_azure_region = os.getenv("JIVAN_SPEECH_AZURE_REGION", "")
speech_azure_tts_endpoint = os.getenv("JIVAN_SPEECH_AZURE_TTS_ENDPOINT", "")
speech_azure_voice_en = os.getenv("JIVAN_SPEECH_AZURE_VOICE_EN", "en-US-AriaNeural")
speech_azure_voice_ru = os.getenv("JIVAN_SPEECH_AZURE_VOICE_RU", "ru-RU-SvetlanaNeural")
speech_azure_voice_de = os.getenv("JIVAN_SPEECH_AZURE_VOICE_DE", "de-DE-KatjaNeural")
speech_elevenlabs_api_key = os.getenv("JIVAN_SPEECH_ELEVENLABS_API_KEY", "")
speech_elevenlabs_voice_en = os.getenv("JIVAN_SPEECH_ELEVENLABS_VOICE_EN", "")
speech_elevenlabs_voice_ru = os.getenv("JIVAN_SPEECH_ELEVENLABS_VOICE_RU", "")
speech_elevenlabs_voice_de = os.getenv("JIVAN_SPEECH_ELEVENLABS_VOICE_DE", "")
speech_elevenlabs_model = os.getenv("JIVAN_SPEECH_ELEVENLABS_MODEL", "eleven_multilingual_v2")
speech_cartesia_api_key = os.getenv("JIVAN_SPEECH_CARTESIA_API_KEY", "")
speech_cartesia_voice_en = os.getenv("JIVAN_SPEECH_CARTESIA_VOICE_EN", "")
speech_cartesia_voice_ru = os.getenv("JIVAN_SPEECH_CARTESIA_VOICE_RU", "")
speech_cartesia_voice_de = os.getenv("JIVAN_SPEECH_CARTESIA_VOICE_DE", "")

# Local fallback tuning.
speech_local_rate = int(os.getenv("JIVAN_SPEECH_LOCAL_RATE", "175"))
speech_energy_threshold = int(os.getenv("JIVAN_SPEECH_ENERGY_THRESHOLD", "3000"))

# Latency tuning.
speech_low_latency_mode = os.getenv("JIVAN_SPEECH_LOW_LATENCY_MODE", "1")
speech_tts_nonblocking = os.getenv("JIVAN_SPEECH_TTS_NONBLOCKING", "1")
speech_phrase_time_limit = int(os.getenv("JIVAN_SPEECH_PHRASE_TIME_LIMIT", "0"))
_speech_listen_timeout_env = os.getenv("JIVAN_SPEECH_LISTEN_TIMEOUT_S", "").strip()
speech_listen_timeout = float(_speech_listen_timeout_env) if _speech_listen_timeout_env else None
speech_dynamic_energy_threshold = os.getenv("JIVAN_SPEECH_DYNAMIC_ENERGY", "1")
speech_pause_threshold = float(os.getenv("JIVAN_SPEECH_PAUSE_THRESHOLD", "0.8"))
speech_non_speaking_duration = float(os.getenv("JIVAN_SPEECH_NON_SPEAKING_DURATION", "0.35"))
speech_adjust_noise = os.getenv("JIVAN_SPEECH_ADJUST_NOISE", "0")
speech_mic_wait_timeout = float(os.getenv("JIVAN_SPEECH_MIC_WAIT_TIMEOUT", "12"))
speech_ack_min_interval_s = float(os.getenv("JIVAN_SPEECH_ACK_MIN_INTERVAL_S", "1.2"))
speech_barge_in_enabled = os.getenv("JIVAN_SPEECH_BARGE_IN_ENABLED", "1")
speech_noise_suppression = os.getenv("JIVAN_SPEECH_NOISE_SUPPRESSION", "deepfilternet")
speech_vad_provider = os.getenv("JIVAN_SPEECH_VAD_PROVIDER", "silero")
speech_vad_min_energy = int(os.getenv("JIVAN_SPEECH_VAD_MIN_ENERGY", "120"))
speech_faster_whisper_model = os.getenv("JIVAN_SPEECH_FASTER_WHISPER_MODEL", "medium")
speech_faster_whisper_compute_type = os.getenv("JIVAN_SPEECH_FASTER_WHISPER_COMPUTE", "int8")
speech_faster_whisper_beam_size = int(os.getenv("JIVAN_SPEECH_FASTER_WHISPER_BEAM_SIZE", "5"))
speech_faster_whisper_best_of = int(os.getenv("JIVAN_SPEECH_FASTER_WHISPER_BEST_OF", "5"))
speech_faster_whisper_logprob_threshold = float(
    os.getenv("JIVAN_SPEECH_FASTER_WHISPER_LOGPROB_THRESHOLD", "-1.25")
)
speech_mode = os.getenv("JIVAN_SPEECH_MODE", "conversational")
speech_phrase_time_limit_conversational = int(
    os.getenv("JIVAN_SPEECH_PHRASE_TIME_LIMIT_CONVERSATIONAL", "6")
)
speech_phrase_time_limit_dictation = int(os.getenv("JIVAN_SPEECH_PHRASE_TIME_LIMIT_DICTATION", "14"))
speech_latency_trace = os.getenv("JIVAN_SPEECH_LATENCY_TRACE", "1")

# LLM latency tuning.
llm_timeout_s = int(os.getenv("JIVAN_LLM_TIMEOUT_S", "10"))
llm_tool_fill_timeout_s = int(os.getenv("JIVAN_LLM_TOOL_FILL_TIMEOUT_S", "6"))
llm_fast_model = os.getenv("JIVAN_LLM_FAST_MODEL", llm_model)
latency_trace = os.getenv("JIVAN_LATENCY_TRACE", "1")
llm_fast_timeout_s = int(os.getenv("JIVAN_LLM_FAST_TIMEOUT_S", "7"))
llm_prompt_char_budget = int(os.getenv("JIVAN_LLM_PROMPT_CHAR_BUDGET", "12000"))
brain_no_llm_mode = os.getenv("JIVAN_BRAIN_NO_LLM_MODE", "0")
brain_semantic_cache_ttl_s = int(os.getenv("JIVAN_BRAIN_SEMANTIC_CACHE_TTL_S", "45"))
brain_tool_cache_ttl_s = int(os.getenv("JIVAN_BRAIN_TOOL_CACHE_TTL_S", "60"))

# Protocol reaction tuning.
protocol_ai_reactions = os.getenv("JIVAN_PROTOCOL_AI_REACTIONS", "1")
protocol_reaction_ai_judge = os.getenv("JIVAN_PROTOCOL_REACTION_AI_JUDGE", "1")
protocol_reaction_timeout_s = int(os.getenv("JIVAN_PROTOCOL_REACTION_TIMEOUT_S", "6"))
protocol_reaction_max_words = int(os.getenv("JIVAN_PROTOCOL_REACTION_MAX_WORDS", "18"))

# Mem0 memory layer.
mem0_enabled = os.getenv("JIVAN_MEM0_ENABLED", "0")
mem0_api_key = os.getenv("JIVAN_MEM0_API_KEY", "")
mem0_base_url = os.getenv("JIVAN_MEM0_BASE_URL", "https://api.mem0.ai/v1")
mem0_user_id = os.getenv("JIVAN_MEM0_USER_ID", "default_user")
mem0_collection = os.getenv("JIVAN_MEM0_COLLECTION", "jivan")
mem0_write_mode = os.getenv("JIVAN_MEM0_WRITE_MODE", "safe")
mem0_max_context_items = int(os.getenv("JIVAN_MEM0_MAX_CONTEXT_ITEMS", "4"))
mem0_redact_sensitive = os.getenv("JIVAN_MEM0_REDACT_SENSITIVE", "1")
mem0_local_store_path = os.getenv("JIVAN_MEM0_LOCAL_STORE_PATH", "")
mem0_async_write = os.getenv("JIVAN_MEM0_ASYNC_WRITE", "1")
mem0_read_timeout_ms = int(os.getenv("JIVAN_MEM0_READ_TIMEOUT_MS", "350"))
redis_enabled = os.getenv("JIVAN_REDIS_ENABLED", "0")
redis_url = os.getenv("JIVAN_REDIS_URL", "redis://localhost:6379/0")
redis_session_key = os.getenv("JIVAN_REDIS_SESSION_KEY", "jivan:session:default")
redis_history_ttl_s = int(os.getenv("JIVAN_REDIS_HISTORY_TTL_S", "86400"))
redis_max_items = int(os.getenv("JIVAN_REDIS_MAX_ITEMS", "24"))
security_enforce_source_allowlist = os.getenv("JIVAN_SECURITY_ENFORCE_SOURCE_ALLOWLIST", "0")
security_allowed_source_ips = os.getenv("JIVAN_SECURITY_ALLOWED_SOURCE_IPS", "127.0.0.1,::1")
security_require_tailscale_for_remote = os.getenv("JIVAN_SECURITY_REQUIRE_TAILSCALE_FOR_REMOTE", "1")
security_allowed_tailscale_cidrs = os.getenv("JIVAN_SECURITY_ALLOWED_TAILSCALE_CIDRS", "100.64.0.0/10")
security_allowed_telegram_user_ids = os.getenv("JIVAN_SECURITY_ALLOWED_TELEGRAM_USER_IDS", "")
security_allowed_telegram_usernames = os.getenv("JIVAN_SECURITY_ALLOWED_TELEGRAM_USERNAMES", "")

# Composio MCP bridge.
composio_mcp_enabled = os.getenv("JIVAN_COMPOSIO_MCP_ENABLED", "0")
composio_api_key = os.getenv("JIVAN_COMPOSIO_API_KEY", "")
composio_base_url = os.getenv("JIVAN_COMPOSIO_BASE_URL", "")
composio_entity_id = os.getenv("JIVAN_COMPOSIO_ENTITY_ID", "default")
composio_tool_allowlist = os.getenv("JIVAN_COMPOSIO_TOOL_ALLOWLIST", "")
composio_tool_allowlist_telegram = os.getenv("JIVAN_COMPOSIO_TOOL_ALLOWLIST_TELEGRAM", "")
composio_tool_allowlist_giphy = os.getenv("JIVAN_COMPOSIO_TOOL_ALLOWLIST_GIPHY", "")
composio_tool_allowlist_gmail = os.getenv("JIVAN_COMPOSIO_TOOL_ALLOWLIST_GMAIL", "")
composio_use_tool_router = os.getenv("JIVAN_COMPOSIO_USE_TOOL_ROUTER", "1")
composio_tool_router_url = os.getenv("JIVAN_COMPOSIO_TOOL_ROUTER_URL", "")
composio_tool_router_session_id = os.getenv("JIVAN_COMPOSIO_TOOL_ROUTER_SESSION_ID", "")
composio_auto_create_session = os.getenv("JIVAN_COMPOSIO_AUTO_CREATE_SESSION", "1")
composio_external_user_id = os.getenv("JIVAN_COMPOSIO_EXTERNAL_USER_ID", "")
composio_enable_noauth_toolkits = os.getenv("JIVAN_COMPOSIO_ENABLE_NOAUTH_TOOLKITS", "1")
composio_noauth_toolkits = os.getenv("JIVAN_COMPOSIO_NOAUTH_TOOLKITS", "")
composio_timeout_s = int(os.getenv("JIVAN_COMPOSIO_TIMEOUT_S", "8"))
composio_project_id = os.getenv("JIVAN_COMPOSIO_PROJECT_ID", "")
composio_org_id = os.getenv("JIVAN_COMPOSIO_ORG_ID", "")
composio_org_member_email = os.getenv("JIVAN_COMPOSIO_ORG_MEMBER_EMAIL", "")
composio_user_id = os.getenv("JIVAN_COMPOSIO_USER_ID", "")
composio_playground_test_user_id = os.getenv("JIVAN_COMPOSIO_PLAYGROUND_TEST_USER_ID", "")
composio_telegram_auth_config_id = os.getenv("JIVAN_COMPOSIO_TELEGRAM_AUTH_CONFIG_ID", "")
composio_giphy_auth_config_id = os.getenv("JIVAN_COMPOSIO_GIPHY_AUTH_CONFIG_ID", "")
composio_gmail_auth_config_id = os.getenv("JIVAN_COMPOSIO_GMAIL_AUTH_CONFIG_ID", "")
telegram_state_path = os.getenv("JIVAN_TELEGRAM_STATE_PATH", "")

# Runtime / ops
runtime_log_path = os.getenv("JIVAN_RUNTIME_LOG_PATH", "Jarvis/data/runtime_events.jsonl")
runtime_replay_path = os.getenv("JIVAN_RUNTIME_REPLAY_PATH", "Jarvis/data/conversation_replay.jsonl")
runtime_receipts_path = os.getenv("JIVAN_RUNTIME_RECEIPTS_PATH", "Jarvis/data/delivery_receipts.jsonl")
runtime_outbound_queue_path = os.getenv("JIVAN_RUNTIME_OUTBOUND_QUEUE_PATH", "Jarvis/data/outbound_queue.jsonl")
runtime_metrics_path = os.getenv("JIVAN_RUNTIME_METRICS_PATH", "Jarvis/data/metrics_snapshot.json")
runtime_secrets_scan = os.getenv("JIVAN_RUNTIME_SECRETS_SCAN", "1")
runtime_outbound_queue_enabled = os.getenv("JIVAN_RUNTIME_OUTBOUND_QUEUE_ENABLED", "1")
runtime_outbound_retry_max = int(os.getenv("JIVAN_RUNTIME_OUTBOUND_RETRY_MAX", "2"))
runtime_sandbox_mode = os.getenv("JIVAN_RUNTIME_SANDBOX_MODE", "0")
runtime_offline_mode = os.getenv("JIVAN_RUNTIME_OFFLINE_MODE", "0")
runtime_owner_only_critical = os.getenv("JIVAN_RUNTIME_OWNER_ONLY_CRITICAL", "1")

# Audio device / profile tuning
speech_input_device_index = os.getenv("JIVAN_SPEECH_INPUT_DEVICE_INDEX", "")
speech_output_device_name = os.getenv("JIVAN_SPEECH_OUTPUT_DEVICE_NAME", "")
speech_profile = os.getenv("JIVAN_SPEECH_PROFILE", "home")
speech_ducking_enabled = os.getenv("JIVAN_SPEECH_DUCKING_ENABLED", "1")
