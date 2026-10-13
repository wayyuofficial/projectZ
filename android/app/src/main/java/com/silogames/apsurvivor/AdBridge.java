package com.silogames.apsurvivor;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;

/**
 * 게임(HTML)과 AdMob 보상형 광고 사이의 다리 (M17, 지시 #172).
 *
 * 게임 HTML 은 통신을 하지 않는다(검사 c3). 광고는 여기 껍데기에서만 불러온다.
 *  - 게임: AdBridge.isReady() 로 광고가 있는지 묻고, AdBridge.show(종류) 로 띄워 달라고 한다.
 *  - 여기: 광고를 끝까지 봤는지(보상 콜백) 기억했다가 광고가 닫히면
 *          window.onAdResult(종류, 성공) 을 부른다. 보상은 게임이 준다.
 *  - 광고는 미리 하나 불러 둔다. 보여 준 뒤·실패한 뒤 다시 부른다.
 */
public class AdBridge {

    private static final long RETRY_MS = 30_000;   // 불러오기 실패(오프라인 등) 뒤 다시 시도

    private final Activity act;
    private final WebView web;
    private final String unitId;
    private final Handler main = new Handler(Looper.getMainLooper());

    private volatile RewardedAd ad;     // JS 스레드가 isReady 로 읽는다
    private boolean loading;
    private volatile boolean showing;

    public AdBridge(Activity act, WebView web) {
        this.act = act;
        this.web = web;
        this.unitId = act.getString(R.string.admob_rewarded_id);
        MobileAds.initialize(act, status -> load());
    }

    /** 메인 스레드에서만 부른다. */
    private void load() {
        if (loading || ad != null) return;
        loading = true;
        RewardedAd.load(act, unitId, new AdRequest.Builder().build(), new RewardedAdLoadCallback() {
            @Override
            public void onAdLoaded(RewardedAd r) {
                Log.i("AdBridge", "광고 준비됨");
                ad = r;
                loading = false;
            }

            @Override
            public void onAdFailedToLoad(LoadAdError e) {
                Log.w("AdBridge", "광고 불러오기 실패: " + e);   // 코드·메시지·응답 정보 — Logcat 'AdBridge'
                ad = null;
                loading = false;
                main.postDelayed(AdBridge.this::load, RETRY_MS);
            }
        });
    }

    @JavascriptInterface
    public boolean isReady() {
        return ad != null && !showing;
    }

    @JavascriptInterface
    public void show(String kind) {
        final String k = safeKind(kind);
        main.post(() -> {
            RewardedAd a = ad;
            if (a == null || showing) { result(k, false); load(); return; }
            ad = null;
            showing = true;
            final boolean[] earned = { false };
            a.setFullScreenContentCallback(new FullScreenContentCallback() {
                @Override
                public void onAdDismissedFullScreenContent() {
                    showing = false;
                    result(k, earned[0]);   // 끝까지 봤을 때만 성공
                    load();
                }

                @Override
                public void onAdFailedToShowFullScreenContent(AdError e) {
                    showing = false;
                    result(k, false);
                    load();
                }
            });
            a.show(act, reward -> earned[0] = true);
        });
    }

    /** 종류 문자열을 그대로 JS 에 다시 넣으므로 영문 소문자·숫자만 남긴다. */
    private static String safeKind(String s) {
        if (s == null) return "";
        return s.replaceAll("[^a-z0-9]", "");
    }

    private void result(String kind, boolean ok) {
        web.evaluateJavascript("window.onAdResult && window.onAdResult('" + kind + "', " + ok + ")", null);
    }
}
