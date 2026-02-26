import time

from Jarvis.speech_engine import SpeechEngine


def _log_error(context, error):
    print(f"{context}: {error}")

class JarvisAssistant:
    def __init__(self):
        self._mic_disabled_reason = None
        self._mic_warned = False
        self._app_shutdown_cb = None
        self._app_shutdown_requested = False
        self._speech = SpeechEngine()

    def set_app_shutdown_callback(self, cb):
        """
        Register a callback that cleanly shuts down the GUI/app.
        This may be called from a worker thread.
        """
        self._app_shutdown_cb = cb

    def request_app_shutdown(self, farewell_text=""):
        if self._app_shutdown_requested:
            return False
        self._app_shutdown_requested = True
        cb = self._app_shutdown_cb
        if not cb:
            return False
        try:
            cb(farewell_text or "")
            return True
        except Exception as e:
            _log_error("App shutdown callback failed", e)
            return False

    def mic_available(self) -> bool:
        return self._speech.mic_available()

    def last_input_language(self):
        try:
            return self._speech.last_input_language()
        except Exception:
            return "en"

    def last_input_text(self):
        try:
            return self._speech.last_input_text()
        except Exception:
            return ""

    def last_metrics(self):
        try:
            return self._speech.last_metrics()
        except Exception:
            return {}

    def set_listen_mode(self, mode):
        try:
            return bool(self._speech.set_mode(mode))
        except Exception:
            return False

    def get_listen_mode(self):
        try:
            return self._speech.get_mode()
        except Exception:
            return "conversational"

    def set_mic_profile(self, profile):
        try:
            return bool(self._speech.set_profile(profile))
        except Exception:
            return False

    def list_input_devices(self):
        try:
            return self._speech.list_input_devices()
        except Exception:
            return []

    def set_input_device(self, index):
        try:
            return bool(self._speech.set_input_device(index))
        except Exception:
            return False

    def warmup(self):
        try:
            return bool(self._speech.warmup())
        except Exception:
            return False

    def mic_input(self):
        """
        Fetch input from mic
        return: user's voice input as text if true, false if fail
        """
        if self._app_shutdown_requested:
            time.sleep(0.2)
            return ""

        if self._mic_disabled_reason:
            if not self._mic_warned:
                print(self._mic_disabled_reason)
                self._mic_warned = True
            time.sleep(1.0)
            return ""

        try:
            command, _lang = self._speech.listen_and_transcribe()
            return command
        except Exception as e:
            msg = str(e) or "Microphone error"
            if "PyAudio" in msg:
                self._mic_disabled_reason = "Could not find PyAudio; check installation"
                if not self._mic_warned:
                    print(self._mic_disabled_reason)
                    self._mic_warned = True
            else:
                if not self._mic_warned:
                    _log_error("Speech capture failed", msg)
                    self._mic_warned = True
            time.sleep(1.0)
            return ""


    def tts(self, text):
        """
        Convert any text to speech
        :param text: text(String)
        :return: True/False (Play sound if True otherwise write exception to log and return  False)
        """
        return self._speech.speak(text, wait=True)

    def tts_async(self, text):
        return self._speech.speak(text, wait=False)

    def wait_until_silent(self, timeout_s=10):
        return self._speech.wait_until_silent(timeout_s=timeout_s)

    def tell_me_date(self):
        from Jarvis.features import date_time

        return date_time.date()

    def tell_time(self):
        from Jarvis.features import date_time

        return date_time.time()

    def launch_any_app(self, path_of_app):
        """
        Launch any windows application 
        :param path_of_app: path of exe 
        :return: True is success and open the application, False if fail
        """
        from Jarvis.features import launch_app

        return launch_app.launch_app(path_of_app)

    def launch_app_name(self, app_name, new_window=False):
        """
        Launch an installed app by a common name (best-effort).
        :param app_name: e.g. "chrome", "notepad", "calculator"
        :param new_window: request a new window when supported
        """
        from Jarvis.features import launch_app

        return launch_app.launch_app_by_name(app_name, new_window=new_window)

    def website_opener(self, domain):
        """
        This will open website according to domain
        :param domain: any domain, example "youtube.com"
        :return: True if success, False if fail
        """
        from Jarvis.features import website_open

        return website_open.website_opener(domain)


    def weather(self, city):
        """
        Return weather
        :param city: Any city of this world
        :return: weather info as string if True, or False
        """
        try:
            from Jarvis.features import weather

            res = weather.fetch_weather(city)
        except Exception as e:
            _log_error("Weather fetch failed", e)
            res = False
        return res

    def tell_me(self, topic):
        """
        Tells about anything from wikipedia
        :param topic: any string is valid options
        :return: First 500 character from wikipedia if True, False if fail
        """
        from Jarvis.features import wikipedia

        return wikipedia.tell_me_about(topic)

    def news(self):
        """
        Fetch top news of the day from google news
        :return: news list of string if True, False if fail
        """
        from Jarvis.features import news

        return news.get_news()
    
    def search_anything_google(self, command):
        from Jarvis.features import google_search

        google_search.google_search(command)

    def take_note(self, text):
        from Jarvis.features import note

        note.note(text)
    
    def system_info(self):
        from Jarvis.features import system_stats

        return system_stats.system_stats()

    def location(self, location):
        from Jarvis.features import loc

        current_loc, target_loc, distance = loc.loc(location)
        return current_loc, target_loc, distance

    def my_location(self):
        from Jarvis.features import loc

        city, state, country = loc.my_location()
        return city, state, country
