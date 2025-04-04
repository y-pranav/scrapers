import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import re
import re

async def scrape_page(context, url, page_num):
    page = await context.new_page()
    results = []

    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('.flex.h-\\[50px\\]', timeout=10000)
        await page.wait_for_timeout(1500)

        rows = await page.query_selector_all('.flex.h-\\[50px\\].w-full')

        for row in rows:
            try:
                user_link = await row.query_selector('a[href^="/u/"]')
                username = None
                if user_link:
                    href = await user_link.get_attribute("href")
                    match = re.search(r'/u/([^/]+)/', href)
                    if match:
                        username = match.group(1)

                cells = await row.query_selector_all('div[class*="flex-[1_0_0]"]')

                score = await cells[1].inner_text() if len(cells) > 1 else None
                finish_time = await cells[2].inner_text() if len(cells) > 2 else None

                async def get_question_time(cell):
                    try:
                        inner_divs = await cell.query_selector_all('div > div')
                        if len(inner_divs) >= 1:
                            return (await inner_divs[0].inner_text()).strip()
                    except:
                        return None
                    return None

                q1 = await get_question_time(cells[3]) if len(cells) > 3 else None
                q2 = await get_question_time(cells[4]) if len(cells) > 4 else None
                q3 = await get_question_time(cells[5]) if len(cells) > 5 else None
                q4 = await get_question_time(cells[6]) if len(cells) > 6 else None

                if username:
                    results.append({
                        "Name": username,
                        "Score": score,
                        "Finish Time": finish_time,
                        "Q1 (3)": q1,
                        "Q2 (4)": q2,
                        "Q3 (6)": q3,
                        "Q4 (7)": q4
                    })

            except Exception as e:
                print(f"Error processing row: {e}")

        print(f"Page {page_num}: {len(results)} users processed")

    except Exception as e:
        print(f"Error on page {page_num}: {e}")
    finally:
        await page.close()

    return results


async def scrape_leetcode_rankings_async(base_url, total_pages, max_pages=None, concurrency=10):
    all_results = []
    pages_to_scrape = min(total_pages, max_pages) if max_pages else total_pages

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        async def block_junk(route, request):
            if request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_junk)

        warmup = await context.new_page()
        await warmup.goto("https://leetcode.com/", wait_until="networkidle")
        await warmup.close()

        sem = asyncio.Semaphore(concurrency)
        tasks = []

        async def bound_scrape(page_num):
            url = base_url.format(page_no=page_num)
            async with sem:
                return await scrape_page(context, url, page_num)

        for page_num in range(1, pages_to_scrape + 1):
            tasks.append(bound_scrape(page_num))

        results = await asyncio.gather(*tasks)

        for page_results in results:
            all_results.extend(page_results)

        await browser.close()

    return all_results

if __name__ == "__main__":
    contest = "weekly-contest-443"
    base_url = f"https://leetcode.com/contest/{contest}/ranking/{{page_no}}/?region=global_v2"
    total_pages = 800
    max_pages = 20
    concurrency = 10

    results = asyncio.run(
        scrape_leetcode_rankings_async(base_url, total_pages, max_pages, concurrency)
    )

    df = pd.DataFrame(results)
    df.to_csv("leetcode_contest_results.csv", index=False)
    print(f"\nScraped {len(results)} users with full data. Saved to 'leetcode_contest_results.csv'")
