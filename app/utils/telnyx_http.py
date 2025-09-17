import httpx


TELNYX_BASE_URL = "https://api.telnyx.com/v2/calls"


async def telnyx_cmd(call_control_id: str, action: str, telnyx_api_key: str, body: dict | None = None) -> httpx.Response:
    url = f"{TELNYX_BASE_URL}/{call_control_id}/actions/{action}"
    headers = {
        "Authorization": f"Bearer {telnyx_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        return resp


