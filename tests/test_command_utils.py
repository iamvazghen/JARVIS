import unittest
import importlib.util
from pathlib import Path


def _load_command_utils():
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / "Jarvis" / "command_utils.py"
    spec = importlib.util.spec_from_file_location("command_utils", str(mod_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


command_utils = _load_command_utils()
extract_open_target = command_utils.extract_open_target
extract_topic = command_utils.extract_topic
extract_weather_city = command_utils.extract_weather_city
extract_where_place = command_utils.extract_where_place
extract_youtube_query = command_utils.extract_youtube_query
is_goodbye = command_utils.is_goodbye
split_open_target = command_utils.split_open_target
wants_monday_protocol = command_utils.wants_monday_protocol


class CommandUtilsTests(unittest.TestCase):
    def test_extract_topic(self):
        self.assertEqual(extract_topic("tell me about Alan Turing"), "Alan Turing")
        self.assertEqual(extract_topic("who is Ada Lovelace"), "Ada Lovelace")
        self.assertEqual(extract_topic("what is recursion"), "recursion")

    def test_extract_open_target(self):
        self.assertEqual(extract_open_target("open github.com"), "github.com")
        self.assertEqual(extract_open_target("open "), "")

    def test_split_open_target(self):
        self.assertEqual(split_open_target("excel app"), ("excel", True))
        self.assertEqual(split_open_target("github.com"), ("github.com", False))

    def test_extract_weather_city(self):
        self.assertEqual(extract_weather_city("weather in new york"), "new york")
        self.assertEqual(extract_weather_city("weather tokyo"), "tokyo")

    def test_extract_youtube_query(self):
        self.assertEqual(extract_youtube_query("play coding music on youtube"), "coding music")
        self.assertEqual(extract_youtube_query("youtube lofi"), "lofi")

    def test_extract_where_place(self):
        self.assertEqual(extract_where_place("where is berlin"), "berlin")
        self.assertEqual(extract_where_place("where is"), "")

    def test_goodbye_and_protocol_detection(self):
        self.assertTrue(is_goodbye("goodbye for now"))
        self.assertFalse(is_goodbye("let us continue"))
        self.assertTrue(wants_monday_protocol("run monday protocol"))
        self.assertTrue(wants_monday_protocol("monday"))
        self.assertFalse(wants_monday_protocol("what is monday motivation"))


if __name__ == "__main__":
    unittest.main()
