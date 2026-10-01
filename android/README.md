# android — WebView 래퍼 (M2 선행 작업)

`game/index.html` 하나를 안드로이드 앱으로 감싼다. 게임 코드는 여기에 **복사하지 않는다.**
`app/build.gradle` 의 `assets.srcDirs` 가 저장소의 `game/` 폴더를 그대로 가리킨다 — 복사본을 두면 갈라진다.

## 빌드 (확인됨 — 2026-09-08 실제로 성공)

```bash
# JDK 21 을 써야 한다. Android Studio 내장 jbr 은 JDK 25 라 Gradle 8.7 / AGP 8.5.2 가 지원하지 않는다.
JAVA_HOME=~/.jdks/jbr-21.0.11 ./gradlew assembleDebug
```

- 결과: `android/app/build/outputs/apk/debug/app-debug.apk` (**23.1 KB**)
- 디버그 키로 서명된다. 폰에 넣을 때 **출처를 알 수 없는 앱 설치**를 허용해야 한다
- Android Studio 에서는 `Build > Build Bundle(s)/APK(s) > Build APK(s)` 로도 같은 결과가 나온다
- 폰을 USB로 연결하고 **개발자 옵션 → USB 디버깅** 을 켜면 ▶ 로 바로 설치·실행된다

## 빌드하다 걸린 것 (기록해 둔다)

| 문제 | 처리 |
|---|---|
| `checkDebugDuplicateClasses` 실패 — `androidx.appcompat` 이 끌고 온 `kotlin-stdlib 1.8.22` 와 `kotlin-stdlib-jdk7/jdk8 1.6.21` 충돌 | **appcompat 을 통째로 제거.** WebView 하나짜리 앱에 AndroidX 는 필요 없다. 프레임워크 `Activity` + `Theme.NoTitleBar.Fullscreen` 으로 바꿨다 |
| Studio 내장 JDK 가 25 | `~/.jdks/jbr-21.0.11` 을 `JAVA_HOME` 으로 지정 |
| Sync 가 래퍼 없이 돌아 `gradlew` 가 없었다 | `gradle wrapper` 로 생성해 저장소에 넣었다 |
| `game/README.md` 가 앱 assets 에 딸려 들어갔다 | `ignoreAssetsPattern` 으로 제외 |

## 이 래퍼가 신경 쓴 것

| 항목 | 이유 |
|---|---|
| `setDomStorageEnabled(true)` | **WebView는 DOM Storage가 기본으로 꺼져 있다.** 켜지 않으면 localStorage가 죽어 저장이 전부 사라진다 |
| `setDefaultTextEncodingName("UTF-8")` | 실기 한글 깨짐을 한 번 겪었다 (지시 #15) |
| `screenOrientation="portrait"` | 세로 전용 게임 |
| `LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES` | 게임의 `env(safe-area-inset-*)` 가 노치를 피하도록 |
| `FLAG_KEEP_SCREEN_ON` | 방치형이라 보고 있는 시간이 길다 |
| INTERNET 권한 **없음** | 게임은 서버 통신을 하지 않는다 (검사 C3) |
| `onBackPressed` → `moveTaskToBack` | 뒤로 가기로 앱이 죽지 않게 |

이 설정들은 `checks/c11_webview_storage.py` 가 지킨다. 지우면 검사가 막는다.

## 아직 확인 못 한 것

**빌드도 설치도 해 본 적이 없다.** 도구가 없어 컴파일조차 못 해봤다.
gradle 버전·의존성 버전이 실제로 맞물리는지는 **처음 Sync 할 때 드러난다.**
안 맞으면 Android Studio 가 고칠 방법을 알려준다 — 그 메시지를 그대로 알려주면 맞춘다.

## 서명

`release` 빌드에 서명 설정을 넣지 않았다.
스토어에 올릴 때 `Build > Generate Signed Bundle / APK` 로 키를 만든다.
**키 파일과 비밀번호는 저장소에 넣지 않는다.**

## 에뮬레이터로 확인하기 (2026-10-01 — 테스트 기기가 없을 때, 지시 #142)

1. Android Studio → **Open** → 이 폴더(`android/`). Gradle Sync 가 끝날 때까지 기다린다.
   - Sync 가 JDK 로 실패하면: **Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK** 를 `jbr-21`(`~/.jdks/jbr-21.0.11`)로.
2. 오른쪽 **Device Manager → + → Create Virtual Device** → Phone 에서 **Pixel 6** → 시스템 이미지 **API 34 (x86_64)** 옆 다운로드(1GB 남짓, 한 번만) → Finish.
   (2026-10-01 확인: SDK 에 emulator 는 있고 시스템 이미지·AVD 는 없었다.)
3. 위 툴바에서 그 기기를 고르고 **▶ Run 'app'**. 에뮬레이터가 뜨고 앱이 설치·실행된다. 게임을 고친 뒤에는 ▶ 만 다시 누르면 된다 — assets 가 `game/` 을 그대로 가리킨다.
4. 이미 만든 APK 만 넣으려면: 저장소 루트의 `zombie-survival-debug.apk` 를 에뮬레이터 창에 **끌어다 놓는다**.
- 처음부터: 일일 탭 맨 아래 "저장 지우기 (테스트)" 를 5초 안에 두 번. 옛 저장 위 이전 확인: 지우지 말고 ▶ 로 덮어 설치.
- 오류 보기: 아래 **Logcat** 에서 `package:com.wayyu.zombiesurvival.debug`. 화면 캡처: 에뮬레이터 옆 카메라 버튼.
- **에뮬레이터가 못 보는 것**: 실제 폰의 fps·발열, 손 터치 감각, DPR 4 뭉개짐, 노치. (`plans/실기묶음.md`)
- **버벅이다 통째로 멈추면** (2026-10-01 실제로 겪음: 런처·systemui 가 `HardwareRenderer` 시간 초과로 죽고 "The system died"): 게임이 아니라 가상 폰의 그래픽이 죽은 것이다. **원인은 Graphics = Automatic 이 소프트웨어 그래픽을 골라 쓴 것** — Device Manager → 연필(Edit) → Show Advanced Settings → **Graphics 를 Hardware 로** 바꾸고 Cold Boot 하니 잘 돈다(사람이 확인). 처음에 AI 는 반대로(Software 로 바꾸라고) 권했다 — 틀렸다. 화면·동작만 보려면 PC 크롬에서 `game/index.html` 을 열고 F12 → 기기 모드(375×812)도 된다.
