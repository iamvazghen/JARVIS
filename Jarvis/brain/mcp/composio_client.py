import json
import re
import time

import requests
try:
    from Jarvis.runtime.receipts import record_receipt
except Exception:
    def record_receipt(channel, action, ok, details=None):  # type: ignore
        return False
try:
    from Jarvis.runtime.outbound_queue import enqueue, remove
except Exception:
    def enqueue(channel, action, payload):  # type: ignore
        return "", False
    def remove(item_id):  # type: ignore
        return False

from Jarvis.config import config
try:
    from .telegram_state import TelegramStateStore
except Exception:
    try:
        from Jarvis.brain.mcp.telegram_state import TelegramStateStore
    except Exception:
        class TelegramStateStore:  # type: ignore[no-redef]
            def get_primary_chat_id(self):
                return None

            def get_last_message_id(self, chat_id=None):
                return None

            def update_from_updates_result(self, payload):
                return False

            def update_from_send_message_result(self, payload):
                return False


def _as_bool(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


class ComposioMCPClient:
    def __init__(self):
        self.enabled = _as_bool(getattr(config, "composio_mcp_enabled", "0"))
        self.api_key = getattr(config, "composio_api_key", "") or ""
        self.base_url = getattr(config, "composio_base_url", "") or ""
        self.entity_id = getattr(config, "composio_entity_id", "default") or "default"
        self.playground_test_user_id = (
            getattr(config, "composio_playground_test_user_id", "") or ""
        )
        if (not self.entity_id or self.entity_id == "default") and self.playground_test_user_id:
            self.entity_id = self.playground_test_user_id
        self.use_tool_router = _as_bool(getattr(config, "composio_use_tool_router", "1"))
        self.tool_router_url = getattr(config, "composio_tool_router_url", "") or ""
        self.tool_router_session_id = getattr(config, "composio_tool_router_session_id", "") or ""
        self.auto_create_session = _as_bool(getattr(config, "composio_auto_create_session", "1"))
        self.external_user_id = getattr(config, "composio_external_user_id", "") or ""
        self.enable_noauth_toolkits = _as_bool(
            getattr(config, "composio_enable_noauth_toolkits", "1")
        )
        self.noauth_toolkits_raw = getattr(config, "composio_noauth_toolkits", "") or ""
        self.telegram_auth_config_id = getattr(config, "composio_telegram_auth_config_id", "") or ""
        self.giphy_auth_config_id = getattr(config, "composio_giphy_auth_config_id", "") or ""
        self.gmail_auth_config_id = getattr(config, "composio_gmail_auth_config_id", "") or ""
        raw_allow = getattr(config, "composio_tool_allowlist", "") or ""
        raw_allow_telegram = getattr(config, "composio_tool_allowlist_telegram", "") or ""
        raw_allow_giphy = getattr(config, "composio_tool_allowlist_giphy", "") or ""
        raw_allow_gmail = getattr(config, "composio_tool_allowlist_gmail", "") or ""
        merged_allow = ",".join([raw_allow, raw_allow_telegram, raw_allow_giphy, raw_allow_gmail])
        self.allowlist = {x.strip() for x in merged_allow.split(",") if x.strip()}
        if not self.external_user_id:
            self.external_user_id = self.entity_id
        self._rpc_id = 0
        self._router_initialized = False
        self._client = self._init_sdk_client()
        self._telegram_state = TelegramStateStore()
        self._health_cache = None
        self._health_cache_ts = 0.0

    def _toolkit_aliases(self):
        return {
            "codeinterpreter": ["CODEINTERPRETER", "CODE_INTERPRETER"],
            "composio_search": ["COMPOSIO_SEARCH"],
            "composio": ["COMPOSIO_"],
            "browser_tool": ["BROWSER_TOOL", "BROWSER"],
            "hackernews": ["HACKERNEWS", "HACKER_NEWS"],
            "weathermap": ["WEATHERMAP", "OPENWEATHER", "OPEN_WEATHER"],
            "text_to_pdf": ["TEXT_TO_PDF", "PDF"],
            "entelligence": ["ENTELLIGENCE"],
            "gemini": ["GEMINI"],
            "yelp": ["YELP"],
            "seat_geek": ["SEAT_GEEK", "SEATGEEK"],
            "giphy": ["GIPHY"],
        }

    def _toolkit_patterns(self, toolkit):
        key = str(toolkit or "").strip().lower()
        return self._toolkit_aliases().get(key, [key.upper()] if key else [])

    def _router_native_tools(self):
        return {
            "COMPOSIO_MANAGE_CONNECTIONS",
            "COMPOSIO_MULTI_EXECUTE_TOOL",
            "COMPOSIO_REMOTE_BASH_TOOL",
            "COMPOSIO_REMOTE_WORKBENCH",
            "COMPOSIO_SEARCH_TOOLS",
            "COMPOSIO_GET_TOOL_SCHEMAS",
        }

    def _is_telegram_tool(self, tool_name):
        return str(tool_name or "").upper().startswith("TELEGRAM_")

    def _has_tool_router(self):
        return bool(self.tool_router_url.strip())

    def _init_sdk_client(self):
        if self.use_tool_router:
            return None
        if not self.api_key:
            return None
        try:
            from composio import ComposioToolSet  # type: ignore
        except Exception:
            return None
        try:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            return ComposioToolSet(**kwargs)
        except Exception:
            return None

    def _is_allowed_tool(self, tool_name):
        if not self.allowlist:
            return True
        name = str(tool_name or "").strip()
        if not name:
            return False
        if name in self.allowlist:
            return True
        upper_name = name.upper()
        for rule in self.allowlist:
            r = str(rule or "").strip()
            if not r:
                continue
            if r.endswith("*"):
                prefix = r[:-1].upper()
                if upper_name.startswith(prefix):
                    return True
        # If no-auth toolkits are enabled, allow their discovered tool name prefixes.
        for toolkit in self._noauth_toolkits():
            patterns = self._toolkit_patterns(toolkit)
            if any(p and p in upper_name for p in patterns):
                return True
        return False

    def _normalize_name(self, item):
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            fn = item.get("function")
            if isinstance(fn, dict):
                fn_name = fn.get("name")
                if fn_name:
                    return str(fn_name).strip()
            for key in ("tool_name", "name", "slug", "id"):
                value = item.get(key)
                if value:
                    return str(value).strip()
        return ""

    def _extract_tool_names(self, data):
        if isinstance(data, dict):
            # Different SDKs may wrap with `tools` or `data`.
            candidate = data.get("tools")
            if isinstance(candidate, list):
                data = candidate
            else:
                candidate = data.get("data")
                if isinstance(candidate, list):
                    data = candidate
        if not isinstance(data, list):
            return []
        names = []
        for item in data:
            name = self._normalize_name(item)
            if not name:
                continue
            if not self._is_allowed_tool(name):
                continue
            names.append(name)
        return sorted(set(names))

    def _noauth_toolkits(self):
        if not self.enable_noauth_toolkits:
            return []
        return [x.strip() for x in self.noauth_toolkits_raw.split(",") if x.strip()]

    def _list_noauth_tools(self):
        toolkits = self._noauth_toolkits()
        if not toolkits:
            return {"ok": True, "tools": []}
        if not self.api_key:
            return {"ok": False, "error_code": "missing_api_key", "tools": []}
        if not self.external_user_id:
            return {"ok": False, "error_code": "missing_external_user_id", "tools": []}
        try:
            from composio import Composio  # type: ignore
        except Exception:
            return {"ok": False, "error_code": "sdk_unavailable", "tools": []}

        try:
            composio = Composio(api_key=self.api_key)
            tools_client = getattr(composio, "tools", None)
            if tools_client is None or not hasattr(tools_client, "get"):
                return {"ok": False, "error_code": "sdk_missing_tools_get", "tools": []}
            try:
                data = tools_client.get(self.external_user_id, {"toolkits": toolkits})
            except TypeError:
                data = tools_client.get(user_id=self.external_user_id, toolkits=toolkits)
        except Exception as e:
            return {"ok": False, "error_code": "list_noauth_failed", "details": str(e), "tools": []}

        tools = self._extract_tool_names(data)
        return {"ok": True, "tools": tools}

    def list_tools(self):
        if not self.enabled:
            return {"ok": False, "error_code": "disabled", "tools": []}
        if not self.api_key:
            return {"ok": False, "error_code": "missing_api_key", "tools": []}
        merged = []
        errors = []

        if self._has_tool_router():
            router = self._list_tools_via_router()
            if router.get("ok"):
                merged.extend(router.get("tools") or [])
            else:
                errors.append(router)
        else:
            if not self._client:
                errors.append({"ok": False, "error_code": "sdk_unavailable", "tools": []})
            else:
                try:
                    if hasattr(self._client, "get_tools"):
                        data = self._client.get_tools()
                    elif hasattr(self._client, "list_tools"):
                        data = self._client.list_tools()
                    else:
                        data = []
                        errors.append({"ok": False, "error_code": "sdk_missing_list_tools", "tools": []})
                    merged.extend(self._extract_tool_names(data))
                except Exception as e:
                    errors.append(
                        {"ok": False, "error_code": "list_tools_failed", "details": str(e), "tools": []}
                    )

        noauth = self._list_noauth_tools()
        if noauth.get("ok"):
            merged.extend(noauth.get("tools") or [])
        else:
            errors.append(noauth)

        deduped = sorted(set([x for x in merged if x]))
        # Keep configured explicit allowlist names discoverable even if tool listing
        # endpoint returns partial data for a temporary router session.
        explicit_allow = [x for x in self.allowlist if x and not str(x).endswith("*")]
        deduped = sorted(set(deduped + explicit_allow))
        if deduped:
            return {"ok": True, "tools": deduped}
        if errors:
            first = errors[0]
            out = {"ok": False, "tools": [], "error_code": first.get("error_code", "list_tools_failed")}
            if first.get("details"):
                out["details"] = first.get("details")
            return out
        return {"ok": False, "tools": [], "error_code": "no_tools_available"}

    def _is_outbound_action_tool(self, tool_name):
        up = str(tool_name or "").upper()
        return up.startswith("TELEGRAM_SEND_") or up.startswith("GMAIL_SEND_")

    def _execute_with_outbound_queue(self, *, tool_name, tool_input):
        queue_enabled = str(getattr(config, "runtime_outbound_queue_enabled", "1")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        retries = max(0, int(getattr(config, "runtime_outbound_retry_max", 2)))
        job_id = ""
        if queue_enabled and self._is_outbound_action_tool(tool_name):
            job_id, _ = enqueue("composio", tool_name, tool_input or {})

        last = {"ok": False, "tool_name": tool_name, "error_code": "execution_failed"}
        for _ in range(retries + 1):
            last = self._execute_via_router(tool_name=tool_name, tool_input=tool_input)
            if last.get("ok"):
                break
            time.sleep(0.2)

        if job_id and last.get("ok"):
            remove(job_id)
        if self._is_outbound_action_tool(tool_name):
            record_receipt(
                "composio",
                tool_name,
                bool(last.get("ok")),
                {"error_code": last.get("error_code", ""), "job_id": job_id},
            )
        return last

    def execute(self, *, tool_name, tool_input=None):
        requested_tool_name = str(tool_name or "").strip()
        tool_name = requested_tool_name
        tool_input = tool_input if isinstance(tool_input, dict) else {}
        if not tool_name:
            return {"ok": False, "error_code": "missing_tool_name"}
        if not self.enabled:
            return {"ok": False, "error_code": "disabled", "tool_name": tool_name}
        if not self.api_key:
            return {"ok": False, "error_code": "missing_api_key", "tool_name": tool_name}
        resolved = self._resolve_tool_name(tool_name=tool_name, tool_input=tool_input)
        if not resolved.get("ok"):
            return {
                "ok": False,
                "tool_name": tool_name,
                "error_code": resolved.get("error_code", "tool_resolution_failed"),
                "details": resolved.get("details", ""),
            }
        tool_name = resolved.get("tool_name", tool_name)
        tool_input = self._apply_default_auth_config(
            requested_tool_name=requested_tool_name,
            resolved_tool_name=tool_name,
            tool_input=tool_input,
        )
        tool_input = self._strip_meta_args(tool_input)
        if self._is_telegram_tool(tool_name):
            tool_input = self._prepare_telegram_args(tool_name=tool_name, tool_input=tool_input)
        if not self._is_allowed_tool(tool_name):
            return {"ok": False, "error_code": "tool_not_allowed", "tool_name": tool_name}
        if self._has_tool_router():
            res = self._execute_with_outbound_queue(tool_name=tool_name, tool_input=tool_input)
            self._update_telegram_state_from_result(tool_name=tool_name, tool_result=res)
            return res
        if not self._client:
            return {"ok": False, "error_code": "sdk_unavailable", "tool_name": tool_name}

        try:
            if hasattr(self._client, "execute_tool"):
                result = self._client.execute_tool(tool_name=tool_name, arguments=tool_input)
            elif hasattr(self._client, "execute_action"):
                result = self._client.execute_action(action=tool_name, params=tool_input)
            elif hasattr(self._client, "execute"):
                result = self._client.execute(action=tool_name, params=tool_input)
            elif hasattr(self._client, "run"):
                result = self._client.run(tool_name=tool_name, arguments=tool_input)
            else:
                return {
                    "ok": False,
                    "error_code": "sdk_missing_execute",
                    "tool_name": tool_name,
                }
        except Exception as e:
            return {
                "ok": False,
                "error_code": "execution_failed",
                "tool_name": tool_name,
                "details": str(e),
            }

        out = {"ok": True, "tool_name": tool_name, "data": result}
        self._update_telegram_state_from_result(tool_name=tool_name, tool_result=out)
        return out

    def _apply_default_auth_config(self, *, requested_tool_name, resolved_tool_name, tool_input):
        args = dict(tool_input or {})
        if args.get("auth_config_id"):
            return args

        requested = str(requested_tool_name or "").upper()
        resolved = str(resolved_tool_name or "").upper()
        if resolved.startswith("TELEGRAM_"):
            cfg = str(self.telegram_auth_config_id or "").strip()
            if cfg:
                args["auth_config_id"] = cfg
        if resolved.startswith("GMAIL_"):
            cfg = str(self.gmail_auth_config_id or "").strip()
            if cfg:
                args["auth_config_id"] = cfg
        if requested.startswith("AUTO_TOOLKIT:GIPHY") or resolved.startswith("GIPHY_"):
            cfg = str(self.giphy_auth_config_id or "").strip()
            if cfg:
                args["auth_config_id"] = cfg
        return args

    def _strip_meta_args(self, tool_input):
        if not isinstance(tool_input, dict):
            return {}
        clean = {}
        for k, v in tool_input.items():
            key = str(k)
            if key.startswith("_"):
                continue
            clean[key] = v
        return clean

    def _prepare_telegram_args(self, *, tool_name, tool_input):
        args = dict(tool_input or {})
        chat_id_needed_tools = {
            "TELEGRAM_SEND_MESSAGE",
            "TELEGRAM_SEND_PHOTO",
            "TELEGRAM_SEND_DOCUMENT",
            "TELEGRAM_SEND_LOCATION",
            "TELEGRAM_SEND_POLL",
            "TELEGRAM_GET_CHAT",
            "TELEGRAM_GET_CHAT_MEMBER",
            "TELEGRAM_GET_CHAT_MEMBERS_COUNT",
            "TELEGRAM_GET_CHAT_ADMINISTRATORS",
            "TELEGRAM_GET_CHAT_HISTORY",
            "TELEGRAM_EDIT_MESSAGE",
            "TELEGRAM_DELETE_MESSAGE",
            "TELEGRAM_EXPORT_CHAT_INVITE_LINK",
            "TELEGRAM_FORWARD_MESSAGE",
        }
        upper_name = str(tool_name or "").upper()
        if upper_name in chat_id_needed_tools and not args.get("chat_id"):
            chat_id = self._telegram_state.get_primary_chat_id()
            if chat_id not in ("", None):
                args["chat_id"] = chat_id

        # Reply/edit/delete convenience when caller requested "last".
        if args.pop("_reply_to_last", False) and not args.get("reply_to_message_id"):
            msg_id = self._telegram_state.get_last_message_id(args.get("chat_id"))
            if msg_id not in ("", None):
                args["reply_to_message_id"] = msg_id

        if args.pop("_use_last_message_id", False) and not args.get("message_id"):
            msg_id = self._telegram_state.get_last_message_id(args.get("chat_id"))
            if msg_id not in ("", None):
                args["message_id"] = msg_id
        return args

    def _parse_multi_execute_content(self, result):
        if not isinstance(result, dict):
            return {}
        content = result.get("content")
        if not isinstance(content, list) or not content:
            return {}
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text", "")
        else:
            text = str(first)
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _update_telegram_state_from_result(self, *, tool_name, tool_result):
        if not self._is_telegram_tool(tool_name):
            return
        if not isinstance(tool_result, dict) or not tool_result.get("ok"):
            return
        data = tool_result.get("data")
        if not isinstance(data, dict):
            return
        payload = data
        # Multi-execute structure: {"successful":true,"data":{"results":[{"response":{"successful":...,"data":{...}}}]}}
        if "successful" in data and isinstance(data.get("data"), dict):
            rows = data.get("data", {}).get("results")
            if isinstance(rows, list) and rows:
                first = rows[0] if isinstance(rows[0], dict) else {}
                response = first.get("response") if isinstance(first, dict) else {}
                if isinstance(response, dict):
                    payload = response.get("data") if isinstance(response.get("data"), dict) else {}
        if not isinstance(payload, dict):
            return
        up = str(tool_name).upper()
        if up == "TELEGRAM_GET_UPDATES":
            self._telegram_state.update_from_updates_result(payload)
        elif up == "TELEGRAM_SEND_MESSAGE":
            self._telegram_state.update_from_send_message_result(payload)
        elif up in ("TELEGRAM_SEND_PHOTO", "TELEGRAM_SEND_DOCUMENT", "TELEGRAM_SEND_LOCATION", "TELEGRAM_SEND_POLL"):
            self._telegram_state.update_from_send_message_result(payload)

    def _resolve_tool_name(self, *, tool_name, tool_input):
        if not str(tool_name).startswith("AUTO_TOOLKIT:"):
            return {"ok": True, "tool_name": tool_name}
        parts = str(tool_name).split(":", 2)
        toolkit = parts[1].strip().lower() if len(parts) >= 2 else ""
        if not toolkit:
            return {"ok": False, "error_code": "missing_toolkit_name"}

        listed = self.list_tools()
        tools = [str(x) for x in (listed.get("tools") or []) if str(x).strip()]
        # Fallback to explicit allowlist names when listing is partial/unavailable.
        if not tools:
            tools = [str(x) for x in self.allowlist if str(x).strip()]
        if not tools:
            return {
                "ok": False,
                "error_code": "tool_list_unavailable",
                "details": listed.get("error_code", "no_tools_available"),
            }

        patterns = self._toolkit_patterns(toolkit)
        candidates = []
        for t in tools:
            up = t.upper()
            if any(p in up for p in patterns):
                candidates.append(t)
        if not candidates:
            return {"ok": False, "error_code": "toolkit_tool_not_found", "details": toolkit}

        hint = str((tool_input or {}).get("_action_hint", "")).strip().upper()
        if hint:
            hinted = [t for t in candidates if hint in t.upper()]
            if hinted:
                return {"ok": True, "tool_name": sorted(hinted)[0]}
        return {"ok": True, "tool_name": sorted(candidates)[0]}

    def _extract_mcp_url(self, mcp_obj):
        if isinstance(mcp_obj, str):
            return mcp_obj.strip()
        if isinstance(mcp_obj, dict):
            for key in ("url", "endpoint", "mcp_url"):
                value = mcp_obj.get(key)
                if value:
                    return str(value).strip()
        for attr in ("url", "endpoint", "mcp_url"):
            value = getattr(mcp_obj, attr, "")
            if value:
                return str(value).strip()
        return ""

    def _extract_session_id_from_url(self, url):
        marker = "/tool_router/"
        if marker not in url:
            return ""
        tail = url.split(marker, 1)[-1]
        sid = tail.split("/mcp", 1)[0]
        return sid.strip()

    def _ensure_tool_router_session(self):
        if not self.use_tool_router:
            return {"ok": False, "error_code": "tool_router_disabled"}
        if self._has_tool_router():
            return {"ok": True}
        if not self.auto_create_session:
            return {"ok": False, "error_code": "missing_tool_router_url"}
        if not self.api_key:
            return {"ok": False, "error_code": "missing_api_key"}
        if not self.external_user_id:
            return {"ok": False, "error_code": "missing_external_user_id"}

        try:
            from composio import Composio  # type: ignore
        except Exception:
            return {"ok": False, "error_code": "sdk_unavailable"}

        try:
            composio = Composio(api_key=self.api_key)
            session = composio.create(user_id=self.external_user_id)
            mcp = getattr(session, "mcp", None)
            mcp_url = self._extract_mcp_url(mcp)
            if not mcp_url:
                return {"ok": False, "error_code": "session_missing_mcp_url"}
            self.tool_router_url = mcp_url
            if not self.tool_router_session_id:
                self.tool_router_session_id = self._extract_session_id_from_url(mcp_url)
            self._router_initialized = False
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error_code": "session_create_failed", "details": str(e)}

    def _router_headers(self):
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            # Composio tool router may respond via SSE framing even for JSON-RPC calls.
            "Accept": "application/json, text/event-stream",
        }
        if self.entity_id:
            headers["x-composio-entity-id"] = self.entity_id
        return headers

    def _decode_router_response(self, resp):
        try:
            return resp.json()
        except Exception:
            text = resp.text or ""
            if not text:
                raise
            blocks = []
            current = []
            for line in text.splitlines():
                if line.startswith("data:"):
                    current.append(line[len("data:") :].strip())
                    continue
                if not line.strip() and current:
                    blocks.append("\n".join(current))
                    current = []
            if current:
                blocks.append("\n".join(current))
            if not blocks:
                raise
            last_err = None
            for payload in reversed(blocks):
                try:
                    return json.loads(payload)
                except Exception as e:
                    # Some providers return non-standard \xNN escapes inside JSON strings.
                    # Normalize these to escaped form so json parser can proceed.
                    try:
                        fixed = re.sub(r"\\x([0-9a-fA-F]{2})", r"\\\\x\1", payload)
                        return json.loads(fixed)
                    except Exception:
                        last_err = e
            raise last_err if last_err else ValueError("Unable to parse SSE response payload")

    def _mcp_request(self, method, params=None):
        ready = self._ensure_tool_router_session()
        if not ready.get("ok"):
            return {
                "ok": False,
                "error_code": ready.get("error_code", "missing_tool_router_url"),
                "details": ready.get("details", ""),
            }
        self._rpc_id += 1
        payload = {"jsonrpc": "2.0", "id": self._rpc_id, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            resp = requests.post(
                self.tool_router_url,
                headers=self._router_headers(),
                json=payload,
                timeout=int(getattr(config, "composio_timeout_s", 8)),
            )
            resp.raise_for_status()
            data = self._decode_router_response(resp)
        except Exception as e:
            return {"ok": False, "error_code": "router_request_failed", "details": str(e)}

        if isinstance(data, dict) and data.get("error"):
            err = data.get("error") or {}
            msg = err.get("message") if isinstance(err, dict) else str(err)
            return {"ok": False, "error_code": "router_error", "details": str(msg or "")}
        if not isinstance(data, dict):
            return {"ok": False, "error_code": "router_invalid_response"}
        return {"ok": True, "result": data.get("result")}

    def _ensure_router_initialized(self):
        if self._router_initialized:
            return {"ok": True}
        init_payload = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jivan", "version": "1.0"},
        }
        res = self._mcp_request("initialize", init_payload)
        if not res.get("ok"):
            return res
        self._router_initialized = True
        return {"ok": True}

    def _list_tools_via_router(self):
        init = self._ensure_router_initialized()
        if not init.get("ok"):
            out = {"ok": False, "tools": [], "error_code": init.get("error_code", "init_failed")}
            if init.get("details"):
                out["details"] = init.get("details")
            return out
        res = self._mcp_request("tools/list", {})
        if not res.get("ok"):
            out = {"ok": False, "tools": [], "error_code": res.get("error_code", "list_tools_failed")}
            if res.get("details"):
                out["details"] = res.get("details")
            return out
        result = res.get("result") if isinstance(res.get("result"), dict) else {}
        tools = self._extract_tool_names(result.get("tools") or [])
        return {"ok": True, "tools": tools}

    def _execute_via_router(self, *, tool_name, tool_input):
        init = self._ensure_router_initialized()
        if not init.get("ok"):
            out = {"ok": False, "tool_name": tool_name, "error_code": init.get("error_code", "init_failed")}
            if init.get("details"):
                out["details"] = init.get("details")
            return out
        upper_name = str(tool_name or "").upper()
        if upper_name in self._router_native_tools():
            payload = {"name": tool_name, "arguments": tool_input or {}}
            res = self._mcp_request("tools/call", payload)
            if not res.get("ok"):
                out = {"ok": False, "tool_name": tool_name, "error_code": res.get("error_code", "execution_failed")}
                if res.get("details"):
                    out["details"] = res.get("details")
                return out
            return {"ok": True, "tool_name": tool_name, "data": res.get("result")}

        # Tool router exposes COMPOSIO_MULTI_EXECUTE_TOOL as the normal path for most toolkit slugs.
        wrapper_args = {
            "tools": [{"tool_slug": tool_name, "arguments": tool_input or {}}],
            "sync_response_to_workbench": False,
            "thought": f"Execute {tool_name}",
        }
        res = self._mcp_request(
            "tools/call",
            {"name": "COMPOSIO_MULTI_EXECUTE_TOOL", "arguments": wrapper_args},
        )
        if not res.get("ok"):
            out = {"ok": False, "tool_name": tool_name, "error_code": res.get("error_code", "execution_failed")}
            if res.get("details"):
                out["details"] = res.get("details")
            return out
        parsed = self._parse_multi_execute_content(res.get("result"))
        if isinstance(parsed, dict) and parsed.get("successful") is False:
            return {
                "ok": False,
                "tool_name": tool_name,
                "error_code": "execution_failed",
                "details": parsed.get("error", "multi_execute_failed"),
                "data": parsed,
            }
        return {"ok": True, "tool_name": tool_name, "data": parsed or (res.get("result") or {})}

    def health_check(self, force=False):
        now = time.time()
        if not force and self._health_cache is not None and (now - self._health_cache_ts) < 30:
            return dict(self._health_cache)

        if not self.enabled:
            status = {"enabled": False, "ok": False, "status": "disabled"}
        elif not self.api_key:
            status = {"enabled": True, "ok": False, "status": "missing_api_key"}
        elif self._has_tool_router():
            probe = self._list_tools_via_router()
            if probe.get("ok"):
                status = {"enabled": True, "ok": True, "status": "connected"}
            else:
                status = {
                    "enabled": True,
                    "ok": False,
                    "status": probe.get("error_code", "connect_failed"),
                }
                details = probe.get("details")
                if details:
                    status["details"] = details
        elif not self._client:
            status = {"enabled": True, "ok": False, "status": "sdk_unavailable"}
        else:
            probe = self.list_tools()
            if probe.get("ok"):
                status = {"enabled": True, "ok": True, "status": "connected"}
            else:
                status = {
                    "enabled": True,
                    "ok": False,
                    "status": probe.get("error_code", "connect_failed"),
                }
                details = probe.get("details")
                if details:
                    status["details"] = details

        self._health_cache = status
        self._health_cache_ts = now
        return dict(status)
