import requests
from bs4 import BeautifulSoup
import sqlite3

# 뉴스 목록 URL
BASE_URL = "https://www.mk.co.kr/news/stock/latest/"

# SQLite 데이터베이스 연결 (뉴스 상세용)
conn_details = sqlite3.connect("../db/news_details_mk.db")
cursor_details = conn_details.cursor()

# 뉴스 상세 테이블 생성
cursor_details.execute("""
CREATE TABLE IF NOT EXISTS news_details_mk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE,  -- 중복 방지: UNIQUE 제약 조건 추가
    author TEXT,
    author_email TEXT,
    input_date TEXT,
    update_date TEXT,
    summary TEXT,
    content TEXT
)
""")
conn_details.commit()

# 뉴스 목록 크롤링
response = requests.get(BASE_URL)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

articles = soup.select("#list_area > li") #[:] 상위 n개의 뉴스

for article in articles:
    try:
        # 뉴스 목록 정보 크롤링
        title = article.select_one("a > div.txt_area > h3").get_text(strip=True)
        link = article.select_one("a")["href"]
        full_link = f"https://www.mk.co.kr{link}" if link.startswith("/") else link

        # 상세 페이지 요청
        article_response = requests.get(full_link)
        article_response.raise_for_status()
        article_soup = BeautifulSoup(article_response.text, "html.parser")

        # 뉴스 상세 정보 크롤링
        author_elem = article_soup.select_one("#container a > dt")
        author = author_elem.get_text(strip=True) if author_elem else "작성자 없음"

        email_elem = article_soup.select_one("#container a > dd")
        email = email_elem.get_text(strip=True) if email_elem else "이메일 없음"

        input_date_elem = article_soup.select_one("#container dl:nth-child(1) > dd")
        input_date = input_date_elem.get_text(strip=True) if input_date_elem else "입력 날짜 없음"

        update_date_elem = article_soup.select_one("#container dl:nth-child(2) > dd")
        update_date = update_date_elem.get_text(strip=True) if update_date_elem else "수정 날짜 없음"

        summary_elem = article_soup.select_one("#container div.mid_title > div")
        summary = summary_elem.get_text(strip=True) if summary_elem else "요약 없음"

        content_elem = article_soup.select_one("#container div.news_cnt_detail_wrap")
        content = content_elem.get_text(strip=True) if content_elem else "본문 없음"

        # 중복 확인 (title, author, email을 기준으로 확인)
        cursor_details.execute("""
                                SELECT COUNT(*) FROM news_details_mk 
                                WHERE title = ? AND author = ? AND author_email = ?
                                """, (title, author, email))

        if cursor_details.fetchone()[0] > 0:
            print(f"Skipping duplicate news: {title} by {author} ({email})")
            continue

        # 데이터 저장
        cursor_details.execute("""
        INSERT INTO news_details_mk (title, author, author_email, input_date, update_date, summary, content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, email, input_date, update_date, summary, content))
        conn_details.commit()
        print(f"Saved news: {title}")

    except Exception as e:
        print(f"Error occurred while processing news detail for URL: {full_link} - {e}")


# 데이터 조회 (옵션)
cursor_details.execute("SELECT * FROM news_details_mk")
rows = cursor_details.fetchall()

print("크롤링이 종료되었습니다.")
# print("뉴스 상세 데이터:")
# for row in rows:
#     print(row)

# SQLite 연결 종료
conn_details.close()
