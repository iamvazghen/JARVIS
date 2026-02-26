import datetime
import os
import pprint
import random
import re
import sys
import threading
import time
from typing import Any, cast

import pyautogui
import pyjokes
import pywhatkit
import requests
import wolframalpha
from PIL import Image
from PyQt5 import QtCore
from PyQt5.QtCore import QDate, QThread, QTime, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow

from Jarvis import JarvisAssistant
from Jarvis.brain import JarvisBrain
from Jarvis.command_utils import (
    extract_launch_target,
    extract_open_target,
    extract_topic,
    extract_weather_city,
    extract_where_place,
    extract_youtube_query,
    is_goodbye,
    normalize_command,
    split_open_target,
    wants_monday_protocol,
)
from Jarvis.config import config
from Jarvis.features.gui import Ui_MainWindow
from Jarvis.protocols.farewells import pick as pick_protocol_farewell
from Jarvis.protocols.reactions import pick as pick_protocol_reaction
from Jarvis.protocols import get_protocol as get_registered_protocol
from Jarvis.protocols import run_protocol as run_registered_protocol
from Jarvis.runtime import (
    set_turn_id,
    log_event,
    replay_event,
    startup_precheck,
    metrics_inc,
    metrics_observe_ms,
    metrics_snapshot,
    recent_receipts,
)

obj = JarvisAssistant()

GREETINGS = [
    "hello jivan",
    "jivan",
    "wake up jivan",
    "you there jivan",
    "time to work jivan",
    "hey jivan",
    "ok jivan",
    "are you there",
]
GREETINGS_RES = [
    "always there for you sir",
    "i am ready sir",
    "your wish my command",
    "how can i help you sir?",
    "i am online and ready sir",
]

COMMON_APPS = {"excel", "word", "powerpoint", "chrome", "edge", "notepad", "calculator"}


def speak(text):
    ok = obj.tts(text)
    if not ok:
        print("TTS failed (ElevenLabs unavailable or misconfigured).")


app_id = config.wolframalpha_id


def computational_intelligence(question):
    try:
        client = wolframalpha.Client(app_id)
        answer = client.query(question)
        return next(answer.results).text
    except Exception as e:
        print(f"WolframAlpha failed: {e}")
        return None


brain = JarvisBrain(assistant=obj, wolfram_fn=computational_intelligence)


def startup():
    try:
        health = brain.mem0_health(force=True)
    except Exception as e:
        print(f"Mem0 health check failed: {e}")
        return

    status = health.get("status", "unknown")
    if health.get("ok"):
        print("Mem0: connected")
    else:
        print(f"Mem0: {status}")

    try:
        mcp_health = brain.mcp_health(force=True)
    except Exception as e:
        print(f"Composio MCP health check failed: {e}")
        return

    mcp_status = mcp_health.get("status", "unknown")
    if mcp_health.get("ok"):
        print("Composio MCP: connected")
    else:
        print(f"Composio MCP: {mcp_status}")

    try:
        redis_health = brain.redis_health(force=True)
    except Exception as e:
        print(f"Redis health check failed: {e}")
        return
    redis_status = redis_health.get("status", "unknown")
    if redis_health.get("ok"):
        print("Redis buffer: connected")
    else:
        print(f"Redis buffer: {redis_status}")
    return


def wish():
    hour = int(datetime.datetime.now().hour)
    if 0 <= hour <= 12:
        speak("Good morning.")
    elif 12 < hour < 18:
        speak("Good afternoon.")
    else:
        speak("Good evening.")
    c_time = obj.tell_time()
    speak(f"Time is {c_time}.")
    speak("JIVAN is online.")


