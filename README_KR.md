# Citation Network Builder
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) [![Stars](https://img.shields.io/github/stars/idlhy0218/Citation-Network?style=flat-square)](https://github.com/idlhy0218/Citation-Network/stargazers) ![Version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)

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


## 처음 설치 방법

### 0단계 - 저장소 가져오기 (Fork & Clone)

1. 이 저장소의 GitHub 페이지 우측 상단에 있는 **Fork** 버튼을 클릭하여 본인 계정으로 저장소를 복제합니다.
2. 복제된 본인의 GitHub 저장소에서 코드를 로컬 컴퓨터로 복제(Clone)하거나 ZIP 파일로 다운로드하여 적당한 폴더에 압축을 풉니다.
   - Git 명령어를 사용하는 경우:
     ```bash
     git clone https://github.com/idlhy0218/Citation-Network.git
     ```
   - 또는 **GitHub Desktop** 프로그램을 사용하여 내 로컬 폴더로 가져옵니다.


### 1단계 - 프로젝트 폴더에서 터미널 열기 & 패키지 설치

명령 프롬프트(cmd) 또는 PowerShell을 열고 프로젝트 폴더로 이동한 뒤 필요한 패키지를 설치합니다.

> [!TIP]
> **터미널을 쉽게 여는 방법 (Windows)**:
> 1. 파일 탐색기에서 이 프로젝트 폴더(`Citation Network`)로 들어갑니다.
> 2. 탐색기 맨 위 주소창(경로가 표시된 곳)을 클릭하여 기존 주소를 지우고 **`cmd`**라고 입력한 뒤 **Enter**를 누릅니다.
> 3. 해당 폴더 경로로 바로 설정된 명령 프롬프트 창이 나타납니다.

창이 열리면 아래 명령어를 실행하여 필요한 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt
```


### 2단계 - 설정 파일 생성 및 API 키 입력

초기 다운로드 시에는 설정 파일의 틀만 존재합니다. 설정 파일(`.env`)을 만들고 내 정보를 채워 넣어야 합니다.

1. 터미널에 아래 명령어를 입력하여 템플릿 파일을 복사해 설정 파일(`.env`)을 만듭니다.
   - **명령 프롬프트(cmd)**:
     ```cmd
     copy .env.example .env
     ```
   - **PowerShell**:
     ```powershell
     cp .env.example .env
     ```
   *(또는 파일 탐색기에서 `.env.example` 파일을 복사한 뒤 이름을 `.env`로 바꾸어도 됩니다. 뒤에 `.txt`가 붙지 않도록 주의하세요.)*

2. 생성된 `.env` 파일을 메모장이나 텍스트 에디터로 열어 아래 항목을 입력하고 저장합니다.

   * **ZOTERO_USER_ID**: Zotero 웹사이트 로그인 후 [Zotero API Settings](https://www.zotero.org/settings/keys) 페이지 상단에서 **"Your userID for API calls is XXXXXX"** 부분의 숫자를 복사해 입력합니다.
   * **ZOTERO_API_KEY**: 같은 페이지 아래의 **"Create new private key"** 버튼을 눌러 발급받은 키를 복사해 입력합니다.
   * **OBSIDIAN_VAULT_PATH**: Obsidian을 열었을 때 보이는 볼트 폴더의 전체 경로를 입력합니다. (예: `C:\Users\Username\Documents\MyVault`)

```ini
# [필수 입력] Zotero API 정보와 Obsidian 경로
ZOTERO_USER_ID=본인의 Zotero 사용자 ID (숫자)
ZOTERO_API_KEY=본인의 Zotero API 키
OBSIDIAN_VAULT_PATH=C:\Users\사용자이름\경로\Obsidian 볼트 폴더

# [선택 입력] 환경에 맞게 나만의 폴더명 설정 및 속도 개선
CITATION_NETWORK_FOLDER=Citation Network
OPENALEX_EMAIL=your_email@domain.com
```

3. **내 취향에 맞게 설정 변경하기 (선택 사항)**:
   * **노트 저장 폴더명 변경**: Obsidian 볼트 내에서 노트가 생성될 폴더의 이름을 나만의 이름으로 바꾸고 싶다면 `CITATION_NETWORK_FOLDER` 값을 원하는 이름(예: `인용망 분석` 등)으로 변경합니다. 기본값은 `Citation Network`입니다.
   * **OpenAlex API 속도 개선**: 수집할 논문의 양이 수십 개 이상으로 많다면 `OPENALEX_EMAIL` 부분에 본인의 실제 이메일 주소를 입력해 주세요. OpenAlex API 측에서 신원 식별을 해주는 사용자에게 더 빠른 API 요청 대역폭(Polite Pool)을 무료로 제공해 주므로 작업 속도가 현저히 빨라집니다.


### 3단계 - 연결 확인

설치가 올바르게 완료되었고 API 연결이 성공하는지 확인하려면 아래 명령어를 실행합니다.

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


## 알아두면 좋은 것

- DOI가 없는 논문은 인용 관계를 조회할 수 없습니다. Zotero에서 DOI를 추가해 두면 더 많은 연결이 만들어집니다.
- OpenAlex는 무료 학술 데이터베이스입니다. 별도 회원가입이나 API 키가 필요하지 않습니다.
- 같은 폴더를 다시 실행하면 노트가 업데이트됩니다. 직접 작성한 내용 아래에 새 섹션이 덮어쓰이는 방식이므로 노트에 메모를 추가해도 됩니다.
- `.env` 파일에는 개인 API 키가 들어있습니다. GitHub에 올라가지 않도록 `.gitignore`에 등록되어 있습니다.
