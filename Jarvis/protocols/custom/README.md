Custom Protocol Format (JSON)
============================

Create `.json` files in this folder. Each file can contain:

1. A single protocol object, or
2. A list of protocol objects.

Protocol schema (supported fields):

```json
{
  "name": "focus_chain",
  "aliases": ["focus mode chain"],
  "description": "Example custom protocol chain",
  "side_effects": true,
  "requires_confirmation": true,
  "confirmation_policy": "if_side_effects",
  "triggers": ["run protocol focus chain", "focus chain protocol"],
  "negative_triggers": [],
  "cooldown_s": 5,
  "args_schema": {
    "target": { "type": "string", "required": false }
  },
  "steps": [
    { "type": "say", "text": "Running custom protocol for {{target}}" },
    { "type": "action", "name": "shutdown_app" }
  ]
}
```

Step types:

- `say`: add message event (text can use placeholders like `{{target}}`, `{{user_text}}`)
- `action`: currently supports `shutdown_app` and `shutdown_pc`
- `tool`: execute a Brain tool by name with explicit args
- `protocol`: execute another protocol by name

Example nested protocol step:

```json
{ "type": "protocol", "name": "monday" }
```

Example tool step:

```json
{
  "type": "tool",
  "name": "focus_mode",
  "args": { "close_apps": true, "confirm": true }
}
```

Notes:

- Protocol `name` must be lowercase-safe and unique.
- Files are auto-discovered at runtime from this folder.
- Invalid files are skipped with a console warning.
