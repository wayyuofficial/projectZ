package com.silogames.apsurvivor;

import android.annotation.SuppressLint;
import android.content.pm.ApplicationInfo;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.graphics.Insets;
import android.view.View;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.window.OnBackInvokedDispatcher;

/**
 * 단일 HTML 게임을 WebView 로 감싼다.
 *
 * 주의할 점 두 가지:
 *  1) DOM Storage 는 WebView 에서 기본으로 꺼져 있다. 켜지 않으면 localStorage 가 통째로 죽고
 *     방치형 게임의 저장이 전부 사라진다. setDomStorageEnabled(true) 는 선택이 아니다.
 *  2) 문자 인코딩을 UTF-8 로 못 박는다. 지시 #15 에서 실기 한글 깨짐을 겪었다.
 */
public class MainActivity extends Activity {

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);


        web = new WebView(this);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(0xFF05080A);
        root.addView(web, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);

        // 대상 SDK 35+ 는 앱이 화면 끝까지(상태 표시줄·제스처 막대·둥근 모서리 자리까지) 강제로 그려진다.
        // 2026-10-08 에뮬레이터(API 36) 제보: 맨 아래 광고 버튼이 화면 가장자리에 잘렸다(지시 #176).
        // 막대는 숨긴 채로 두되, 막대·카메라 구멍이 차지할 자리만큼 게임을 안쪽으로 들인다(그 자리는 검은 띠).
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((v, ins) -> {
                Insets in = ins.getInsetsIgnoringVisibility(
                        WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                FrameLayout.LayoutParams lp = (FrameLayout.LayoutParams) web.getLayoutParams();
                // 값이 바뀔 때만 다시 배치한다 — 매번 setLayoutParams 하면 배치·인셋이 되풀이돼 첫 화면이 끝나지 않을 수 있다(지시 #186)
                if (lp.leftMargin != in.left || lp.topMargin != in.top || lp.rightMargin != in.right || lp.bottomMargin != in.bottom) {
                    lp.setMargins(in.left, in.top, in.right, in.bottom);
                    web.setLayoutParams(lp);
                }
                return WindowInsets.CONSUMED;
            });
        }

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);              // localStorage. 끄면 저장이 죽는다
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setDefaultTextEncodingName("UTF-8");     // 한글 깨짐 방지 (지시 #15)
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        s.setMediaPlaybackRequiresUserGesture(false);

        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new AdBridge(this, web), "AdBridge");   // M17 — 보상형 광고 다리
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setBackgroundColor(0xFF05080A);

        // 화면이 꺼지지 않게 - 방치형이라 보고 있는 시간이 길다
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        goImmersive();

        // 대상 SDK 36(지시 #174)부터 뒤로 가기에 onBackPressed 가 불리지 않는다(예측형 뒤로 가기).
        // 그대로 두면 뒤로 가기가 앱을 끝낸다 — 안드로이드 13+ 는 새 방식으로 같은 동작(앱 내리기)을 건다.
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, () -> moveTaskToBack(true));
        }

        // 디버그 빌드에서만: 콘솔 오류·로딩 단계를 Logcat 'GameBoot' 로 (2026-10-08 첫 화면이 검게 남는 문제를 보려고)
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            WebView.setWebContentsDebuggingEnabled(true);
            web.setWebChromeClient(new WebChromeClient() {
                @Override
                public boolean onConsoleMessage(ConsoleMessage m) {
                    Log.i("GameBoot", "console " + m.messageLevel() + " " + m.message() + " @" + m.lineNumber());
                    return true;
                }
            });
            Handler h = new Handler(Looper.getMainLooper());
            for (final int sec : new int[] { 2, 5, 10, 20, 40 }) {
                h.postDelayed(() -> web.evaluateJavascript(
                        "(function(){try{var c=document.getElementById('c');return JSON.stringify({rs:document.readyState,draw:typeof draw,G:typeof G,cw:c&&c.width,ch:c&&c.height,css:c&&c.style.width,imgs:Array.prototype.filter.call(document.images||[],function(i){return !i.complete}).length})}catch(e){return 'ERR '+e}})()",
                        v -> Log.i("GameBoot", sec + "s " + v)), sec * 1000L);
            }
        }
        web.loadUrl("file:///android_asset/index.html");
    }

    /** 전체화면. 게임이 env(safe-area-inset-*) 로 노치를 피한다. */
    private void goImmersive() {
        View d = getWindow().getDecorView();
        d.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            getWindow().getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) goImmersive();
    }

    /** 뒤로 가기로 앱이 바로 죽지 않게 - 게임은 페이지 이동이 없으므로 앱을 내린다. (안드로이드 12 이하) */
    @Override
    public void onBackPressed() {
        moveTaskToBack(true);
    }

    @Override
    protected void onPause() {
        // 게임이 pagehide/visibilitychange 에서 저장한다. WebView 에도 알린다.
        // 지시 #180 — 배경음악이 앱을 내린 뒤에도 흐르지 않게 게임 오디오를 멈춘다(웹뷰 onPause 는 오디오를 안 멈춘다)
        if (web != null) web.evaluateJavascript("window.onAppPause && window.onAppPause()", null);
        if (web != null) web.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) web.onResume();
        if (web != null) web.evaluateJavascript("window.onAppResume && window.onAppResume()", null);
    }
}
