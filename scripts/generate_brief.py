#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모닝 브리프 자동 생성 스크립트 (데이터 버전)
- 무료 시세(Yahoo Finance)로 지수/원자재/환율/국내지수를 수집
- 앱이 읽는 brief.json 스키마로 저장
- GitHub Actions에서 매일 실행됨 (데스크톱 불필요)
"""
import json, datetime
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
    """마지막 종가와 전일 대비 등락률(%) 반환. 실패 시 None."""
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

def pct(x):
    return f"{x:+.2f}%"

def num(x, d=0):
    return f"{x:,.{d}f}"

def updown(x, up="상승", down="하락", flat="보합"):
    return up if x > 0.15 else (down if x < -0.15 else flat)

# ---------- 데이터 수집 ----------
sp   = quote("^GSPC")   # S&P500
ndq  = quote("^IXIC")   # 나스닥
dji  = quote("^DJI")    # 다우
tnx  = quote("^TNX")    # 미 10년물 금리
wti  = quote("CL=F")    # WTI 유가
gold = quote("GC=F")    # 금
dxy  = quote("DX-Y.NYB")# 달러인덱스
krw  = quote("KRW=X")   # 원/달러
eur  = quote("EURUSD=X")# 유로/달러
jpy  = quote("JPY=X")   # 달러/엔
soxx = quote("SOXX")    # 반도체 ETF
kospi= quote("^KS11")   # 코스피
kosdaq=quote("^KQ11")   # 코스닥

def y10():
    if not tnx: return None
    v = tnx[0]
    return v/10.0 if v > 20 else v   # ^TNX가 10배로 오는 경우 보정

# ---------- 섹션 텍스트 ----------
sections = []

# 미국 증시
if sp and ndq and dji:
    body = f"S&P500 {num(sp[0],0)}({pct(sp[1])}), 나스닥 {num(ndq[0],0)}({pct(ndq[1])}), 다우 {num(dji[0],0)}({pct(dji[1])})."
    if sp[1] > 0:
        take = "위험선호가 회복된 흐름 — 실적 견고한 대형주 중심으로 접근, 과열 구간은 분할 관점."
    else:
        take = "위험회피 흐름 — 현금·우량주 비중과 분할 대응 관점 유지, 감정적 추격매매 자제."
    sections.append({"icon":"🇺🇸","title":"미국 증시","body":body,"take":take})

# 금리 / Fed
y = y10()
if y is not None:
    d = tnx[1] if tnx else 0
    body = f"미 10년물 국채금리 {y:.2f}%({pct(d)}). 금리 방향이 성장주 밸류에이션의 핵심 변수."
    take = ("금리 상승 국면 — 고PER 성장주엔 역풍, 현금흐름·가격전가력 있는 기업이 상대적으로 유리."
            if d > 0 else
            "금리 안정/하락은 성장주에 우호적 — 다만 배경(경기둔화 여부)도 함께 확인.")
    sections.append({"icon":"🏦","title":"금리 / Fed","body":body,"take":take})

# 원자재
if wti and gold:
    body = f"WTI 유가 ${num(wti[0],1)}({pct(wti[1])}), 금 ${num(gold[0],0)}({pct(gold[1])})."
    take = ("유가 상승은 인플레·금리 경로를 자극 — 정유·에너지 단기 수혜, 금은 실질금리 방향 확인."
            if wti[1] > 0 else
            "유가 안정은 인플레 압력 완화 요인 — 금리·성장주에 우호적일 수 있음.")
    sections.append({"icon":"🛢️","title":"원자재 (유가·금)","body":body,"take":take})

# 환율
if krw:
    parts = [f"원/달러 {num(krw[0],1)}원({pct(krw[1])})"]
    if dxy: parts.append(f"달러인덱스 {num(dxy[0],1)}")
    if eur: parts.append(f"유로 {eur[0]:.4f}")
    body = " · ".join(parts) + "."
    take = ("원화 약세 국면 — 수입 비중 큰 사업엔 원가 부담, 수출주엔 유리. 환헤지·타이밍 주의."
            if krw[1] > 0 else
            "원화 강세 국면 — 외국인 수급엔 우호적, 수출주엔 부담. 방향 단기 주시.")
    sections.append({"icon":"💱","title":"환율","body":body,"take":take})

# 섹터 포커스 — 반도체
if soxx:
    body = f"미 반도체 ETF(SOXX) {pct(soxx[1])}. 반도체가 시장 방향을 주도하는 국면."
    take = ("반도체 강세 — AI 인프라 수요가 뒷받침, 대장주 중심 옥석 가리기."
            if soxx[1] > 0 else
            "반도체 약세 — 매크로發 조정인지 실적 훼손인지 구분, 과매도 시 우량주 분할 관점.")
    sections.append({"icon":"🔧","title":"섹터 포커스 — 반도체","body":body,"take":take})

# 국내 증시
if kospi:
    parts = [f"코스피 {num(kospi[0],0)}({pct(kospi[1])})"]
    if kosdaq: parts.append(f"코스닥 {num(kosdaq[0],1)}({pct(kosdaq[1])})")
    body = " · ".join(parts) + "."
    take = ("반등/강세 구간 — 개별 우량주 밸류·수급 확인하며 대응."
            if kospi[1] > 0 else
            "약세 구간 — 지수 추종보다 개별 우량주 밸류·수급 점검, 현금 여력 확인.")
    sections.append({"icon":"🇰🇷","title":"국내 증시","body":body,"take":take})

# ---------- 요약 ----------
if sp:
    summary = (f"간밤 미국 증시는 {updown(sp[1])} 마감(S&P500 {pct(sp[1])}). "
               + (f"유가 {updown(wti[1],'급등','하락','보합')}, " if wti else "")
               + (f"원/달러 {updown(krw[1],'상승','하락','보합')}. " if krw else "")
               + "주요 지표를 아래에 정리했습니다.")
else:
    summary = "시세 데이터를 수집했습니다. 아래 지표를 확인하세요."

# ---------- 테마 (데이터 기반 상위 3개) ----------
cands = []
if wti:  cands.append((abs(wti[1]),  {"title":f"유가 {updown(wti[1],'급등','하락','보합')}",
                                       "detail":f"WTI {pct(wti[1])} — 인플레·금리·에너지주에 파급."}))
if soxx: cands.append((abs(soxx[1]), {"title":f"반도체 {updown(soxx[1],'강세','약세','보합')}",
                                       "detail":f"SOXX {pct(soxx[1])} — 시장 방향을 좌우하는 핵심 섹터."}))
if krw:  cands.append((abs(krw[1]),  {"title":f"원화 {updown(krw[1],'약세','강세','보합')}",
                                       "detail":f"원/달러 {pct(krw[1])} — 수급·수출입에 영향."}))
if gold: cands.append((abs(gold[1]), {"title":f"금 {updown(gold[1],'상승','하락','보합')}",
                                       "detail":f"금 {pct(gold[1])} — 안전자산·실질금리 시그널."}))
cands.sort(key=lambda t: t[0], reverse=True)
themes = [c[1] for c in cands[:3]]
while len(themes) < 3:
    themes.append({"title":"시장 점검","detail":"주요 지표 흐름을 확인하세요."})

# 안전장치: 데이터 수집이 부실하면 기존 brief.json을 덮어쓰지 않고 실패 처리
if len(sections) < 4:
    import sys
    print(f"ERROR: 수집된 섹션 {len(sections)}개 — 데이터 수집 실패로 판단, brief.json 유지하고 종료.")
    sys.exit(1)

brief = {
    "dateLabel": date_label,
    "summary": summary,
    "sections": sections,
    "themes": themes,
    "sources": "Yahoo Finance (자동 수집)"
}

with open("brief.json", "w", encoding="utf-8") as f:
    json.dump(brief, f, ensure_ascii=False, indent=2)

print("brief.json 생성 완료:", date_label, "| 섹션", len(sections), "개")
