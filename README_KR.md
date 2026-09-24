# Citation Network Builder v1.2.0

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white) ![Version](https://img.shields.io/badge/version-1.2.0-8E7CC3?style=flat-square) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)

**Citation Network Builder**는 **Zotero**에 저장된 논문들의 인용 관계를 무료 학술 데이터베이스인 **OpenAlex**로 자동 분석하여, **Obsidian** 상호 연결 노트 및 앱 내 **인터랙티브 2D 인용망 그래프**로 시각화해주는 연구용 도구입니다.

---

## 3단계 빠른 시작 가이드 (Quick Start)

### 1단계: 파이썬 및 패키지 설치
1. [python.org](https://python.org)에서 **Python 3.9 이상**을 다운로드하여 설치합니다.
   > [!IMPORTANT]
   > 윈도우 설치 시 설치 창 맨 아래의 **"Add python.exe to PATH"** 체크박스를 반드시 체크하세요.
2. 터미널(또는 명령 프롬프트)을 열고 프로그램 폴더로 이동한 뒤 아래 명령어를 입력합니다:
   ```bash
   pip install -r requirements.txt
   ```

### 2단계: 환경 설정 (.env 입력 - 딱 3가지)
프로젝트 폴더의 `.env.example` 파일을 복사하여 이름을 `.env`로 바꾼 뒤, 아래 3개 항목만 본인 정보로 채워 넣습니다:

```ini
ZOTERO_USER_ID=1234567                   # https://www.zotero.org/settings/keys 에 적힌 숫자 ID
ZOTERO_API_KEY=본인의_API_키              # 동일 페이지에서 [Create new private key]로 생성
OBSIDIAN_VAULT_PATH=C:\Users\이름\Vault  # 내 Obsidian 볼트 폴더의 절대 경로
```

### 3단계: 프로그램 실행
- **윈도우**: **`run.bat`** 파일을 더블클릭합니다.
- **또는 터미널**:
  ```bash
  python main.py
  ```

---

## 화면 사용법 (4개 패널 한눈에 보기)

화면 상단의 버튼(`[Collections]`, `[Console & Run]`, `[Graph View]`, `[Citation Index]`)으로 원하는 패널을 접거나 펼칠 수 있으며, 패널 사이의 분할선을 마우스로 드래그하여 크기를 자유롭게 조절할 수 있습니다.

```
[Collections]          [Console & Run]       [Graph View]            [Citation Index]
+--------------------+---------------------+-----------------------+---------------------+
| 1. 폴더 선택       | 2. 빌드 시작        | 3. 인터랙티브 그래프  | 4. 인덱스 & 조테로  |
|                    |                     |                       |                     |
| - My Library       | [Build Network]     | - 노드 드래그 (스프링)| - 논문 상세 서지    |
|   ├─ AI 논문       | - 실시간 로그 콘솔  | - 마우스 휠 줌/패닝   | - Cites [1], [2]... |
|   └─ 생명과학      | - 3단계 진행률      | - Settings 슬라이더   | - [Open in Zotero]  |
+--------------------+---------------------+-----------------------+---------------------+
```

1. **패널 1: Collections (좌측)**
   - 인용 관계를 분석할 Zotero 폴더를 클릭하여 선택합니다. (라이브러리 전체는 최상단 **`My Library`** 선택)
2. **패널 2: Console & Run (중앙 좌측)**
   - **`Build Citation Network`** 버튼을 누릅니다. 실시간 3단계 진행률과 분석 로그가 표시됩니다.
3. **패널 3: Graph View (중앙 우측)**
   - 안티앨리어싱 고해상도 벡터 그래픽으로 완성된 논문망을 자유롭게 탐색합니다.
   - **조작**: 마우스 휠로 확대/축소, 바탕 드래그로 화면 이동.
   - **물리 시뮬레이션**: 특정 노드를 드래그하면 연결된 논문들이 탄성 스프링에 따라 자연스럽게 딸려옵니다.
   - **설정**: 우측 상단 **`Settings & Palette`**를 눌러 노드 크기, 연결 거리, 반발력 슬라이더를 조절하거나, 2D 스펙트럼 색상판에서 원하는 색상을 클릭하여 바꿀 수 있습니다.
4. **패널 4: Citation Index (우측)**
   - 상단 헤더의 **`Citation Index`** 버튼을 누르면 열립니다.
   - 선택한 논문이 참고한 문헌(**Cites**)과 이 논문을 인용한 문헌(**Cited By**)을 `[1]`, `[2]`... 번호 매김 카드로 보여줍니다.
   - 카드를 클릭하면 그래프 뷰에서 해당 논문으로 즉시 이동합니다.
   - **`Open in Zotero`** 버튼을 누르면 조테로 데스크톱 앱이 열리면서 **해당 논문이 즉시 파란색으로 선택/하이라이트**됩니다.

---

## Obsidian(옵시디언)에서 결과 확인하기

빌드가 완료되면 옵시디언 볼트 내에 선택한 컬렉션 이름의 폴더로 노트들이 자동 생성됩니다.

1. **Obsidian**을 실행합니다.
2. `Ctrl + G` (Mac은 `Cmd + G`)를 눌러 **Graph View**를 엽니다.
3. 우측 상단 그래프 필터에 `path:"[선택한 폴더 이름]"`을 입력합니다.
4. 그래프 설정의 **Display** 항목에서 **Arrows(화살표)**를 켜면 인용 방향(`A ──> B`: A가 B를 인용함)을 화살표로 한눈에 볼 수 있습니다.
5. 각 논문 노트 내부의 `[Open in Zotero]` 링크를 누르면 조테로 원본 항목으로 즉시 점프합니다.

---

## 유용한 팁 & 자주 묻는 질문 (FAQ)

- **논문에 DOI가 꼭 필요한가요?** 네, OpenAlex는 DOI를 기반으로 인용 데이터를 찾습니다. Zotero에서 논문에 DOI를 많이 채워둘수록 더 풍성한 인용망이 연결됩니다.
- **같은 폴더에 다시 실행해도 안전한가요?** 네! 다시 실행해도 인용 관계만 최신으로 갱신되며, 자동 생성 영역 아래에 사용자가 직접 적은 메모나 코멘트는 삭제되지 않고 그대로 보존됩니다.
- **내 개인정보는 안전한가요?** `.env` 파일에 저장된 API 키는 오직 내 컴퓨터에서만 작동하며 외부나 GitHub에 절대 공유되지 않습니다.
- **터미널 콘솔 모드로 쓰고 싶다면?** 터미널에서 `python main.py --cli`를 실행하면 콘솔 대화형으로 사용할 수 있습니다.

---

## 라이선스

MIT License. 학술 연구 및 개인 연구 목적으로 자유롭게 사용하실 수 있습니다.
