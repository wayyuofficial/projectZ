// 아포칼립스 서바이버 — iOS 껍데기 (지시 #200)
// 안드로이드(android/ MainActivity)와 같은 구조: 게임 폴더(game/)를 앱에 통째로 넣고 웹뷰로 연다.
// 게임 코드는 그대로다 — 저장(localStorage)·그림(img/)·배경음악(snd/)은 앱 안 파일에서 읽는다(서버 통신 없음).
// 광고: iOS 에는 아직 AdBridge 가 없다 → 게임은 광고 없이 보상을 바로 준다(시험용). 출시 전 AdMob iOS 를 붙인다.
import SwiftUI
import WebKit

@main
struct ApocalypseSurvivorApp: App {
    @Environment(\.scenePhase) private var phase

    var body: some Scene {
        WindowGroup {
            GameView()
                .ignoresSafeArea()               // 노치·홈 바 여백은 게임 CSS(env(safe-area-inset-*))가 맡는다
                .background(Color.black)
                .statusBarHidden(true)
                .persistentSystemOverlays(.hidden)
        }
        .onChange(of: phase) { p in              // 앱이 내려가면 소리를 멈추고, 돌아오면 잇는다(안드로이드 onPause/onResume 과 같다)
            switch p {
            case .active: GameWeb.shared.call("window.onAppResume && window.onAppResume()")
            case .background, .inactive: GameWeb.shared.call("window.onAppPause && window.onAppPause()")
            @unknown default: break
            }
        }
    }
}

/// 웹뷰 하나를 앱 전체가 같이 쓴다(장면이 다시 만들어져도 게임이 처음부터 다시 뜨지 않게).
final class GameWeb: NSObject, WKNavigationDelegate {
    static let shared = GameWeb()
    let view: WKWebView

    override init() {
        let c = WKWebViewConfiguration()
        c.allowsInlineMediaPlayback = true                 // 소리를 전체 화면 플레이어 없이
        c.mediaTypesRequiringUserActionForPlayback = []   // 시작 화면 터치 뒤 배경음악이 바로 나오게
        c.websiteDataStore = .default()                   // 저장(localStorage)이 앱을 껐다 켜도 남는다
        view = WKWebView(frame: .zero, configuration: c)
        super.init()
        view.isOpaque = false
        view.backgroundColor = .black
        view.scrollView.backgroundColor = .black
        view.scrollView.isScrollEnabled = false            // 캔버스 게임 — 화면이 끌려 다니지 않게
        view.scrollView.bounces = false
        view.scrollView.contentInsetAdjustmentBehavior = .never
        view.navigationDelegate = self
        if #available(iOS 16.4, *) { view.isInspectable = true }   // 맥 사파리 '개발자' 메뉴로 콘솔을 볼 수 있다(디버그)
        if let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "game") {
            view.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        } else {
            view.loadHTMLString("<body style='background:#000;color:#fff;font:16px sans-serif;padding:40px'>game 폴더가 앱에 안 들어 있다 — ios/README.md 3단계(파란 폴더로 넣기)를 확인</body>", baseURL: nil)
        }
    }

    func call(_ js: String) { view.evaluateJavaScript(js, completionHandler: nil) }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        webView.scrollView.pinchGestureRecognizer?.isEnabled = false   // 두 손가락 확대 막기
    }
}

struct GameView: UIViewRepresentable {
    func makeUIView(context: Context) -> WKWebView { GameWeb.shared.view }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
