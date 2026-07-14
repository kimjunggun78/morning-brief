#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모닝 브리프 자동 생성 스크립트 (데이터 + AI 코멘트 버전)
- 무료 시세(Yahoo Finance)로 지수/원자재/환율/국내지수 수집
- ANTHROPIC_API_KEY 가 있으면 Claude Haiku로 요약·시사점·테마를 생성
  (없거나 실패하면 규칙 기반 코멘트로 자동 폴백)
- 앱이 읽는 brief.json 스키마로 저장 / GitHub Actions에서 매일 실행
"""
import json, os, datetime, urllib.request
from zoneinfo import ZoneInfo

try:
    import yfinance as yf
except Exception:
    yf = None

KST = ZoneInfo("Asia/Seoul")
now = datetime.datetime.now(KST)
WD = "월화수목금토일"[now.weekday()]
date_label = f"{now:%Y-%m-%d} ({WD}) · 간밤 마감 기준"

def quote(ticker):
    if yf is None:
        return None
    try:
        h = yf.Ticker(ticker).history(period="7d")
        c = h["Close"].dropna()
        if len(c) < 2:
            return None
        last, prev = float(c.iloc[-1]), float(c.iloc[-2])
        return last, (last - prev) / prev * 100.0
    except Exception:
        return None

def pct(x):  return f"{x:+.2f}%"
def num(x, d=0): return f"{x:,.{d}f}"
def updown(x, up="상승", down="하락", flat="보합"):
    return up if x > 0.15 else (down if x < -0.15 else flat)

# ---------- 데이터 수집 ----------
sp=quote("^GSPC"); ndq=quote("^IXIC"); dji=quote("^DJI"); tnx=quote("^TNX")
wti=quote("CL=F"); gold=quote("GC=F"); dxy=quote("DX-Y.NYB"); krw=quote("KRW=X")
eur=quote("EURUSD=X"); soxx=quote("SOXX"); kospi=quote("^KS11"); kosdaq=quote("^KQ11")

def y10():
    if not tnx: return None
    v = tnx[0]; return v/10.0 if v > 20 else v

sections = []
if sp and ndq and dji:
    sections.append({"icon":"🇺🇸","title":"미국 증시",
        "body":f"S&P500 {num(sp[0])}({pct(sp[1])}), 나스닥 {num(ndq[0])}({pct(ndq[1])}), 다우 {num(dji[0])}({pct(dji[1])}).",
        "take":("위험선호 회복 — 실적 견고한 대형주 중심, 과열은 분할 관점." if sp[1]>0
                else "위험회피 흐름 — 현금·우량주 비중, 추격매매 자제.")})
y = y10()
if y is not None:
    d = tnx[1] if tnx else 0
    sections.append({"icon":"🏦","title":"금리 / Fed",
        "body":f"미 10년물 국채금리 {y:.2f}%({pct(d)}). 금리 방향이 밸류에이션의 핵심 변수.",
        "take":("금리 상승 — 고PER 성장주엔 역풍, 현금흐름 우량주 유리." if d>0
                else "금리 안정/하락은 성장주에 우호적 — 배경도 확인.")})
if wti and gold:
    sections.append({"icon":"🛢️","title":"원자재 (유가·금)",
        "body":f"WTI 유가 ${num(wti[0],1)}({pct(wti[1])}), 금 ${num(gold[0])}({pct(gold[1])}).",
        "take":("유가 상승은 인플레·금리 자극 — 에너지 수혜, 금은 실질금리 확인." if wti[1]>0
                else "유가 안정은 인플레 완화 — 금리·성장주에 우호적.")})
if krw:
    parts=[f"원/달러 {num(krw[0],1)}원({pct(krw[1])})"]
    if dxy: parts.append(f"달러인덱스 {num(dxy[0],1)}")
    if eur: parts.append(f"유로 {eur[0]:.4f}")
    sections.append({"icon":"💱","title":"환율","body":" · ".join(parts)+".",
        "take":("원화 약세 — 수입 원가 부담, 수출주 유리. 환헤지 주의." if krw[1]>0
                else "원화 강세 — 외국인 수급 우호, 수출주 부담. 방향 주시.")})
if soxx:
    sections.append({"icon":"🔧","title":"섹터 포커스 — 반도체",
        "body":f"미 반도체 ETF(SOXX) {pct(soxx[1])}. 반도체가 시장 방향을 주도.",
        "take":("반도체 강세 — AI 수요 뒷받침, 대장주 옥석 가리기." if soxx[1]>0
                else "반도체 약세 — 매크로發/실적 훼손 구분, 과매도 시 분할 관점.")})
if kospi:
    parts=[f"코스피 {num(kospi[0])}({pct(kospi[1])})"]
    if kosdaq: parts.append(f"코스닥 {num(kosdaq[0],1)}({pct(kosdaq[1])})")
    sections.append({"icon":"🇰🇷","title":"국내 증시","body":" · ".join(parts)+".",
        "take":("강세 구간 — 개별 우량주 밸류·수급 확인." if kospi[1]>0
                else "약세 구간 — 지수보다 개별 우량주 점검, 현금 여력 확인.")})

# ---------- 규칙 기반 요약/테마 (폴백) ----------
if sp:
    summary = (f"간밤 미국 증시는 {updown(sp[1])} 마감(S&P500 {pct(sp[1])}). "
               + (f"유가 {updown(wti[1],'급등','하락','보합')}, " if wti else "")
               + (f"원/달러 {updown(krw[1],'상승','하락','보합')}. " if krw else "")
               + "주요 지표를 아래에 정리했습니다.")
else:
    summary = "시세 데이터를 수집했습니다. 아래 지표를 확인하세요."

cands=[]
if wti:  cands.append((abs(wti[1]),  {"title":f"유가 {updown(wti[1],'급등','하락','보합')}","detail":f"WTI {pct(wti[1])} — 인플레·금리·에너지주에 파급."}))
if soxx: cands.append((abs(soxx[1]), {"title":f"반도체 {updown(soxx[1],'강세','약세','보합')}","detail":f"SOXX {pct(soxx[1])} — 시장 방향을 좌우하는 핵심 섹터."}))
if krw:  cands.append((abs(krw[1]),  {"title":f"원화 {updown(krw[1],'약세','강세','보합')}","detail":f"원/달러 {pct(krw[1])} — 수급·수출입에 영향."}))
if gold: cands.append((abs(gold[1]), {"title":f"금 {updown(gold[1],'상승','하락','보합')}","detail":f"금 {pct(gold[1])} — 안전자산·실질금리 시그널."}))
cands.sort(key=lambda t:t[0], reverse=True)
themes=[c[1] for c in cands[:3]]
while len(themes)<3: themes.append({"title":"시장 점검","detail":"주요 지표 흐름을 확인하세요."})

sources = "Yahoo Finance (자동 수집)"

# ---------- AI 코멘트 (선택) ----------
def enhance_with_ai(sections):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or len(sections) < 4:
        return None
    lines = [f"{i}. {s['title']}: {s['body']}" for i, s in enumerate(sections)]
    prompt = (
        "당신은 48세 개인투자자(가치·성장주, 숫자·논리 중심)를 위한 한국어 아침 시장 브리핑을 씁니다.\n"
        "아래 오늘의 지표를 보고 JSON만 출력하세요(설명 금지).\n"
        "형식: {\"summary\": \"2문장 요약\", \"takes\": [섹션 수만큼 각 1줄 시사점 문자열], "
        "\"themes\": [{\"title\":\"짧은 제목\",\"detail\":\"1줄 설명\"} 정확히 3개]}\n"
        "시사점은 가치·성장주 투자 판단에 도움되는 한 줄. 과도한 확신·매수/매도 추천 금지, 사실·근거 중심. 투자 조언 아닌 정보.\n"
        f"takes 배열은 정확히 {len(sections)}개, 섹션 순서와 동일하게.\n\n"
        "오늘의 지표:\n" + "\n".join(lines)
    )
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            resp = json.loads(r.read().decode("utf-8"))
        text = resp["content"][0]["text"]
        s = text.find("{"); e = text.rfind("}")
        data = json.loads(text[s:e+1])
        takes = data["takes"]; themes_ai = data["themes"]
        if (isinstance(takes, list) and len(takes) == len(sections)
                and isinstance(themes_ai, list) and len(themes_ai) >= 3):
            return data["summary"], takes, themes_ai[:3]
    except Exception as ex:
        print("AI 코멘트 실패(폴백 사용):", ex)
    return None

ai = enhance_with_ai(sections)
if ai:
    summary, takes, themes = ai[0], ai[1], ai[2]
    for i, s in enumerate(sections):
        s["take"] = takes[i]
    sources = "Yahoo Finance (시세) · Claude Haiku (코멘트)"
    print("AI 코멘트 적용됨")

# ---------- 안전장치 & 저장 ----------
if len(sections) < 4:
    import sys
    print(f"ERROR: 수집된 섹션 {len(sections)}개 — 데이터 수집 실패로 판단, brief.json 유지하고 종료.")
    sys.exit(1)

brief = {"dateLabel": date_label, "summary": summary,
         "sections": sections, "themes": themes, "sources": sources}
with open("brief.json", "w", encoding="utf-8") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)
print("brief.json 생성 완료:", date_label, "| 섹션", len(sections), "개 |", sources)
