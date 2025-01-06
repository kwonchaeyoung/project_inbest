'''
((Run 하는 날짜 기준) -1) 날짜의 기사 전체 크롤링하는 코드
실행 시 날짜 입력(입력형식: YYYY-MM-DD)하면 해당일의 기사 모두 크롤링
'''
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timedelta

# User-Agent 설정
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# SQLite 데이터베이스 연결 (뉴스 상세용)
conn_details = sqlite3.connect("../db/news_details_naver.db")
cursor_details = conn_details.cursor()

# 뉴스 상세 테이블 생성
cursor_details.execute("""
CREATE TABLE IF NOT EXISTS news_details_naver (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,  
    author TEXT,
    author_email TEXT,
    input_date TEXT,
    update_date TEXT,
    summary TEXT,
    content TEXT,
    press TEXT
)
""")
conn_details.commit()

# 날짜와 페이지를 기반으로 뉴스 크롤링
def crawl_news_by_date_and_page(target_date, max_pages=20):
    for page in range(1, max_pages + 1):
        try:
            # URL 생성
            url = f"https://finance.naver.com/news/mainnews.naver?date={target_date}&page={page}"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 기사 목록 크롤링
            articles = soup.select("div.mainNewsList > ul > li")
            if not articles:
                print(f"No articles found on page {page}. Stopping.")
                break

            for article in articles:
                try:
                    # 제목과 링크
                    title_tag = article.select_one("dl > dd > a")
                    title = title_tag.get_text(strip=True)
                    link = f"https://finance.naver.com{title_tag['href']}"

                    # 뉴스 상세 페이지 요청
                    article_response = requests.get(link, headers=HEADERS)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.text, "html.parser")

                    # 상세 정보 크롤링
                    author_elem = article_soup.select_one("em.media_end_head_journalist_name")
                    author = author_elem.get_text(strip=True) if author_elem else "작성자 없음"

                    email_elem = article_soup.select_one("#contents span.byline_s")
                    author_email = email_elem.get_text(strip=True) if email_elem else "이메일 없음"

                    input_date_elem = article_soup.select_one(
                        "span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME"
                    )
                    input_date = input_date_elem.get_text(strip=True) if input_date_elem else "입력 날짜 없음"

                    update_date_elem = article_soup.select_one(
                        "span.media_end_head_info_datestamp_time._ARTICLE_MODIFY_DATE_TIME"
                    )
                    update_date = update_date_elem.get_text(strip=True) if update_date_elem else "수정 날짜 없음"

                    summary_elem = article_soup.select_one("#dic_area > strong")
                    summary = summary_elem.get_text(strip=True) if summary_elem else "요약 없음"

                    content_elem = article_soup.select_one("#dic_area")
                    content = content_elem.get_text(strip=True) if content_elem else "본문 없음"

                    press_tag = article.select_one("dl > dd.articleSummary > span.press")
                    press = press_tag.get_text(strip=True) if press_tag else "출처 없음"

                    # 중복 확인
                    cursor_details.execute("""
                    SELECT COUNT(*) FROM news_details_naver
                    WHERE title = ? AND author_email = ? AND press = ?
                    """, (title, author_email, press))
                    if cursor_details.fetchone()[0] > 0:
                        print(f"Skipping duplicate news: {title}")
                        continue

                    # 데이터 저장
                    cursor_details.execute("""
                    INSERT INTO news_details_naver (title, author, author_email, input_date, update_date, summary, content, press)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, author, author_email, input_date, update_date, summary, content, press))
                    conn_details.commit()
                    print(f"Saved news: {title}")

                except Exception as e:
                    print(f"Error occurred while processing news detail for article: {e}")

        except Exception as e:
            print(f"Error occurred for page {page}: {e}")

# 날짜 입력 받기
user_date = input("크롤링할 날짜를 입력하세요 (YYYY-MM-DD 형식): ").strip()

# 날짜 유효성 확인
try:
    datetime.strptime(user_date, '%Y-%m-%d')
    crawl_news_by_date_and_page(user_date)
except ValueError:
    print("잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력해주세요.")

print("크롤링이 종료되었습니다.")

# SQLite 연결 종료
conn_details.close()
