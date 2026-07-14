#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모닝 브리프 자동 생성 (시세 + AI 코멘트 + 핵심 뉴스 20+20)
- 시세: Yahoo Finance (무료)
- AI 코멘트 & 뉴스: ANTHROPIC_API_KEY 있으면 Claude(웹검색)로 생성, 없으면 규칙 기반/뉴스 생략
- GitHub Actions에서 매일 실행
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
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"

def quote(t):
    if yf is None: return None
    try:
        c = yf.Ticker(t).history(period="7d")["Close"].dropna()
        if len(c) < 2: return None
        return float(c.iloc[-1]), (float(c.iloc[-1])-float(c.iloc[-2]))/float(c.iloc[-2])*100
    except Exception:
        return None

def pct(x): return f"{x:+.2f}%"
def num(x,d=0): return f"{x:,.{d}f}"
def ud(x,u="상승",d="하락",f="보합"): return u if x>0.15 else (d if x<-0.15 else f)

# ---------- 시세 ----------
sp=quote("^GSPC"); ndq=quote("^IXIC"); dji=quote("^DJI"); tnx=quote("^TNX")
wti=quote("CL=F"); gold=quote("GC=F"); dxy=quote("DX-Y.NYB"); krw=quote("KRW=X")
eur=quote("EURUSD=X"); soxx=quote("SOXX"); kospi=quote("^KS11"); kosdaq=quote("^KQ11")
def y10():
    if not tnx: return None
    return tnx[0]/10.0 if tnx[0]>20 else tnx[0]

sections=[]
if sp and ndq and dji:
    sections.append({"icon":"🇺🇸","title":"미국 증시",
        "body":f"S&P500 {num(sp[0])}({pct(sp[1])}), 나스닥 {num(ndq[0])}({pct(ndq[1])}), 다우 {num(dji[0])}({pct(dji[1])}).",
        "take":("위험선호 회복 — 실적 견고한 대형주 중심, 과열은 분할." if sp[1]>0 else "위험회피 — 현금·우량주 비중, 추격매매 자제.")})
y=y10()
if y is not None:
    d=tnx[1] if tnx else 0
    sections.append({"icon":"🏦","title":"금리 / Fed",
        "body":f"미 10년물 국채금리 {y:.2f}%({pct(d)}). 금리 방향이 밸류에이션의 핵심 변수.",
        "take":("금리 상승 — 고PER 성장주 역풍, 현금흐름 우량주 유리." if d>0 else "금리 안정/하락은 성장주에 우호적 — 배경 확인.")})
if wti and gold:
    sections.append({"icon":"🛢️","title":"원자재 (유가·금)",
        "body":f"WTI ${num(wti[0],1)}({pct(wti[1])}), 금 ${num(gold[0])}({pct(gold[1])}).",
        "take":("유가 상승은 인플레·금리 자극 — 에너지 수혜, 금은 실질금리 확인." if wti[1]>0 else "유가 안정은 인플레 완화 — 금리·성장주 우호적.")})
if krw:
    p=[f"원/달러 {num(krw[0],1)}원({pct(krw[1])})"]
    if dxy: p.append(f"달러인덱스 {num(dxy[0],1)}")
    if eur: p.append(f"유로 {eur[0]:.4f}")
    sections.append({"icon":"💱","title":"환율","body":" · ".join(p)+".",
        "take":("원화 약세 — 수입 원가 부담, 수출주 유리." if krw[1]>0 else "원화 강세 — 외국인 수급 우호, 수출주 부담.")})
if soxx:
    sections.append({"icon":"🔧","title":"섹터 포커스 — 반도체",
        "body":f"미 반도체 ETF(SOXX) {pct(soxx[1])}. 반도체가 시장 방향을 주도.",
        "take":("반도체 강세 — AI 수요 뒷받침, 대장주 옥석 가리기." if soxx[1]>0 else "반도체 약세 — 매크로/실적 구분, 과매도 시 분할 관점.")})
if kospi:
    p=[f"코스피 {num(kospi[0])}({pct(kospi[1])})"]
    if kosdaq: p.append(f"코스닥 {num(kosdaq[0],1)}({pct(kosdaq[1])})")
    sections.append({"icon":"🇰🇷","title":"국내 증시","body":" · ".join(p)+".",
        "take":("강세 — 개별 우량주 밸류·수급 확인." if kospi[1]>0 else "약세 — 개별 우량주 점검, 현금 여력 확인.")})

# ---------- 규칙 기반 요약/테마 (폴백) ----------
summary = ((f"간밤 미국 증시는 {ud(sp[1])} 마감(S&P500 {pct(sp[1])}). " if sp else "")
           + (f"유가 {ud(wti[1],'급등','하락','보합')}, " if wti else "")
           + (f"원/달러 {ud(krw[1],'상승','하락','보합')}. " if krw else "")
           + "주요 지표와 핵심 뉴스를 아래에 정리했습니다.") or "시세 데이터를 정리했습니다."
