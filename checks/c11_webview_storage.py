# -*- coding: utf-8 -*-
"""안드로이드 WebView 래퍼가 게임을 죽이는 설정으로 되어 있는지.

근거: 지시 #17. 사례가 아니라 **결정적 사실**이라 바로 검사로 내렸다 (C10 과 같은 이유).
WebView 는 DOM Storage 가 **기본으로 꺼져 있다.** 켜지 않으면 localStorage 가 통째로 죽고,
저장이 생명줄인 방치형 게임에서는 진행이 하나도 남지 않는다.
정본 `canon/00-identity.md`: "저장이 깨지면 방치형은 게임이 끝난다."
"""
NAME = "안드로이드 WebView 설정이 게임을 죽이는지"
PRIORITY = 1

import io, os, re, glob

NEED = [
    (r"setDomStorageEnabled\s*\(\s*true\s*\)",
     "setDomStorageEnabled(true) 가 없다 — localStorage 가 죽어 저장이 전부 사라진다"),
    (r"setJavaScriptEnabled\s*\(\s*true\s*\)",
     "setJavaScriptEnabled(true) 가 없다 — 게임이 아예 안 돈다"),
    (r'setDefaultTextEncodingName\s*\(\s*"UTF-8"\s*\)',
     'setDefaultTextEncodingName("UTF-8") 가 없다 — 한글이 깨질 수 있다 (지시 #15)'),
]

BANNED = [
    (r"setDomStorageEnabled\s*\(\s*false\s*\)", "setDomStorageEnabled(false) 가 있다"),
]


BLOCK = re.compile(r"/\*.*?\*/", re.S)
LINE = re.compile(r"//.*")


def strip_comments(src):
    """주석을 지우고 본다. 주석 처리된 호출은 있는 것이 아니다.
    (2026-09-08: 이 처리가 없어서 // 로 막아둔 setDomStorageEnabled 를 통과시켰다.)"""
    return LINE.sub("", BLOCK.sub("", src))


def run(root):
    src = os.path.join(root, "android", "app", "src", "main")
    if not os.path.isdir(src):
        return {"status": "skip", "detail": ["android/ 프로젝트가 없다 — 래퍼를 만들면 이 검사가 살아난다"]}

    javas = glob.glob(os.path.join(src, "java", "**", "*.java"), recursive=True) + \
        glob.glob(os.path.join(src, "java", "**", "*.kt"), recursive=True)
    if not javas:
        return {"status": "fail", "detail": ["android/ 는 있는데 액티비티 소스가 없다"]}

    text = ""
    for p in javas:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            text += strip_comments(f.read()) + "\n"

    bad = []
    for rx, msg in NEED:
        if not re.search(rx, text):
            bad.append(msg)
    for rx, msg in BANNED:
        if re.search(rx, text):
            bad.append(msg)

    # 게임 자산 경로가 저장소의 game/ 을 가리키는지 (복사본을 두면 원본과 갈라진다)
    gradle = os.path.join(root, "android", "app", "build.gradle")
    if os.path.exists(gradle):
        with io.open(gradle, encoding="utf-8", errors="replace") as f:
            g = f.read()
        if "assets.srcDirs" not in g or "../../game" not in g:
            bad.append("app/build.gradle 의 assets.srcDirs 가 ../../game 을 가리키지 않는다 "
                       "— 게임 복사본이 원본과 갈라진다")
    else:
        bad.append("android/app/build.gradle 이 없다")

    # 게임이 서버 통신을 안 하므로 인터넷 권한도 요구하지 않아야 한다
    man = os.path.join(src, "AndroidManifest.xml")
    if os.path.exists(man):
        with io.open(man, encoding="utf-8", errors="replace") as f:
            m = f.read()
        if "android.permission.INTERNET" in m:
            bad.append("INTERNET 권한을 요청한다 — 게임은 서버 통신을 하지 않는다 (검사 C3와 어긋남)")
    else:
        bad.append("AndroidManifest.xml 이 없다")

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["WebView 설정 %d개 파일 통과" % len(javas)]}
