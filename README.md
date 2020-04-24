# instacrawler

## GET READY
```console
$ pip install requirements.txt
$ wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add - 
$ sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
$ sudo apt-get update
$ sudo apt-get install google-chrome-stable
$ google-chrome --version
```
Chrome의 version을 확인하여 driver 다운로드
[Chromedriver](https://chromedriver.chromium.org/downloads)
해당 버전에 맞는 driver 설치를 누르면, OS 별로 파일 다운로드 창이 나오는데 여기서 해당 OS를 '마우스 우클릭 - 링크 주소 복사'하여,

```console
$ wget https://chromedriver.storage.googleapis.com/81.0.4044.69/chromedriver_linux64.zip
$ sudo apt-get install unzip
$ unzip chromedriver_linux64.zip
$ rm chromedriver_linux64.zip
$ ls
```
chromedriver가 생성된 것을 볼 수 있다.

## Requirements
- Python 3.x
- Selenium
- tqdm
- [Chromedriver](https://chromedriver.chromium.org/downloads)

## Structure
instacrawler는 크게 `Crawler`와 `Preprocessing`으로 나눠진다.

### Crawler.py
`Crawler`는 미리 정의된 검색어를 instagram에서 검색하여 나오는 게시물들을 Crawling하여 하나의 태그에 대한 job이 완료된 시점의 timestamp를 filename으로 사용하여 pickle을 drop한다. 각 post에 대하여 `Crawler`가 pickle에 저장하는 데이터는 다음과 같다.
- Posted date
- Raw post content(with HTML tag forms)
- User name
- ~~Likes~~
- Image URL

### Preprocessing.py
`Preprocessing`은 `Crawler`가 drop한 pickle을 열어서 Raw post content로부터 다음과 같은 데이터를 추출하고 데이터를 form에 맞게 Database에 commit한다.
- Hashtags
- Processed main content(without HTML tag form)