class MainThread(QThread):
    def __init__(self):
        super().__init__()
        self._last_screenshot_name = None
        self._last_ack_ts = 0.0

    def run(self):
        self.TaskExecution()

    def _shutdown(self, farewell_text="", shutdown_pc=False):
        obj.wait_until_silent(timeout_s=2)
        requested = obj.request_app_shutdown(farewell_text)
        if farewell_text and not requested:
            speak(farewell_text)
        if shutdown_pc:
            os.system("shutdown /s /t 0")

    def _ack_if_slow(self, lowered):
        if str(getattr(config, "speech_low_latency_mode", "1")).lower() not in ("1", "true", "yes", "on"):
            return
        if lowered == "brain":
            now = time.time()
            min_gap = float(getattr(config, "speech_ack_min_interval_s", 1.2))
            if now - self._last_ack_ts < min_gap:
                return
            self._last_ack_ts = now
            obj.tts_async(random.choice(["One moment.", "On it.", "Right away.", "Working on that."]))
            return
        slow_markers = (
            "weather",
            "news",
            "headlines",
            "calculate",
            "who is",
            "what is",
            "tell me about",
            "email",
            "google",
            "youtube",
            "where is",
            "where am i",
            "current location",
            "calendar",
            "ip address",
        )
        if not any(marker in lowered for marker in slow_markers):
            return
        now = time.time()
        min_gap = float(getattr(config, "speech_ack_min_interval_s", 1.2))
        if now - self._last_ack_ts < min_gap:
            return
        self._last_ack_ts = now
        ack_pool = [
            "One moment.",
            "On it.",
            "Right away.",
            "Working on that.",
        ]
        obj.tts_async(random.choice(ack_pool))

    def _handle_open_target(self, target):
        normalized, explicit_app = split_open_target(target)
        if explicit_app or normalized in COMMON_APPS:
            ok = obj.launch_app_name(normalized, new_window=True)
            speak(f"Opening {normalized}." if ok else "Sorry, I couldn't find that application.")
            return True

        opened = obj.website_opener(target)
        speak(f"Opening {target}." if opened else "Couldn't open that target.")
        return True

    def _handle_knowledge_query(self, command, lowered):
        if not (
            lowered.startswith("who is ")
            or lowered.startswith("what is ")
            or lowered.startswith("tell me about ")
        ):
            return False

        answer = computational_intelligence(command)
        if answer:
            print(answer)
            speak(answer)
            return True

        topic = extract_topic(command)
        if not topic:
            speak("Please tell me the topic you want.")
            return True

        wiki = obj.tell_me(topic)
        if wiki:
            print(wiki)
            speak(str(wiki))
            return True

        return False

    def _handle_command(self, command):
        turn_started = time.perf_counter()
        turn_id = set_turn_id()
        log_event("turn_start", text=command)
        lowered = normalize_command(command)
        if not lowered:
            return True

        self._ack_if_slow(lowered)

        if lowered in ("dictation mode", "enable dictation mode", "start dictation mode"):
            ok = obj.set_listen_mode("dictation")
            speak("Dictation mode enabled." if ok else "Couldn't change listen mode.")
            return True

        if lowered in ("conversation mode", "enable conversation mode", "normal mode"):
            ok = obj.set_listen_mode("conversational")
            speak("Conversation mode enabled." if ok else "Couldn't change listen mode.")
            return True

        if lowered in ("list microphones", "list microphone devices", "show microphones"):
            rows = obj.list_input_devices()
            if not rows:
                speak("No microphone devices found.")
                return True
            first = rows[:5]
            msg = "Available microphones: " + ", ".join([f"{r.get('index')} {r.get('name')}" for r in first])
            print(msg)
            speak(msg)
            return True

        if lowered in ("sandbox mode on", "enable sandbox mode"):
            setattr(config, "runtime_sandbox_mode", "1")
            speak("Sandbox mode enabled.")
            return True
        if lowered in ("sandbox mode off", "disable sandbox mode"):
            setattr(config, "runtime_sandbox_mode", "0")
            speak("Sandbox mode disabled.")
            return True
        if lowered in ("offline mode on", "enable offline mode"):
            setattr(config, "runtime_offline_mode", "1")
            speak("Offline mode enabled.")
            return True
        if lowered in ("offline mode off", "disable offline mode"):
            setattr(config, "runtime_offline_mode", "0")
            speak("Offline mode disabled.")
            return True

        if lowered.startswith("use microphone "):
            idx = lowered.replace("use microphone ", "", 1).strip()
            ok = obj.set_input_device(idx)
            speak("Microphone updated." if ok else "Could not set microphone.")
            return True

        if lowered.startswith("set profile "):
            profile = lowered.replace("set profile ", "", 1).strip()
            ok = obj.set_mic_profile(profile)
            speak("Audio profile updated." if ok else "Unknown profile. Use home, office, or car.")
            return True

        if wants_monday_protocol(lowered):
            proto_name = "monday_morning" if "monday morning" in lowered else "monday"
            proto = get_registered_protocol(proto_name)
            proto_spec = (proto.spec() if proto else {}) if proto else {}
            speak(pick_protocol_reaction(proto_name, user_text=command, spec=proto_spec))
            result = run_registered_protocol(
                name=proto_name,
                user_text=command,
                confirm=True,
                dry_run=False,
                args={},
            )
            if not result.get("ok"):
                speak("Protocol could not run right now.")
                return True
            action = (result.get("action") or "").strip().lower()
            if action == "shutdown_pc":
                self._shutdown(pick_protocol_farewell("monday_morning"), shutdown_pc=True)
            else:
                self._shutdown(pick_protocol_farewell("monday"))
            return False

        if lowered in GREETINGS:
            speak(random.choice(GREETINGS_RES))
            return True

        if lowered in ("latency stats", "brain stats", "performance stats"):
            stats = brain.runtime_stats() if hasattr(brain, "runtime_stats") else {}
            msg = (
                f"LLM calls {int(stats.get('llm_calls', 0))}, "
                f"tool calls {int(stats.get('tool_calls', 0))}, "
                f"cache hits {int(stats.get('cache_hits', 0))}."
            )
            print(msg)
            speak(msg)
            log_event("brain_stats", stats=stats)
            return True
        if lowered in ("delivery receipts", "show delivery receipts"):
            rows = recent_receipts(limit=10)
            msg = f"Delivery receipts: {len(rows)} recent records."
            print(msg)
            speak(msg)
            return True

        if ("time" in lowered) and ("timer" not in lowered):
            now_time = obj.tell_time()
            print(now_time)
            speak(now_time)
            return True

        if re.search(r"\bdate\b", lowered):
            now_date = obj.tell_me_date()
            print(now_date)
            speak(now_date)
            return True

        if lowered.startswith("open "):
            target = extract_open_target(command)
            if not target:
                speak("What should I open?")
                return True
            return self._handle_open_target(target)

        if lowered.startswith("launch ") or lowered.startswith("start "):
            app = extract_launch_target(command)
            if not app:
                speak("Which app should I launch?")
                return True
            ok = obj.launch_app_name(app, new_window=True)
            speak(f"Launching {app}." if ok else "Sorry, I couldn't find that application.")
            return True

        if "weather" in lowered:
            city = extract_weather_city(command)
            if not city:
                speak("Please tell me the city name.")
                return True
            weather_res = obj.weather(city=city)
            if weather_res:
                print(weather_res)
                speak(weather_res)
            else:
                speak("Sorry, I couldn't fetch the weather right now.")
            return True

        if "calculate" in lowered:
            answer = computational_intelligence(command)
            speak(answer if answer else "Sorry, I couldn't answer that.")
            return True

        if self._handle_knowledge_query(command, lowered):
            return True

        if "buzzing" in lowered or "news" in lowered or "headlines" in lowered:
            news_res = obj.news()
            if not news_res or not isinstance(news_res, list):
                speak("Sorry, I couldn't fetch the news right now.")
                return True
            speak("Source: The Times Of India")
            speak("Todays Headlines are.")
            for article in news_res[:7]:
                title = article.get("title") if isinstance(article, dict) else str(article)
                if not title:
                    continue
                pprint.pprint(title)
                speak(title)
            speak("These were the top headlines.")
            return True

        if "search google for" in lowered:
            obj.search_anything_google(command)
            return True

        if "play music" in lowered or "hit some music" in lowered:
            music_dir = "F://Songs//Imagine_Dragons"
            if not os.path.isdir(music_dir):
                speak("Music directory is not available.")
                return True
            for song in os.listdir(music_dir):
                os.startfile(os.path.join(music_dir, song))
            return True

        if "youtube" in lowered:
            video = extract_youtube_query(command)
            if not video:
                speak("What should I play on YouTube?")
                return True
            speak(f"Okay sir, playing {video} on youtube")
            pywhatkit.playonyt(video)
            return True

        if "email" in lowered or "send email" in lowered:
            speak("Email is managed via MCP now. Please use the MCP email tool.")
            return True

        if ("calendar" in lowered) or ("plans" in lowered and "do i have" in lowered):
            speak("Calendar is managed via MCP now. Please use the MCP calendar tool.")
            return True

        if "make a note" in lowered or "write this down" in lowered or "remember this" in lowered:
            speak("What would you like me to write down?")
            note_text = obj.mic_input()
            if not note_text:
                speak("Sorry, I didn't catch that.")
                return True
            obj.take_note(str(note_text))
            speak("I've made a note of that")
            return True

        if "close the note" in lowered or "close notepad" in lowered:
            speak("Okay sir, closing notepad")
            os.system("taskkill /f /im notepad++.exe")
            os.system("taskkill /f /im notepad.exe")
            return True

        if "joke" in lowered:
            joke = pyjokes.get_joke()
            print(joke)
            speak(joke)
            return True

        if "system" in lowered:
            sys_info = obj.system_info()
            print(sys_info)
            speak(sys_info)
            return True

        if "where is" in lowered:
            place = extract_where_place(command)
            if not place:
                speak("Please tell me the place name.")
                return True
            current_loc, target_loc, distance = obj.location(place)
            try:
                if not isinstance(target_loc, dict) or not distance:
                    raise ValueError("location unavailable")

                city = target_loc.get("city", "")
                state = target_loc.get("state", "")
                country = target_loc.get("country", "")
                if city:
                    res = (
                        f"{place} is in {state} state and country {country}. "
                        f"It is {distance} km away from your current location"
                    )
                else:
                    res = (
                        f"{state} is a state in {country}. "
                        f"It is {distance} km away from your current location"
                    )
                print(res)
                speak(res)
            except Exception as e:
                print(f"Location lookup failed: {e}")
                speak("Sorry sir, I couldn't get the co-ordinates for that location.")
            return True

        if "ip address" in lowered:
            try:
                ip = requests.get("https://api.ipify.org", timeout=10).text
            except requests.RequestException as e:
                print(f"IP lookup failed: {e}")
                ip = ""
            if not ip:
                speak("Network unavailable.")
            else:
                print(ip)
                speak(f"Your ip address is {ip}")
            return True

        if "switch the window" in lowered or "switch window" in lowered:
            speak("Okay sir, Switching the window")
            pyautogui.keyDown("alt")
            pyautogui.press("tab")
            time.sleep(1)
            pyautogui.keyUp("alt")
            return True

        if "where i am" in lowered or "current location" in lowered or "where am i" in lowered:
            try:
                city, state, country = obj.my_location()
                print(city, state, country)
                speak(f"You are currently in {city} city which is in {state} state and country {country}")
            except Exception as e:
                print(f"Current location failed: {e}")
                speak("Sorry sir, I couldn't fetch your current location. Please try again")
            return True

        if (
            "take screenshot" in lowered
            or "take a screenshot" in lowered
            or "capture the screen" in lowered
        ):
            speak("By what name do you want to save the screenshot?")
            name = obj.mic_input() or "screenshot"
            speak("Alright sir, taking the screenshot")
            img = pyautogui.screenshot()
            filename = f"{name}.png"
            img.save(filename)
            self._last_screenshot_name = filename
            speak("The screenshot has been successfully captured")
            return True

        if "show me the screenshot" in lowered:
            if not self._last_screenshot_name:
                speak("No screenshot is available yet.")
                return True
            try:
                img = Image.open(self._last_screenshot_name)
                img.show(img)
                speak("Here it is sir")
            except OSError as e:
                print(f"Screenshot display failed: {e}")
                speak("Sorry sir, I am unable to display the screenshot")
            return True

        if "hide all files" in lowered or "hide this folder" in lowered:
            os.system("attrib +h /s /d")
            speak("Sir, all the files in this folder are now hidden")
            return True

        if "visible" in lowered or "make files visible" in lowered:
            os.system("attrib -h /s /d")
            speak("Sir, all the files in this folder are now visible")
            return True

        if is_goodbye(lowered):
            farewell = "Going offline."
            if brain.enabled():
                farewell = (
                    brain.respond(
                        "User said goodbye. Respond briefly and go offline.",
                        command_context={
                            "source": "local",
                            "ip": "127.0.0.1",
                            "language": obj.last_input_language(),
                        },
                    )
                    or farewell
                )
            speak(farewell)
            self._shutdown("")
            return False

        if brain.enabled():
            self._ack_if_slow("brain")
            ai_started = time.perf_counter()
            ai_reply = brain.respond(
                command,
                command_context={
                    "source": "local",
                    "ip": "127.0.0.1",
                    "language": obj.last_input_language(),
                    "role": "owner",
                },
            )
            if ai_reply:
                print(ai_reply)
                speak(ai_reply)
                replay_event("assistant_reply", {"text": ai_reply})
            else:
                speak("AI brain is not configured.")
            if str(getattr(config, "latency_trace", "1")).lower() in ("1", "true", "yes", "on"):
                llm_ms = int((time.perf_counter() - ai_started) * 1000)
                total_ms = int((time.perf_counter() - turn_started) * 1000)
                print(f"[latency] brain={llm_ms}ms total={total_ms}ms mode={obj.get_listen_mode()}")
                metrics_inc("turns_total", 1)
                metrics_observe_ms("turn_total_ms", total_ms)
                metrics_snapshot()
            log_event("turn_end", turn_id=turn_id)
            return True

        speak("AI brain is not configured.")
        if str(getattr(config, "latency_trace", "1")).lower() in ("1", "true", "yes", "on"):
            total_ms = int((time.perf_counter() - turn_started) * 1000)
            print(f"[latency] total={total_ms}ms mode={obj.get_listen_mode()}")
        return True

    def TaskExecution(self):
        while not self.isInterruptionRequested():
            command = obj.mic_input()
            if self.isInterruptionRequested():
                break
            if not command:
                continue
            print(f"You said [{obj.last_input_language()}]: {command}")
            replay_event("user_input", {"lang": obj.last_input_language(), "text": command})
            if str(getattr(config, "latency_trace", "1")).lower() in ("1", "true", "yes", "on"):
                m = obj.last_metrics()
                if isinstance(m, dict) and m:
                    print(
                        f"[latency] capture={m.get('capture_ms', 0)}ms stt={m.get('stt_ms', 0)}ms"
                        f" provider={m.get('stt_provider', '')}"
                    )
            should_continue = self._handle_command(command)
            if not should_continue:
                break


