# android — WebView 래퍼 (M2 선행 작업)

`game/index.html` 하나를 안드로이드 앱으로 감싼다. 게임 코드는 여기에 **복사하지 않는다.**
`app/build.gradle` 의 `assets.srcDirs` 가 저장소의 `game/` 폴더를 그대로 가리킨다 — 복사본을 두면 갈라진다.

## 이 폴더로는 APK가 안 나온다. 도구가 필요하다.

2026-09-08 조회 결과 이 PC에는 **빌드 도구가 하나도 없다.**

| 도구 | 상태 |
|---|---|
| `java` / `javac` (JDK) | 없음 |
| `gradle` | 없음 |
| Android SDK (`adb`·`sdkmanager`·`apksigner`·`aapt2`·`d8`) | 없음 |
| `ANDROID_HOME` / `ANDROID_SDK_ROOT` | 미설정 |
| `node` / `npm` | 없음 → Capacitor·Cordova·Bubblewrap **불가** |

## 사람이 할 일 (한 번만)

1. **Android Studio 설치** — https://developer.android.com/studio
   JDK와 Android SDK가 함께 깔린다. 따로 설치할 필요 없다.
2. Android Studio 에서 **이 `android` 폴더를 연다** (`Open`, 상위 `project2` 가 아니라 `android`).
3. 처음 열면 Gradle 래퍼가 없다고 할 수 있다 → **"Use Gradle wrapper" / 동기화(Sync)** 를 누르면 Studio 가 채워 넣는다.
   (`gradle/wrapper/gradle-wrapper.jar` 는 바이너리라 저장소에 넣지 않았다.)
4. 폰을 USB로 연결하고 **개발자 옵션 → USB 디버깅** 을 켠 뒤 ▶ 실행.
   또는 `Build > Build Bundle(s)/APK(s) > Build APK(s)` 로 APK 파일을 만든다.
   - 디버그 APK 위치: `android/app/build/outputs/apk/debug/app-debug.apk`
   - 폰에 옮겨 설치할 때는 **출처를 알 수 없는 앱 설치**를 허용해야 한다.

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
