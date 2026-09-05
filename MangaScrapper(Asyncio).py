# ======= CONFIG =======
START_LINK = "https://truyenqqko.com/truyen-tranh/jujutsu-kaisen-chu-thuat-hoi-chien-5058"
FOLDER = "JJK"
AUTHOR = "Jujutsu Kaisen"

WORKER_COUNT = 4
SAVE_SEM_COUNT = 4

import asyncio
import os
from urllib.parse import urlsplit, urlunsplit
import json
from PIL import Image
import traceback

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from rich.console import Group
from rich.live import Live
from rich.text import Text
from rich.table import Table

class ProgressDisplay:
    MAX_CHAPTERS = 20
    MAX_ERRORS = 6

    MAIN_BARS = 20
    CHAPTER_BARS = 6

    STATUS_COLORS = {
        "Opening": "yellow",
        "Crawling": "orange1",
        "Saving": "bright_blue",
        "Completed": "bright_green",
        "Error": "red",
    }

    def __init__(self):
        self.chapters = {}
        self.errors = []

        self.progress_num1 = 0
        self.progress_num2 = 0

        self.live = Live(
            self.render(),
            refresh_per_second=10,
            transient=False
        )

    # =========================
    # Progress tổng
    # =========================

    def progress(self, num1, num2):
        self.progress_num1 = num1
        self.progress_num2 = num2
        self.refresh()

    # =========================
    # Chapter state
    # =========================

    def state(self, chapterName, status, percentage=0):

        if status not in (
            "Opening",
            "Crawling",
            "Saving",
            "Completed",
            "Error"
        ):
            raise ValueError(
                f"Status không hợp lệ: {status}"
            )

        # Tạo Chapter nếu chưa tồn tại
        if chapterName not in self.chapters:
            self.chapters[chapterName] = {
                "status": status,
                "percentage": percentage,
                "bars": 0
            }

        chapter = self.chapters[chapterName]

        chapter["percentage"] = percentage

        # Xác định số vạch
        if status == "Opening":
            chapter["bars"] = 1

        elif status == "Crawling":
            if percentage < 33:
                chapter["bars"] = 2
            elif percentage <= 66:
                chapter["bars"] = 3
            else:
                chapter["bars"] = 4

        elif status == "Saving":
            chapter["bars"] = 5

        elif status == "Completed":
            chapter["bars"] = 6

        elif status == "Error":
            # Giữ nguyên số vạch hiện tại
            pass

        chapter["status"] = status

        # -------------------------
        # Error list
        # -------------------------

        if status == "Error":
            if chapterName not in self.errors:
                self.errors.append(chapterName)

            self.errors = self.errors[-self.MAX_ERRORS:]

        # Nếu Chapter đã hết lỗi thì xóa khỏi Error
        else:
            if chapterName in self.errors:
                self.errors.remove(chapterName)

        self.refresh()

    # =========================
    # Progress bar
    # =========================

    @staticmethod
    def bar(current, maximum):
        current = max(0, min(current, maximum))

        filled = "━━" * current
        empty = "  " * (maximum - current)

        return f"[{filled}{empty}]"

    # =========================
    # Sort Chapter
    # =========================

    @staticmethod
    def chapter_sort_key(name):
        try:
            number = int(
                "".join(
                    c for c in name
                    if c.isdigit()
                )
            )
            return (0, number)

        except ValueError:
            return (1, name)

    # =========================
    # Render
    # =========================

    def render(self):

        # Progress tổng
        if self.progress_num2 > 0:
            ratio = (
                self.progress_num1 /
                self.progress_num2
            )
        else:
            ratio = 0

        bars = round(
            ratio * self.MAIN_BARS
        )

        progress_bar = self.bar(
            bars,
            self.MAIN_BARS
        )

        progress_line = Text(
            f"Progress: "
            f"{self.progress_num1}/"
            f"{self.progress_num2} "
            f"{progress_bar}"
            f" {round(ratio * 100)}%"
        )

        # =========================
        # Chapter table
        # =========================

        chapter_table = Table(
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 0)
        )

        sorted_chapters = sorted(
            self.chapters.items(),
            key=lambda x:
                self.chapter_sort_key(x[0])
        )

        # Chỉ lấy 20 Chapter cuối
        sorted_chapters = sorted_chapters[
            -self.MAX_CHAPTERS:
        ]

        for chapterName, data in sorted_chapters:

            status = data["status"]
            percentage = data["percentage"]
            bars = data["bars"]

            color = self.STATUS_COLORS[status]

            bar = self.bar(
                bars,
                self.CHAPTER_BARS
            )

            text = Text()

            text.append(
                f"{chapterName} ",
                style=color
            )

            text.append(
                f"{bar} ",
                style=color
            )

            text.append(
                status,
                style=color
            )

            if status == "Crawling":
                text.append(
                    f" {percentage}%",
                    style=color
                )

            chapter_table.add_row(text)

        # =========================
        # Error table
        # =========================

        error_table = Table(
            title="Error",
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 0)
        )

        for chapterName in self.errors[
            -self.MAX_ERRORS:
        ]:
            error_table.add_row(
                Text(
                    chapterName,
                    style="red"
                )
            )

        # =========================
        # Group
        # =========================

        return Group(
            progress_line,
            chapter_table,
            error_table
        )

    # =========================
    # Refresh
    # =========================

    def refresh(self):
        self.live.update(
            self.render()
        )

    # =========================
    # Start / Stop
    # =========================

    def start(self):
        self.live.start()

    def stop(self):
        self.live.stop()

