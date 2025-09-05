from utils.logger import write_log
from utils.paths import (
    get_output_path,
)


current_game_responses = []
current_game_info = {
    "code": "",
    "name": "",
    "mode": "",
    "token": "",
    "language": "",
    "page": any,
}
import asyncio

ERROR_PATTERNS = [
    "internal server error",
    "service unavailable",
    "gateway timeout",
    "bad gateway",
]

ERROR_STATUS_CODES = [400, 401, 403, 404, 408, 500, 502, 503, 504]


TRACKED_ENDPOINTS = [
    "gameService",
    "playerService",
    "betService",
]


def set_game_info(game_code: str, game_name: str, language: str, token: str, page: any):
    global current_game_info
    current_game_info["code"] = game_code
    current_game_info["name"] = game_name
    current_game_info["language"] = language
    current_game_info["token"] = token
    current_game_info["page"] = page


def set_current_mode(mode: str):
    global current_game_info
    current_game_info["mode"] = mode


async def on_response(response):
    try:
        if not any(endpoint in response.url for endpoint in TRACKED_ENDPOINTS):
            return

        content_type = response.headers.get("content-type", "").lower()
        body_data = None

        if "application/json" in content_type:
            try:
                body_data = await response.json()
            except Exception:
                body_data = await response.text()
        elif any(t in content_type for t in ["text", "xml", "html"]):
            body_data = await response.text()
        else:
            raw = await response.body()
            body_data = f"[non-text content: {len(raw)} bytes]"

        body_str = str(body_data).lower()

        data = {
            "url": response.url,
            "status": response.status,
            "method": response.request.method,
            "body": body_data,
        }

        game_code = current_game_info["code"]
        game_name = current_game_info["name"]
        mode = current_game_info["mode"]

        if response.status in ERROR_STATUS_CODES or any(
            err in body_str for err in ERROR_PATTERNS
        ):
            screenshot_result = await _capture_screenshot_error(
                token=current_game_info["token"],
                game_code=game_code,
                language=current_game_info["language"],
                mode=mode,
                page=current_game_info["page"],
            )

            print(f"❌ Game [{game_code}] {game_name} | Mode [{mode}]")
            write_log(
                f"❌ Game [{game_code}] {game_name} | Mode [{mode}] failed with status {response.status}: {response.url}"
            )

    except Exception as e:
        write_log(f"⚠️ Error tracking response: {e}")


async def _capture_screenshot_error(token, game_code, language, mode, page):
    from actions.game_actions import capture_screenshot

    try:
        mode_folder = get_output_path(token, game_code, language) / mode
        mode_folder.mkdir(parents=True, exist_ok=True)
        output_path = mode_folder / "ERROR_capture.jpg"

        await asyncio.sleep(0.5)
        await capture_screenshot(page, output_path, mode)
        return True

    except Exception as e:
        return False
