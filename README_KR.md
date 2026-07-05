# Citation Network Builder v1.0.1
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) [![Stars](https://img.shields.io/github/stars/idlhy0218/Citation-Network?style=flat-square)](https://github.com/idlhy0218/Citation-Network/stargazers) ![Version](https://img.shields.io/badge/version-1.0.1-blue?style=flat-square)

Zotero에 저장된 논문들의 메타데이터와 무료 학술 데이터베이스인 OpenAlex API를 사용하여 논문들 간의 인용 관계를 분석하고, 이를 Obsidian 노트 및 인용 네트워크(시각화 그래프)로 자동 변환하는 도구입니다.

### 작업 흐름

1. Zotero: 내 라이브러리에서 분석할 폴더(컬렉션)와 논문 목록을 수집합니다.
2. OpenAlex: 각 논문의 DOI를 기반으로 OpenAlex 데이터베이스를 조회하여 해당 폴더 내 논문들 사이의 인용 및 피인용 관계를 찾아냅니다.
3. Obsidian: 분석 완료된 관계 정보를 바탕으로 개별 논문 노트를 생성하고 내부 링크([[wiki-link]])로 서로 연결합니다. Obsidian의 Graph View를 통해 인용망을 시각화합니다.



## 필요한 것

- **Python 3.9 이상** (https://python.org)
  - > [!IMPORTANT]
  > 설치 파일 실행 시 맨 아래에 있는 **"Add python.exe to PATH"** 옵션을 반드시 체크해 주세요. 체크하지 않으면 터미널에서 `python` 명령어를 찾을 수 없다는 오류가 발생합니다.
- **Zotero 계정 및 API 키**
- **Obsidian** (https://obsidian.md)


## 설치 방법

1. **저장소 복제**:
   ```bash
   git clone https://github.com/idlhy0218/Citation-Network.git
   cd Citation-Network
   ```

2. **필수 패키지 설치**:
   ```bash
   pip install -r requirements.txt
   ```

3. **환경 설정 (.env)**:
   `.env.example` 파일을 복사하여 `.env` 파일을 생성한 뒤, 아래 필수 설정을 채워 넣습니다.
   * **ZOTERO_USER_ID**: [Zotero API Settings](https://www.zotero.org/settings/keys) 페이지 상단의 "Your userID for API calls"의 숫자 ID.
   * **ZOTERO_API_KEY**: 동일 페이지에서 "Create new private key"로 생성한 API 키.
   * **OBSIDIAN_VAULT_PATH**: Obsidian 볼트 폴더의 절대 경로.

   ```ini
   # 필수 설정 (Required)
   ZOTERO_USER_ID=본인의_Zotero_사용자_ID
   ZOTERO_API_KEY=본인의_Zotero_API_키
   OBSIDIAN_VAULT_PATH=C:\Users\Username\Documents\MyVault

   # 선택 설정 (Optional)
   ZOTERO_LIBRARY_TYPE=user                 # 그룹 라이브러리는 'group'으로 변경
   CITATION_NETWORK_FOLDER=Citation Network  # 볼트 내 생성될 폴더명
   OPENALEX_EMAIL=your_email@domain.com      # Polite Pool을 통한 OpenAlex 호출 속도 향상
   ```

4. **연결 상태 확인**:
   ```bash
   python main.py --test
   ```

터미널 창에 `"Zotero connection successful"`과 `"OpenAlex connection successful"` 메시지가 모두 출력되면 준비가 완료된 것입니다.


## 사용 방법

### 기본 실행 (권장)

`run.bat` 파일을 더블클릭하거나, 명령 프롬프트에서 아래 명령어를 실행합니다.

    python main.py

실행하면 Zotero 폴더 목록이 트리 구조로 나타납니다.

    ============================================================
      조테로 폴더를 선택하세요
      (A) = 하위 폴더 있음  /  (단일) = 하위 폴더 없음
    ============================================================
      1.  (단일) Introduction
      2.  (A)    Machine Learning
          3.  (단일) Supervised Learning
          4.  (단일) Unsupervised Learning
      ...

번호를 입력하면 해당 폴더와 하위 폴더의 모든 논문이 처리됩니다.

### 폴더 이름을 직접 지정해서 실행

    python main.py --collection "Machine Learning"

폴더 이름을 따옴표로 감싸서 입력합니다. 하위 폴더가 있으면 자동으로 함께 처리됩니다.

### API 연결 테스트

    python main.py --test


## 파일 구조와 역할

    Citation Network/
    │
    ├── run.bat                   실행 파일. 더블클릭으로 바로 실행됩니다.
    │
    ├── main.py                   프로그램의 시작점. 폴더 선택, 전체 흐름 제어.
    │
    ├── .env                      API 키와 경로 설정 파일.
    │                             이 파일은 절대 GitHub에 올리지 마세요.
    │
    ├── requirements.txt          필요한 Python 패키지 목록.
    │                             처음 설치 시 한 번만 실행하면 됩니다.
    │
    ├── cache/
    │   └── openalex_cache.json   OpenAlex 조회 결과를 저장해두는 캐시.
    │                             두 번째 실행부터는 이 파일 덕분에 훨씬 빠릅니다.
    │
    └── src/
        ├── zotero_client.py      Zotero에서 논문 목록과 메타데이터를 가져옵니다.
        ├── openalex_client.py    OpenAlex에서 논문 간 인용 관계를 조회합니다.
        └── obsidian_writer.py    논문 정보를 Obsidian 마크다운 노트로 저장합니다.


## 결과물 확인 방법

노트는 Obsidian 볼트 내 `.env` 파일에 설정한 폴더(기본값: `Citation Network`) 안에 생성됩니다.

각 폴더 안에는 아래 두 종류의 파일이 만들어집니다.

- `논문citekey.md` : 개별 논문 노트. 인용한 논문과 인용받은 논문이 링크로 연결됩니다.
- `_Index.md` : 해당 폴더의 전체 논문 목록 표.

Obsidian에서 Graph View를 열면 논문들 사이의 인용 관계가 시각적으로 표시됩니다.
Graph View에서 필터 입력란에 `path:"설정한 폴더명"` (예: `path:"Citation Network"`)을 입력하면 이 도구로 만든 노트만 표시됩니다.

> [!TIP]
> **인용 방향 화살표 표시 (v1.0.1+)**: Obsidian 그래프 뷰 설정에서 **화살표(Arrows)** 기능을 활성화해 주세요. 화살표는 인용하는 논문에서 피인용 논문 방향으로 연결됩니다 (A ──> B는 A 논문이 B 논문을 인용했다는 의미입니다). 나를 인용한 논문(`Cited by`) 섹션은 그래프 뷰에서 양방향 화살표가 그려져 관계가 왜곡되는 것을 막기 위해 위키링크가 아닌 일반 텍스트로 표기됩니다.


## 알아두면 좋은 것

- DOI가 없는 논문은 인용 관계를 조회할 수 없습니다. Zotero에서 DOI를 추가해 두면 더 많은 연결이 만들어집니다.
- OpenAlex는 무료 학술 데이터베이스입니다. 별도 회원가입이나 API 키가 필요하지 않습니다.
- 같은 폴더를 다시 실행하면 노트가 업데이트됩니다. 직접 작성한 내용 아래에 새 섹션이 덮어쓰이는 방식이므로 노트에 메모를 추가해도 됩니다.
- `.env` 파일에는 개인 API 키가 들어있습니다. GitHub에 올라가지 않도록 `.gitignore`에 등록되어 있습니다.