class FileManager:
    def __init__(self, folder):
        #state dạng name:state. State = True nghĩa là file đã được lưu
        # Kiểm tra file
        if os.path.exists("Completed.json"):
            with open("Completed.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}
        if folder not in self.data:
            self.data[folder] = {}
        self.state:dict = self.data[folder]
        self.titleList:dict = {}
    
    def _updateJson(self):
        with open("Completed.json", "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def _handle_name(self, name:str):
        # Tên có dạng Chương Số hoặc Chương Số.Số
        prefix = name.split()[0]
        num = name.split()[1].split('.')
        if len(num) == 1:
            return f"{num[0].zfill(4)}0"
        elif len(num) == 2 and num[1].isdigit():
            return f"{num[0].zfill(4)}{num[1]}"
        else:
            raise ValueError
    
    def _load_image(self, data: bytes) -> Image.Image:
        """Đọc bytes thành RGB PIL Image."""
        from io import BytesIO
        from PIL import Image, ImageFile

        # Thử bình thường
        try:
            with BytesIO(data) as bio:
                img = Image.open(bio)
                img.load()

                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, "white")
                    background.paste(img, mask=img.getchannel("A"))
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                return img.copy()

        except Exception:
            pass

        # Thử ảnh bị truncated
        old_value = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True

        try:
            with BytesIO(data) as bio:
                img = Image.open(bio)
                img.load()

                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, "white")
                    background.paste(img, mask=img.getchannel("A"))
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                return img.copy()

        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = old_value

    def _create_error_image(
        self,
        index: int,
        data: bytes
    ) -> Image.Image:
        """Tạo ảnh thay thế khi ảnh gốc không thể đọc."""
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont

        width, height = 800, 1200

        # Cố lấy kích thước ảnh gốc
        try:
            with BytesIO(data) as bio:
                temp = Image.open(bio)
                width, height = temp.size
        except Exception:
            pass

        width = max(400, min(width, 2000))
        height = max(400, min(height, 3000))

        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(
                "arial.ttf",
                max(24, width // 25)
            )
            small_font = ImageFont.truetype(
                "arial.ttf",
                max(16, width // 40)
            )
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        title = f"ẢNH #{index} BỊ LỖI"
        message = "Không thể đọc dữ liệu ảnh"

        title_box = draw.textbbox((0, 0), title, font=font)
        message_box = draw.textbbox((0, 0), message, font=small_font)

        title_w = title_box[2] - title_box[0]
        title_h = title_box[3] - title_box[1]

        message_w = message_box[2] - message_box[0]
        message_h = message_box[3] - message_box[1]

        draw.text(
            (
                (width - title_w) / 2,
                (height - title_h - message_h - 30) / 2
            ),
            title,
            fill="black",
            font=font
        )

        draw.text(
            (
                (width - message_w) / 2,
                (height + title_h + 30 - message_h) / 2
            ),
            message,
            fill="black",
            font=small_font
        )

        draw.rectangle(
            (0, 0, width - 1, height - 1),
            outline="black",
            width=5
        )

        return img

    def _images_to_pdf(self, images: list[bytes], output: str, title: str = ""):
        if not images:
            return

        pil_images = []

        for index, data in enumerate(images):
            try:
                img = self._load_image(data)
                pil_images.append(img)

            except Exception as e:
                # Không đọc được -> thay bằng ảnh báo lỗi

                with open("error.log", "a", encoding="utf-8") as f:
                    print(
                        f"[Save] Ảnh #{index} lỗi - {len(data):,} bytes",
                        file=f
                    )
                    traceback.print_exc(file=f)
                img = self._create_error_image(index, data)
                pil_images.append(img)

        if not pil_images:
            raise ValueError("Không có ảnh để tạo PDF")

        try:
            pil_images[0].save(
                output,
                "PDF",
                resolution=100.0,
                save_all=True,
                append_images=pil_images[1:],
                author=AUTHOR,
                title=title
            )
        finally:
            for img in pil_images:
                img.close()
    
    async def save(self, name, images: list[bytes]):
        output = os.path.join(FOLDER, f"{self.titleList[name][1]} - {self.titleList[name][0]}.pdf")
        await asyncio.to_thread(self._images_to_pdf, images, output, self.titleList[name][0])
        self.state[name] = True
        self._updateJson()
        
    def remainLinks(self, links: list):
        ans = []
        lenLinks = len(str(len(links)))
        for pos, i in enumerate(links):
            name = self._handle_name(i[0])
            if self.state.get(name, False) == False:
                ans.append([name, i[1]])
                self.state[name] = False
                self.titleList[name] = (i[0],str(pos).zfill(lenLinks))
        self.data[FOLDER] = self.state = dict(sorted(self.state.items()))
        self._updateJson()
        return ans
    
    def getLenChapter(self):
        return len(self.state)
    def getCompletedChapter(self):
        return sum(1 for v in self.state.values() if v is True)

async def handle_response(response, image: dict):
    url = response.url
    # Chỉ xử lý jpg/png/jpeg
    path = urlsplit(url).path.lower()
    if not path.endswith((".jpg", ".jpeg", ".png")):
        return
    # Làm sạch URL: bỏ query (?r=...), fragment (#...)
    parts = urlsplit(url)
    clean_url = urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        "",
        ""
    ))
    try:
        data = await response.body()
        image[clean_url] = data
    except Exception:
        pass
    
