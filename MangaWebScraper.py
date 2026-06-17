from playwright.sync_api import sync_playwright

from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas

# Chỉnh sửa để lấy tên link
def getName(link):
    return "Konosuba/Chap_" + link.split("-")[-1] + '.pdf'

def images_to_pdf(images_bytes, pdf_path, page_width=1000):
    c = canvas.Canvas(pdf_path)

    for image_bytes in images_bytes:
        img = Image.open(BytesIO(image_bytes))

        w, h = img.size
        page_height = h * page_width / w
        c.setPageSize((page_width, page_height))

        c.drawInlineImage(
            img, 0, 0,
            width=page_width,
            height=page_height
        )

        c.showPage()

    c.save()

def nextPage():
    page.keyboard.press("ArrowRight")

knownLinks = []
image = {}
def handle_response(response):
    knownLinks.append(response.url)
    try:
        body = response.body()
    except:
        return
    image[response.url] = body

with sync_playwright() as p:
    context = p.chromium.launch(headless=False)
    page = context.new_page()
    #Handle Response
    page.on("response", handle_response)
    page.goto("")

    oldlink = ''
    retry = 0
    while True:
        page.wait_for_timeout(1000)
        page.wait_for_load_state("domcontentloaded")
        
        # Retry
        link = page.url
        if link == oldlink:
            if retry > 10:
                print("Timeout")
                exit(1)
            retry += 1
            print("= Retrying:", link)
            nextPage()
            continue
        else:
            oldlink = link
            retry = 0
        
        # Process
        print("==== Processing:", link)
        page.wait_for_timeout(500)
        for _ in range(20):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(50)
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(50)
            
        # Find links
        all_links = page.locator(".relative.mb-3 img").evaluate_all(
            "elements => elements.map(el => el.src)"
        )
        requiredLinks = set(all_links)
        print("Get", len(all_links), "links")
        
        # Check Downloaded Links
        n = 0
        for _ in range(100):
            for link in knownLinks[:]:
                if link in requiredLinks:
                    #print("Downloaded",n,":", link)
                    requiredLinks.remove(link)
                    n += 1
            if n == len(all_links):
                break
            page.wait_for_timeout(1000)
        else:
            print("Timeout")
            print("Missing:", requiredLinks)
            exit(1)
            
        # Convert to PDF
        print("Completed")
        images = []
        for link in all_links:
            image_bytes = image[link]
            images.append(image_bytes)
        
        images_to_pdf(images, getName(page.url))
        print("Redirecting")
        knownLinks = []
        image = {}
        nextPage()