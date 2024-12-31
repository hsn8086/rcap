import asyncio
import heapq
from itertools import combinations
import math
from playwright.async_api import async_playwright
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


async def get_ticket()->str:
    async with async_playwright() as p:
        load_timeout = 20000
        load_timeout_short = 10000
        wait_timeout = 4000
        browser = await p.chromium.launch(
            headless=True,
            timeout=load_timeout,
        )  # 设置headless=False来显示浏览器
        page = await browser.new_page()
        
        load_js = """
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
                # 等待iframe加载
                iframe_element = ae(
                    await page.wait_for_selector("iframe", timeout=load_timeout_short)
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
                target_img_style = ae(await target_img_element.get_attribute("style"))
                target_img_url = ae(
                    re.search(r'url\("(.+?)"\)', target_img_style)
                ).group(1)

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
                    print(e)
                    try:
                        await ae(
                            await iframe.wait_for_selector(
                                "div.tc-action.tc-icon.tc-action--refresh.show-reload img",
                                timeout=wait_timeout,
                            )
                        ).click()
                        await asyncio.sleep(1)
                    except Exception as e:
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
                await iframe.wait_for_selector("div.tc-action.verify-btn.show", timeout=wait_timeout)
            )
            await verify_btn.click(timeout=wait_timeout)

            await asyncio.sleep(3)

            ticket = await page.evaluate("ticket")
            if ticket:
                return ticket
            else:
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
