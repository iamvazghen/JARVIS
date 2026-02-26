from .custom_loader import load_file_protocols
from .engine import ProtocolEngine


# Built-ins can stay empty when using file-based protocols as the source of truth.
_PROTOCOL_MODULES = []
_ENGINE = ProtocolEngine()


def _all_protocol_modules():
    return list(_PROTOCOL_MODULES) + list(load_file_protocols())


def list_protocols():
    return _ENGINE.list_specs(_all_protocol_modules())


def get_protocol(name):
    return _ENGINE.get_protocol(_all_protocol_modules(), name)


def run_protocol(*, name="", user_text="", confirm=False, dry_run=False, args=None, idempotency_key="", **kwargs):
    merged_args = dict(args or {})
    merged_args.update(kwargs or {})
    assistant = merged_args.pop("assistant", None)
    wolfram_fn = merged_args.pop("wolfram_fn", None)
    return _ENGINE.run(
        _all_protocol_modules(),
        name=name,
        user_text=user_text,
        confirm=confirm,
        dry_run=dry_run,
        args=merged_args,
        idempotency_key=idempotency_key,
        assistant=assistant,
        wolfram_fn=wolfram_fn,
    )
