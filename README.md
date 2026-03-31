# yFriend - AI YouTube Video Generator

AI가 자동으로 YouTube 영상을 생성하는 프로토타입입니다.
주제를 입력하면 스크립트 → 키프레임 이미지 → 나레이션 → 최종 영상을 자동 생성합니다.

## 기능 (Sprint 2.5)

- **Script**: Gemini 2.5 Flash로 한국어 나레이션 스크립트 자동 생성
- **Visual**: Gemini 2.5 Flash Image로 장면별 키프레임 이미지 생성
- **Voice**: Edge TTS로 한국어 나레이션 음성 생성
- **Assembly**: FFmpeg로 이미지 + 나레이션 + 자막 → MP4 조립

## 설치

```bash
pip install -r requirements.txt
FFmpeg가 필요합니다:

Windows: https://ffmpeg.org/download.html
Mac: brew install ffmpeg
Linux: sudo apt install ffmpeg
설정
Copycp config.yaml.example config.yaml
config.yaml을 열고 Gemini API 키를 입력하세요. API 키는 https://aistudio.google.com/app/apikey 에서 무료 발급 가능합니다.

실행
Copypython main.py "한국의 사계절이 아름다운 이유"
프로젝트 구조
Copyyfriend/
├── main.py                 # 진입점
├── config.yaml.example     # 설정 템플릿
├── requirements.txt        # 의존성
├── core/                   # 불변 코어
│   ├── models.py           # 데이터 모델
│   ├── config.py           # 설정 로더
│   ├── orchestrator.py     # 실행 오케스트레이터
│   ├── project.py          # 프로젝트 폴더 관리
│   ├── contracts.py        # QA 규격
│   ├── interfaces.py       # 엔진 인터페이스
│   └── qa.py               # 품질 검증
├── engines/                # 가변 엔진 (교체 가능)
│   ├── script/
│   │   └── gemini_flash.py
│   ├── visual/
│   │   └── gemini_image.py
│   ├── voice/
│   │   └── edge_tts_engine.py
│   ├── assembly/
│   │   └── ffmpeg_assembly.py
│   └── advisor/
│       └── self_improve.py
├── macros/
├── projects/               # 출력 (gitignore)
└── tests/
    └── test_core.py
자기 개선 리포트
Copypython -m engines.advisor.self_improve
현재 점수와 다음 개선 과제를 자동 분석합니다.

License
MIT