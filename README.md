# instacrawler

instacrawler는 크게 `Crawler`와 `Preprocessing`으로 나눠진다.

## Crawler.py
`Crawler`는 미리 정의된 검색어를 instagram에서 검색하여 나오는 게시물들을 Crawling하여 하나의 태그에 대한 job이 완료된 시점의 timestamp를 filename으로 사용하여 pickle을 drop한다. 각 post에 대하여 `Crawler`가 pickle에 저장하는 데이터는 다음과 같다.
- Posted date
- Raw post content(with HTML tag forms)
- User name
- Likes
- Image URL

## Preprocessing.py
`Preprocessing`은 `Crawler`가 drop한 pickle을 열어서 Raw post content로부터 다음과 같은 데이터를 추출하고 데이터를 form에 맞게 Database에 commit한다.
- Hashtags
- Processed main content(without HTML tag form)
