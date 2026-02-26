import json
import os
import re
import tempfile
import time
import winsound
import ctypes
import xml.sax.saxutils as saxutils
import audioop
import queue
import threading
import wave

import requests
import speech_recognition as sr

from Jarvis.config import config


def _log_error(context, error):
    print(f"{context}: {error}")


def _normalize_lang(lang):
    t = (lang or "").strip().lower()
    if t.startswith("en"):
        return "en"
    if t.startswith("ru"):
        return "ru"
    if t.startswith("de"):
        return "de"
    return ""


def _detect_text_language(text, fallback="en"):
    s = text or ""
    for ch in s:
        code = ord(ch)
        if (0x0041 <= code <= 0x007A) or code in (0x00C4, 0x00D6, 0x00DC, 0x00DF, 0x00E4, 0x00F6, 0x00FC):
            # Keep default/fallback for latin script; EN/DE are both latin.
            continue
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    return _normalize_lang(fallback) or "en"


def _voice_for_lang(lang):
    lang = _normalize_lang(lang) or "en"
    if lang == "ru":
        return getattr(config, "speech_tts_voice_ru", "alloy")
    if lang == "de":
        return getattr(config, "speech_tts_voice_de", "alloy")
    return getattr(config, "speech_tts_voice_en", "alloy")


def _postprocess_transcript(text):
    value = str(text or "").strip()
    if not value:
        return ""
    replacements = (
        (r"\btelly\b", "telegram"),
        (r"\btelegra+m\b", "telegram"),
        (r"\btele gram\b", "telegram"),
        (r"\bcomposure\b", "composio"),
        (r"\bcomp osio\b", "composio"),
        (r"\bg mail\b", "gmail"),
        (r"\bgiphy\b", "giphy"),
    )
    out = value
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