cands=[]
if wti:  cands.append((abs(wti[1]),{"title":f"유가 {ud(wti[1],'급등','하락','보합')}","detail":f"WTI {pct(wti[1])} — 인플레·금리·에너지주 파급."}))
if soxx: cands.append((abs(soxx[1]),{"title":f"반도체 {ud(soxx[1],'강세','약세','보합')}","detail":f"SOXX {pct(soxx[1])} — 시장 방향 핵심 섹터."}))
if krw:  cands.append((abs(krw[1]),{"title":f"원화 {ud(krw[1],'약세','강세','보합')}","detail":f"원/달러 {pct(krw[1])} — 수급·수출입 영향."}))
if gold: cands.append((abs(gold[1]),{"title":f"금 {ud(gold[1],'상승','하락','보합')}","detail":f"금 {pct(gold[1])} — 안전자산·실질금리 시그널."}))
cands.sort(key=lambda t:t[0],reverse=True)
themes=[c[1] for c in cands[:3]]
while len(themes)<3: themes.append({"title":"시장 점검","detail":"주요 지표 흐름을 확인하세요."})
sources="Yahoo Finance (자동 수집)"
news_global=[]; news_korea=[]

# ---------- Anthropic API 공통 호출 ----------
def call_claude(payload):
    body=json.dumps(payload).encode("utf-8")
    req=urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key":API_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp=json.loads(r.read().decode("utf-8"))
    return "".join(b.get("text","") for b in resp.get("content",[]) if b.get("type")=="text")

def extract_json(text):
    s=text.find("{"); e=text.rfind("}")
    return json.loads(text[s:e+1])

# ---------- AI 코멘트 ----------
if API_KEY and len(sections)>=4:
    try:
        lines=[f"{i}. {s['title']}: {s['body']}" for i,s in enumerate(sections)]
        prompt=("48세 개인투자자(가치·성장주, 숫자·논리 중심)를 위한 한국어 아침 브리핑. 아래 지표로 JSON만 출력.\n"
                "{\"summary\":\"2문장 요약\",\"takes\":[섹션 수만큼 1줄 시사점],\"themes\":[{\"title\":\"\",\"detail\":\"\"} 3개]}\n"
                "과도한 확신·매수/매도 추천 금지, 사실·근거 중심. 투자 조언 아닌 정보.\n"
                f"takes는 정확히 {len(sections)}개, 섹션 순서 동일.\n\n지표:\n"+"\n".join(lines))
        data=extract_json(call_claude({"model":MODEL,"max_tokens":1200,
            "messages":[{"role":"user","content":prompt}]}))
        if len(data["takes"])==len(sections) and len(data["themes"])>=3:
            summary=data["summary"]
            for i,s in enumerate(sections): s["take"]=data["takes"][i]
            themes=data["themes"][:3]
            sources="Yahoo Finance (시세) · Claude (코멘트·뉴스)"
    except Exception as ex:
        print("AI 코멘트 실패(폴백):",ex)

# ---------- AI 뉴스 (웹검색) ----------
if API_KEY:
    try:
        prompt=(f"오늘({now:%Y-%m-%d}) 웹을 검색해 개인투자자에게 중요한 시장·경제 뉴스를 정리하라.\n"
                "해외(글로벌) 핵심 뉴스 20개, 국내(한국) 핵심 뉴스 20개. 정말 중요하면 각 20개를 넘겨도 된다.\n"
                "미국 증시·금리/Fed·섹터·원자재·환율 및 한국 증시/경제 이슈 위주. 단순 정치·연예 뉴스 제외.\n"
                "해외 뉴스도 제목은 한국어로. 각 항목: title(한 줄), source(매체명), take(투자 시사점 한 줄).\n"
                "해외 매체(Bloomberg/Reuters/WSJ/FT/CNBC) 우선. JSON만 출력:\n"
                "{\"newsGlobal\":[{\"title\":\"\",\"source\":\"\",\"take\":\"\"}],\"newsKorea\":[{...}]}")
        text=call_claude({"model":MODEL,"max_tokens":8000,
            "tools":[{"type":"web_search_20250305","name":"web_search","max_uses":8}],
            "messages":[{"role":"user","content":prompt}]})
        nd=extract_json(text)
        ng=nd.get("newsGlobal",[]); nk=nd.get("newsKorea",[])
        clean=lambda arr:[{"title":x.get("title","").strip(),"source":x.get("source","").strip(),
                           "take":x.get("take","").strip()} for x in arr if x.get("title")]
        news_global=clean(ng); news_korea=clean(nk)
        print(f"뉴스 수집: 해외 {len(news_global)} · 국내 {len(news_korea)}")
        if news_global or news_korea:
            sources="Yahoo Finance (시세) · Claude (코멘트·뉴스)"
    except Exception as ex:
        print("AI 뉴스 실패(생략):",ex)

# ---------- 안전장치 & 저장 ----------
if len(sections)<4:
    import sys
    print(f"ERROR: 섹션 {len(sections)}개 — 데이터 수집 실패, brief.json 유지하고 종료."); sys.exit(1)

brief={"dateLabel":date_label,"summary":summary,"sections":sections,"themes":themes,
       "newsGlobal":news_global,"newsKorea":news_korea,"sources":sources}
with open("brief.json","w",encoding="utf-8") as f:
    json.dump(brief,f,ensure_ascii=False,indent=2)
print("brief.json 완료:",date_label,"| 섹션",len(sections),"| 해외뉴스",len(news_global),"| 국내뉴스",len(news_korea))