async def save_chapter(name, images, file: FileManager, screen: ProgressDisplay, save_sem: asyncio.Semaphore):
    async with save_sem:  # giới hạn số PDF convert chạy song song, tránh nghẽn CPU/RAM
        try:
            screen.state(name, "Saving")
            await file.save(name, images)
            screen.state(name, "Completed")
        except Exception:
            with open("error.log", "a", encoding="utf-8") as f:
                print(f"[Save] Lỗi khi lưu chương {name}", file=f)
                traceback.print_exc(file=f)
            screen.state(name, "Error")
        finally:
            screen.progress(file.getCompletedChapter(), file.getLenChapter())
    
async def wait_for_all_images(chapter, srcs, images: dict, screen:ProgressDisplay, deadline = 60):
    # Lướt qua từng src, kiểm tra trong images đã có ảnh chưa
    # Lọc bỏ các ảnh không đúng đuôi
    counter = 0
    while True:
        need = set(srcs)
        have = set(images.keys())
        if need and need.issubset(have):
            return
        if counter > deadline:
            raise PlaywrightTimeoutError(
                f"Cho anh qua lau cho '{srcs}' "
                f"({len(have & need)}/{len(need)} anh)"
            )
        counter += 1
        # Tính toán có bao nhiêu ảnh đã có
        screen.state(chapter, "Crawling", int((len(have & need) / len(need)) * 100))
        await asyncio.sleep(0.5)

async def worker(worker_id, queue, browser, file:FileManager, screen:ProgressDisplay, 
                 save_tasks: list[asyncio.Task], save_sem: asyncio.Semaphore):
    while True:
        try:
            name, url = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        screen.state(name, "Opening")
        page = await browser.new_page()
        try:
            # Gắn handler TRƯỚC khi goto
            images = {}
            page.on("response", lambda response: asyncio.create_task(handle_response(response, images)))

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000
            )
            screen.state(name, "Crawling")
            srcs = await page.locator(".page-chapter img").evaluate_all(
                """imgs => imgs.map(img => {
                    const url = new URL(img.src);
                    url.search = "";
                    url.hash = "";
                    return url.href;
                })"""
            )
            srcs = [i for i in srcs if i.endswith((".jpg", ".jpeg", ".png"))] # Loại bỏ ảnh không phù hợp
            await wait_for_all_images(name ,srcs, images, screen)
            task = asyncio.create_task(
                save_chapter(name, 
                             [images[src] for src in srcs], 
                             file, screen, save_sem)
            )
            save_tasks.append(task)
            screen.progress(file.getCompletedChapter(), file.getLenChapter())

        except Exception:
            with open("error.log", "a", encoding="utf-8") as f:
                print(f"[Worker {worker_id}] Lỗi: {url} Chapter:{name}", file=f)
                traceback.print_exc(file=f)
                print("=====================================\n",file=f)
            screen.state(name, "Error")
            screen.progress(file.getCompletedChapter(), file.getLenChapter())

        finally:
            await page.close()
            queue.task_done()

async def main():
    os.makedirs(FOLDER, exist_ok=True)
    queue = asyncio.Queue()
    
    screen = ProgressDisplay()
    screen.start()
    save_tasks =[]
    save_sems = asyncio.Semaphore(SAVE_SEM_COUNT)
    
    file = FileManager(FOLDER)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        # Lấy URLs list
        page = await browser.new_page()
        await page.goto(START_LINK, wait_until="domcontentloaded")
        chapters = await page.locator(".works-chapter-item a").evaluate_all("""
                els => els.map(a => [a.textContent.trim(), a.href])
            """)
        chapters = file.remainLinks(chapters[::-1])
        screen.progress(file.getCompletedChapter(), file.getLenChapter())
        await page.close()
        context = await browser.new_context()
        for chapter in chapters:
            await queue.put(chapter)
        # Chỉ tạo 4 worker
        workers = [
            asyncio.create_task(worker(i + 1, queue, context, file, screen, save_tasks, save_sems))
            for i in range(WORKER_COUNT)
        ]

        await queue.join()
        await asyncio.gather(*workers)
        await asyncio.gather(*save_tasks)
        await browser.close()
        input()

asyncio.run(main())