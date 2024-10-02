import logging
import os
import random
import time
from datetime import datetime
from typing import Optional

import pyautogui
from DrissionPage import ChromiumOptions, ChromiumPage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudflareBypass:
    def __init__(
        self, proxy_server: Optional[str] = None, user_agent: Optional[str] = None
    ):
        options = ChromiumOptions()
     #   options.set_paths(browser_path=config.BROWSER_PATH)

        # https://stackoverflow.com/questions/68289474/selenium-headless-how-to-bypass-cloudflare-detection-using-selenium
        options.headless(True)

        if user_agent:
            options.set_user_agent(user_agent)

        arguments = []
        if proxy_server:
            arguments.append(f"--proxy-server={proxy_server}")

        # 最大化窗口保证坐标的准确性
        arguments.append("--start-maximized")
        arguments.append("--no-sandbox")

        for argument in arguments:
            options.set_argument(argument)

        self.page = ChromiumPage(addr_or_opts=options)
        print(self.page.user_agent)

    def bypass(self, url: str):
        self.page.set.cookies.clear()
        self.page.get(url)

        logger.info(f"self.page.get(url)")
        check_count = 0
        while True:
            print(self.page.cookies())
            if self.is_passed():
                break

            if check_count >= 5:
                error_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-DrissionPage")
                #error_path = os.path.join(config.BROWSER_DATA, "error")
                # self.page.get_screenshot(
                #     path=error_path, name=f"{error_time}.png", full_page=True
                # )
                raise Exception("Meet challenge restart")

            self.try_to_click_challenge()

            check_count += 1

        return self.page.cookies(all_info=True)

    def locate_cf_button(self):
        button = None
        eles = self.page.eles("tag:input")
        for ele in eles:
            if "name" in ele.attrs.keys() and "type" in ele.attrs.keys():
                if "turnstile" in ele.attrs["name"] and ele.attrs["type"] == "hidden":
                    button = ele.parent().shadow_root.child()("tag:body").shadow_root("tag:input")
                    break

        if button:
            return button
        else:
            # If the button is not found, search it recursively
            self.log_message("Basic search failed. Searching for button recursively.")
            ele = self.page.ele("tag:body")
            iframe = self.search_recursively_shadow_root_with_iframe(ele)
            if iframe:
                button = self.search_recursively_shadow_root_with_cf_input(iframe("tag:body"))
            else:
                self.log_message("Iframe not found. Button search failed.")
            return button

    def try_to_click_challenge(self):

        logger.info(f"try_to_click_challenge")


        try:
            # wrapper = self.page.ele(".cf-turnstile-wrapper")
            # shadow_root = wrapper.shadow_root
            # iframe = shadow_root.ele("tag=iframe", timeout=15)
            # verify_element = iframe.ele("Verify you are human", timeout=25)
            # time.sleep(random.uniform(2, 5))

            button = self.locate_cf_button()

            logger.info(f"button {button}")

            # 2024-07-05
            # 直接在element上执行click(通过CDP协议)无法通过cloudflare challenge
            # 原因:
            # CDP命令执行的event中client_x, client_y与screen_x, screen_y是一样的，而手动点击触发的事件两者是不一样的,所以无法使用CDP模拟出鼠标点击通过验证
            # 解决方法:
            # 先获取点击的坐标，使用pyautogui模拟鼠标点击
            # CDP参考 https://chromedevtools.github.io/devtools-protocol/tot/Input/
            # verify_element.click()
            def generate_biased_random(n):
                weights = [min(i, n - i + 1) for i in range(1, n + 1)]
                return random.choices(range(1, n + 1), weights=weights)[0]

            # if config.env == "dev":
            #     property_list = {
            #         attr: getattr(verify_element.rect, attr)
            #         for attr in dir(verify_element.rect)
            #         if not attr.startswith("__")
            #         and not callable(getattr(verify_element.rect, attr))
            #     }
            #
            #     # 手动遍历字典并格式化输出
            #     for key, value in property_list.items():
            #         print(f"{key}: {value}")
            #
            #     print("\n")
            #     property_list = {
            #         attr: getattr(self.page.rect, attr)
            #         for attr in dir(self.page.rect)
            #         if not attr.startswith("__")
            #         and not callable(getattr(self.page.rect, attr))
            #     }
            #
            #     # 手动遍历字典并格式化输出
            #     for key, value in property_list.items():
            #         print(f"{key}: {value}")

            screen_x, screen_y = button.rect.screen_location
            page_x, page_y = self.page.rect.page_location
            width, height = button.rect.size
            offset_x, offset_y = generate_biased_random(
                int(width - 1)
            ), generate_biased_random(int(height - 1))

            click_x, click_y = (
                screen_x + page_x + offset_x,
                screen_y + page_y + offset_y,
            )

            logger.info(f"click_x, click_y")

            pyautogui.moveTo(
                click_x, click_y, duration=0.5, tween=pyautogui.easeInElastic
            )

            logger.info(f"pyautogui.click() ++++ ")

            pyautogui.click()

            logger.info(f"pyautogui.click() ---- ")

            self.page.wait.load_start(timeout=20)
        except Exception as e:
            # 2025-05-26
            # 有时会出现错误，重试能解决一部分问题
            # 1. DrissionPage.errors.ContextLostError: 页面被刷新，请操作前尝试等待页面刷新或加载完成。
            # 2. DrissionPage.errors.ElementNotFoundError:
            #    没有找到元素。
            #    method: ele()
            #    args: {'locator': 'Verify you are human', 'index': 1}

            logger.info(f"Exception {e}")

            self.page.refresh()
            time.sleep(5)

    def is_passed(self):
        return any(
            cookie.get("name") == "cf_clearance" for cookie in self.page.cookies()
        )

    def close(self):
        try:
            self.page.close()
        except Exception as e:
            print(e)