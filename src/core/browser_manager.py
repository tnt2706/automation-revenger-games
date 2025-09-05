from pathlib import Path
from typing import Optional, Union
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from utils.logger import write_log


class BrowserManager:
    def __init__(self, headless: bool = True, use_profile: bool = False, **kwargs):
        self.headless = headless
        self.use_profile = use_profile
        self.browser_options = {
            "headless": headless,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
            **kwargs,
        }
        self.playwright = None
        self.browser: Optional[Union[Browser, BrowserContext]] = None
        self.is_persistent = False

    async def launch(self) -> Union[Browser, BrowserContext]:
        try:
            self.playwright = await async_playwright().start()
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            if self.use_profile:
                user_data_dir = str(
                    Path.home() / "Library/Application Support/Google/Chrome"
                )
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    **self.browser_options,
                )
                self.is_persistent = True
                write_log("✅ Google Chrome launched with real user profile")
            else:
                self.browser = await self.playwright.chromium.launch(
                    executable_path=chrome_path,
                    **self.browser_options,
                )
                self.is_persistent = False
                write_log("✅ Google Chrome launched (fresh instance)")

            return self.browser

        except Exception as e:
            write_log(f"❌ Error launching Chrome: {str(e)}")
            raise

    async def new_page(self) -> Page:
        if not self.browser:
            raise RuntimeError("Browser not launched")

        if self.is_persistent:
            page = await self.browser.new_page()
        else:
            context = await self.browser.new_context()
            page = await context.new_page()

        write_log("✅ New page created")
        return page

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
                write_log("✅ Browser closed")

            if self.playwright:
                await self.playwright.stop()
                write_log("✅ Playwright stopped")

        except Exception as e:
            write_log(f"⚠️ Error closing browser: {str(e)}")