startExecution = MainThread()


class Main(QMainWindow):
    shutdownRequested = QtCore.pyqtSignal(str)
    healthStatusReady = QtCore.pyqtSignal(str)
    healthWarn = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.pushButton.clicked.connect(self.startTask)  # type: ignore[attr-defined]
        self._clock_timer = None
        shutdown_signal = cast(Any, self.shutdownRequested)
        shutdown_signal.connect(self._handle_shutdown)
        status_signal = cast(Any, self.healthStatusReady)
        status_signal.connect(self._set_status_chip)
        warn_signal = cast(Any, self.healthWarn)
        warn_signal.connect(obj.tts_async)
        obj.set_app_shutdown_callback(shutdown_signal.emit)

    def __del__(self):
        sys.stdout = sys.__stdout__

    def startTask(self):
        # Do not block UI on startup announcement.
        obj.tts_async("JIVAN is running and ready to assist you.")
        self._set_status_chip("Starting...")
        if not obj.mic_available():
            self._set_status_chip("Mic unavailable (install PyAudio)")
            obj.tts_async("Microphone is unavailable. Please install PyAudio and restart JIVAN.")
            return
        if self._clock_timer is None:
            self._clock_timer = QTimer(self)
            self._clock_timer.timeout.connect(self.showTime)  # type: ignore[attr-defined]
            self._clock_timer.start(1000)
        if not startExecution.isRunning():
            startExecution.start()
        self._start_background_health_checks()

    def _set_status_chip(self, text):
        try:
            self.ui.statusChip.setText(str(text))
        except Exception:
            pass

    def _start_background_health_checks(self):
        threading.Thread(target=self._run_background_health_checks, daemon=True).start()
        threading.Thread(target=self._warmup_models_and_clients, daemon=True).start()

    def _run_background_health_checks(self):
        status_signal = cast(Any, self.healthStatusReady)
        warn_signal = cast(Any, self.healthWarn)
        try:
            chk = startup_precheck(assistant=obj, brain=brain)
            mem_status = f"Mem0 {chk.get('mem0','unknown')}"
            mcp_status = f"Composio MCP {chk.get('mcp','unknown')}"
            redis_status = f"Redis {chk.get('redis','unknown')}"
            print(mem_status.replace(" connected", ": connected"))
            print(mcp_status.replace(" connected", ": connected"))
            print(redis_status.replace(" connected", ": connected"))
            status_signal.emit(f"{mem_status} | {mcp_status} | {redis_status}")
            if str(chk.get("mem0")) != "connected":
                warn_signal.emit("Mem0 is not connected. Running with local memory fallback.")
            for w in chk.get("warnings", []):
                log_event("precheck_warning", warning=w)
        except Exception as e:
            print(f"Startup health checks failed: {e}")

    def _warmup_models_and_clients(self):
        try:
            obj.warmup()
        except Exception:
            pass
        try:
            # Trigger lazy client/session initialization.
            brain.mcp_health(force=True)
            brain.mem0_health(force=True)
            brain.redis_health(force=True)
        except Exception:
            pass

    def _handle_shutdown(self, farewell_text):
        farewell_text = (farewell_text or "").strip()
        if farewell_text:
            speak(farewell_text)
        if self._clock_timer is not None:
            try:
                self._clock_timer.stop()
            except Exception:
                pass
        if startExecution.isRunning():
            startExecution.requestInterruption()
            startExecution.wait(1500)
        try:
            self.close()
        except Exception:
            pass
        QApplication.instance().quit()

    def showTime(self):
        current_time = QTime.currentTime()
        current_date = QDate.currentDate()
        label_time = current_time.toString("hh:mm:ss")
        label_date = current_date.toString(Qt.ISODate)
        self.ui.textBrowser.setText(label_date)
        self.ui.textBrowser_2.setText(label_time)


app = QApplication(sys.argv)
jivan = Main()
jivan.show()
exit(app.exec_())
