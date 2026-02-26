import requests


def spec():
    return {
        "name": "ip_address",
        "description": "Get your public IP address as seen on the internet.",
        "args": {},
    }


def run(*, assistant=None, wolfram_fn=None):
    return requests.get("https://api.ipify.org", timeout=10).text

