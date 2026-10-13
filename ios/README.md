# 아포칼립스 서바이버 — 아이폰 앱 (지시 #200)

게임(`game/` 폴더)을 웹뷰로 감싸는 작은 iOS 앱. 안드로이드(`android/`)와 같은 구조다. 게임 코드는 그대로 쓴다.

## 준비
- 맥 + Xcode(15 이상) · 아이폰(iOS 16 이상) · 라이트닝/USB-C 케이블
- 무료 애플 ID 로 내 아이폰에 설치할 수 있다 — 단 **7일마다** Xcode 에서 다시 설치해야 한다. 지인 테스트(TestFlight)·앱스토어는 애플 개발자 계정(연 $99)이 필요하다.

## 처음 한 번 — 프로젝트 만들기
1. Xcode → **File → New → Project… → iOS → App** → Next
   - Product Name: `ApocalypseSurvivor` · Interface: **SwiftUI** · Language: **Swift** · Storage: None · 테스트 체크 해제
   - Organization Identifier: `com.silogames` (번들 ID 가 `com.silogames.ApocalypseSurvivor` 가 된다)
   - 저장 위치: 이 저장소의 `ios/` 폴더(‘Create Git repository’ 는 끈다)
2. Xcode 가 만든 `ApocalypseSurvivorApp.swift` 와 `ContentView.swift` 를 **지우고**, 이 폴더의 `ApocalypseSurvivor/ApocalypseSurvivorApp.swift` 를 프로젝트에 끌어다 넣는다(‘Copy items if needed’ 끔, Target 체크).
3. **`game` 폴더를 앱에 넣는다** — 탐색기에 끌어다 넣는 방식은 새 Xcode 에서 폴더가 흩어지기 쉬워(실제로 'game 폴더가 앱에 안 들어 있다'가 떴다) 아래 방식으로 한다(2026-10-09 맥에서 확인):
   - 프로젝트(파란 아이콘) → TARGETS **ApocalypseSurvivor** → **Build Phases** → **Copy Bundle Resources** 펼치기 → **+** → **Add Other… → Add Files…** → 저장소의 `game` 폴더를 (들어가지 말고) 한 번 클릭 → Open → **Create folder references** → Finish
   - 목록에 **파란 폴더 `game` 한 줄**이면 맞다. `index.html`·그림이 여러 줄로 따로 보이면 지우고(−) 다시.
   - 그 뒤 **Product → Clean Build Folder**(⇧⌘K) → 아이폰의 앱 지우기 → ▶
4. 프로젝트 → Target **ApocalypseSurvivor** →
   - **General**: Minimum Deployments **iOS 16.0** · Device Orientation **Portrait 만** · Status Bar Style 기본
   - **Info**: `Status bar is initially hidden` = YES 추가 · (선택) `Bundle display name` = `아포칼립스 서바이버`
   - **Signing & Capabilities**: Automatically manage signing 켜기 · Team 에서 내 애플 ID(Personal Team) 고르기
5. 아이콘: `Assets` → `AppIcon` 에 `ios/AppIcon-1024.png` 를 끌어다 넣는다(1024 한 장이면 된다).

## 아이폰에 설치
1. 아이폰을 케이블로 맥에 연결 → 위쪽 기기 목록에서 내 아이폰 선택 → ▶(Run)
2. 처음이면 아이폰에서: **설정 → 개인정보 보호 및 보안 → 개발자 모드 켜기**(재시동) · 앱이 안 열리면 **설정 → 일반 → VPN 및 기기 관리 → 내 애플 ID → 신뢰**
3. 시작 화면 → TAP TO START → 게임. 저장은 앱을 껐다 켜도 남는다.

## 알아 둘 것
- **광고**: iOS 엔 아직 광고가 없다 — 광고 버튼을 누르면 광고 없이 보상이 바로 들어온다(시험용). 출시 전 AdMob iOS SDK 와 iOS 광고 단위 ID 를 붙인다.
- **게임을 고친 뒤**: 저장소를 맥에서 받아(git pull) Xcode 에서 다시 ▶ 한다. `game` 을 복사해 넣었다면 Xcode 쪽 `game` 은 옛것이니 3단계로 다시 넣는다(제자리 참조로 넣었다면 그대로 따라온다).
- **콘솔 보기**: 맥 사파리 → 설정 → 고급 → ‘웹 개발자용 기능 보기’ → 개발자 메뉴 → 내 아이폰 → index.html.
- 저장은 안드로이드·PC 와 따로다(기기마다 새 게임).
