import asyncio
from dataclasses import dataclass
import heapq
from http.client import IM_USED
from itertools import combinations
import json
import math
from pathlib import Path
import random
import shutil
import socket
import threading
from weakref import proxy
from playwright.async_api import async_playwright
from playwright.async_api import ProxySettings
from loguru import logger
from .sth import handle_client, proxy_forever
import time
import cv2
import numpy as np
import re
import httpx


# 目标图片的显示尺寸与实际尺寸的比例
actual_target_width = 672
actual_target_height = 480
display_target_width = 340
display_target_height = 240.84

# 验证码iframe的实际尺寸
iframe_width = 360
iframe_height = 360

# 目标图片在iframe中的偏移位置
iframe_offset_x = 10
iframe_offset_y = 70


class Socks2Http:
    def __init__(self, host: str, port: int, username: str, password: str):
        port_h = random.randint(10000, 20000)
        self.proxy_thread = threading.Thread(
            target=self.process,
            args=(port_h, host, port, username, password),
            daemon=True,
        )
        self.proxy_thread.start()
        self.server = f"http://127.0.0.1:{port_h}"

    def process(
        self,
        port: int,
        socks5_host: str,
        socks5_port: int,
        username: str,
        password: str,
    ):
        # 创建代理服务���套接字
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置地址和端口
        server_address = ("127.0.0.1", port)
        # 绑定地址和端口
        server_socket.bind(server_address)
        # 监听连接
        server_socket.listen(5)
        logger.info("Proxy listening on: %s:%d" % server_address)
        try:
            while True:
                # 等待客户端连接
                client_socket, client_address = server_socket.accept()
                logger.debug("Client connect：%s:%d" % client_address)
                # 创建线程处理客户端请求
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, socks5_host, socks5_port, username, password),
                    daemon=True,
                )
                client_thread.start()

        finally:
            # 关闭服务器套接字
            server_socket.close()


proxies = [
    # {
    #     "url": "socks5://gm.rainplay.cn:19189",
    #     "username": "test",
    #     "password": "1145141919810",
    # }
    # ProxySettings(
    #     server="socks5://test:1145141919810@gm.rainplay.cn:19189"
    # )
    #     ProxySettings(
    #     server="http://192.168.7.5:7890"
    # )
    # ProxySettings(server="http://127.0.0.1:" + str(port))
    # ProxySettings(
    #     server="http://127.0.0.1:12345", username="test", password="1145141919810"
    # )
    {
        "type": "http",
        "server": Socks2Http("gm.rainplay.cn", 19189, "test", "1145141919810").server,
        "ban_time": 0,
        "ban_count": 10,
        "base_ban_count": 10,
    },
    {"type": "local", "ban_time": 0, "ban_count": 10, "base_ban_count": 10},
]


def ae(inp):
    assert inp
    return inp


# 下载图片数据
async def download_image(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)


