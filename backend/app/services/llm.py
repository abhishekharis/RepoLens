"""Model provider. Snowflake Cortex REST API is the live provider; 'offline' is an honestly labeled fallback."""
import json, os, urllib.request, urllib.error

class LLMError(Exception):
    pass

def provider():
    return "snowflake" if os.getenv("SNOWFLAKE_ACCOUNT") and os.getenv("SNOWFLAKE_TOKEN") else "offline"

def model_name():
    return os.getenv("SNOWFLAKE_MODEL", "mistral-7b")

def complete(system: str, user: str, max_tokens: int = 700) -> str:
    """Call Snowflake Cortex inference:complete (non-streaming). Raises LLMError with a user-safe message."""
    account, token = os.getenv("SNOWFLAKE_ACCOUNT"), os.getenv("SNOWFLAKE_TOKEN")
    if not (account and token):
        raise LLMError("Snowflake credentials are not configured. Copy .env.example to .env and set SNOWFLAKE_ACCOUNT and SNOWFLAKE_TOKEN.")
    url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/inference:complete"
    body = {"model": model_name(), "max_tokens": max_tokens, "temperature": 0.1, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json",
               "X-Snowflake-Authorization-Token-Type": os.getenv("SNOWFLAKE_TOKEN_TYPE", "PROGRAMMATIC_ACCESS_TOKEN")}
    req = urllib.request.Request(url, json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        raise LLMError(f"Snowflake API returned HTTP {e.code}. Check the account, token, and that model '{model_name()}' is available in your region.")
    except (KeyError, IndexError, json.JSONDecodeError):
        raise LLMError("Snowflake returned an unexpected response format.")
    except Exception:
        raise LLMError("Could not reach the Snowflake API (timeout or network error). Try again.")
