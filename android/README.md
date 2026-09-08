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