class SpeechEngine:
    def __init__(self):
        self._recognizer = sr.Recognizer()
        self._local_tts = None
        self._conversation_lang = _normalize_lang(
            getattr(config, "speech_default_language", "en")
        ) or "en"
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_event = threading.Event()
        self._tts_queue = queue.Queue()
        self._nonblocking_tts = str(getattr(config, "speech_tts_nonblocking", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self._barge_in_enabled = str(getattr(config, "speech_barge_in_enabled", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self._mci_alias = None
        self._interrupt_playback = threading.Event()
        self._faster_whisper_model = None
        self._last_input_text = ""
        self._last_input_lang = self._conversation_lang
        self._metrics = {"capture_ms": 0, "stt_ms": 0, "stt_provider": ""}

        try:
            import pyttsx3  # type: ignore

            self._local_tts = pyttsx3.init("sapi5")
            self._local_tts.setProperty("rate", int(getattr(config, "speech_local_rate", 175)))
            self._select_local_voice(self._conversation_lang)
        except Exception:
            self._local_tts = None
        self._configure_recognizer()

        self._tts_worker = threading.Thread(target=self._tts_worker_loop, daemon=True)
        self._tts_worker.start()
        self._apply_profile()

    def _configure_recognizer(self):
        self._recognizer.energy_threshold = int(getattr(config, "speech_energy_threshold", 3000))
        self._recognizer.dynamic_energy_threshold = str(
            getattr(config, "speech_dynamic_energy_threshold", "1")
        ).lower() in ("1", "true", "yes", "on")
        self._recognizer.pause_threshold = float(getattr(config, "speech_pause_threshold", 0.45))
        self._recognizer.non_speaking_duration = float(
            getattr(config, "speech_non_speaking_duration", 0.2)
        )

    def _apply_profile(self):
        profile = str(getattr(config, "speech_profile", "home") or "home").strip().lower()
        if profile == "office":
            self._recognizer.energy_threshold = max(self._recognizer.energy_threshold, 2800)
            self._recognizer.pause_threshold = max(self._recognizer.pause_threshold, 0.85)
        elif profile == "car":
            self._recognizer.energy_threshold = max(self._recognizer.energy_threshold, 3500)
            self._recognizer.pause_threshold = max(self._recognizer.pause_threshold, 0.95)
        else:
            self._recognizer.energy_threshold = max(self._recognizer.energy_threshold, 2200)

    def is_speaking(self):
        with self._lock:
            return self._is_speaking

    def wait_until_silent(self, timeout_s=10.0):
        end = time.time() + max(0.1, float(timeout_s))
        while time.time() < end:
            if not self.is_speaking() and self._tts_queue.empty():
                return True
            time.sleep(0.03)
        return False

    def _mark_speaking(self, value):
        with self._lock:
            self._is_speaking = value

    def _select_local_voice(self, lang):
        if self._local_tts is None:
            return
        wanted = {
            "en": ("en", "english"),
            "ru": ("ru", "russian"),
            "de": ("de", "german"),
        }.get(_normalize_lang(lang) or "en", ("en", "english"))

        voices = self._local_tts.getProperty("voices") or []
        for v in voices:
            hay = " ".join(
                [
                    str(getattr(v, "id", "")),
                    str(getattr(v, "name", "")),
                    str(getattr(v, "languages", "")),
                ]
            ).lower()
            if wanted[0] in hay or wanted[1] in hay:
                self._local_tts.setProperty("voice", v.id)
                return
        if voices:
            self._local_tts.setProperty("voice", voices[0].id)

    def mic_available(self):
        try:
            import pyaudio  # noqa: F401

            return True
        except Exception:
            return False

    def listen_and_transcribe(self):
        # Support barge-in (interrupt TTS when user starts speaking again).
        if self._barge_in_enabled and self.is_speaking():
            self.interrupt_speaking()
        else:
            self.wait_until_silent(timeout_s=float(getattr(config, "speech_mic_wait_timeout", 12)))

        capture_started = time.perf_counter()
        with sr.Microphone(device_index=self._preferred_input_index()) as source:
            print("Listening....")
            if str(getattr(config, "speech_adjust_noise", "0")).lower() in ("1", "true", "yes", "on"):
                self._recognizer.adjust_for_ambient_noise(source, duration=0.25)
            mode = self.get_mode()
            if mode == "dictation":
                phrase_limit = int(getattr(config, "speech_phrase_time_limit_dictation", 14))
            else:
                phrase_limit = int(getattr(config, "speech_phrase_time_limit_conversational", 6))
            hard_limit = getattr(config, "speech_phrase_time_limit", 0)
            if hard_limit not in (None, "") and int(hard_limit) > 0:
                phrase_limit = int(hard_limit)
            audio = self._recognizer.listen(
                source,
                timeout=getattr(config, "speech_listen_timeout", None),
                phrase_time_limit=phrase_limit,
            )
        self._metrics["capture_ms"] = int((time.perf_counter() - capture_started) * 1000)
        if not self._vad_has_speech(audio):
            return "", self._conversation_lang

        # Primary STT provider chain.
        stt_provider = (getattr(config, "speech_stt_provider", "openai") or "openai").lower()
        stt_mode = (getattr(config, "speech_stt_mode", "balanced") or "balanced").strip().lower()
        latency_mode = str(getattr(config, "speech_low_latency_mode", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        provider_chain = []
        # Explicit mode takes precedence; latency mode only affects default path.
        if stt_mode == "accuracy":
            provider_chain = [self._stt_faster_whisper, self._stt_openai, self._stt_google_fallback]
        elif stt_mode == "latency":
            provider_chain = [self._stt_google_fallback, self._stt_faster_whisper, self._stt_openai]
        # Low-latency mode always prioritizes the fastest path first.
        elif latency_mode:
            provider_chain = [self._stt_google_fallback, self._stt_faster_whisper, self._stt_openai]
        elif stt_provider == "faster_whisper":
            provider_chain = [self._stt_faster_whisper, self._stt_google_fallback, self._stt_openai]
        elif stt_provider == "google":
            provider_chain = [self._stt_google_fallback, self._stt_openai]
        elif stt_provider == "openai":
            provider_chain = [self._stt_openai, self._stt_google_fallback]
        else:
            provider_chain = [self._stt_openai, self._stt_faster_whisper, self._stt_google_fallback]

        for fn in provider_chain:
            stt_started = time.perf_counter()
            text, lang = fn(audio)
            if text:
                self._metrics["stt_ms"] = int((time.perf_counter() - stt_started) * 1000)
                self._metrics["stt_provider"] = str(getattr(fn, "__name__", "stt"))
                self._conversation_lang = _normalize_lang(lang) or self._conversation_lang
                self._last_input_text = _postprocess_transcript(text)
                self._last_input_lang = self._conversation_lang
                if str(getattr(config, "speech_latency_trace", "1")).lower() in ("1", "true", "yes", "on"):
                    print(
                        f"[latency] capture={self._metrics['capture_ms']}ms stt={self._metrics['stt_ms']}ms"
                        f" provider={self._metrics['stt_provider']}"
                    )
                return self._last_input_text, self._conversation_lang

        return "", self._conversation_lang

    def last_input_language(self):
        return self._last_input_lang or self._conversation_lang or "en"

    def last_input_text(self):
        return self._last_input_text or ""

    def last_metrics(self):
        return dict(self._metrics)

    def set_mode(self, mode):
        m = str(mode or "").strip().lower()
        if m not in ("conversational", "dictation"):
            return False
        self._conversation_mode = m
        try:
            setattr(config, "speech_mode", m)
        except Exception:
            pass
        return True

    def get_mode(self):
        m = str(getattr(config, "speech_mode", "conversational") or "conversational").strip().lower()
        if m not in ("conversational", "dictation"):
            return "conversational"
        return m

    def set_profile(self, profile):
        p = str(profile or "").strip().lower()
        if p not in ("home", "office", "car"):
            return False
        setattr(config, "speech_profile", p)
        self._configure_recognizer()
        self._apply_profile()
        return True

    def list_input_devices(self):
        try:
            import pyaudio  # type: ignore

            pa = pyaudio.PyAudio()
            rows = []
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if int(info.get("maxInputChannels", 0)) > 0:
                    rows.append({"index": int(i), "name": str(info.get("name", ""))})
            pa.terminate()
            return rows
        except Exception:
            return []

    def _preferred_input_index(self):
        raw = str(getattr(config, "speech_input_device_index", "") or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except Exception:
            return None

    def set_input_device(self, index):
        try:
            idx = int(index)
        except Exception:
            return False
        setattr(config, "speech_input_device_index", str(idx))
        return True

    def warmup(self):
        try:
            if (getattr(config, "speech_stt_provider", "") or "").lower() in ("faster_whisper", ""):
                from faster_whisper import WhisperModel  # type: ignore

                if self._faster_whisper_model is None:
                    self._faster_whisper_model = WhisperModel(
                        getattr(config, "speech_faster_whisper_model", "medium"),
                        compute_type=getattr(config, "speech_faster_whisper_compute_type", "int8"),
                    )
            return True
        except Exception:
            return False

    def speak(self, text, lang_hint=None, wait=None):
        message = str(text or "").strip()
        if not message:
            return False
        lang = _normalize_lang(lang_hint) or _detect_text_language(message, self._conversation_lang)
        self._conversation_lang = lang
        if wait is None:
            wait = not self._nonblocking_tts

        if not wait:
            self._tts_queue.put((message, lang))
            return True
        return self._speak_sync(message, lang)

    def _speak_sync(self, message, lang):
        # Hard-enforce ElevenLabs TTS path (requested behavior).
        self._mark_speaking(True)
        try:
            return self._tts_elevenlabs(message, lang)
        finally:
            self._mark_speaking(False)

    def _tts_worker_loop(self):
        while not self._stop_event.is_set():
            try:
                message, lang = self._tts_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._speak_sync(message, lang)
            finally:
                self._tts_queue.task_done()

    def stop(self):
        self._stop_event.set()
        try:
            self._tts_worker.join(timeout=0.4)
        except Exception:
            pass
        self.interrupt_speaking()

    def interrupt_speaking(self):
        self._interrupt_playback.set()
        if str(getattr(config, "speech_ducking_enabled", "1")).lower() in ("1", "true", "yes", "on"):
            time.sleep(0.08)
        self._stop_mci_playback()
        if self._local_tts is not None:
            try:
                self._local_tts.stop()
            except Exception:
                pass
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        # Drop queued TTS jobs when barge-in is explicit.
        while True:
            try:
                self._tts_queue.get_nowait()
                self._tts_queue.task_done()
            except queue.Empty:
                break
        self._mark_speaking(False)

    def _vad_has_speech(self, audio):
        provider = str(getattr(config, "speech_vad_provider", "silero")).strip().lower()
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        if not raw:
            return False
        rms = audioop.rms(raw, 2)
        min_energy = int(getattr(config, "speech_vad_min_energy", 120))
        if provider not in ("silero", "energy"):
            return True

        # Silero integration is optional; if not installed or fails, fallback to RMS gate.
        if provider == "silero":
            try:
                from silero_vad import get_speech_timestamps, load_silero_vad  # type: ignore

                model = load_silero_vad()
                # The library expects float32 PCM in [-1,1]
                import array

                arr = array.array("h")
                arr.frombytes(raw)
                pcm = [max(-1.0, min(1.0, x / 32768.0)) for x in arr]
                timestamps = get_speech_timestamps(pcm, model, sampling_rate=16000)
                if timestamps:
                    return True
            except Exception:
                pass
        return rms >= min_energy

    def _stt_openai(self, audio):
        api_key = getattr(config, "speech_openai_api_key", "") or getattr(config, "llm_api_key", "")
        base_url = getattr(config, "speech_openai_base_url", "https://api.openai.com/v1")
        model = getattr(config, "speech_openai_stt_model", "whisper-1")
        if not api_key:
            return "", ""

        url = base_url.rstrip("/") + "/audio/transcriptions"
        headers = {"Authorization": "Bearer " + api_key}
        wav = self._preprocess_wav_bytes(audio.get_wav_data())
        files = {"file": ("speech.wav", wav, "audio/wav")}
        data = {"model": model, "response_format": "verbose_json"}

        # Language hint can improve short utterances.
        hint = _normalize_lang(getattr(config, "speech_default_language", ""))
        if hint:
            data["language"] = hint

        try:
            res = requests.post(url, headers=headers, files=files, data=data, timeout=45)
            if not res.ok:
                _log_error("OpenAI STT error", f"{res.status_code} {res.text}")
                return "", ""
            obj = res.json()
            text = (obj.get("text") or "").strip()
            lang = _normalize_lang(obj.get("language", ""))
            return text, lang
        except requests.RequestException as e:
            _log_error("OpenAI STT request failed", e)
            return "", ""
        except (ValueError, json.JSONDecodeError) as e:
            _log_error("OpenAI STT parse failed", e)
            return "", ""

    def _stt_faster_whisper(self, audio):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception:
            return "", ""
        model_name = getattr(config, "speech_faster_whisper_model", "small")
        compute_type = getattr(config, "speech_faster_whisper_compute_type", "int8")
        beam_size = int(getattr(config, "speech_faster_whisper_beam_size", 5))
        best_of = int(getattr(config, "speech_faster_whisper_best_of", 5))
        logprob_threshold = float(getattr(config, "speech_faster_whisper_logprob_threshold", -1.25))
        try:
            if self._faster_whisper_model is None:
                self._faster_whisper_model = WhisperModel(model_name, compute_type=compute_type)
        except Exception as e:
            _log_error("Faster-Whisper model load failed", e)
            return "", ""

        tmp_path = None
        try:
            wav = self._preprocess_wav_bytes(audio.get_wav_data())
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(wav)
                tmp_path = f.name
            lang_hint = _normalize_lang(getattr(config, "speech_default_language", ""))
            segments, info = self._faster_whisper_model.transcribe(
                tmp_path,
                language=(lang_hint or None),
                vad_filter=True,
                beam_size=max(1, beam_size),
                best_of=max(1, best_of),
                temperature=0.0,
                condition_on_previous_text=False,
            )
            seg_list = [seg for seg in segments]
            text = " ".join([seg.text.strip() for seg in seg_list if getattr(seg, "text", "").strip()]).strip()
            avg_logs = [
                float(getattr(seg, "avg_logprob", -2.0))
                for seg in seg_list
                if isinstance(getattr(seg, "avg_logprob", None), (int, float))
            ]
            if avg_logs:
                avg_lp = sum(avg_logs) / float(len(avg_logs))
                if avg_lp < logprob_threshold:
                    return "", ""
            lang = _normalize_lang(getattr(info, "language", ""))
            return text, lang
        except Exception as e:
            _log_error("Faster-Whisper STT failed", e)
            return "", ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _preprocess_wav_bytes(self, wav_bytes):
        provider = str(getattr(config, "speech_noise_suppression", "deepfilternet")).strip().lower()
        if provider not in ("deepfilternet", "none", ""):
            return wav_bytes
        if provider in ("none", ""):
            return wav_bytes
        # Optional DeepFilterNet integration. If unavailable, fallback silently.
        try:
            from deepfilternet import enhance_audio  # type: ignore
        except Exception:
            return wav_bytes
        in_path = None
        out_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f1:
                f1.write(wav_bytes)
                in_path = f1.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f2:
                out_path = f2.name
            enhance_audio(in_path, out_path)
            with open(out_path, "rb") as f3:
                return f3.read()
        except Exception:
            return wav_bytes
        finally:
            for path in (in_path, out_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _stt_google_fallback(self, audio):
        # SpeechRecognition Google fallback; try configured languages.
        langs = getattr(config, "speech_google_fallback_languages", "en-US,ru-RU,de-DE")
        lang_list = [x.strip() for x in str(langs).split(",") if x.strip()]
        if not lang_list:
            lang_list = ["en-US"]

        for lang_code in lang_list:
            try:
                text = self._recognizer.recognize_google(audio, language=lang_code)
                return text, _normalize_lang(lang_code)
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                _log_error("Google STT request failed", e)
                break
        return "", ""

    def _tts_openai(self, text, lang):
        api_key = getattr(config, "speech_openai_api_key", "") or getattr(config, "llm_api_key", "")
        base_url = getattr(config, "speech_openai_base_url", "https://api.openai.com/v1")
        model = getattr(config, "speech_openai_tts_model", "gpt-4o-mini-tts")
        voice = _voice_for_lang(lang)
        if not api_key:
            return False

        url = base_url.rstrip("/") + "/audio/speech"
        headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": "wav",
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if not res.ok:
                _log_error("OpenAI TTS error", f"{res.status_code} {res.text}")
                return False
            return self._play_wav_bytes(res.content)
        except requests.RequestException as e:
            _log_error("OpenAI TTS request failed", e)
            return False

    def _tts_azure(self, text, lang):
        key = getattr(config, "speech_azure_key", "")
        region = getattr(config, "speech_azure_region", "")
        if not key or not region:
            return False

        voice = {
            "en": getattr(config, "speech_azure_voice_en", "en-US-AriaNeural"),
            "ru": getattr(config, "speech_azure_voice_ru", "ru-RU-SvetlanaNeural"),
            "de": getattr(config, "speech_azure_voice_de", "de-DE-KatjaNeural"),
        }.get(_normalize_lang(lang) or "en")
        locale = {
            "en": "en-US",
            "ru": "ru-RU",
            "de": "de-DE",
        }.get(_normalize_lang(lang) or "en", "en-US")

        endpoint = (
            getattr(config, "speech_azure_tts_endpoint", "")
            or f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
        }
        escaped = saxutils.escape(text)
        ssml = (
            f"<speak version='1.0' xml:lang='{locale}'>"
            f"<voice xml:lang='{locale}' name='{voice}'>"
            f"{escaped}"
            "</voice></speak>"
        )

        try:
            res = requests.post(endpoint, headers=headers, data=ssml.encode("utf-8"), timeout=60)
            if not res.ok:
                _log_error("Azure TTS error", f"{res.status_code} {res.text}")
                return False
            return self._play_wav_bytes(res.content)
        except requests.RequestException as e:
            _log_error("Azure TTS request failed", e)
            return False

    def _tts_elevenlabs(self, text, lang):
        api_key = getattr(config, "speech_elevenlabs_api_key", "") or ""
        if not api_key:
            return False
        model = getattr(config, "speech_elevenlabs_model", "eleven_multilingual_v2")
        voice = {
            "en": getattr(config, "speech_elevenlabs_voice_en", ""),
            "ru": getattr(config, "speech_elevenlabs_voice_ru", ""),
            "de": getattr(config, "speech_elevenlabs_voice_de", ""),
        }.get(_normalize_lang(lang) or "en", "")
        if not voice:
            return False

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        }
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.7},
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if not res.ok:
                _log_error("ElevenLabs TTS error", f"{res.status_code} {res.text}")
                return False
            return self._play_wav_bytes(res.content)
        except requests.RequestException as e:
            _log_error("ElevenLabs TTS request failed", e)
            return False

    def _tts_cartesia(self, text, lang):
        api_key = getattr(config, "speech_cartesia_api_key", "") or ""
        if not api_key:
            return False
        voice = {
            "en": getattr(config, "speech_cartesia_voice_en", ""),
            "ru": getattr(config, "speech_cartesia_voice_ru", ""),
            "de": getattr(config, "speech_cartesia_voice_de", ""),
        }.get(_normalize_lang(lang) or "en", "")
        if not voice:
            return False

        url = "https://api.cartesia.ai/tts/bytes"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model_id": "sonic",
            "transcript": text,
            "voice": {"id": voice},
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 24000},
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if not res.ok:
                _log_error("Cartesia TTS error", f"{res.status_code} {res.text}")
                return False
            return self._play_wav_bytes(res.content)
        except requests.RequestException as e:
            _log_error("Cartesia TTS request failed", e)
            return False

    def _play_wav_bytes(self, wav_bytes):
        if not wav_bytes:
            return False
        # ElevenLabs often returns MP3 unless a Pro-only PCM output is configured.
        # Detect MP3 and route playback through MCI to avoid silent output on Windows.
        is_mp3 = wav_bytes.startswith(b"ID3") or (
            len(wav_bytes) > 2 and wav_bytes[0] == 0xFF and (wav_bytes[1] & 0xE0) == 0xE0
        )
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3" if is_mp3 else ".wav") as f:
                f.write(wav_bytes)
                tmp_path = f.name
            # Async playback allows interruption for barge-in.
            self._interrupt_playback.clear()
            if is_mp3:
                return self._play_mp3_file(tmp_path)
            winsound.PlaySound(tmp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            duration = self._wav_duration_s(tmp_path)
            end = time.time() + max(0.2, duration + 0.1)
            while time.time() < end:
                if self._interrupt_playback.is_set():
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    return False
                time.sleep(0.03)
            winsound.PlaySound(None, winsound.SND_PURGE)
            return True
        except Exception as e:
            _log_error("Audio playback failed", e)
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                # Delay tiny bit so file isn't locked on slower systems.
                time.sleep(0.05)
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _mci_send(self, command):
        buf = ctypes.create_unicode_buffer(260)
        err = ctypes.windll.winmm.mciSendStringW(command, buf, 259, 0)
        return int(err), buf.value

    def _stop_mci_playback(self):
        alias = self._mci_alias
        if not alias:
            return
        try:
            self._mci_send(f"stop {alias}")
        except Exception:
            pass
        try:
            self._mci_send(f"close {alias}")
        except Exception:
            pass
        self._mci_alias = None

    def _play_mp3_file(self, path):
        alias = f"jivan_tts_{int(time.time() * 1000) % 1000000}"
        self._mci_alias = alias
        err, _ = self._mci_send(f'open "{path}" type mpegvideo alias {alias}')
        if err != 0:
            self._mci_alias = None
            return False
        try:
            self._mci_send(f"play {alias}")
            started = time.time()
            while True:
                if self._interrupt_playback.is_set():
                    self._mci_send(f"stop {alias}")
                    return False
                err_mode, mode = self._mci_send(f"status {alias} mode")
                if err_mode != 0:
                    break
                if mode.strip().lower() == "stopped":
                    break
                if (time.time() - started) > 20:
                    break
                time.sleep(0.03)
            return True
        finally:
            self._mci_send(f"close {alias}")
            self._mci_alias = None

    def _wav_duration_s(self, path):
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate() or 1
                return float(frames) / float(rate)
        except Exception:
            return 1.8