def match_template(base_img_np: np.ndarray, target_img_np: np.ndarray):
    # 确保图像是灰度图并符合要求
    base_img_gray = cv2.cvtColor(base_img_np, cv2.COLOR_BGR2GRAY)
    _, target_img_gray = cv2.threshold(
        cv2.cvtColor(target_img_np, cv2.COLOR_BGR2GRAY), 40, 255, cv2.THRESH_BINARY
    )

    # 提取基准图片中的三个图标
    icon_width = base_img_gray.shape[1] // 3
    icons = []
    for i in range(3):
        icon = base_img_gray[:, i * icon_width : (i + 1) * icon_width]
        # Find non-zero pixels (icon content)
        _, icon = cv2.threshold(icon, 20, 230, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        non_zero = cv2.findNonZero(cv2.threshold(icon, 30, 255, cv2.THRESH_BINARY)[1])
        x, y, w, h = cv2.boundingRect(non_zero)

        # Clip the image to the bounding rectangle with small padding
        padding = 2
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(icon.shape[1] - x, w + 2 * padding)
        h = min(icon.shape[0] - y, h + 2 * padding)
        icon = icon[y : y + h, x : x + w]

        # _, icon_thresh = cv2.threshold(icon, 127, 255, cv2.THRESH_BINARY)
        # cv2.imshow("Detection Results", icon)
        # cv2.waitKey(60000)  # 显示1秒
        icons.append(icon)

    # 检测关键点和计算描述符
    rst = []

    # result_img = target_img_np.copy()
    for icon in icons:
        icon = cv2.resize(
            icon,
            (int(icon.shape[1] * 1.6), int(icon.shape[0] * 1.6)),
            interpolation=cv2.INTER_CUBIC,
        )

        # First pass: 10-degree steps
        keep_heqpq = []
        for angle in range(-90, 90, 5):
            angle += 360
            angle %= 360

            M = cv2.getRotationMatrix2D(
                (icon.shape[1] // 2, icon.shape[0] // 2), angle, 1
            )
            rotated_icon = cv2.warpAffine(icon, M, (icon.shape[1], icon.shape[0]))
            result = cv2.matchTemplate(
                target_img_gray, rotated_icon, cv2.TM_CCOEFF_NORMED
            )
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if len(keep_heqpq) < 10:
                heapq.heappush(keep_heqpq, (max_val, angle, max_loc))
            else:
                heapq.heappushpop(keep_heqpq, (max_val, angle, max_loc))

        best_score = 0
        # best_angle = 0
        best_location = (0, 0)
        for t in keep_heqpq:
            _, angle, _ = t

            # Second pass: Fine-tuning ±5 degrees
            for angle in range(angle - 3, angle + 3):
                M = cv2.getRotationMatrix2D(
                    (icon.shape[1] // 2, icon.shape[0] // 2), angle, 1
                )
                rotated_icon = cv2.warpAffine(
                    icon, M, (icon.shape[1], icon.shape[0]), borderValue=(255,)
                )
                result = cv2.matchTemplate(
                    target_img_gray, rotated_icon, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val > best_score:
                    best_score = max_val
                    best_location = max_loc
                    # best_angle = angle

        if best_score > 0.7:  # Adjust threshold as needed
            x, y = best_location
            rst.append((x + icon.shape[1] // 2, y + icon.shape[0] // 2))
            # cv2.rectangle(
            #     result_img,
            #     (x, y),
            #     (x + icon.shape[1], y + icon.shape[0]),
            #     (0, 255, 0),
            #     2,
            # )
            # # paste
            # # 将icon粘贴到result_img上
            # M = cv2.getRotationMatrix2D(
            #     (icon.shape[1] // 2, icon.shape[0] // 2), best_angle, 1
            # )
            # rotated_icon = cv2.warpAffine(
            #     icon, M, (icon.shape[1], icon.shape[0]), borderValue=(255,)
            # )
            # result_img[y : y + icon.shape[0], x : x + icon.shape[1]] = cv2.cvtColor(
            #     rotated_icon, cv2.COLOR_GRAY2BGR
            # )

        else:
            raise Exception("Failed to locate icon: score too low")
    for a, b in combinations(rst, 2):
        if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < 600:
            raise Exception("Failed to locate all three icons: too close")
    if len(rst) != 3:
        raise Exception("Failed to locate all three icons")
    # # 显示结果图片
    # cv2.imshow("Detection Results", result_img)
    # cv2.waitKey(3000)  # 显示1秒
    # cv2.destroyAllWindows()
    return rst


async def get_ticket(*, headless: bool = True) -> str:
    data_p = Path("data/pic")
    if data_p.exists():
        shutil.rmtree(data_p)
    data_p.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        load_timeout = 200000
        load_timeout_short = 100000
        wait_timeout = 40000
        # with open("data/proxy.json") as f:
        #     proxy=random.choice(json.load(f))
        count = 0
        while (proxy := random.choice(proxies))["ban_time"] > time.time():
            count = (count + 1) % 100
            if count == 0:
                print("All proxies are banned. Waiting for 10 minutes...")
                for i in range(600):
                    await asyncio.sleep(1)
            await asyncio.sleep(0.1)
        if proxy["type"] == "local":
            browser = await p.chromium.launch(
                headless=headless,
                timeout=load_timeout,
            )
        else:
            browser = await p.chromium.launch(
                headless=headless,
                timeout=load_timeout,
                proxy=ProxySettings(server=proxy["server"]),
            )  # 设置headless=False来显示浏览器
        page = await browser.new_page()

        load_js = """
                ticket = '';
                const captcha = new window.TencentCaptcha("2039519451", (response) => {
                    if (response.ret === 0) {
                        // console.log('ticket:', response.ticket);
                        // console.log('randstr:', response.randstr);
                        ticket=response.ticket;
                    }
                });
                captcha.show();
                """
        try:
            # 打开指定网址
            await page.goto("https://app.rainyun.com", timeout=load_timeout)

            # 执行验证码初始化JavaScript代码
            await page.evaluate(load_js)
            while True:
                for _ in range(30):
                    try:
                        # 等待iframe加载
                        iframe_element = ae(
                            await page.wait_for_selector(
                                "iframe", timeout=load_timeout_short
                            )
                        )

                        iframe = ae(await iframe_element.content_frame())

                        # 获取基准图片的src
                        base_img_element = ae(
                            await iframe.wait_for_selector(
                                "div.tc-instruction-icon img", timeout=wait_timeout
                            )
                        )
                        base_img_src = ae(await base_img_element.get_attribute("src"))

                        # 获取目标图片的background-image
                        target_img_element = ae(
                            await iframe.wait_for_selector(
                                "div.tc-bg-img.unselectable", timeout=wait_timeout
                            )
                        )

                        target_img_style = ae(
                            await target_img_element.get_attribute("style")
                        )
                        target_img_url = ae(
                            re.search(r'url\("(.+?)"\)', target_img_style)
                        ).group(1)
                        break
                    except Exception as e:
                        logger.debug(e)
                        logger.info("Failed to get captcha info. Retrying...")
                        await asyncio.sleep(0.5)
                        continue
                else:
                    raise Exception("Failed to get captcha info.")
                await page.screenshot(path=data_p / f"{time.time_ns()}.png")
                # 下载图片数据
                base_img_np = await download_image(base_img_src)
                target_img_np = await download_image(target_img_url)
                # cv2.imshow("Detection Results", target_img_np)
                # cv2.waitKey(30000)  # 显示1秒
                # cv2.destroyAllWindows()

                try:
                    rst = match_template(base_img_np, target_img_np)
                    if len(rst) == 3:
                        break

                except Exception as e:
                    logger.debug(e)
                    try:
                        await ae(
                            await iframe.wait_for_selector(
                                "div.tc-action.tc-icon.tc-action--refresh.show-reload img",
                                timeout=wait_timeout,
                            )
                        ).click()
                        await page.screenshot(path=data_p / f"{time.time_ns()}.png")
                        await asyncio.sleep(3)
                        for _ in range(30):
                            # 等待刷新
                            try:
                                iframe_element = ae(
                                    await page.wait_for_selector(
                                        "iframe", timeout=load_timeout_short
                                    )
                                )

                                iframe = ae(await iframe_element.content_frame())

                                target_img_element = ae(
                                    await iframe.wait_for_selector(
                                        "div.tc-bg-img.unselectable",
                                        timeout=wait_timeout,
                                    )
                                )
                                target_img_url = ae(
                                    re.search(
                                        r'url\("(.+?)"\)',
                                        ae(
                                            await target_img_element.get_attribute(
                                                "style"
                                            )
                                        ),
                                    )
                                ).group(1)
                                if target_img_style == ae(
                                    await target_img_element.get_attribute("style")
                                ):
                                    await asyncio.sleep(0.5)
                                    continue
                                else:
                                    break
                            except Exception as e:
                                await asyncio.sleep(0.5)
                                continue
                        else:
                            raise Exception("Failed to refresh")
                    except Exception as e:
                        logger.debug(e)
                        await page.reload()
                        await page.evaluate(load_js)

            # # 打印调试信息，检查定位的坐标
            # print("Detected coordinates: ", locations)

            # 模拟点击目标图片中的三个位置（基于坐标）
            for i, t in enumerate(rst):
                x, y = t
                try:
                    # 模拟鼠标点击
                    await iframe.click(
                        "div.tc-bg-img.unselectable",
                        position={"x": x // 2, "y": y // 2},
                        delay=150,
                        button="left",
                        force=True,
                    )
                    await page.screenshot(path=data_p / f"{time.time_ns()}_click.png")
                    # time.sleep(1)
                    if i < 2:
                        await asyncio.sleep(
                            0.2
                            + math.sqrt(
                                (rst[i][0] - rst[i + 1][0]) ** 2
                                + (rst[i][1] - rst[i + 1][1]) ** 2
                            )
                            / 700
                        )
                    else:
                        await asyncio.sleep(1)
                except Exception:
                    raise Exception("Failed to click on icon")

            # # 点击验证按钮
            verify_btn = ae(
                await iframe.wait_for_selector(
                    "div.tc-action.verify-btn.show", timeout=wait_timeout
                )
            )
            await verify_btn.click(timeout=wait_timeout)

            ticket = None
            for _ in range(30):
                await page.screenshot(path=data_p / f"{time.time_ns()}_error.png")
                ticket = await page.evaluate("ticket")
                if ticket:
                    logger.info(f"Got ticket! length: {len(ticket)}")
                    return ticket
                await asyncio.sleep(0.5)
            else:
                await page.screenshot(path=data_p / f"{time.time_ns()}_error.png")
                proxy["ban_count"] -= 1
                if proxy["ban_count"] <= 0:
                    proxy["ban_time"] = time.time() + 86400
                    proxy["ban_count"] = proxy["base_ban_count"]
                raise Exception("Failed to get ticket")

        finally:
            # 关闭浏览器
            await browser.close()


# start = time.time()
# for _ in range(10):
#     flag = True
#     while flag:
#         flag = False
#         try:
#             print(asyncio.run(get_ticket()))
#         except Exception as e:
#             print(e)
#             flag = True
#             time.sleep(3)
# print(time.time() - start)
