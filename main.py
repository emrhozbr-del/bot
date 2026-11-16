# ==============================================================================
# ALFA TRADE CLUB (v6.0.1-Mod2Fix) — NATIVE ANDROID APK (FLET)
# ==============================================================================
import os, sys, gc, json, re, tempfile, base64 as _b64, io as _io, subprocess as _subp, webbrowser
from pathlib import Path
from datetime import datetime
import time, threading
import requests
import flet as ft

# --- ANDROID APK ICIN SAF PYTHON NUMPY, PANDAS VE CCXT EMULATORU ---
class _MiniArray(list):
    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        return _MiniArray(res) if isinstance(idx, slice) else res
    def argmax(self):
        if not self:
            return 0
        return max(range(len(self)), key=lambda i: self[i])
    def argmin(self):
        if not self:
            return 0
        return min(range(len(self)), key=lambda i: self[i])
    def max(self):
        return max(self) if self else 0.0
    def min(self):
        return min(self) if self else 0.0
    def astype(self, t=float):
        return _MiniArray([t(x) for x in self])

class _NumpyMock:
    nan = float('nan')
    integer = int
    def array(self, x, *a, **kw):
        return _MiniArray(x)
    def arange(self, n):
        return list(range(int(n)))
np = _NumpyMock()

class _MiniSeries:
    def __init__(self, data):
        self._d = [float(x) if x is not None and x == x else float('nan') for x in data]
    def __len__(self): return len(self._d)
    def __iter__(self): return iter(self._d)
    @property
    def empty(self): return len(self._d) == 0
    @property
    def values(self): return _MiniArray(self._d)
    @property
    def iloc(self): return self
    def __getitem__(self, idx):
        if isinstance(idx, slice): return _MiniSeries(self._d[idx])
        if isinstance(idx, _MiniSeries): return _MiniSeries([v for v, b in zip(self._d, idx._d) if b])
        return self._d[idx]
    def to_numpy(self, dtype=float, copy=False): return _MiniArray(self._d)
    def astype(self, t=float): return _MiniSeries([t(x) if x == x else float('nan') for x in self._d])
    def _op(self, o, fn):
        if isinstance(o, _MiniSeries): return _MiniSeries([fn(a, b) for a, b in zip(self._d, o._d)])
        return _MiniSeries([fn(a, float(o)) for a in self._d])
    def __sub__(self, o): return self._op(o, lambda a, b: a - b)
    def __add__(self, o): return self._op(o, lambda a, b: a + b)
    def __mul__(self, o): return self._op(o, lambda a, b: a * b)
    def __truediv__(self, o): return self._op(o, lambda a, b: a / b if b != 0 else float('nan'))
    def __rtruediv__(self, o): return _MiniSeries([float(o) / a if a != 0 else float('nan') for a in self._d])
    def __radd__(self, o): return _MiniSeries([float(o) + a for a in self._d])
    def __rsub__(self, o): return _MiniSeries([float(o) - a for a in self._d])
    def __rmul__(self, o): return _MiniSeries([float(o) * a for a in self._d])
    def __neg__(self): return _MiniSeries([-a for a in self._d])
    def __gt__(self, o): return self._op(o, lambda a, b: a > b)
    def __lt__(self, o): return self._op(o, lambda a, b: a < b)
    def __ge__(self, o): return self._op(o, lambda a, b: a >= b)
    def __le__(self, o): return self._op(o, lambda a, b: a <= b)
    def abs(self): return _MiniSeries([abs(a) for a in self._d])
    def diff(self): return _MiniSeries([float('nan')] + [self._d[i] - self._d[i-1] for i in range(1, len(self._d))])
    def shift(self, n=1): return _MiniSeries([float('nan')]*n + self._d[:-n] if n > 0 else self._d)
    def where(self, cond, other=0.0): return _MiniSeries([a if c else float(other) for a, c in zip(self._d, cond._d)])
    def replace(self, old, new): return _MiniSeries([new if a == old else a for a in self._d])
    def fillna(self, val): return _MiniSeries([float(val) if (a != a or a is None) else a for a in self._d])
    def bfill(self):
        out = list(self._d); last = 0.0
        for i in range(len(out)-1, -1, -1):
            if out[i] == out[i]: last = out[i]
            else: out[i] = last
        return _MiniSeries(out)
    def rolling(self, w):
        d = self._d
        class _Roll:
            def mean(s_self):
                out = []
                for i in range(len(d)):
                    seg = [x for x in d[max(0, i-w+1):i+1] if x == x]
                    out.append(sum(seg)/len(seg) if seg else float('nan'))
                return _MiniSeries(out)
        return _Roll()
    def cumsum(self):
        out, s = [], 0.0
        for a in self._d:
            if a == a: s += a
            out.append(s)
        return _MiniSeries(out)
    def min(self):
        v = [a for a in self._d if a == a]
        return min(v) if v else 0.0
    def max(self):
        v = [a for a in self._d if a == a]
        return max(v) if v else 0.0
    def mean(self):
        v = [a for a in self._d if a == a]
        return sum(v)/len(v) if v else 0.0
    def idxmin(self):
        v = [(a, i) for i, a in enumerate(self._d) if a == a]
        return min(v)[1] if v else 0
    def idxmax(self):
        v = [(a, i) for i, a in enumerate(self._d) if a == a]
        return max(v)[1] if v else 0

class _MiniDF:
    def __init__(self, rows=None, columns=None):
        self.columns = list(columns or ['timestamp','open','high','low','close','volume'])
        self._data = {c: [] for c in self.columns}
        if isinstance(rows, dict):
            for c in self.columns: self._data[c] = list(rows.get(c, []))
        elif isinstance(rows, list):
            for r in rows:
                for i, c in enumerate(self.columns):
                    self._data[c].append(float(r[i]) if i < len(r) else 0.0)
    def copy(self):
        df = _MiniDF(columns=self.columns)
        for c in self.columns: df._data[c] = list(self._data[c])
        return df
    def __len__(self): return len(self._data[self.columns[0]]) if self.columns else 0
    @property
    def empty(self): return len(self) == 0
    def get(self, key, default=None):
        if key in self._data: return _MiniSeries(self._data[key])
        return default
    def __getitem__(self, key):
        if isinstance(key, str): return _MiniSeries(self._data[key])
        if isinstance(key, list):
            df = _MiniDF(columns=key)
            for c in key: df._data[c] = list(self._data[c])
            return df
        if isinstance(key, _MiniSeries):
            idxs = [i for i, b in enumerate(key._d) if b]
            df = _MiniDF(columns=self.columns)
            for c in self.columns: df._data[c] = [self._data[c][i] for i in idxs]
            return df
        return None
    def __setitem__(self, key, val):
        if key not in self.columns: self.columns.append(key)
        self._data[key] = list(val._d if isinstance(val, _MiniSeries) else val)
        if '_np_c' in self.__dict__: self.__dict__['_np_c'].pop(key, None)
    @property
    def iloc(self):
        parent = self
        class _Iloc:
            def __getitem__(s_self, idx):
                if isinstance(idx, int):
                    i = idx if idx >= 0 else len(parent) + idx
                    return {c: parent._data[c][i] for c in parent.columns}
                if isinstance(idx, slice):
                    df = _MiniDF(columns=parent.columns)
                    for c in parent.columns: df._data[c] = parent._data[c][idx]
                    return df
        return _Iloc()
    def reset_index(self, drop=True): return self.copy()
    def iterrows(self):
        for i in range(len(self)):
            yield i, {c: self._data[c][i] for c in self.columns}
    def max(self, axis=1):
        n = len(self)
        return _MiniSeries([max(self._data[c][i] for c in self.columns) for i in range(n)])
    def min(self, axis=1):
        n = len(self)
        return _MiniSeries([min(self._data[c][i] for c in self.columns) for i in range(n)])

class _PandasMock:
    DataFrame = _MiniDF
    Series = _MiniSeries
    def concat(self, objs, axis=1):
        df = _MiniDF(columns=[str(i) for i in range(len(objs))])
        for i, s in enumerate(objs): df[str(i)] = s
        return df
    def to_datetime(self, s, unit='ms', utc=True): raise Exception("skip_dt")
pd = _PandasMock()

class _BinanceLite:
    def __init__(self, cfg=None):
        cfg = cfg or {}
        self.apiKey = cfg.get('apiKey', '')
        self.secret = cfg.get('secret', '')
        self.defaultType = cfg.get('options', {}).get('defaultType', 'future')
        self.sandbox = False
    def set_sandbox_mode(self, v): self.sandbox = bool(v)
    def enable_demo_trading(self, v): self.sandbox = bool(v)
    def _base(self):
        if self.defaultType == 'future':
            return 'https://testnet.binancefuture.com' if self.sandbox else 'https://fapi.binance.com'
        return 'https://testnet.binance.vision' if self.sandbox else 'https://api.binance.com'
    def load_markets(self, reload=False):
        url = f"{self._base()}/{'fapi/v1/exchangeInfo' if self.defaultType=='future' else 'api/v3/exchangeInfo'}"
        r = requests.get(url, timeout=10).json()
        out = {}
        for s in r.get('symbols', []):
            if s.get('quoteAsset') != 'USDT': continue
            sym = f"{s['baseAsset']}/USDT"
            out[sym] = {'id': s['symbol'], 'base': s['baseAsset'], 'quote': 'USDT', 'active': s.get('status')=='TRADING', 'spot': self.defaultType!='future', 'future': self.defaultType=='future', 'swap': self.defaultType=='future', 'linear': True, 'info': s}
        return out
    def fetch_tickers(self):
        url = f"{self._base()}/{'fapi/v1/ticker/24hr' if self.defaultType=='future' else 'api/v3/ticker/24hr'}"
        r = requests.get(url, timeout=10).json()
        out = {}
        if isinstance(r, list):
            for t in r:
                s = t.get('symbol', '')
                if s.endswith('USDT'):
                    sym = f"{s[:-4]}/USDT"
                    out[sym] = {'quoteVolume': float(t.get('quoteVolume') or 0.0), 'last': float(t.get('lastPrice') or 0.0)}
        return out
    def fetch_ticker(self, symbol):
        raw = symbol.split(':')[0].replace('/', '')
        url = f"{self._base()}/{'fapi/v1/ticker/price' if self.defaultType=='future' else 'api/v3/ticker/price'}?symbol={raw}"
        r = requests.get(url, timeout=5).json()
        p = float(r.get('price') or 0.0)
        return {'last': p, 'close': p, 'info': r}
    def fetch_ohlcv(self, symbol, timeframe='15m', limit=300):
        raw = symbol.split(':')[0].replace('/', '')
        url = f"{self._base()}/{'fapi/v1/klines' if self.defaultType=='future' else 'api/v3/klines'}?symbol={raw}&interval={timeframe}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        return [[float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in r]
    def amount_to_precision(self, symbol, amount): return round(float(amount), 5)
    def price_to_precision(self, symbol, price): return round(float(price), 6)
    def fetch_balance(self): return {'USDT': {'free': 0.0, 'total': 0.0}}
    def set_leverage(self, lev, symbol): pass
    def set_margin_mode(self, mode, symbol): pass
    def cancel_all_orders(self, symbol): pass
    def create_market_buy_order(self, symbol, amount, params=None): pass
    def create_market_sell_order(self, symbol, amount, params=None): pass
    def create_order(self, symbol, type, side, amount, price=None, params=None): pass

class _CCXTMock:
    binance = _BinanceLite
ccxt = _CCXTMock()

_HTTP_SES = requests.Session()
F, I, R, X, M, N, L, A, G = (float, isinstance, round, Exception, max, min, len, abs, range)
jC, aR, cR, eD = (('Segoe UI', 10, 'bold'), ('Segoe UI', 11, 'bold'), ('Segoe UI', 12, 'bold'), ('Segoe UI', 13, 'bold'))

def _f(d,c,i=-2):
 try:
  m=d.__dict__.get('_np_c')
  if m is None:m={};d.__dict__['_np_c']=m
  a=m.get(c)
  if a is None:
   if c not in d.columns:return 0.0
   a=d[c].to_numpy(dtype=F,copy=False);m[c]=a
  v=F(a[i])
  return 0.0 if v!=v else v
 except X:return 0.0
def _r(r,*cs):
 return tuple((F(r[c])for c in cs))
PIYASA_MODU='her_ikisi';TESTNET_AKTIF=True;KALDIRAC=10;MARJIN_TIPI='ISOLATED';cQ=True;ae=0;bH=150000.0;bs=1000.0;dd=0.01;ISLEM_BASI_RISK_USDT=1.0;dL=2.0;RISK_ODUL_ORANI=3.0;NIHAI_TP_RR=4.0;KISMI_KAR_AL_AKTIF=True;TOPLAM_KAR_KAPAT_USDT=None;MAKS_MARJIN_USDT=100.0;aW=0.0018;a4=6;MAKS_ACIK_ISLEM=6;MIN_CONFLUENCE_SKORU=70;dM=5.5;bI=True;dj=14;eC=1.5;MTF_SABLONLARI={'4h / 1h / 15m (Swing)':('4h','1h','15m'),'4h / 1h / 5m (Alfa Pine MTF)':('4h','1h','5m'),'4h / 30m / 3m (Sniper)':('4h','30m','3m'),'1d / 2h / 15m (Pozisyon)':('1d','2h','15m'),'1d / 1h / 5m (Günlük MTF)':('1d','1h','5m'),'1M / 2h / 15m (Aylık Macro)':('1M','2h','15m'),'1d / 4h / 1h (Pozisyon)':('1d','4h','1h'),'2h / 30m / 5m (Gün İçi)':('2h','30m','5m'),'1h / 15m / 5m (Intraday)':('1h','15m','5m'),'15m / 5m / 1m (Scalp)':('15m','5m','1m')};AKTIF_MTF_SABLONU='1h / 15m / 5m (Intraday)';HTF_ZAMAN_DILIMLERI=['1h','4h','1d','1M'];MTF_ZAMAN_DILIMLERI=['15m','30m','1h','2h'];LTF_ZAMAN_DILIMLERI=['5m','15m','3m'];TUM_ZAMAN_DILIMLERI=['1m','3m','5m','15m','30m','1h','2h','4h','6h','12h','1d','1M'];HTF_PERIYOT='1h';MTF_PERIYOT='15m';LTF_PERIYOT='5m';SWING_PENCERE=5;RISK_SEVIYESI_SECENEKLERI={'Düşük Risk (Skor 80+ | 0.75x)':(80,0.75),'Orta Risk (Skor 70+ | 1.0x)':(70,1.0),'Yüksek Risk (Skor 60+ | 1.35x)':(60,1.35),'Agresif Risk (Skor 50+ | 1.75x)':(50,1.75),'Özel (Manuel Skor & Risk)':(MIN_CONFLUENCE_SKORU,1.0)};AKTIF_RISK_SEVIYESI='Orta Risk (Skor 70+ | 1.0x)';RISK_CARPANI=1.0;ISLEM_TARZI_MODU='DayTrade';STOP_BELIRLEME_SECENEKLERI=['HTF Yapıya Göre (Dip/Tepe & OB)','LTF Yapıya Göre (Kırılım/Mum & POI)','Otomatik (Duruma Göre HTF/LTF)'];STOP_BELIRLEME_MODU='LTF Yapıya Göre (Kırılım/Mum & POI)';GIRIS_MODU_SECENEKLERI=['1. Mod: Sadece Fresh Arz/Talep, OB, OTE, QML','2. Mod: Tüm Öğrenilen Giriş Yerleri'];GIRIS_STRATEJI_MODU='1. Mod: Sadece Fresh Arz/Talep, OB, OTE, QML';BOT_VERSIYONU='v6.0.1-Mod2Fix';BOT_DOSYA_ADI='botv6.0.1_mod2_duzenlenmis.py';BIRINCIL_BOLGE_OLCEK_CARPANI=5.0;BIRINCIL_VIP_EK_SLOT=0;IKINCIL_REZERV_SLOT=0;GEMINI_API_KEY=os.environ.get('GEMINI_API_KEY',os.environ.get('GOOGLE_API_KEY','')).strip();GEMINI_MODEL='gemini-2.5-flash';GEMINI_MODELLERI=['gemini-2.5-flash','gemini-2.5-pro','gemini-2.0-flash','gemini-1.5-pro'];GEMINI_OTOMATIK_ISLEM_YORUMU=True;KYSY_HTF_ATR_CARPANI=1.85;KYSY_LTF_ATR_CARPANI=1.30;EQH_EQL_TOL_ATR=0.30;SFP_MIN_IGNE_ATR=0.12;IKINCIL_BOLGE_GIRIS_AKTIF=False;gemini_sohbet_gecmisi={};htf_1_oncelik_radar_cache={};
def giris_modu_uygula(secim):
 global GIRIS_STRATEJI_MODU,IKINCIL_BOLGE_GIRIS_AKTIF
 sec_str=str(secim or'').strip()
 if'2. Mod'in sec_str or'Tüm'in sec_str or'İkinci'in sec_str or sec_str=='2':
  GIRIS_STRATEJI_MODU='2. Mod: Tüm Öğrenilen Giriş Yerleri'
  IKINCIL_BOLGE_GIRIS_AKTIF=True
 else:
  GIRIS_STRATEJI_MODU='1. Mod: Sadece Fresh Arz/Talep, OB, OTE, QML'
  IKINCIL_BOLGE_GIRIS_AKTIF=False
 return GIRIS_STRATEJI_MODU
def mtf_sablonu_uygula(aA):
 global AKTIF_MTF_SABLONU,HTF_PERIYOT,MTF_PERIYOT,LTF_PERIYOT,ISLEM_TARZI_MODU,RISK_ODUL_ORANI,NIHAI_TP_RR
 if aA in MTF_SABLONLARI:AKTIF_MTF_SABLONU=aA;HTF_PERIYOT,MTF_PERIYOT,LTF_PERIYOT=MTF_SABLONLARI[aA]
 elif'/'in str(aA):
  of=[p.strip().split()[0]for p in str(aA).split('/')]
  if L(of)==3:AKTIF_MTF_SABLONU=str(aA);HTF_PERIYOT,MTF_PERIYOT,LTF_PERIYOT=(of[0],of[1],of[2])
 if'Scalp'in str(AKTIF_MTF_SABLONU)or LTF_PERIYOT in('1m','3m')or HTF_PERIYOT in('15m','30m'):
  ISLEM_TARZI_MODU='Scalp';RISK_ODUL_ORANI=1.5;NIHAI_TP_RR=2.5
 else:
  ISLEM_TARZI_MODU='DayTrade';RISK_ODUL_ORANI=3.0;NIHAI_TP_RR=4.0
 return(HTF_PERIYOT,MTF_PERIYOT,LTF_PERIYOT)
am=['BTC/USDT','ETH/USDT','SOL/USDT','BNB/USDT','AVAX/USDT','ARB/USDT','LINK/USDT','ADA/USDT','XRP/USDT','DOGE/USDT','SUI/USDT','OP/USDT'];bo={'USDC','FDUSD','TUSD','BUSD','DAI','USDP','EUR','AEUR','USDT','UST','USTC','PAXG','WBTC','BTCST','USD1','RLUSD','USDE','PYUSD','USDD','FRAX','LUSD','GUSD','XAU'};API_KEY=os.environ.get('BINANCE_API_KEY','').strip();API_SECRET=os.environ.get('BINANCE_API_SECRET','').strip();TELEGRAM_AKTIF=True;TELEGRAM_TOKEN=os.environ.get('TELEGRAM_BOT_TOKEN','').strip();TELEGRAM_CHAT_ID=os.environ.get('TELEGRAM_CHAT_ID','').strip();ab=[];bk=list(am);acik_islemler={};a1={};analiz_hafizasi={};an={'1h':{},'15m':{}};S=bs;aQ=0.0;T=0.0;V=0.0;ay=0.0;aq=0.0;W=0.0;lG=0.0;bot_calisiyor=False;bE=0;au=0;aC=None;aw=None;aG=None;ao=None;cm=None;
def borsa_kur(b6=PIYASA_MODU,hj=TESTNET_AKTIF):
 global aC,aw,aG,ao,cm,PIYASA_MODU,TESTNET_AKTIF;PIYASA_MODU,TESTNET_AKTIF=(b6,hj)
 def _mk(t,o8=False):
  qX={'enableRateLimit':True,'timeout':15000,'options':{'defaultType':t,'fetchCurrencies':False,'adjustForTimeDifference':True}}
  if o8:qX.update({'apiKey':API_KEY,'secret':API_SECRET})
  return ccxt.binance(qX)
 aC,aw,aG,ao=(_mk('spot'),_mk('future'),_mk('spot',True),_mk('future',True))
 if TESTNET_AKTIF:
  for fn in[lambda:aG.set_sandbox_mode(True),lambda:ao.enable_demo_trading(True)if hasattr(ao,'enable_demo_trading')else None]:
   try:fn()
   except X:pass
 cm=aC if b6=='spot'else aw;return(aG,ao)
def borsa_baglantisi_olustur(dk='future'):
 borsa_kur(dk,TESTNET_AKTIF);return cm
def _yazilabilir_calisma_dizini():
 adaylar=[]
 for _ek in ('FLET_APP_STORAGE_DATA','ANDROID_PRIVATE'):
  if os.environ.get(_ek): adaylar.append(os.environ.get(_ek))
 try:
  if'__file__'in globals()and __file__:adaylar.append(os.path.dirname(os.path.abspath(__file__)))
 except X:pass
 try:adaylar.append(os.getcwd())
 except X:pass
 try:adaylar.append(os.path.join(os.path.expanduser('~'),'AlfaTradeClub'))
 except X:pass
 try:adaylar.append(tempfile.gettempdir())
 except X:pass
 for d_aday in adaylar:
  if not d_aday:continue
  if'program files'in d_aday.lower()or'windows\\system'in d_aday.lower():continue
  try:
   os.makedirs(d_aday,exist_ok=True)
   test_p=os.path.join(d_aday,'.alfa_write_test.tmp')
   with open(test_p,'w',encoding='utf-8')as tf:tf.write('ok')
   try:os.remove(test_p)
   except X:pass
   return d_aday
  except X:continue
 return tempfile.gettempdir()
_BOT_CALISMA_DIZINI=_yazilabilir_calisma_dizini()
try:os.chdir(_BOT_CALISMA_DIZINI)
except X:pass
bd=os.path.join(_BOT_CALISMA_DIZINI,'binance_api_config.json');ap=os.path.join(_BOT_CALISMA_DIZINI,'islem_gecmisi.json');aN=os.path.join(_BOT_CALISMA_DIZINI,'acik_islemler_durum.json');ah=[];
def _api_yukle():
 global API_KEY,API_SECRET,TESTNET_AKTIF,TELEGRAM_TOKEN,TELEGRAM_CHAT_ID,GITHUB_REPO_ADRESI,GITHUB_TOKEN,GEMINI_API_KEY,GEMINI_MODEL,GEMINI_OTOMATIK_ISLEM_YORUMU,KYSY_HTF_ATR_CARPANI,KYSY_LTF_ATR_CARPANI,EQH_EQL_TOL_ATR,SFP_MIN_IGNE_ATR,IKINCIL_BOLGE_GIRIS_AKTIF,BIRINCIL_BOLGE_OLCEK_CARPANI,GIRIS_STRATEJI_MODU,a4,MAKS_ACIK_ISLEM
 try:
  if os.path.exists(bd):
   with open(bd,'r',encoding='utf-8')as f:d=json.load(f)
   API_KEY=str(d.get('api_key',API_KEY)).strip();API_SECRET=str(d.get('api_secret',API_SECRET)).strip()
   if'testnet'in d:TESTNET_AKTIF=bool(d['testnet'])
   TELEGRAM_TOKEN=str(d.get('telegram_token',TELEGRAM_TOKEN)).strip();TELEGRAM_CHAT_ID=str(d.get('telegram_chat_id',TELEGRAM_CHAT_ID)).strip()
   if'github_repo'in d:GITHUB_REPO_ADRESI=str(d.get('github_repo',GITHUB_REPO_ADRESI)).strip()
   if'github_token'in d:GITHUB_TOKEN=str(d.get('github_token',GITHUB_TOKEN)).strip()
   if d.get('gemini_api_key'):GEMINI_API_KEY=str(d.get('gemini_api_key',GEMINI_API_KEY)).strip()
   if d.get('gemini_model'):GEMINI_MODEL=str(d.get('gemini_model',GEMINI_MODEL)).strip()
   if'gemini_oto_yorum'in d:GEMINI_OTOMATIK_ISLEM_YORUMU=bool(d['gemini_oto_yorum'])
   if'kysy_htf_atr'in d:KYSY_HTF_ATR_CARPANI=M(0.6,N(4.0,F(d['kysy_htf_atr'])))
   if'kysy_ltf_atr'in d:KYSY_LTF_ATR_CARPANI=M(0.5,N(3.5,F(d['kysy_ltf_atr'])))
   if'eqh_tol_atr'in d:EQH_EQL_TOL_ATR=M(0.08,N(1.2,F(d['eqh_tol_atr'])))
   if'sfp_min_atr'in d:SFP_MIN_IGNE_ATR=M(0.03,N(0.8,F(d['sfp_min_atr'])))
   if'giris_strateji_modu'in d:giris_modu_uygula(d['giris_strateji_modu'])
   elif'ikincil_bolge_aktif'in d:giris_modu_uygula('2. Mod'if d['ikincil_bolge_aktif']else'1. Mod')
   if'maks_acik_islem'in d:a4=M(1,N(100,int(F(d['maks_acik_islem']))));MAKS_ACIK_ISLEM=a4
   if'birincil_olcek_carpani'in d:BIRINCIL_BOLGE_OLCEK_CARPANI=M(1.5,N(10.0,F(d['birincil_olcek_carpani'])))
 except X:pass
def _api_kaydet_tam():
 try:
  mev={}
  if os.path.exists(bd):
   try:
    with open(bd,'r',encoding='utf-8')as f:mev=json.load(f)
   except X:mev={}
  mev.update({'api_key':API_KEY,'api_secret':API_SECRET,'testnet':TESTNET_AKTIF,'telegram_token':TELEGRAM_TOKEN,'telegram_chat_id':TELEGRAM_CHAT_ID,'github_repo':GITHUB_REPO_ADRESI,'github_token':GITHUB_TOKEN,'stop_modu':STOP_BELIRLEME_MODU,'gemini_api_key':GEMINI_API_KEY,'gemini_model':GEMINI_MODEL,'gemini_oto_yorum':GEMINI_OTOMATIK_ISLEM_YORUMU,'kysy_htf_atr':KYSY_HTF_ATR_CARPANI,'kysy_ltf_atr':KYSY_LTF_ATR_CARPANI,'eqh_tol_atr':EQH_EQL_TOL_ATR,'sfp_min_atr':SFP_MIN_IGNE_ATR,'ikincil_bolge_aktif':IKINCIL_BOLGE_GIRIS_AKTIF,'giris_strateji_modu':GIRIS_STRATEJI_MODU,'maks_acik_islem':a4,'birincil_olcek_carpani':BIRINCIL_BOLGE_OLCEK_CARPANI})
  with open(bd,'w',encoding='utf-8')as f:json.dump(mev,f,ensure_ascii=False,indent=2)
 except X:pass
def _varsayilan_gecmisi_kopyala():
 try:
  if not os.path.exists(ap) and '__file__' in globals() and __file__:
   _kaynak_ap = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'islem_gecmisi.json')
   if os.path.exists(_kaynak_ap) and os.path.abspath(_kaynak_ap) != os.path.abspath(ap):
    with open(_kaynak_ap, 'r', encoding='utf-8') as _f1, open(ap, 'w', encoding='utf-8') as _f2:
     _f2.write(_f1.read())
 except X: pass

def _ig_yukle():
 _varsayilan_gecmisi_kopyala()
 global ah
 try:
  if os.path.exists(ap):
   with open(ap,'r',encoding='utf-8')as f:
    d=json.load(f)
    if I(d,list):ah=d
 except X:pass
_son_acilan_islem_meta_hafizasi={}
_kz_sifirlama_ts=0.0
def _ak_kaydet():
 try:
  nQ={k:v for k,v in acik_islemler.items()if I(v,dict)}
  for k_m,v_m in nQ.items():
   if str(v_m.get('ozet',''))and'[Binance Hesabından Senkronize Edildi]'not in str(v_m.get('ozet','')):
    _son_acilan_islem_meta_hafizasi[k_m]={'ozet':v_m.get('ozet',''),'sl':v_m.get('sl',0.0),'ilk_sl':v_m.get('ilk_sl',0.0),'tp':v_m.get('tp',0.0),'tp_nihai':v_m.get('tp_nihai',0.0),'kaldirac':v_m.get('kaldirac',KALDIRAC),'rontgen':v_m.get('rontgen'),'_acilis_ts':v_m.get('_acilis_ts',time.time())}
  with open(aN,'w',encoding='utf-8')as f:json.dump({'acik_islemler':nQ,'demo_vadeli_bakiye':S,'gerceklesen_pnl':W,'kz_sifirlama_ts':_kz_sifirlama_ts,'meta_hafiza':_son_acilan_islem_meta_hafizasi},f,ensure_ascii=False)
  if 'bulut_durum_gonder' in globals() and GITHUB_TOKEN:
   threading.Thread(target=bulut_durum_gonder, daemon=True).start()
 except X:pass
def _ak_yukle():
 global acik_islemler,S,W,_kz_sifirlama_ts,_son_acilan_islem_meta_hafizasi
 try:
  if os.path.exists(aN):
   with open(aN,'r',encoding='utf-8')as f:d=json.load(f)
   if I(d,dict):
    if I(d.get('acik_islemler'),dict):acik_islemler.update(d['acik_islemler'])
    if'demo_vadeli_bakiye'in d:S=F(d['demo_vadeli_bakiye'])
    if'gerceklesen_pnl'in d:W=F(d['gerceklesen_pnl'])
    if'kz_sifirlama_ts'in d:_kz_sifirlama_ts=F(d['kz_sifirlama_ts']or 0.0)
    if I(d.get('meta_hafiza'),dict):_son_acilan_islem_meta_hafizasi.update(d['meta_hafiza'])
 except X:pass
def _ig_dosya_yaz():
 try:
  with open(ap,'w',encoding='utf-8')as f:json.dump(ah[:500],f,ensure_ascii=False)
 except X:pass
def _ig_kaydet(J,jD,bt,lH,lI,Y,fq,eE,dl,lJ='',rontgen=None,tarih_str=None,binance_tran_id=None,binance_onayli=False):
 global ah;O_sem=f"{('FUT' if jD=='future' else 'SPOT')}:{J.split(':')[0]}"
 if rontgen is None and I(acik_islemler.get(O_sem),dict):rontgen=acik_islemler[O_sem].get('rontgen')
 if rontgen is None and I(_son_acilan_islem_meta_hafizasi.get(O_sem),dict):rontgen=_son_acilan_islem_meta_hafizasi[O_sem].get('rontgen')
 if(not lJ or'[Binance Hesabından Senkronize Edildi]'in str(lJ))and I(_son_acilan_islem_meta_hafizasi.get(O_sem),dict)and _son_acilan_islem_meta_hafizasi[O_sem].get('ozet'):
  lJ=_son_acilan_islem_meta_hafizasi[O_sem]['ozet']
 if binance_tran_id:
  for mev_x in ah:
   if str(mev_x.get('binance_tran_id',''))==str(binance_tran_id)and mev_x.get('sembol')==O_sem:
    mev_x.update({'yon':bt,'giris':R(F(lH),6),'cikis':R(F(lI),6),'miktar':R(F(Y),6),'pnl_usdt':R(F(fq),2),'pnl_yuzde':R(F(eE),2),'binance_onayli':True})
    if tarih_str:mev_x['tarih']=tarih_str
    _ig_dosya_yaz()
    return mev_x
 k={'tarih':tarih_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'sembol':O_sem,'yon':bt,'giris':R(F(lH),6),'cikis':R(F(lI),6),'miktar':R(F(Y),6),'pnl_usdt':R(F(fq),2),'pnl_yuzde':R(F(eE),2),'neden':dl,'model':str(lJ)[:120]}
 if binance_tran_id:k['binance_tran_id']=str(binance_tran_id)
 if binance_onayli:k['binance_onayli']=True
 if I(rontgen,dict):k['rontgen']=rontgen
 ah.insert(0,k)
 _ig_dosya_yaz()
 return k
_api_yukle();_ig_yukle();_ak_yukle();borsa_kur(PIYASA_MODU,TESTNET_AKTIF);
import hmac,hashlib,urllib.parse
_fapi_exinfo_cache={}
_fapi_zaman_farki=0
_fapi_hedge_modu=None
def veri_ist(D):
 return aC if D=='spot'else aw
def emir_ist(D):
 return aG if D=='spot'else ao
def anahtar_yap(J,D):
 return f"{('FUT' if D=='future' else 'SPOT')}:{J.split(':')[0]}"
def _emir_sembolu(ja,J,D='future'):
 baz=str(J or'').split(':')[0].strip()
 if D=='future':
  try:
   mkts=getattr(ja,'markets',None)or getattr(aw,'markets',None)or{}
   if not mkts:
    try:mkts=aw.load_markets()
    except X:mkts={}
   if getattr(ja,'markets',None)is None and mkts:
    try:ja.markets=mkts;ja.markets_by_id=getattr(aw,'markets_by_id',{})
    except X:pass
   aday_f=f"{baz}:USDT"
   if aday_f in mkts:return aday_f
  except X:pass
  return f"{baz}:USDT"if'/'in baz and':'not in str(J)else str(J)
 return baz
def _fapi_imzali_istek(metod,yol,prm=None):
 global _fapi_zaman_farki
 p=dict(prm or{})
 try:
  if _fapi_zaman_farki==0:
   rt=requests.get('https://fapi.binance.com/fapi/v1/time',timeout=5)
   if rt.status_code==200:_fapi_zaman_farki=int(rt.json().get('serverTime',int(time.time()*1000)))-int(time.time()*1000)
 except X:pass
 p['timestamp']=int(time.time()*1000)+int(_fapi_zaman_farki)
 p['recvWindow']=10000
 qs=urllib.parse.urlencode(p)
 sig=hmac.new(API_SECRET.encode('utf-8'),qs.encode('utf-8'),hashlib.sha256).hexdigest()
 url=f"https://fapi.binance.com{yol}?{qs}&signature={sig}"
 hdr={'X-MBX-APIKEY':API_KEY}
 if metod.upper()=='POST':return _HTTP_SES.post(url,headers=hdr,timeout=6)
 if metod.upper()=='DELETE':return _HTTP_SES.delete(url,headers=hdr,timeout=6)
 return _HTTP_SES.get(url,headers=hdr,timeout=6)
from decimal import Decimal,ROUND_DOWN,ROUND_HALF_UP
def _dec_step_format(val,step_str,prec_fallback=4,round_mode=ROUND_DOWN):
 try:
  d_val=Decimal(str(F(val)))
  if step_str and F(step_str)>0:
   s_clean=str(step_str).rstrip('0')
   if s_clean.endswith('.'):s_clean=s_clean[:-1]
   d_step=Decimal(s_clean)
   q_val=(d_val/d_step).to_integral_value(rounding=round_mode)*d_step
   dec_places=max(0,-d_step.as_tuple().exponent)
   return f"{q_val:.{dec_places}f}"
 except X:pass
 return f"{F(val):.{int(prec_fallback)}f}".rstrip('0').rstrip('.')or'0'

def _fapi_hassasiyet_formatla(raw_sym,miktar=None,fiyat=None):
 global _fapi_exinfo_cache
 if not _fapi_exinfo_cache:
  try:
   re_x=requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo',timeout=10)
   if re_x.status_code==200:
    for s_i in re_x.json().get('symbols',[]):
     if I(s_i,dict)and s_i.get('symbol'):_fapi_exinfo_cache[str(s_i['symbol']).upper()]=s_i
  except X:pass
 s_info=_fapi_exinfo_cache.get(raw_sym,{})
 q_prec=int(s_info.get('quantityPrecision',3))
 p_prec=int(s_info.get('pricePrecision',4))
 step_str='';tick_str=''
 for flt in s_info.get('filters',[]):
  if flt.get('filterType')=='LOT_SIZE':step_str=str(flt.get('stepSize',''))
  elif flt.get('filterType')=='PRICE_FILTER':tick_str=str(flt.get('tickSize',''))
 m_str=None;f_str=None
 if miktar is not None:
  m_str=_dec_step_format(miktar,step_str,q_prec,ROUND_DOWN)
  if not m_str or F(m_str)<=0:
   min_s=F(step_str)if step_str and F(step_str)>0 else 10**(-q_prec)
   m_str=_dec_step_format(min_s,step_str,q_prec,ROUND_HALF_UP)
 if fiyat is not None:
  f_str=_dec_step_format(fiyat,tick_str,p_prec,ROUND_HALF_UP)
 return(m_str,f_str)

def _fapi_sl_tp_acik_emirleri_gonder(raw_sym,aU,q_str,f2,eo,log_fn=None):
 global _fapi_hedge_modu
 if _fapi_hedge_modu is None:
  try:
   rd=_fapi_imzali_istek('GET','/fapi/v1/positionSide/dual')
   if rd.status_code==200:_fapi_hedge_modu=bool(rd.json().get('dualSidePosition',False))
  except X:_fapi_hedge_modu=False
 sl_side='SELL'if aU=='LONG'else'BUY'
 pos_side=('LONG'if aU=='LONG'else'SHORT')if _fapi_hedge_modu else None
 _,sl_str=_fapi_hassasiyet_formatla(raw_sym,None,f2)if f2 and F(f2)>0 else(None,None)
 _,tp_str=_fapi_hassasiyet_formatla(raw_sym,None,eo)if eo and F(eo)>0 else(None,None)
 sl_acildi=False;tp_acildi=False
 # 1) STOP-LOSS (SL) AÇIK EMRİ: Önce /fapi/v1/order (reduceOnly miktar ve closePosition), -4120 veya hata dönerse /fapi/v1/algoOrder (CONDITIONAL)
 if sl_str and F(sl_str)>0:
  for sl_deneme in[
   {'symbol':raw_sym,'side':sl_side,'type':'STOP_MARKET','stopPrice':sl_str,'quantity':q_str,'reduceOnly':'true','workingType':'MARK_PRICE'},
   {'symbol':raw_sym,'side':sl_side,'type':'STOP_MARKET','stopPrice':sl_str,'closePosition':'true','workingType':'MARK_PRICE'},
   {'symbol':raw_sym,'side':sl_side,'type':'STOP','price':sl_str,'stopPrice':sl_str,'quantity':q_str,'reduceOnly':'true','timeInForce':'GTC','workingType':'MARK_PRICE'}
  ]:
   try:
    p_sl=dict(sl_deneme)
    if pos_side:
     p_sl['positionSide']=pos_side
     if'closePosition'not in p_sl:p_sl.pop('reduceOnly',None)
    r_sl=_fapi_imzali_istek('POST','/fapi/v1/order',p_sl)
    if r_sl.status_code==200:
     sl_acildi=True;break
   except X:pass
  if not sl_acildi:
   for algo_sl in[
    {'algoType':'CONDITIONAL','symbol':raw_sym,'side':sl_side,'type':'STOP_MARKET','triggerPrice':sl_str,'quantity':q_str,'reduceOnly':'true','workingType':'MARK_PRICE'},
    {'algoType':'CONDITIONAL','symbol':raw_sym,'side':sl_side,'type':'STOP_MARKET','triggerPrice':sl_str,'closePosition':'true','workingType':'MARK_PRICE'}
   ]:
    try:
     p_asl=dict(algo_sl)
     if pos_side:
      p_asl['positionSide']=pos_side
      p_asl.pop('reduceOnly',None)
     r_asl=_fapi_imzali_istek('POST','/fapi/v1/algoOrder',p_asl)
     if r_asl.status_code==200:
      sl_acildi=True;break
    except X:pass
 # 2) TAKE-PROFIT (TP) AÇIK EMRİ: Önce doğrudan Open Orders sekmesinde görünen LIMIT (reduceOnly) emri + TAKE_PROFIT_MARKET / algoOrder yedeği
 if tp_str and F(tp_str)>0:
  for tp_deneme in[
   {'symbol':raw_sym,'side':sl_side,'type':'LIMIT','price':tp_str,'quantity':q_str,'timeInForce':'GTC','reduceOnly':'true'},
   {'symbol':raw_sym,'side':sl_side,'type':'TAKE_PROFIT_MARKET','stopPrice':tp_str,'quantity':q_str,'reduceOnly':'true','workingType':'MARK_PRICE'},
   {'symbol':raw_sym,'side':sl_side,'type':'TAKE_PROFIT_MARKET','stopPrice':tp_str,'closePosition':'true','workingType':'MARK_PRICE'}
  ]:
   try:
    p_tp=dict(tp_deneme)
    if pos_side:
     p_tp['positionSide']=pos_side
     p_tp.pop('reduceOnly',None)
    r_tp=_fapi_imzali_istek('POST','/fapi/v1/order',p_tp)
    if r_tp.status_code==200:
     tp_acildi=True;break
   except X:pass
  if not tp_acildi:
   try:
    p_atp={'algoType':'CONDITIONAL','symbol':raw_sym,'side':sl_side,'type':'TAKE_PROFIT_MARKET','triggerPrice':tp_str,'quantity':q_str,'reduceOnly':'true','workingType':'MARK_PRICE'}
    if pos_side:
     p_atp['positionSide']=pos_side
     p_atp.pop('reduceOnly',None)
    r_atp=_fapi_imzali_istek('POST','/fapi/v1/algoOrder',p_atp)
    if r_atp.status_code==200:tp_acildi=True
   except X:pass
 return(sl_acildi,tp_acildi)

def _fapi_gercek_vadeli_emir_ac(J,aU,Y,f2,eo=None,kaldirac=10,marjin_tipi='ISOLATED',log_fn=None):
 global _fapi_hedge_modu
 raw_sym=str(J).split(':')[0].replace('/','').upper()
 try:_fapi_imzali_istek('POST','/fapi/v1/leverage',{'symbol':raw_sym,'leverage':int(kaldirac)})
 except X:pass
 try:_fapi_imzali_istek('POST','/fapi/v1/marginType',{'symbol':raw_sym,'marginType':'ISOLATED'if'ISO'in str(marjin_tipi).upper()else'CROSSED'})
 except X:pass
 if _fapi_hedge_modu is None:
  try:
   rd=_fapi_imzali_istek('GET','/fapi/v1/positionSide/dual')
   if rd.status_code==200:_fapi_hedge_modu=bool(rd.json().get('dualSidePosition',False))
  except X:_fapi_hedge_modu=False
 q_str,sl_str=_fapi_hassasiyet_formatla(raw_sym,Y,f2)
 side='BUY'if aU=='LONG'else'SELL'
 ord_p={'symbol':raw_sym,'side':side,'type':'MARKET','quantity':q_str}
 if _fapi_hedge_modu:ord_p['positionSide']='LONG'if aU=='LONG'else'SHORT'
 r_ord=_fapi_imzali_istek('POST','/fapi/v1/order',ord_p)
 if r_ord.status_code!=200 and'-4061'in r_ord.text:
  _fapi_hedge_modu=not bool(_fapi_hedge_modu)
  if _fapi_hedge_modu:ord_p['positionSide']='LONG'if aU=='LONG'else'SHORT'
  else:ord_p.pop('positionSide',None)
  r_ord=_fapi_imzali_istek('POST','/fapi/v1/order',ord_p)
 if r_ord.status_code!=200:
  raise X(f"binance {r_ord.text}")
 ord_json=r_ord.json()
 gercek_q=F(ord_json.get('executedQty')or ord_json.get('origQty')or q_str)
 if gercek_q>0:q_str,_=_fapi_hassasiyet_formatla(raw_sym,gercek_q,None)
 _fapi_sl_tp_acik_emirleri_gonder(raw_sym,aU,q_str,f2,eo,log_fn)
 return ord_json

def _fapi_pozisyon_gercekten_kapali_mi(raw_sym,beklenen_yon=None):
 try:
  r_p=_fapi_imzali_istek('GET','/fapi/v2/positionRisk',{'symbol':str(raw_sym).upper()})
  if r_p.status_code!=200 or not I(r_p.json(),list)or L(r_p.json())==0:
   return False
  for p_it in r_p.json():
   if not I(p_it,dict):continue
   amt=F(p_it.get('positionAmt')or 0.0)
   if A(amt)>0.0:
    yon_p='LONG'if amt>0 else'SHORT'
    if beklenen_yon is None or yon_p==beklenen_yon:
     return False
  return True
 except X:
  return False

def _fapi_gercek_vadeli_emir_kapat(J,bt,Y):
 global _fapi_hedge_modu
 raw_sym=str(J).split(':')[0].replace('/','').upper()
 q_str,_=_fapi_hassasiyet_formatla(raw_sym,Y,None)
 side='SELL'if bt=='LONG'else'BUY'
 ord_p={'symbol':raw_sym,'side':side,'type':'MARKET','quantity':q_str}
 if _fapi_hedge_modu:ord_p['positionSide']='LONG'if bt=='LONG'else'SHORT'
 else:ord_p['reduceOnly']='true'
 r_cl=_fapi_imzali_istek('POST','/fapi/v1/order',ord_p)
 if r_cl.status_code!=200 and'-4061'in r_cl.text:
  _fapi_hedge_modu=not bool(_fapi_hedge_modu)
  if _fapi_hedge_modu:
   ord_p.pop('reduceOnly',None)
   ord_p['positionSide']='LONG'if bt=='LONG'else'SHORT'
  else:
   ord_p.pop('positionSide',None)
   ord_p['reduceOnly']='true'
  r_cl=_fapi_imzali_istek('POST','/fapi/v1/order',ord_p)
 kapandi_ok=False;ord_j={}
 if r_cl.status_code==200:
  kapandi_ok=True
  try:ord_j=r_cl.json()
  except X:ord_j={}
 else:
  if _fapi_pozisyon_gercekten_kapali_mi(raw_sym,bt):
   kapandi_ok=True
  else:
   try:
    r_pr=_fapi_imzali_istek('GET','/fapi/v2/positionRisk',{'symbol':raw_sym})
    if r_pr.status_code==200 and I(r_pr.json(),list):
     for pr_i in r_pr.json():
      amt_r=F(pr_i.get('positionAmt')or 0.0)
      if A(amt_r)>0 and(('LONG'if amt_r>0 else'SHORT')==bt):
       q_r,_=_fapi_hassasiyet_formatla(raw_sym,A(amt_r),None)
       ord_p['quantity']=q_r
       r_cl2=_fapi_imzali_istek('POST','/fapi/v1/order',ord_p)
       if r_cl2.status_code==200:
        kapandi_ok=True
        try:ord_j=r_cl2.json()
        except X:ord_j={}
       break
   except X:pass
 if kapandi_ok:
  try:_fapi_imzali_istek('DELETE','/fapi/v1/allOpenOrders',{'symbol':raw_sym})
  except X:pass
  try:_fapi_imzali_istek('DELETE','/fapi/v1/algoOpenOrders',{'symbol':raw_sym})
  except X:pass
 return(kapandi_ok,ord_j)

_user_trades_senk_cache={}
_son_gecmis_tam_senk_ts=0.0
def _fapi_gercek_kapanis_verisi_al(raw_sym,bq_m=None,min_ts_ms=0):
 raw_s=str(raw_sym).replace('/','').upper()
 acilis_sn=F((bq_m or{}).get('_acilis_ts')or 0.0)
 if min_ts_ms>0:
  alt_ms=int(min_ts_ms)
 elif acilis_sn>0:
  alt_ms=int((acilis_sn-90.0)*1000)
 else:
  alt_ms=int((time.time()-86400.0)*1000)
 try:
  r_ut=_fapi_imzali_istek('GET','/fapi/v1/userTrades',{'symbol':raw_s,'limit':100})
  if r_ut.status_code==200 and I(r_ut.json(),list):
   k_list=[t for t in r_ut.json()if I(t,dict)and int(t.get('time')or 0)>=alt_ms and A(F(t.get('realizedPnl')or 0.0))>1e-12]
   if k_list:
    k_list.sort(key=lambda x:int(x.get('time')or 0))
    son_t=int(k_list[-1].get('time')or 0)
    grup=[t for t in k_list if A(int(t.get('time')or 0)-son_t)<=30000]
    top_pnl=sum((F(t.get('realizedPnl')or 0.0)for t in grup))
    top_qty=sum((F(t.get('qty')or 0.0)for t in grup))
    cikis_f=(sum((F(t.get('price')or 0.0)*F(t.get('qty')or 0.0)for t in grup))/top_qty)if top_qty>0 else F((bq_m or{}).get('anlik')or 0.0)
    ps_u=str(grup[-1].get('positionSide')or'').upper()
    sd_u=str(grup[-1].get('side')or'').upper()
    yon_u=ps_u if ps_u in('LONG','SHORT')else('LONG'if sd_u=='SELL'else('SHORT'if sd_u=='BUY'else str((bq_m or{}).get('yon')or'LONG')))
    if top_qty>0 and cikis_f>0:
     giris_f=(cikis_f-(top_pnl/top_qty))if yon_u=='LONG'else(cikis_f+(top_pnl/top_qty))
    else:
     giris_f=F((bq_m or{}).get('giris')or 0.0)
    lev_u=int(M(1,F((bq_m or{}).get('kaldirac')or KALDIRAC)))
    marj_u=F((bq_m or{}).get('borsa_marjin_usdt')or(bq_m or{}).get('marjin_usdt')or 0.0)
    if marj_u<=0 and giris_f>0 and top_qty>0:
     marj_u=(top_qty*giris_f)/M(lev_u,1)
    roe_u=(top_pnl/M(marj_u,1e-09))*100.0 if marj_u>0 else 0.0
    tran_id=str(grup[-1].get('orderId')or grup[-1].get('id')or son_t)
    t_str=datetime.fromtimestamp(son_t/1000.0).strftime('%Y-%m-%d %H:%M:%S')
    return{'bulundu':True,'pnl_usdt':R(top_pnl,4),'pnl_yuzde':R(roe_u,2),'giris':R(giris_f,6),'cikis':R(cikis_f,6),'miktar':R(top_qty,6),'yon':yon_u,'tarih':t_str,'time_ms':son_t,'tran_id':tran_id}
 except X:pass
 try:
  r_ic=_fapi_imzali_istek('GET','/fapi/v1/income',{'symbol':raw_s,'incomeType':'REALIZED_PNL','startTime':alt_ms,'limit':50})
  if r_ic.status_code==200 and I(r_ic.json(),list):
   ic_list=[x for x in r_ic.json()if I(x,dict)and int(x.get('time')or 0)>=alt_ms and A(F(x.get('income')or 0.0))>1e-12]
   if ic_list:
    ic_list.sort(key=lambda x:int(x.get('time')or 0))
    son_t=int(ic_list[-1].get('time')or 0)
    grup_ic=[x for x in ic_list if A(int(x.get('time')or 0)-son_t)<=30000]
    top_pnl=sum((F(x.get('income')or 0.0)for x in grup_ic))
    giris_f=F((bq_m or{}).get('giris')or 0.0)
    mik_f=F((bq_m or{}).get('miktar')or 0.0)
    yon_u=str((bq_m or{}).get('yon')or'LONG')
    if giris_f>0 and mik_f>0:
     cikis_f=(giris_f+(top_pnl/mik_f))if yon_u=='LONG'else(giris_f-(top_pnl/mik_f))
    else:
     cikis_f=F((bq_m or{}).get('anlik')or giris_f)
    lev_u=int(M(1,F((bq_m or{}).get('kaldirac')or KALDIRAC)))
    marj_u=F((bq_m or{}).get('borsa_marjin_usdt')or(bq_m or{}).get('marjin_usdt')or((mik_f*giris_f)/M(lev_u,1)if giris_f>0 and mik_f>0 else 1.0))
    roe_u=(top_pnl/M(marj_u,1e-09))*100.0
    tran_id=str(grup_ic[-1].get('tranId')or grup_ic[-1].get('tradeId')or son_t)
    t_str=datetime.fromtimestamp(son_t/1000.0).strftime('%Y-%m-%d %H:%M:%S')
    return{'bulundu':True,'pnl_usdt':R(top_pnl,4),'pnl_yuzde':R(roe_u,2),'giris':R(giris_f,6),'cikis':R(cikis_f,6),'miktar':R(mik_f,6),'yon':yon_u,'tarih':t_str,'time_ms':son_t,'tran_id':tran_id}
 except X:pass
 return{'bulundu':False}

def _tarih_str_to_ms(t_str):
 try:
  return int(datetime.strptime(str(t_str).strip(),'%Y-%m-%d %H:%M:%S').timestamp()*1000)
 except X:
  return 0

def _fapi_gecmis_tam_senkronize_et(borsa_pozlar=None,zorla=False,log_fn=None):
 global ah,W,_son_gecmis_tam_senk_ts,_user_trades_senk_cache
 if TESTNET_AKTIF or not API_KEY or not API_SECRET:return False
 simdi_s=time.time()
 if(not zorla)and(simdi_s-_son_gecmis_tam_senk_ts)<12.0:return False
 _son_gecmis_tam_senk_ts=simdi_s
 try:
  if borsa_pozlar is None:
   cd=_fapi_canli_hesap_durumu_cek(sadece_pozisyon=True)
   if cd.get('pozisyon_ok'):borsa_pozlar=cd.get('pozisyonlar',{})
   else:borsa_pozlar={}
  # 1) Açık olan pozisyonların strateji/özet bilgisi yanlışlıkla geçmişe düşmüşse geri yükle
  for x_m in list(ah):
   if not I(x_m,dict):continue
   s_m=str(x_m.get('sembol',''))
   mod_m=str(x_m.get('model',''))
   if s_m and mod_m and'[Binance Hesabından Senkronize Edildi]'not in mod_m:
    if s_m not in _son_acilan_islem_meta_hafizasi:
     _son_acilan_islem_meta_hafizasi[s_m]={'ozet':mod_m,'rontgen':x_m.get('rontgen')}
    if I(acik_islemler.get(s_m),dict)and'[Binance Hesabından Senkronize Edildi]'in str(acik_islemler[s_m].get('ozet','')):
     acik_islemler[s_m]['ozet']=mod_m
     if x_m.get('rontgen')and not acik_islemler[s_m].get('rontgen'):
      acik_islemler[s_m]['rontgen']=x_m['rontgen']
  # 2) Binance hesabındaki son 7 günlük tüm REALIZED_PNL kayıtlarını tek seferde çek
  bas_7g_ms=int((simdi_s-7*86400)*1000)
  r_inc=_fapi_imzali_istek('GET','/fapi/v1/income',{'incomeType':'REALIZED_PNL','startTime':bas_7g_ms,'limit':1000})
  if r_inc.status_code!=200 or not I(r_inc.json(),list):
   return False
  ham_inc=[it for it in r_inc.json()if I(it,dict)and str(it.get('symbol','')).upper().endswith('USDT')and A(F(it.get('income')or 0.0))>1e-12]
  ham_inc.sort(key=lambda x:int(x.get('time')or 0))
  # Sembol bazında 30sn içindeki parçalı kapanışları tek kapanış işlemi olarak grupla
  sembol_kumeleri={}
  for it in ham_inc:
   r_s=str(it['symbol']).upper()
   t_ms=int(it.get('time')or 0)
   inc_v=F(it.get('income')or 0.0)
   tr_id=str(it.get('tradeId')or'')
   trn_id=str(it.get('tranId')or t_ms)
   k_list=sembol_kumeleri.setdefault(r_s,[])
   if k_list and A(t_ms-k_list[-1]['max_t'])<=30000:
    k_list[-1]['pnl_usdt']+=inc_v
    k_list[-1]['max_t']=M(k_list[-1]['max_t'],t_ms)
    if tr_id:k_list[-1]['trade_ids'].add(tr_id)
    k_list[-1]['tran_id']=trn_id
   else:
    k_list.append({'raw_sym':r_s,'sembol':f"FUT:{r_s[:-4]}/USDT",'pnl_usdt':inc_v,'min_t':t_ms,'max_t':t_ms,'trade_ids':{tr_id}if tr_id else set(),'tran_id':trn_id})
  # İlgili semboller için userTrades detaylarını (gerçek giriş, çıkış, miktar, yön) çek
  tum_kumeler=[]
  for r_s,k_list in sembol_kumeleri.items():
   son_max_t=k_list[-1]['max_t']
   c_ut=_user_trades_senk_cache.get(r_s)
   if not c_ut or c_ut[0]<son_max_t:
    try:
     r_ut=_fapi_imzali_istek('GET','/fapi/v1/userTrades',{'symbol':r_s,'limit':100})
     if r_ut.status_code==200 and I(r_ut.json(),list):
      _user_trades_senk_cache[r_s]=(son_max_t,r_ut.json())
      c_ut=_user_trades_senk_cache[r_s]
    except X:pass
   ut_list=c_ut[1]if c_ut else[]
   for km in k_list:
    eslesen_fills=[t for t in ut_list if I(t,dict)and A(F(t.get('realizedPnl')or 0.0))>1e-12 and((str(t.get('id')or'')in km['trade_ids'])or(km['min_t']-5000<=int(t.get('time')or 0)<=km['max_t']+5000))]
    if eslesen_fills:
     top_pnl=sum((F(t.get('realizedPnl')or 0.0)for t in eslesen_fills))
     top_qty=sum((F(t.get('qty')or 0.0)for t in eslesen_fills))
     cikis_f=(sum((F(t.get('price')or 0.0)*F(t.get('qty')or 0.0)for t in eslesen_fills))/top_qty)if top_qty>0 else 0.0
     ps_u=str(eslesen_fills[-1].get('positionSide')or'').upper()
     sd_u=str(eslesen_fills[-1].get('side')or'').upper()
     yon_u=ps_u if ps_u in('LONG','SHORT')else('LONG'if sd_u=='SELL'else'SHORT')
     giris_f=((cikis_f-(top_pnl/top_qty))if yon_u=='LONG'else(cikis_f+(top_pnl/top_qty)))if(top_qty>0 and cikis_f>0)else 0.0
     km['pnl_usdt']=R(top_pnl,4)
     km['miktar']=R(top_qty,6)
     km['cikis']=R(cikis_f,6)
     km['giris']=R(giris_f,6)
     km['yon']=yon_u
     km['tran_id']=str(eslesen_fills[-1].get('orderId')or km['tran_id'])
    else:
     km['pnl_usdt']=R(km['pnl_usdt'],4)
     km['miktar']=0.0;km['cikis']=0.0;km['giris']=0.0;km['yon']='LONG'
    km['tarih']=datetime.fromtimestamp(km['max_t']/1000.0).strftime('%Y-%m-%d %H:%M:%S')
    tum_kumeler.append(km)
  # 3) Mevcut ah (islem_gecmisi) kayıtlarını Binance gerçek verileriyle eşleştir, sahte/kapanmamış olanları temizle!
  yeni_ah=[]
  kullanilan_tran_ids=set()
  degisiklik_var=False
  en_eski_ah_ms=min((_tarih_str_to_ms(x.get('tarih',''))for x in ah if I(x,dict)and _tarih_str_to_ms(x.get('tarih',''))>0),default=0)
  for x in ah:
   if not I(x,dict):continue
   sem_x=str(x.get('sembol',''))
   if not sem_x.startswith('FUT:'):
    yeni_ah.append(x);continue
   x_ms=_tarih_str_to_ms(x.get('tarih',''))
   # 7 günden daha eski kayıtları koru
   if x_ms>0 and x_ms<bas_7g_ms:
    yeni_ah.append(x);continue
   adaylar=[km for km in sembol_kumeleri.get(sem_x.split(':',1)[-1].replace('/','').upper(),[])if km['tran_id']not in kullanilan_tran_ids and(str(x.get('binance_tran_id',''))==km['tran_id']or(x_ms>0 and A(x_ms-km['max_t'])<=1800000))]
   if adaylar:
    adaylar.sort(key=lambda km:0 if str(x.get('binance_tran_id',''))==km['tran_id']else A(x_ms-km['max_t']))
    es_km=adaylar[0]
    kullanilan_tran_ids.add(es_km['tran_id'])
    giris_son=es_km['giris']if es_km['giris']>0 else F(x.get('giris')or 0.0)
    cikis_son=es_km['cikis']if es_km['cikis']>0 else F(x.get('cikis')or 0.0)
    mik_son=es_km['miktar']if es_km['miktar']>0 else F(x.get('miktar')or 0.0)
    yon_son=es_km['yon']if es_km.get('giris',0)>0 else str(x.get('yon')or'LONG')
    pnl_son=R(F(es_km['pnl_usdt']),2)
    meta_m=_son_acilan_islem_meta_hafizasi.get(sem_x,{})
    lev_son=int(M(1,F(meta_m.get('kaldirac')or KALDIRAC)))
    marj_son=(mik_son*giris_son)/M(lev_son,1)if(giris_son>0 and mik_son>0)else 1.0
    roe_son=R((F(es_km['pnl_usdt'])/M(marj_son,1e-09))*100.0,2)
    if R(F(x.get('pnl_usdt',0)),2)!=pnl_son or R(F(x.get('giris',0)),6)!=R(giris_son,6)or R(F(x.get('cikis',0)),6)!=R(cikis_son,6)or not x.get('binance_onayli'):
     degisiklik_var=True
    x_guncel=dict(x)
    x_guncel.update({'tarih':es_km['tarih'],'yon':yon_son,'giris':R(giris_son,6),'cikis':R(cikis_son,6),'miktar':R(mik_son,6),'pnl_usdt':pnl_son,'pnl_yuzde':roe_son,'binance_tran_id':es_km['tran_id'],'binance_onayli':True})
    if(not x_guncel.get('model')or'[Binance Hesabından Senkronize Edildi]'in str(x_guncel.get('model','')))and meta_m.get('ozet'):
     x_guncel['model']=str(meta_m['ozet'])[:120]
    yeni_ah.append(x_guncel)
   else:
    # Binance REALIZED_PNL geçmişinde karşılığı olmayan (gerçekte kapanmamış / açık olan) sahte kaydı sil!
    degisiklik_var=True
    if log_fn:
     log_fn(f"🧹 [GEÇMİŞ SENKRONİZASYONU] Binance hesabında kapanmamış olan hatalı geçmiş kaydı temizlendi: {sem_x} ({x.get('tarih','-')})")
  # 4) Bot çalışırken veya bilinen paritelerde Binance'de kapanmış ama geçmişe henüz yazılmamış gerçek işlemleri ekle
  alt_ekleme_ms=en_eski_ah_ms if en_eski_ah_ms>0 else int((simdi_s-86400)*1000)
  for km in tum_kumeler:
   if km['tran_id']in kullanilan_tran_ids:continue
   if km['max_t']>=alt_ekleme_ms or km['sembol']in _son_acilan_islem_meta_hafizasi:
    if km['giris']<=0 and km['sembol']not in _son_acilan_islem_meta_hafizasi:continue
    meta_m=_son_acilan_islem_meta_hafizasi.get(km['sembol'],{})
    giris_k=km['giris']if km['giris']>0 else F(meta_m.get('giris')or 0.0)
    cikis_k=km['cikis']if km['cikis']>0 else giris_k
    mik_k=km['miktar']if km['miktar']>0 else 0.0
    lev_k=int(M(1,F(meta_m.get('kaldirac')or KALDIRAC)))
    marj_k=(mik_k*giris_k)/M(lev_k,1)if(giris_k>0 and mik_k>0)else 1.0
    roe_k=R((F(km['pnl_usdt'])/M(marj_k,1e-09))*100.0,2)
    yeni_k={'tarih':km['tarih'],'sembol':km['sembol'],'yon':km['yon'],'giris':R(giris_k,6),'cikis':R(cikis_k,6),'miktar':R(mik_k,6),'pnl_usdt':R(F(km['pnl_usdt']),2),'pnl_yuzde':roe_k,'neden':'BORSADA KAPANDI (SL/TP/MANUEL)','model':str(meta_m.get('ozet')or'[Binance Gerçekleşen İşlem]')[:120],'binance_tran_id':km['tran_id'],'binance_onayli':True}
    if I(meta_m.get('rontgen'),dict):yeni_k['rontgen']=meta_m['rontgen']
    yeni_ah.append(yeni_k)
    kullanilan_tran_ids.add(km['tran_id'])
    degisiklik_var=True
  yeni_ah.sort(key=lambda item:_tarih_str_to_ms(item.get('tarih','')),reverse=True)
  ah=yeni_ah[:500]
  # Toplam Gerçekleşen Net K/Z (W) değerini doğrudan Binance onaylı geçmiş işlemlerden güncelle
  sifir_ms=int(_kz_sifirlama_ts*1000)if _kz_sifirlama_ts>0 else 0
  yeni_w=R(sum((F(x.get('pnl_usdt')or 0.0)for x in ah if I(x,dict)and(sifir_ms<=0 or _tarih_str_to_ms(x.get('tarih',''))>=sifir_ms))),2)
  if A(W-yeni_w)>=0.01:
   W=yeni_w
   degisiklik_var=True
  if degisiklik_var:
   _ig_dosya_yaz()
   _ak_kaydet()
  return degisiklik_var
 except X:
  return False

_son_bakiye_senk_ts=0.0
_son_acik_emir_senk_ts=0.0
_cached_acik_emir_sembolleri=set()
def _fapi_canli_hesap_durumu_cek(sadece_pozisyon=False):
 # Binance Vadeli gerçek hesabından açık pozisyonları (entryPrice, markPrice, unRealizedProfit, Margin) çok hızlı çeker
 global _son_bakiye_senk_ts,_son_acik_emir_senk_ts,_cached_acik_emir_sembolleri
 sonuc={'ok':False,'pozisyon_ok':False,'bakiye_ok':False,'wallet_balance':0.0,'available_balance':0.0,'unrealized_pnl':0.0,'pozisyonlar':{},'acik_emir_sembolleri':set(_cached_acik_emir_sembolleri)}
 if TESTNET_AKTIF or not API_KEY or not API_SECRET:return sonuc
 simdi_c=time.time()
 try:
  r_pos=_fapi_imzali_istek('GET','/fapi/v2/positionRisk')
  if r_pos.status_code==200 and I(r_pos.json(),list)and L(r_pos.json())>0:
   sonuc['ok']=True
   sonuc['pozisyon_ok']=True
   toplam_upnl=0.0
   for p_item in r_pos.json():
    if not I(p_item,dict):continue
    amt=F(p_item.get('positionAmt')or 0.0)
    if A(amt)<=0.0:continue
    r_s=str(p_item.get('symbol','')).upper()
    if not r_s.endswith('USDT'):continue
    baz_s=r_s[:-4]+'/USDT'
    yon_p='LONG'if amt>0 else'SHORT'
    ep=F(p_item.get('entryPrice')or 0.0)
    mp_v=F(p_item.get('markPrice')or ep)
    upnl=F(p_item.get('unRealizedProfit')or 0.0)
    toplam_upnl+=upnl
    lev=int(M(1,F(p_item.get('leverage')or KALDIRAC)))
    m_type=str(p_item.get('marginType')or'isolated').lower()
    iso_w=F(p_item.get('isolatedWallet')or 0.0)
    iso_m=F(p_item.get('isolatedMargin')or 0.0)
    init_m=F(p_item.get('initialMargin')or 0.0)
    notional_m=A(F(p_item.get('notional')or(A(amt)*mp_v)))/M(lev,1)
    # Binance Mobil/Web "Margin (USDT)" ve "ROI (%)" hesabı ile birebir aynı marjin değeri:
    if m_type=='isolated'and iso_w>0:
     marj_u=iso_w
    elif init_m>0:
     marj_u=init_m
    elif notional_m>0:
     marj_u=notional_m
    else:
     marj_u=(A(amt)*ep)/M(lev,1)
    sonuc['pozisyonlar'][f"FUT:{baz_s}"]={'raw_sym':r_s,'sembol':baz_s,'yon':yon_p,'miktar':A(amt),'giris':ep,'anlik':mp_v,'pnl_usdt':upnl,'kaldirac':lev,'marjin_usdt':R(marj_u,2)}
   sonuc['unrealized_pnl']=toplam_upnl
  if(not sadece_pozisyon)or(simdi_c-_son_bakiye_senk_ts)>=6.0:
   r_acc=_fapi_imzali_istek('GET','/fapi/v2/balance')
   if r_acc.status_code==200 and I(r_acc.json(),list):
    _son_bakiye_senk_ts=simdi_c
    for b_it in r_acc.json():
     if I(b_it,dict)and str(b_it.get('asset','')).upper()=='USDT':
      sonuc['wallet_balance']=F(b_it.get('balance')or 0.0)
      sonuc['available_balance']=F(b_it.get('availableBalance')or 0.0)
      sonuc['bakiye_ok']=True
      sonuc['ok']=True;break
  eksik_emir_kontrol_gerekli=any((not I(acik_islemler.get(k_p),dict)or not acik_islemler[k_p].get('_sl_tp_senk_denendi',False))for k_p in sonuc['pozisyonlar'])
  if eksik_emir_kontrol_gerekli and(simdi_c-_son_acik_emir_senk_ts)>=8.0:
   _son_acik_emir_senk_ts=simdi_c
   yeni_set=set()
   r_oo=_fapi_imzali_istek('GET','/fapi/v1/openOrders')
   if r_oo.status_code==200 and I(r_oo.json(),list):
    for o_item in r_oo.json():
     if I(o_item,dict)and o_item.get('symbol'):
      yeni_set.add(str(o_item['symbol']).upper())
   try:
    r_ao=_fapi_imzali_istek('GET','/fapi/v1/openAlgoOrders')
    if r_ao.status_code==200:
     ao_list=r_ao.json().get('orders',[])if I(r_ao.json(),dict)else(r_ao.json()if I(r_ao.json(),list)else[])
     for ao_item in ao_list:
      if I(ao_item,dict)and ao_item.get('symbol'):
       yeni_set.add(str(ao_item['symbol']).upper())
   except X:pass
   _cached_acik_emir_sembolleri=yeni_set
   sonuc['acik_emir_sembolleri']=yeni_set
 except X:pass
 return sonuc
def _fmt_f(v):
 try:
  n=F(v or 0.0);a=A(n)
  if 0<a<1:return f"{n:.6f}"
  if a<100:return f"{n:.4f}"
  return f"{n:.2f}"
 except X:return str(v)
def _fmt_pnl(v):
 try:return f"{F(v or 0.0):+.2f} USDT"
 except X:return"+0.00 USDT"
def _normalize_tf(bN):
 s=str(bN or'15m').strip()
 return'1M'if s=='1M'else s.lower()
_parite_yukle_kilit=threading.Lock()
parite_hacim_map={}
def _hacim_kademesi_hesapla(v_usdt):
 v=F(v_usdt or 0.0)
 return 5 if v>=100000000.0 else(4 if v>=30000000.0 else(3 if v>=10000000.0 else(2 if v>=3000000.0 else(1 if v>=500000.0 else 0))))
def _fmt_hacim(v_usdt):
 v=F(v_usdt or 0.0)
 if v>=1000000000.0:return f"{v/1000000000.0:.2f}B$"
 if v>=1000000.0:return f"{v/1000000.0:.1f}M$"
 if v>=1000.0:return f"{v/1000.0:.0f}K$"
 return f"{v:.0f}$" 
def _rest_ile_borsa_paritelerini_cek(D):
 nI=[]
 try:
  if D=='future':
   r_ex=requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo',timeout=12)
   r_tk=requests.get('https://fapi.binance.com/fapi/v1/ticker/24hr',timeout=12)
  else:
   r_ex=requests.get('https://api.binance.com/api/v3/exchangeInfo',timeout=12)
   r_tk=requests.get('https://api.binance.com/api/v3/ticker/24hr',timeout=12)
  vol_map={}
  if r_tk.status_code==200:
   for tk_item in r_tk.json():
    if I(tk_item,dict)and tk_item.get('symbol'):
     vol_map[str(tk_item['symbol']).upper()]=F(tk_item.get('quoteVolume')or 0.0)
  if r_ex.status_code==200:
   sym_list=r_ex.json().get('symbols',[])
   for s_inf in sym_list:
    if not I(s_inf,dict):continue
    raw_id=str(s_inf.get('symbol','')).upper()
    mR=str(s_inf.get('baseAsset','')).upper()
    mS=str(s_inf.get('quoteAsset','')).upper()
    inf_st=str(s_inf.get('status')or s_inf.get('contractStatus')or'TRADING').upper()
    inf_u_type=str(s_inf.get('underlyingType')or'').upper()
    inf_c_type=str(s_inf.get('contractType')or'').upper()
    if inf_u_type in('EQUITY','COMMODITY','FX','INDEX','PRE_MARKET','PREMARKET')or'TRADIFI'in inf_c_type or'STOCK'in inf_c_type:continue
    if inf_st!='TRADING'or mS!='USDT'or not mR or mR in bo or any((mR.endswith(ek)for ek in('UP','DOWN','BULL','BEAR'))):continue
    if D=='future':
     if inf_c_type not in('PERPETUAL','TRADITIONAL_PERPETUAL','')or'_'in raw_id:continue
    else:
     if not s_inf.get('isSpotTradingAllowed',True):continue
    iz=F(vol_map.get(raw_id,0.0))
    if vol_map and 0<iz<bH:continue
    qY=f"{mR}/USDT"
    nI.append((qY,D,iz))
 except X:pass
 nI.sort(key=lambda x:x[2],reverse=True)
 return nI[:ae]if ae>0 else nI

def tek_borsa_paritelerini_cek(D):
 nI=[]
 try:
  a9=veri_ist(D)
  hk=a9.markets if(getattr(a9,'markets',None)and L(a9.markets)>50)else a9.load_markets(True)
  try:o9=a9.fetch_tickers()
  except X:o9={}
  seen_base=set()
  for qY,m in hk.items():
   mR,mS=(str(m.get('base','')).upper(),str(m.get('quote','')).upper())
   inf=m.get('info')or{}
   inf_st=str(inf.get('status')or inf.get('contractStatus')or'TRADING').upper()
   inf_u_type=str(inf.get('underlyingType')or'').upper()
   inf_c_type=str(inf.get('contractType')or'').upper()
   if inf_u_type in('EQUITY','COMMODITY','FX','INDEX','PRE_MARKET','PREMARKET')or'TRADIFI'in inf_c_type or'STOCK'in inf_c_type or m.get('subType')in('tradfi','stock'):continue
   if not m.get('active',True)or inf_st!='TRADING'or mS!='USDT'or not mR or mR in bo or any((mR.endswith(ek)for ek in('UP','DOWN','BULL','BEAR'))):continue
   if D=='future'and(not(m.get('linear',True)and(m.get('swap',False)or m.get('future',False)))or'_'in str(m.get('id',''))):continue
   elif D!='future'and not m.get('spot',True):continue
   norm_sym=f"{mR}/USDT"
   if norm_sym in seen_base:continue
   seen_base.add(norm_sym)
   tk_d=o9.get(qY)or o9.get(norm_sym)or o9.get(f"{norm_sym}:USDT")or{}
   iz=F(tk_d.get('quoteVolume')or(tk_d.get('info')or{}).get('quoteVolume')or 0.0)
   if o9 and 0<iz<bH:continue
   nI.append((norm_sym,D,iz))
 except X:
  nI=[]
 if L(nI)<30:
  rest_list=_rest_ile_borsa_paritelerini_cek(D)
  if L(rest_list)>L(nI):
   return rest_list
 nI.sort(key=lambda x:x[2],reverse=True);return nI[:ae]if ae>0 else nI

def pariteleri_yukle(ba=None):
 global ab,bk,au
 with _parite_yukle_kilit:
  nJ,qZ,fE=([],0,0)
  for pa,pb in[('future','Vadeli (Futures)'),('spot','Spot')]:
   if PIYASA_MODU in(pa,'her_ikisi'):
    try:
     ad=tek_borsa_paritelerini_cek(pa)
     if L(ad)<30:
      ad_rest=_rest_ile_borsa_paritelerini_cek(pa)
      if L(ad_rest)>L(ad):ad=ad_rest
     nJ.extend(ad)
     if pa=='future':qZ=L(ad)
     else:fE=L(ad)
    except X as e:
     try:
      ad_fb=_rest_ile_borsa_paritelerini_cek(pa)
      nJ.extend(ad_fb)
      if pa=='future':qZ=L(ad_fb)
      else:fE=L(ad_fb)
     except X:
      if ba:ba(f'⚠️ {pb} parite listesi çekilirken uyarı: {e}')
  if nJ:
   nJ.sort(key=lambda x:x[2],reverse=True)
   if PIYASA_MODU=='her_ikisi':
    fut_baz={s.split(':')[0]for s,p,_ in nJ if p=='future'}
    nJ=[(s,p,v)for s,p,v in nJ if p=='future'or s.split(':')[0]not in fut_baz]
   for s_h,p_h,v_h in nJ:
    parite_hacim_map[anahtar_yap(s_h,p_h)]=F(v_h)
    parite_hacim_map[s_h]=M(F(parite_hacim_map.get(s_h,0.0)),F(v_h))
   ab=[(s,p)for s,p,_ in nJ];bk=[s for s,_ in ab];au=L(ab)
   if ba:ba(f'🌐 Otomatik Borsa Taraması Hazır (Yüksek Hacim Öncelikli) -> Vadeli: {qZ} parite | Spot: {fE} parite | Toplam: {au} aktif USDT paritesi taranacak!')
   return bk
  if L(ab)>L(am)*2:
   return bk
  ab=[(s,'future')for s in am]+[(s,'spot')for s in am]if PIYASA_MODU=='her_ikisi'else[(s,'spot'if PIYASA_MODU=='spot'else'future')for s in am];bk=[s for s,_ in ab];au=L(ab);return bk
def tg_bildir(fs):
 if TELEGRAM_AKTIF and TELEGRAM_TOKEN:
  try:requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',json={'chat_id':TELEGRAM_CHAT_ID,'text':fs,'parse_mode':'HTML'},timeout=5)
  except X as e:print(f'Telegram Hatası: {e}')
def bakiye_oku(a9):
 try:
  if a9 is ao and not TESTNET_AKTIF and API_KEY and API_SECRET:
   r_b=_fapi_imzali_istek('GET','/fapi/v2/account')
   if r_b.status_code==200:
    jd=r_b.json()
    og=F(jd.get('totalWalletBalance')or 0.0)
    rf=F(jd.get('availableBalance')or 0.0)
    if og>0 or rf>0:return(rf,og)
  b=a9.fetch_balance();rf,og=(F(b.get('USDT',{}).get('free',0.0)or 0.0),F(b.get('USDT',{}).get('total',0.0)or 0.0))
  if'info'in b and I(b['info'],dict):
   twb=F(b['info'].get('totalWalletBalance')or 0.0)
   avb=F(b['info'].get('availableBalance')or 0.0)
   if twb>0:og=twb
   if avb>0:rf=avb
  return(rf,og)
 except X:return(0.0,0.0)
def bakiye_getir():
 global ay,aq;jS,rV=bakiye_oku(aG)if PIYASA_MODU in('spot','her_ikisi')else(0.0,0.0);nR,pc=(0.0,0.0)
 if PIYASA_MODU in('future','her_ikisi'):
  if not TESTNET_AKTIF:
   nR,pc=bakiye_oku(ao)
   if pc<=0.0 and S>0:
    r4=sum((d['miktar']*d['giris']/M(d.get('kaldirac',KALDIRAC),1)for d in acik_islemler.values()if I(d,dict)and d.get('piyasa')=='future'));pc,nR=(M(0.0,S),M(0.0,S-r4))
  else:r4=sum((d['miktar']*d['giris']/M(d.get('kaldirac',KALDIRAC),1)for d in acik_islemler.values()if I(d,dict)and d.get('piyasa')=='future'));pc,nR=(M(0.0,S),M(0.0,S-r4))
 ay,aq=(jS,nR);return(jS+nR,rV+pc)
_ohlcv_kisa_cache={}
def veri_cek(J,bN,limit=120,D=None):
 tf_n=_normalize_tf(bN)
 p_tip=D if D else('spot'if PIYASA_MODU=='spot'else'future')
 c_key=(str(J).split(':')[0],tf_n,p_tip,int(limit))
 simdi_t=time.time()
 eski_c=_ohlcv_kisa_cache.get(c_key)
 ttl_sn=5.0 if tf_n in('1m','3m','5m')else(15.0 if tf_n in('15m','30m')else 30.0)
 if eski_c and(simdi_t-eski_c[0])<=ttl_sn:
  return eski_c[1]
 oP=None;son_hata=None
 raw_s=str(J).split(':')[0].replace('/','').upper()
 # 1) HIZLI DOĞRUDAN REST KLINES (Kalıcı _HTTP_SES bağlantısıyla ~40ms, sembol uyuşmazlığı ve takılma olmaz):
 u_kl=f"https://fapi.binance.com/fapi/v1/klines?symbol={raw_s}&interval={tf_n}&limit={int(limit)}"if p_tip=='future'else f"https://api.binance.com/api/v3/klines?symbol={raw_s}&interval={tf_n}&limit={int(limit)}"
 for deneme_r in G(2):
  try:
   r_kl=_HTTP_SES.get(u_kl,timeout=4)
   if r_kl.status_code==200:
    j_kl=r_kl.json()
    if I(j_kl,list)and L(j_kl)>=5:
     oP=[[int(k[0]),F(k[1]),F(k[2]),F(k[3]),F(k[4]),F(k[5])]for k in j_kl]
     break
  except X as e_fb:
   son_hata=e_fb
   time.sleep(0.08)
 # 2) CCXT Yedeği (Yalnızca doğrudan REST yanıt vermezse):
 if not oP or L(oP)<5:
  try:
   ist=veri_ist(p_tip)
   J_c=_emir_sembolu(ist,J,p_tip)
   oP=ist.fetch_ohlcv(J_c,timeframe=tf_n,limit=limit)
  except X as e_v:
   son_hata=son_hata or e_v
 if not oP or L(oP)<5:
  if eski_c:return eski_c[1]
  raise X(son_hata or f"{J} ({tf_n}) veri alinamadi")
 df=indiktorleri_ekle(pd.DataFrame(oP,columns=['timestamp','open','high','low','close','volume']));eF=J.split(':')[0]
 if eF in('BTC/USDT','ETH/USDT','SOL/USDT'):an.setdefault(tf_n,{})[eF]=df
 if L(_ohlcv_kisa_cache)>600:_ohlcv_kisa_cache.clear()
 _ohlcv_kisa_cache[c_key]=(simdi_t,df)
 return df
def anlik_fiyat_getir(J,D='future'):
 raw_s=str(J).split(':')[0].replace('/','').upper()
 try:
  if D=='future':
   # Vadeli işlemlerde Binance PNL hesabıyla birebir uyum için doğrudan Mark Price (premiumIndex) çekilir:
   r_mp=_HTTP_SES.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={raw_s}",timeout=3)
   if r_mp.status_code==200:
    v_mp=F(r_mp.json().get('markPrice')or r_mp.json().get('indexPrice')or 0.0)
    if v_mp>0:return v_mp
   r_tp=_HTTP_SES.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={raw_s}",timeout=3)
   if r_tp.status_code==200:
    v_tp=F(r_tp.json().get('price')or 0.0)
    if v_tp>0:return v_tp
  else:
   r_sp=_HTTP_SES.get(f"https://api.binance.com/api/v3/ticker/price?symbol={raw_s}",timeout=3)
   if r_sp.status_code==200:
    v_sp=F(r_sp.json().get('price')or 0.0)
    if v_sp>0:return v_sp
 except X:pass
 try:
  ist=veri_ist(D)
  v=F(ist.fetch_ticker(_emir_sembolu(ist,J,D))['last'])
  if v>0:return v
 except X:pass
 try:
  ak_k=anahtar_yap(J,D)
  if ak_k in analiz_hafizasi and'df_15m_full'in analiz_hafizasi[ak_k]:return _f(analiz_hafizasi[ak_k]['df_15m_full'],'close',-1)
 except X:pass
 raise X(f'{J} anlik fiyat alinamadi')
def islem_kar_zarar_hesapla(O,bq):
 if not I(bq,dict):return(0.0,0.0,0.0,0.0,0.0,1,0.0)
 bt=bq.get('yon','LONG');b0=bq.get('piyasa','future');bZ=F(bq.get('giris')or 0.0);bM=F(bq.get('anlik')or bZ);Y=F(bq.get('miktar')or 0.0);sl=F(bq.get('sl')or 0.0);k1=int(M(1,F(bq.get('kaldirac')or(KALDIRAC if b0=='future'else 1))))
 if Y<=0 and bZ>0:
  Y=R((MAKS_MARJIN_USDT*k1)/bZ,6)
  bq['miktar']=Y
 fark=(bZ-bM)if bt=='SHORT'else(bM-bZ)
 hesap_pnl=fark*Y
 # Gerçek Binance Vadeli pozisyonlarında doğrudan Binance'in bildirdiği unRealizedProfit ve markPrice kullanılır:
 if not bq.get('simule',False)and b0=='future'and'borsa_pnl_usdt'in bq:
  if F(bq.get('borsa_mark_fiyat')or 0.0)>0:
   bM=F(bq['borsa_mark_fiyat'])
  gW=F(bq['borsa_pnl_usdt'])
 else:
  gW=hesap_pnl
 fk=F(bq.get('borsa_marjin_usdt')or 0.0)if(not bq.get('simule',False)and b0=='future'and F(bq.get('borsa_marjin_usdt')or 0.0)>0)else((Y*bZ)/M(k1,1)if bZ>0 else F(bq.get('marjin_usdt')or MAKS_MARJIN_USDT))
 nD=(gW/M(fk,1e-09))*100.0 if fk>0 else((fark/M(bZ,1e-09))*100.0*k1 if bZ>0 else 0.0)
 k0=R(A(bZ-sl)*Y,2)if(sl>0 and bZ>0 and Y>0)else F(bq.get('risk_usdt')or ISLEM_BASI_RISK_USDT)
 bq['anlik']=bM;bq['pnl_usdt']=R(gW,4);bq['pnl_yuzde']=R(nD,2);bq['marjin_usdt']=R(fk,2);bq['risk_usdt']=k0
 return(gW,nD,bZ,bM,fk,k1,k0)
def indiktorleri_ekle(df):
 df=df.copy();tr=pd.concat([df['high']-df['low'],(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1);df['atr']=tr.rolling(dj).mean().bfill();d=df['close'].diff();rs=d.where(d>0,0.0).rolling(14).mean()/(-d.where(d<0,0.0)).rolling(14).mean().replace(0,np.nan);df['rsi']=(100.0-100.0/(1.0+rs)).fillna(50.0);qH=(df['high']+df['low'])/2.0;df['ao']=(qH.rolling(5).mean()-qH.rolling(34).mean()).fillna(0.0);df['cvd']=((df['close']-df['low']-(df['high']-df['close']))/(df['high']-df['low']).replace(0,1e-09)*df['volume']).cumsum();return df
def _df_periyot_sn_bul(df):
 """DataFrame zaman damgalarindan mum periyodunu saniye cinsinden bulur (1h = 3600sn)."""
 try:
  if df is not None and'timestamp'in df.columns and L(df)>=3:
   t1=F(_f(df,'timestamp',-1));t2=F(_f(df,'timestamp',-2));t3=F(_f(df,'timestamp',-3))
   d1=A(t1-t2);d2=A(t2-t3)
   ms=N(d1,d2)if(d1>0 and d2>0)else M(d1,d2)
   if ms>10000:return ms/1000.0
   if ms>0:return ms
 except X:pass
 return 14400.0
def _df_1h_ve_alti_mi(df,n=SWING_PENCERE):
 """1h ve alti (1h, 30m, 15m, 5m, 3m, 1m -> <= 3600sn) ise True, 1h ustu HTF (2h, 4h, 1d, 1M) ise False doner."""
 if n<=3:return True
 return _df_periyot_sn_bul(df)<=3660.0
def _mum_kapanis_onayli_tepe_mi(df,i,E):
 # KURAL: Tepe noktaları belirlenirken mumun iğne ucu (high) baz alınır; uzun iğneli mumlar elenmez!
 return True
def _mum_kapanis_onayli_dip_mi(df,i,E):
 # KURAL: Dip noktaları belirlenirken mumun iğne ucu (low) baz alınır; uzun iğneli mumlar elenmez!
 return True
def _net_sert_tepe_mi(df,i,E,n=SWING_PENCERE):
 if not _mum_kapanis_onayli_tepe_mi(df,i,E):return False
 if n<=1:return True
 hassas_1h_alti=_df_1h_ve_alti_mi(df,n)
 ct=L(df);h=_f(df,'high',i);l_0=_f(df,'low',i);l_arr=df.__dict__['_np_c']['low']
 w=3 if hassas_1h_alti else M(3,n+1)
 b1=M(0,i-w);b2=N(ct-1,i+w)
 min_sol=F(l_arr[b1:i+1].min())if i>b1 else l_0
 min_sag=F(l_arr[i:b2+1].min())if b2>i else l_0
 esik=E*(0.82 if hassas_1h_alti else(1.55 if n>=4 else 1.1))
 sag_esik=esik*0.5 if i>=ct-3 else esik
 return(h-min_sol)>=esik and(h-min_sag)>=sag_esik
def _net_sert_dip_mi(df,i,E,n=SWING_PENCERE):
 if not _mum_kapanis_onayli_dip_mi(df,i,E):return False
 if n<=1:return True
 hassas_1h_alti=_df_1h_ve_alti_mi(df,n)
 ct=L(df);l=_f(df,'low',i);h_0=_f(df,'high',i);h_arr=df.__dict__['_np_c']['high']
 w=3 if hassas_1h_alti else M(3,n+1)
 b1=M(0,i-w);b2=N(ct-1,i+w)
 max_sol=F(h_arr[b1:i+1].max())if i>b1 else h_0
 max_sag=F(h_arr[i:b2+1].max())if b2>i else h_0
 esik=E*(0.82 if hassas_1h_alti else(1.55 if n>=4 else 1.1))
 sag_esik=esik*0.5 if i>=ct-3 else esik
 return(max_sol-l)>=esik and(max_sag-l)>=sag_esik
def ham_swing_noktalarini_bul(df,n=SWING_PENCERE,cn=False):
 aa,ar=([],[])
 hassas_1h_alti=_df_1h_ve_alti_mi(df,n)
 n_eff=1 if n<=1 else(2 if hassas_1h_alti else(3 if n>=4 else M(1,n)))
 if L(df)<2*n_eff+2:return(aa,ar)
 E=M(_f(df,'atr',-2)if'atr'in df.columns else _f(df,'close',-2)*0.002,_f(df,'close',-2)*0.001)
 _f(df,'high',0);_f(df,'low',0)
 h_np=df.__dict__['_np_c']['high'];l_np=df.__dict__['_np_c']['low']
 for i in G(n_eff,L(df)-n_eff):
  if h_np[i]==h_np[i-n_eff:i+n_eff+1].max()and(not cn or(l_np[i]>=l_np[i-1]and l_np[i]>=l_np[i+1])):
   if _net_sert_tepe_mi(df,i,E,n):aa.append((i,F(h_np[i])))
  if l_np[i]==l_np[i-n_eff:i+n_eff+1].min()and(not cn or(h_np[i]<=h_np[i-1]and h_np[i]<=h_np[i+1])):
   if _net_sert_dip_mi(df,i,E,n):ar.append((i,F(l_np[i])))
 if n>=2 and(L(aa)<2 or L(ar)<2):
  aa,ar=([],[])
  for i in G(n_eff,L(df)-n_eff):
   if h_np[i]==h_np[i-n_eff:i+n_eff+1].max()and _mum_kapanis_onayli_tepe_mi(df,i,E):aa.append((i,F(h_np[i])))
   if l_np[i]==l_np[i-n_eff:i+n_eff+1].min()and _mum_kapanis_onayli_dip_mi(df,i,E):ar.append((i,F(l_np[i])))
 return(aa,ar)
def _aralikta_gecerli_tepe_bul(df,bas,bit,E):
 Bas=M(0,int(bas));Bit=N(L(df)-1,int(bit))
 if Bit<Bas:return(Bas,_f(df,'high',Bas))
 en_i,en_v=(Bas,_f(df,'high',Bas))
 tepe_kilit=False
 for j in G(Bas+1,Bit+1):
  hj,lj,cj=(_f(df,'high',j),_f(df,'low',j),_f(df,'close',j))
  if not tepe_kilit:
   if hj>=en_v:en_i,en_v=(j,hj)
   elif j>=en_i+2 and(en_v-lj)>=E*0.85:tepe_kilit=True
  else:
   # İlk tepenin iğnesi (en_v) oluştuktan sonra, yeni tepenin oluşması için mum kapanışının (cj) önceki tepenin iğnesinin (en_v) üstünde kapatması şarttır!
   if cj>en_v:
    en_i,en_v=(j,hj);tepe_kilit=False
 return(en_i,en_v)
def _aralikta_gecerli_dip_bul(df,bas,bit,E):
 Bas=M(0,int(bas));Bit=N(L(df)-1,int(bit))
 if Bit<Bas:return(Bas,_f(df,'low',Bas))
 en_i,en_v=(Bas,_f(df,'low',Bas))
 dip_kilit=False
 for j in G(Bas+1,Bit+1):
  lj,hj,cj=(_f(df,'low',j),_f(df,'high',j),_f(df,'close',j))
  if not dip_kilit:
   if lj<=en_v:en_i,en_v=(j,lj)
   elif j>=en_i+2 and(hj-en_v)>=E*0.85:dip_kilit=True
  else:
   # İlk dibin iğnesi (en_v) oluştuktan sonra, yeni dibin oluşması için mum kapanışının (cj) önceki dibin iğnesinin (en_v) altında kapatması şarttır!
   if cj<en_v:
    en_i,en_v=(j,lj);dip_kilit=False
 return(en_i,en_v)
def _sert_salinim_onayli_mi(df,bas_i,bas_v,bit_i,bit_v,E,n=2,ana_bacak=0.0):
 genlik=A(F(bit_v)-F(bas_v));bar_fark=M(1,A(int(bit_i)-int(bit_i if bas_i is None else bas_i)))
 hassas_1h_alti=_df_1h_ve_alti_mi(df,n)
 tf_sn=_df_periyot_sn_bul(df)
 if hassas_1h_alti:
  min_genlik=E*(N(1.05,KYSY_LTF_ATR_CARPANI*0.82)if tf_sn>=1800 else N(0.88,KYSY_LTF_ATR_CARPANI*0.72))
 else:
  min_genlik=E*(KYSY_HTF_ATR_CARPANI if n>=4 else KYSY_LTF_ATR_CARPANI)
 if genlik<min_genlik:return False
 # Ana dalga (ana_bacak) içindeki küçük ara duraksamaların (örn. 0.0980->0.0755 düşüşü içindeki 0.0858->0.0885 tepkisinin)
 # ana swing (LH/HL) sayılmasını önlemek için en az %28 geri çekilme şartı:
 if not hassas_1h_alti and ana_bacak>E*3.0 and genlik<M(ana_bacak*0.28,E*1.8):return False
 if hassas_1h_alti and ana_bacak>E*3.2 and genlik<M(ana_bacak*0.28,E*1.5):return False
 min_b=2 if hassas_1h_alti else(3 if n>=4 else 2)
 if bar_fark<min_b and genlik<min_genlik*(1.35 if hassas_1h_alti else 1.75):return False
 B1,B2=M(0,N(int(bas_i),int(bit_i))),N(L(df)-1,M(int(bas_i),int(bit_i)))
 dusus_mu=F(bit_v)<F(bas_v)
 zit_say=sum((1 for j in G(B1+1,B2+1)if(_f(df,'close',j)<_f(df,'open',j)if dusus_mu else _f(df,'close',j)>_f(df,'open',j))))
 max_mum=M((A(_f(df,'close',j)-_f(df,'open',j))for j in G(B1,B2+1)),default=0.0)
 if zit_say<1 and genlik<min_genlik*1.65:return False
 if not hassas_1h_alti and n>=4 and zit_say<2 and genlik<min_genlik*1.55:return False
 return max_mum>=E*(0.30 if hassas_1h_alti else 0.42)or genlik>=min_genlik*(1.12 if hassas_1h_alti else 1.3)
def _qml_yapisi_bul(uH,uL,yon=None,df=None):
 zz=sorted([(int(i),F(v),'H')for i,v in uH]+[(int(i),F(v),'L')for i,v in uL],key=lambda x:x[0])
 temiz=[]
 for item in zz:
  if not temiz or temiz[-1][2]!=item[2]:temiz.append(item)
  else:
   if item[2]=='H'and item[1]>=temiz[-1][1]:temiz[-1]=item
   elif item[2]=='L'and item[1]<=temiz[-1][1]:temiz[-1]=item
 if L(temiz)<4:return None
 bull_qml,bear_qml=(None,None)
 bull_any,bear_any=(None,None)
 for m in G(L(temiz)-1,2,-1):
  p0,p1,p2,p3=(temiz[m-3],temiz[m-2],temiz[m-1],temiz[m])
  if p0[0]<=0 and m==3:continue
  if p0[2]=='L'and p1[2]=='H'and p2[2]=='L'and p3[2]=='H':
   if p2[1]<p0[1]and p3[1]>p1[1]and p1[1]>p0[1]:
    cand=(int(p0[0]),R(F(p0[1]),6),int(p2[0]),R(F(p2[1]),6),int(p1[0]),R(F(p1[1]),6),int(p3[0]),R(F(p3[1]),6))
    if bull_any is None:bull_any=cand
    sonraki_daha_dusuk=any((x[1]<p2[1]for x in temiz[m+1:]if x[2]=='L'))
    if bull_qml is None and not sonraki_daha_dusuk and(df is None or F(df['low'].iloc[p3[0]:].min())>=p2[1]):
     bull_qml=cand
  if p0[2]=='H'and p1[2]=='L'and p2[2]=='H'and p3[2]=='L':
   if p2[1]>p0[1]and p3[1]<p1[1]and p0[1]>p1[1]:
    cand=(int(p0[0]),R(F(p0[1]),6),int(p2[0]),R(F(p2[1]),6),int(p1[0]),R(F(p1[1]),6),int(p3[0]),R(F(p3[1]),6))
    if bear_any is None:bear_any=cand
    sonraki_daha_yuksek=any((x[1]>p2[1]for x in temiz[m+1:]if x[2]=='H'))
    if bear_qml is None and not sonraki_daha_yuksek and(df is None or F(df['high'].iloc[p3[0]:].max())<=p2[1]):
     bear_qml=cand
 b_sec=bull_qml or bull_any
 br_sec=bear_qml or bear_any
 if yon=='BULLISH':return b_sec or br_sec
 if yon=='BEARISH':return br_sec or b_sec
 if bull_qml and bear_qml:return bull_qml if bull_qml[6]>=bear_qml[6]else bear_qml
 if bull_qml or bear_qml:return bull_qml or bear_qml
 if b_sec and br_sec:return b_sec if b_sec[6]>=br_sec[6]else br_sec
 return b_sec or br_sec
def _kysy_ltf_swing_analizi(df,n=2,cn=False):
 rH,rL=ham_swing_noktalarini_bul(df,n,cn);mt={'kysy_onay':False,'bos_list':[],'elenen_highs':[],'elenen_lows':[],'elenen_sayi':0,'son_kirilim_tipi':'YOK','son_kirilim_yon':'NOTR','son_kirilim_seviye':None,'son_kirilim_idx':None,'aktif_aralik_kirildi':False,'qml_seviyesi':None,'qml_idx':None,'bull_qml_meta':None,'bear_qml_meta':None,'aday_arz_talep_bazlari':[]}
 if L(df)<8 or L(rH)<1 or L(rL)<1:return([],[],mt)
 E=M(_f(df,'atr',-2)if'atr'in df.columns else _f(df,'close',-2)*0.002,_f(df,'close',-2)*0.001)
 hassas_1h_alti=_df_1h_ve_alti_mi(df,n)
 tf_sn=_df_periyot_sn_bul(df)
 n_piv=2 if hassas_1h_alti else(3 if n>=4 else M(1,n))
 min_pb=E*((N(1.05,KYSY_LTF_ATR_CARPANI*0.82)if tf_sn>=1800 else N(0.88,KYSY_LTF_ATR_CARPANI*0.72))if hassas_1h_alti else(KYSY_HTF_ATR_CARPANI if n>=4 else KYSY_LTF_ATR_CARPANI))
 min_bar=2 if hassas_1h_alti else(3 if n>=4 else 2)
 if rH[0][0]>=min_bar:
  i0_l,v0_l=_aralikta_gecerli_dip_bul(df,0,rH[0][0]-1,E)
  if(rH[0][1]-v0_l)>=min_pb*0.85 and(not rL or i0_l<rL[0][0]):rL.insert(0,(i0_l,v0_l))
 if rL[0][0]>=min_bar:
  i0_h,v0_h=_aralikta_gecerli_tepe_bul(df,0,rL[0][0]-1,E)
  if(v0_h-rL[0][1])>=min_pb*0.85 and(not rH or i0_h<rH[0][0]):rH.insert(0,(i0_h,v0_h))
 rH_map={i:v for i,v in rH};rL_map={i:v for i,v in rL}
 hi,hv=rH[0];li,lv=rL[0];tr=0;oH,oL,bL=([],[],[]);sI=M(1,N(hi,li)+1);kilit_h,kilit_l=(False,False)
 for k in G(sI,L(df)):
  cl,ch,clw=(_f(df,'close',k),_f(df,'high',k),_f(df,'low',k))
  tepe_onay=_mum_kapanis_onayli_tepe_mi(df,k,E)
  dip_onay=_mum_kapanis_onayli_dip_mi(df,k,E)
  aktif_leg=A(hv-lv)
  if tr==0:
   if k>hi+min_bar and cl>hv:
    mI,mV=_aralikta_gecerli_dip_bul(df,hi+1,k-1,E)
    if(hv-mV)>=min_pb*0.85 and(mI-hi)>=min_bar:
     bI,bV=_aralikta_gecerli_dip_bul(df,0,M(0,hi-1),E)if hi>=min_bar else(mI,mV)
     yv=ch
     if hi>=min_bar and bI<hi and(hv-bV)>=min_pb*0.85:
      if mV>=bV-E*0.2:
       oL=[(bI,bV),(mI,mV)];oH=[(hi,hv),(k,yv)]
       bL.append((k,hv,mI,mV,'BULLISH','BULL_BOS'))
      else:
       tI,tV=_aralikta_gecerli_tepe_bul(df,0,M(0,bI-1),E)if bI>=min_bar else(hi,hv)
       if bI>=min_bar and tI<bI and(tV-bV)>=min_pb*0.85 and tV>hv:
        oH=[(tI,tV),(hi,hv),(k,yv)];oL=[(bI,bV),(mI,mV)]
        bL.append((k,hv,mI,mV,'BULLISH','BULL_MSB_CHOCH'))
       else:
        oH=[(hi,hv),(k,yv)];oL=[(mI,mV)]
     else:
      oH=[(hi,hv),(k,yv)];oL=[(mI,mV)]
     li,lv=(mI,mV);hi,hv=(k,yv);tr=1;kilit_h=False
    elif ch>hv:
     hi,hv=(k,ch)
   elif k>li+min_bar and cl<lv:
    xI,xV=_aralikta_gecerli_tepe_bul(df,li+1,k-1,E)
    if(xV-lv)>=min_pb*0.85 and(xI-li)>=min_bar:
     tI,tV=_aralikta_gecerli_tepe_bul(df,0,M(0,li-1),E)if li>=min_bar else(xI,xV)
     yv=clw
     if li>=min_bar and tI<li and(tV-lv)>=min_pb*0.85:
      if xV<=tV+E*0.2:
       oH=[(tI,tV),(xI,xV)];oL=[(li,lv),(k,yv)]
       bL.append((k,lv,xI,xV,'BEARISH','BEAR_BOS'))
      else:
       bI,bV=_aralikta_gecerli_dip_bul(df,0,M(0,tI-1),E)if tI>=min_bar else(li,lv)
       if tI>=min_bar and bI<tI and(tV-bV)>=min_pb*0.85 and bV<lv:
        oL=[(bI,bV),(li,lv),(k,yv)];oH=[(tI,tV),(xI,xV)]
        bL.append((k,lv,xI,xV,'BEARISH','BEAR_MSB_CHOCH'))
       else:
        oL=[(li,lv),(k,yv)];oH=[(xI,xV)]
     else:
      oL=[(li,lv),(k,yv)];oH=[(xI,xV)]
     hi,hv=(xI,xV);li,lv=(k,yv);tr=-1;kilit_l=False
    elif clw<lv:
     li,lv=(k,clw)
   else:
    if k in rH_map and ch>hv and k<=li+n_piv*4:hi,hv=(k,ch)
    if k in rL_map and clw<lv and k<=hi+n_piv*4:li,lv=(k,clw)
  elif tr==1:
   if not kilit_h:
    if ch>=hv:
     hi,hv=(k,ch)
     if oH:oH[-1]=(hi,hv)
    elif(k-n_piv in rL_map and k-n_piv>=hi+min_bar and _sert_salinim_onayli_mi(df,hi,hv,k-n_piv,rL_map[k-n_piv],E,n,aktif_leg))or(k>=hi+min_bar and _sert_salinim_onayli_mi(df,hi,hv,k,clw,E,n,aktif_leg)):
     kilit_h=True
   # KURAL: Yeni oluşan tepenin gövdesi (cl) bir önceki tepenin iğnesinin (hv) üstünde kapattıysa yeni oluşan tepenin iğne ucu (ch) yeni tepe noktamız olur!
   bos_yukari_kirdi=bool(cl>hv)
   if kilit_h and k>hi+min_bar and bos_yukari_kirdi:
    mI,mV=_aralikta_gecerli_dip_bul(df,hi+1,k-1,E)
    gercek_hl=bool(_sert_salinim_onayli_mi(df,hi,hv,mI,mV,E,n,aktif_leg)and(ch-mV)>=min_pb and(mI-hi)>=min_bar and(k-mI)>=2 and(aktif_leg<=E*2.5 or(hv-mV)>=aktif_leg*0.28))
    if gercek_hl:
     if not oL or oL[-1][0]!=mI:oL.append((mI,mV))
     li,lv=(mI,mV);yv=ch
     bL.append((k,hv,mI,mV,'BULLISH','BULL_BOS'))
     hi,hv=(k,yv);oH.append((hi,hv));kilit_h=False
    else:
     t_i,t_v=_aralikta_gecerli_tepe_bul(df,li+1,k,E)
     if ch>=t_v:t_i,t_v=(k,ch)
     hi,hv=(t_i,t_v)
     if oH:oH[-1]=(hi,hv)
     kilit_h=False
   elif k>li+min_bar and cl<lv:
    xI,xV=_aralikta_gecerli_tepe_bul(df,li+1,k-1,E)if k-1>=li+1 else(hi,hv)
    if _sert_salinim_onayli_mi(df,xI,xV,k,clw,E,n):
     if oH and xV>=hv and(not kilit_h or any((_f(df,'close',m_c)>hv for m_c in G(hi+1,k)))):
      hi,hv=(xI,xV);oH[-1]=(hi,hv)
     yv=clw
     choch_ok=L(oH)>=2 and L(oL)>=2 and(oH[-1][1]>oH[-2][1]or oL[-1][1]>oL[-2][1])
     bL.append((k,lv,hi,hv,'BEARISH','BEAR_MSB_CHOCH'if choch_ok else'BEAR_BOS'))
     li,lv=(k,yv);oL.append((li,lv));tr=-1;kilit_l=False
  elif tr==-1:
   if not kilit_l:
    if clw<=lv:
     li,lv=(k,clw)
     if oL:oL[-1]=(li,lv)
    elif(k-n_piv in rH_map and k-n_piv>=li+min_bar and _sert_salinim_onayli_mi(df,li,lv,k-n_piv,rH_map[k-n_piv],E,n,aktif_leg))or(k>=li+min_bar and _sert_salinim_onayli_mi(df,li,lv,k,ch,E,n,aktif_leg)):
     kilit_l=True
   # KURAL (image_2edd06.png -> 1057320a.png): Yeni oluşan dibin gövdesi (cl) bir önceki dibin iğnesinin (lv) altında kapattıysa yeni oluşan dibin iğne ucu (clw) yeni dip noktamız olur!
   # Sadece iğnesi önceki dibin iğnesinin altına inip gövdesi (cl) önceki dibin iğnesinin altında kapatmayan mumlar (Kırmızı Ok) kesinlikle dip kabul edilmez!
   bos_asagi_kirdi=bool(cl<lv)
   if kilit_l and k>li+min_bar and bos_asagi_kirdi:
    xI,xV=_aralikta_gecerli_tepe_bul(df,li+1,k-1,E)
    gercek_lh=bool(_sert_salinim_onayli_mi(df,li,lv,xI,xV,E,n,aktif_leg)and(xV-clw)>=min_pb and(xI-li)>=min_bar and(k-xI)>=2 and(aktif_leg<=E*2.5 or(xV-lv)>=aktif_leg*0.28))
    if gercek_lh:
     if not oH or oH[-1][0]!=xI:oH.append((xI,xV))
     hi,hv=(xI,xV);yv=clw
     bL.append((k,lv,xI,xV,'BEARISH','BEAR_BOS'))
     li,lv=(k,yv);oL.append((li,lv));kilit_l=False
    else:
     d_i,d_v=_aralikta_gecerli_dip_bul(df,hi+1,k,E)
     if clw<=d_v:d_i,d_v=(k,clw)
     li,lv=(d_i,d_v)
     if oL:oL[-1]=(li,lv)
     kilit_l=False
   elif k>hi+min_bar and cl>hv:
    mI,mV=_aralikta_gecerli_dip_bul(df,hi+1,k-1,E)if k-1>=hi+1 else(li,lv)
    if _sert_salinim_onayli_mi(df,mI,mV,k,ch,E,n):
     if oL and mV<=lv and(not kilit_l or any((_f(df,'close',m_c)<lv for m_c in G(li+1,k)))):
      li,lv=(mI,mV);oL[-1]=(li,lv)
     yv=ch
     choch_ok=L(oH)>=2 and L(oL)>=2 and(oL[-1][1]<oL[-2][1]or oH[-1][1]<oH[-2][1])
     bL.append((k,hv,li,lv,'BULLISH','BULL_MSB_CHOCH'if choch_ok else'BULL_BOS'))
     hi,hv=(k,yv);oH.append((hi,hv));tr=1;kilit_h=False
 # KIRILIM YOKSA SWING YOKTUR KURALI (1.png vs image_b35979.png):
 # Döngü sonunda fiyat ne son tepeyi (hv) ne de son dibi (lv) kırmadıysa oH ve oL listelerine ASLA yeni swing noktası eklenmez!
 # Yalnızca Arz/Talep bölgesi tespiti (örn. cys1.png'deki mor Arz bölgesi) için aday_arz_talep_bazlari kaydedilir:
 if tr==-1 and oL and oH and li>hi and li<L(df)-5:
  xI_end,xV_end=_aralikta_gecerli_tepe_bul(df,li+1,L(df)-3,E)
  if li+min_bar<=xI_end<=L(df)-4 and xV_end<hv and(xV_end-lv)>=M(min_pb*1.5,A(hv-lv)*0.55):
   sonraki_dip_i,sonraki_dip_v=_aralikta_gecerli_dip_bul(df,xI_end+1,L(df)-1,E)
   if(xV_end-sonraki_dip_v)>=M(min_pb*1.2,(xV_end-lv)*0.65):
    mt['aday_arz_talep_bazlari'].append((N(L(df)-3,xI_end+1),xV_end,xI_end,xV_end,'BEARISH','BEAR_BOS'))
 elif tr==1 and oH and oL and hi>li and hi<L(df)-5:
  mI_end,mV_end=_aralikta_gecerli_dip_bul(df,hi+1,L(df)-3,E)
  if hi+min_bar<=mI_end<=L(df)-4 and mV_end>lv and(hv-mV_end)>=M(min_pb*1.5,A(hv-lv)*0.55):
   sonraki_tepe_i,sonraki_tepe_v=_aralikta_gecerli_tepe_bul(df,mI_end+1,L(df)-1,E)
   if(sonraki_tepe_v-mV_end)>=M(min_pb*1.2,(hv-mV_end)*0.65):
    mt['aday_arz_talep_bazlari'].append((N(L(df)-3,mI_end+1),mV_end,mI_end,mV_end,'BULLISH','BULL_BOS'))
 if not oH or not oL:
  oH,oL=(rH[-4:],rL[-4:])
 oH_set={i for i,_ in oH};oL_set={i for i,_ in oL}
 el_h=[(i,v)for i,v in rH if i not in oH_set];el_l=[(i,v)for i,v in rL if i not in oL_set]
 mt['elenen_highs']=el_h;mt['elenen_lows']=el_l;mt['elenen_sayi']=L(el_h)+L(el_l);mt['bos_list']=bL;mt['kysy_onay']=L(bL)>0
 if bL:
  mt['son_kirilim_idx'],mt['son_kirilim_seviye'],_,_,mt['son_kirilim_yon'],mt['son_kirilim_tipi']=bL[-1]
 qm_found=_qml_yapisi_bul(oH,oL,mt['son_kirilim_yon']if mt['son_kirilim_yon']in('BULLISH','BEARISH')else None,df)
 if qm_found:
  mt['qml_idx'],mt['qml_seviyesi']=(qm_found[0],qm_found[1])
 return(oH,oL,mt)
def kirilim_yoksa_swing_yoktur_analizi(df,n=SWING_PENCERE,cn=False):
 return _kysy_ltf_swing_analizi(df,n,cn)
def swing_noktalarini_bul(df,n=SWING_PENCERE,cn=False,kirilim_sarti=True):
 if n<=1 or not kirilim_sarti:return ham_swing_noktalarini_bul(df,n,cn)
 uH,uL,_=kirilim_yoksa_swing_yoktur_analizi(df,n,cn);return(uH,uL)
def wyckoff_analizi(df,aa,ar):
 a5={'wyckoff_fazi':'TREND_IMPULSIVE','konsolidasyon_mu':False,'egimli_flama_mi':False,'spring_manipulasyon':False,'utad_manipulasyon':False,'aciklama':''}
 if L(df)<35 or L(aa)<2 or L(ar)<2:return a5
 ak=_f(df,'close',-2);E=M(_f(df,'atr',-2),ak*0.001);qI=(_f(df,'close',-14)-_f(df,'close',-34))/M(_f(df,'close',-34),1e-09);lK=df.iloc[-14:-3];iA,hp=(F(lK['high'].max()),F(lK['low'].min()))
 if L(aa)>=3 and L(ar)>=3:
  he,le=(aa[-1][1]-aa[-3][1],ar[-1][1]-ar[-3][1])
  if he*le>0 and A(he)<=E*4.5 and A(le)<=E*4.5:a5['egimli_flama_mi']=True
 ft=F(df['low'].iloc[-4:-1].min())<hp and ak>hp;fu=F(df['high'].iloc[-4:-1].max())>iA and ak<iA;a5['spring_manipulasyon'],a5['utad_manipulasyon']=(ft,fu)
 if iA-hp<=E*4.2 or a5['egimli_flama_mi']:
  a5['konsolidasyon_mu']=True
  if qI<=-0.015:a5['wyckoff_fazi']='ACCUMULATION_SPRING'if ft else'RE_DISTRIBUTION'if fu else'ACCUMULATION_RANGE';a5['aciklama']='Wyckoff Accumulation + Spring/PO3 Süpürmesi (YT-Part1&2)'if ft else'Wyckoff Re-Distribution (Üst Likidite Operasyonu) (YT-Part1&2)'if fu else'Wyckoff Accumulation Talep Alanı (YT-Part1&2)'
  elif qI>=0.015:a5['wyckoff_fazi']='DISTRIBUTION_UTAD'if fu else'RE_ACCUMULATION'if ft else'DISTRIBUTION_RANGE';a5['aciklama']='Wyckoff Distribution + UTAD/PO3 Süpürmesi (YT-Part1&2)'if fu else'Wyckoff Re-Accumulation (Alt Likidite Yakıt Operasyonu) (YT-Part1&2)'if ft else'Wyckoff Konsolidasyon Alanı (YT-Part1&2)'
  else:a5['wyckoff_fazi'],a5['aciklama']=('CONSOLIDATION_RANGE','Alıcı-Satıcı Dengesi / Range Konsolidasyonu (YT-Part1&2)')
 return a5
def ext_int_swing_ayristir(df,aa,ar):
 cS={'external_yon':'NOTR','strong_point':None,'strong_idx':None,'weak_point':None,'weak_idx':None,'break_line_fl':None,'break_line_idx':None,'internal_yon':'NOTR','internal_choch':'YOK','external_msb':False,'kuru_kafa_trendline_tuzagi':False,'uc_istasyon':{}}
 if L(aa)<1 or L(ar)<1:return cS
 aa_p=([aa[0]]*(3-L(aa))+list(aa))if L(aa)<3 else list(aa)
 ar_p=([ar[0]]*(3-L(ar))+list(ar))if L(ar)<3 else list(ar)
 cl,bb,bc=(_f(df,'close',-2),_f(df,'low',-2),_f(df,'high',-2));E=M(_f(df,'atr',-2),cl*0.001);(hS,H0),(gd,H1),(hf,H2)=(aa_p[-3],aa_p[-2],aa_p[-1]);(hT,L0),(ge,L1),(hg,L2)=(ar_p[-3],ar_p[-2],ar_p[-1])
 hq=(hf>hg and H2>=H1)or(H2>H1 and cl>=L2)
 cS['external_yon']='BULLISH'if hq else'BEARISH'
 if hq:
  gf,hh=(hg,L2);w_i,w_v=(hf,H2);fl_i,fl_v=(gd,H1);cS['external_msb']=bool(L2<L1 and H2>H1)
 else:
  gf,hh=(hf,H2);w_i,w_v=(hg,L2);fl_i,fl_v=(ge,L1);cS['external_msb']=bool(H2>H1 and L2<L1)
 cS['strong_point'],cS['strong_idx']=(F(hh),int(gf))
 cS['weak_point'],cS['weak_idx']=(F(w_v),int(w_i))
 cS['break_line_fl'],cS['break_line_idx']=(F(fl_v),int(fl_i))
 be,hV=(cS['break_line_fl'],cS['weak_point'])
 bF=(be-(be-hh)*0.25 if be>hh else be-E*0.35)if hq else(be+(hh-be)*0.25 if hh>be else be+E*0.35)
 lX=(be+(hV-be)*0.25 if hV>be else be+E*0.4)if hq else(be-(be-hV)*0.25 if be>hV else be-E*0.4)
 cS['uc_istasyon']={'ITZ':R(bF,6),'FL':R(be,6),'FO':R(lX,6),'FTR':R(lX,6),'VALID_ORIGIN':R(hh,6)}
 # 01-2-40.pdf (Sayfa 5-7, 12-14): Dinamik Trend Çizgisi + Son Strong Area (HL/LH) Kırılımı (Kuru Kafa ☠️) vs Trendline Tuzağı
 if L(ar)>=3 and hq and hg>hT:
  tl_egim=(L1-L0)/M(ge-hT,1)
  tl_beklenen=L0+tl_egim*(L(df)-2-hT)
  if tl_egim>0 and cl<tl_beklenen and cl>=L2:cS['kuru_kafa_trendline_tuzagi']=True
 elif L(aa)>=3 and(not hq)and hf>hS:
  tl_egim=(H1-H0)/M(gd-hS,1)
  tl_beklenen=H0+tl_egim*(L(df)-2-hS)
  if tl_egim<0 and cl>tl_beklenen and cl<=H2:cS['kuru_kafa_trendline_tuzagi']=True
 d0,d4=swing_noktalarini_bul(df,1,kirilim_sarti=False)
 if L(d0)>=2 and L(d4)>=2:
  pN,oh,pO,oi=(d0[-2][1],d0[-1][1],d4[-2][1],d4[-1][1])
  son_h_i,son_l_i=(int(d0[-1][0]),int(d4[-1][0]))
  if cl>oh:
   cS['internal_yon'],cS['internal_choch']=('BULLISH','BULL_STRONG_CHOCH'if oi<pO else'BULL_IBOS'if oh>pN and oi>pO else'BULL_WEAK_CHOCH')
  elif cl<oi:
   cS['internal_yon'],cS['internal_choch']=('BEARISH','BEAR_STRONG_CHOCH'if oh>pN else'BEAR_IBOS'if oi<pO and oh<pN else'BEAR_WEAK_CHOCH')
  else:
   # Son 8 mum içinde gerçekleşmiş ve ardından LTF Arz/Talep bölgesini retest eden iç kırılımları (CHoCH / i-BOS) koru
   ct_d=L(df)
   prev_l_i=int(d4[-2][0]);prev_h_i=int(d0[-2][0])
   kapanisla_asagi_kirdi=any((_f(df,'close',k_c)<pO for k_c in G(M(0,prev_l_i+1),ct_d)))
   kapanisla_yukari_kirdi=any((_f(df,'close',k_c)>pN for k_c in G(M(0,prev_h_i+1),ct_d)))
   if son_l_i>son_h_i and oi<pO and kapanisla_asagi_kirdi and son_l_i>=ct_d-8 and cl<=oh:
    cS['internal_yon'],cS['internal_choch']=('BEARISH','BEAR_STRONG_CHOCH'if oh>pN else'BEAR_IBOS')
   elif son_h_i>son_l_i and oh>pN and kapanisla_yukari_kirdi and son_h_i>=ct_d-8 and cl>=oi:
    cS['internal_yon'],cS['internal_choch']=('BULLISH','BULL_STRONG_CHOCH'if oi<pO else'BULL_IBOS')
 return cS
def rbr_dbd_analizi(df,bu,aH,aJ,B='BULLISH'):
 g=B=='BULLISH';a5={'kalip_adi':'DBR'if g else'RBD','hidden_base_dp':False,'v_shape_1mum':False,'patlama_ayrilis':False,'imbalance_koku':aJ if g else aH,'banker_mumu':False,'yaklasim_ipuclari':[],'yaklasim_ek_puan':0.0}
 if bu<4 or bu>=L(df)-3:return a5
 E=M(_f(df,'atr',-2),_f(df,'close',-2)*0.001);qJ=_f(df,'close',bu-1)-_f(df,'open',M(0,bu-4));a5['kalip_adi']=('RBR_FTR'if qJ>E*0.5 else'DBR')if g else('DBD_FTR'if qJ<-E*0.5 else'RBD');jT,hr=(df.iloc[bu],df.iloc[N(L(df)-2,bu+1)]);o1,c1,h1,l1=_r(jT,'open','close','high','low');o2,c2,h2,l2=_r(hr,'open','close','high','low');a5['imbalance_koku']=(o2 if c2>o2 else aJ)if g else(o2 if c2<o2 else aH)
 if(c1>o1 and c2>o2 and h1-c1>E*0.15 and o2-l2>E*0.15)if g else(c1<o1 and c2<o2 and c1-l1>E*0.15 and h2-o2>E*0.15):a5['hidden_base_dp']=True
 if A(c2-o2)>=E*1.15 or A(o2-c1)>E*0.12:a5['patlama_ayrilis']=True
 jE=sum((1 for k in G(bu,N(L(df)-2,bu+5))if aH-E*0.1<=_f(df,'close',k)<=aJ+E*0.1));a5['v_shape_1mum']=jE<=1;qK=L(df)-2-(bu+M(jE,1))
 if jE<=2 and qK>=8:a5['yaklasim_ipuclari'].append(f'YavasDonus(2m->{qK}m)');a5['yaklasim_ek_puan']+=1.0
 if L(df)>=8:
  ilk_d=df.iloc[-8:-5];son_d=df.iloc[-5:-2]
  q0=F((ilk_d['close']-ilk_d['open']).abs().mean());lY=F((son_d['close']-son_d['open']).abs().mean())
  ileri_ilk=F((ilk_d[['open','close']].min(axis=1)-ilk_d['low']).mean()if g else(ilk_d['high']-ilk_d[['open','close']].max(axis=1)).mean())
  ileri_son=F((son_d[['open','close']].min(axis=1)-son_d['low']).mean()if g else(son_d['high']-son_d[['open','close']].max(axis=1)).mean())
  if q0>0 and lY<=q0*0.75:a5['yaklasim_ipuclari'].append('GovdeKuculmesi/Doji');a5['yaklasim_ek_puan']+=1.0
  if ileri_ilk>0 and ileri_son<=ileri_ilk*0.80:a5['yaklasim_ipuclari'].append('IleriIgneKisalmasi');a5['yaklasim_ek_puan']+=0.5
  lZ=F((son_d['high']-son_d[['open','close']].max(axis=1)).mean());l4=F((son_d[['open','close']].min(axis=1)-son_d['low']).mean())
  if(lZ>l4*1.20)if g else(l4>lZ*1.20):a5['yaklasim_ipuclari'].append('TersUstIgneUzamasi'if g else'TersAltIgneUzamasi');a5['yaklasim_ek_puan']+=1.0
  mp,mc=(df.iloc[-3],df.iloc[-2]);pg=A(F(mp['close'])-F(mp['open']))
  if(F(mp['close'])<F(mp['open'])and pg>E*0.65 and F(mc['close'])>F(mc['open']))if g else(F(mp['close'])>F(mp['open'])and pg>E*0.65 and F(mc['close'])<F(mc['open'])):a5['banker_mumu']=True;a5['yaklasim_ipuclari'].append('BankerManipulasyonMumu_ReversalOnay');a5['yaklasim_ek_puan']+=1.0
 return a5
def ftr_fo_itz_taramasi(df,z,C,a='1H',B='BULLISH'):
 l5,K,az,bz,pe=([],[],[],None,False)
 if L(df)<15:return(l5,bz,K,az,pe)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);qL=z.get('uc_istasyon',{});a6=z.get('strong_point');g=B=='BULLISH';aX='Bullish'if g else'Bearish'
 for i in G(M(3,L(df)-28),L(df)-4):
  oj,iV,ok=(df.iloc[i-1],df.iloc[i],df.iloc[i+1]);iB=F(oj['close'])-F(oj['open']);fF=A(F(iV['close'])-F(iV['open']));fG=F(ok['close'])-F(ok['open']);nS=df['close'].iloc[i+2:-2]
  jU1=(iB>E*0.48 and fF<=E*0.58 and fG>E*0.52 and F(ok['close'])>F(oj['high']))if g else(iB<-E*0.48 and fF<=E*0.58 and fG<-E*0.52 and F(ok['close'])<F(oj['low']))
  jU2=False;jc2,jd2=(0.0,0.0)
  if not jU1 and i+2<L(df)-3:
   ok2=df.iloc[i+2];fF2=A(F(ok['close'])-F(ok['open']));fG2=F(ok2['close'])-F(ok2['open']);nS=df['close'].iloc[i+3:-2]
   jU2=(iB>E*0.48 and fF<=E*0.55 and fF2<=E*0.55 and fG2>E*0.52 and F(ok2['close'])>M(F(oj['high']),F(iV['high'])))if g else(iB<-E*0.48 and fF<=E*0.55 and fF2<=E*0.55 and fG2<-E*0.52 and F(ok2['close'])<N(F(oj['low']),F(iV['low'])))
   if jU2:jc2,jd2=(N(F(iV['low']),F(ok['low'])),M(F(iV['open']),F(iV['close']),F(ok['open']),F(ok['close'])))if g else(N(F(iV['open']),F(iV['close']),F(ok['open']),F(ok['close'])),M(F(iV['high']),F(ok['high'])))
  if jU1 or jU2:
   jc,jd=((F(iV['low']),M(F(iV['open']),F(iV['close'])))if g else(N(F(iV['open']),F(iV['close'])),F(iV['high'])))if jU1 else(jc2,jd2)
   r5=(not nS.empty and F(nS.min())<jc-E*0.1)if g else(not nS.empty and F(nS.max())>jd+E*0.1)
   if not r5 and((jc-E*0.2<=bb<=jd+E*0.15 and ak>=jc)if g else(jc-E*0.15<=bc<=jd+E*0.2 and ak<=jd)):
    m_say='1Mum'if jU1 else'2Mum_InsideDoji'
    l5.append(f"{a}_{('1Mum_FTR' if g else 'Bear_1Mum_FTR')}");K.append(f"[{a}] {aX} {m_say} {('RBR' if g else 'DBD')} Trend Devam FTR Testi ({jc:.4f}-{jd:.4f}) (08.pdf & YT-Part3)");az.append(('BB/FL',i,jc,jd));bz=(jc if bz is None else N(bz,jc))if g else(jd if bz is None else M(bz,jd));break
 d5,g7=(qL.get('FO'),qL.get('ITZ'));de=bb if g else bc
 if d5 and A(de-d5)<=E*0.35 and(ak>=d5 if g else ak<=d5):l5.append(f"{a}_{('FirstObstacle_FO' if g else 'Bear_FirstObstacle_FO')}");K.append(f'[{a}] {aX} First Obstacle (FO - Kırılım Sonrası İlk Tepki/Engel: {d5:.4f}) Testi (YT-Part3)');fH=d5-E*0.45 if g else d5+E*0.45;bz=fH if bz is None else N(bz,fH)if g else M(bz,fH)
 if g7 and A(de-g7)<=E*0.38 and(ak>=g7 if g else ak<=g7):
  l5.append(f"{a}_{('ITZ' if g else 'Bear_ITZ')}")
  if a6 and L(C)>0 and(g7-a6>E*0.8 if g else a6-g7>E*0.8):pe=True;bz=a6;K.append(f"[{a}] {aX} ITZ ({g7:.4f}) Testi + UYARI: ITZ ile Origin OB ({a6:.4f}) arasında açık Imbalance var (Manipülasyon Tuzağı Kalkanı); stop Origin OB'ye çekildi! (YT-Part3)")
  else:K.append(f'[{a}] {aX} ITZ (Kırılım Öncesi Son Yapı: {g7:.4f}) Testi (08.pdf & YT-Part3)');pP=g7-E*0.45 if g else g7+E*0.45;bz=pP if bz is None else N(bz,pP)if g else M(bz,pP)
 return(l5,bz,K,az,pe)
def dp_ve_fl_analizi(df,z,C,a='1H',B='BULLISH'):
 l6,l7,l8,l9=([],[],[],None);hl={'magic_line':None,'fl_turu':'YOK','dp_turu':'YOK','swing_modeli':'V_Shape'};aa,ar=(z.get('highs',[]),z.get('lows',[]))
 if L(df)<18 or L(aa)<2 or L(ar)<2:return(l6,l9,l7,l8,hl)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);g=B=='BULLISH'
 def _dpt(hs,ht):
  for k in G(M(2,hs),N(L(df)-3,ht)+1):
   c1,c2=(df.iloc[k-1],df.iloc[k]);a0,bi,cg,ch=_r(c1,'open','close','high','low');br,a8,cI,cJ=_r(c2,'open','close','high','low');kH,h9=(A(bi-a0),A(a8-br));nh,ni=(cg-M(a0,bi),N(a0,bi)-ch);nj,nk=(cI-M(br,a8),N(br,a8)-cJ);mT=(a8>br)if g else(a8<br);rg=(bi<a0)if g else(bi>a0)
   if((bi>a0 and mT and nh>E*0.08 and nk>E*0.08 and cJ<=cg)if g else(bi<a0 and mT and ni>E*0.08 and nj>E*0.08 and cI>=ch))and kH>E*0.3 and h9>E*0.3:return('HiddenBase_DP',N(cJ,M(a0,bi)-E*0.15)if g else N(ch,M(br,a8)-E*0.15),M(cg,N(br,a8)+E*0.15)if g else M(cI,N(a0,bi)+E*0.15),k)
   mera_ok=(cI>=cg and cJ<=ch and(cI>cg or cJ<ch)and((nk>=kH*0.85 and N(a0,bi)>=cJ and M(a0,bi)<=N(br,a8)+E*0.15)or(rg and a8>cg)if g else(nj>=kH*0.85 and M(a0,bi)<=cI and N(a0,bi)>=M(br,a8)-E*0.15)or(rg and a8<ch)))
   if mera_ok:return('MeraMera_QML_DP',cJ if g else N(a0,bi),M(a0,bi)if g else cI,k)
   if rg and mT and(a8>=a0 if g else a8<=a0)and h9>M(kH*1.05,E*0.38):return('BuE_Engulf_DP'if g else'BE_Engulf_DP',N(ch,cJ)if g else a0,a0 if g else M(cg,cI),k)
   if kH<=E*0.25 and mT and h9>E*0.45:return('Doji_DP',ch,cg,k-1)
   if mT and h9>E*0.38 and A((M(a0,bi)-N(br,a8))if g else(N(a0,bi)-M(br,a8)))<=E*0.1:return('WBS_DP',N(ch,cJ)if g else(N(a0,bi)+M(br,a8))/2.0-E*0.1,(M(a0,bi)+N(br,a8))/2.0+E*0.1 if g else M(cg,cI),k)
  return('Standart_Base',None,None,None)
 k9,bh=aa[-2]if g else ar[-2]
 if k9<3 or k9>=L(df)-3:return(l6,l9,l7,l8,hl)
 bP=next((k for k in G(k9+1,L(df)-2)if(_f(df,'close',k)>bh if g else _f(df,'close',k)<bh)),None)
 if bP is None:return(l6,l9,l7,l8,hl)
 hl['magic_line']=R(bh,5);fv='high'if g else'low';oQ=[v for r7,v in(ar if g else aa)if r7<bP];qM=sum((1 for dN in G(M(0,k9-2),N(L(df)-2,k9+3))if A(F(df[fv].iloc[dN])-bh)<=E*0.25));ma,nT=(False,'W_Model'if g else'M_Model')
 if L(oQ)>=2:
  lp,mU=(oQ[-2],oQ[-1]);pf=A(mU-lp)/M(lp,1e-09)
  if pf<=0.008:ma,nT=(True,'W_EsitIkiliDip'if g else'M_EsitIkiliTepe')
  elif(mU>lp if g else mU<lp)and pf<=0.018:ma,nT=(True,'W_SagAyakYuksek'if g else'M_SagOmuzAlcak')
  elif(mU<lp if g else mU>lp)and pf<=0.018:ma,nT=(True,'W_SolAyakYuksek_QML'if g else'M_SolOmuzAlcak_QML')
 hl['swing_modeli']=nT if ma else('Keskin_V_Shape'if g else'Keskin_Ters_V_Shape')if qM<=1 else('Yayvan_V_Shape'if g else'Yayvan_Ters_V_Shape')if qM<=4 else'Cup_U_Canak'if g else'Ters_Cup_U_Canak';cT=sum((1 for dN in G(M(0,k9-12),bP)if A(F(df[fv].iloc[dN])-bh)<=E*0.35));oR=cT>=3;hm,fI=(False,bP)
 if bP+4<L(df)-2:
  mb=df.iloc[bP+1:N(L(df)-2,bP+9)];q1=sum((1 for _,r in mb.iterrows()if(F(r['close'])<F(r['open'])if g else F(r['close'])>F(r['open']))))
  if g:
   if q1>=2 and F(mb['low'].min())<=bh+E*0.2 and(F(df['high'].iloc[bP+1:-1].max())>_f(df,'high',bP)+E*0.4):hm,fI=(True,int(mb['low'].idxmin()))
  elif q1>=2 and F(mb['high'].max())>=bh-E*0.2 and(F(df['low'].iloc[bP+1:-1].min())<_f(df,'low',bP)-E*0.4):hm,fI=(True,int(mb['high'].idxmax()))
 lL=df.iloc[bP];la,nU,rW,ph=_r(lL,'open','close','high','low');qN=nU-la if g else la-nU;oS=(la<bh<nU if g else nU<bh<la)and qN>=E*0.7 and(qN/M(rW-ph,1e-09)>=0.68);qO=fI if hm else bP;lM,eO,g8,fJ=_dpt(qO-1,qO+1);hl['dp_turu']=lM;eq=''if g else'Bear_'
 if hm:
  jF=f'{eq}Genis_FL_BaseKing'
  if g:gg=eO if eO is not None else _f(df,'low',fI);gh=g8 if g8 is not None else M(bh,gg+E*0.35)
  else:gh=g8 if g8 is not None else _f(df,'high',fI);gg=eO if eO is not None else N(bh,gh-E*0.35)
 elif oR:jF=f'{eq}WickingBase_FL';gg=eO if eO is not None else bh-E*(0.25 if g else 0.2);gh=g8 if g8 is not None else bh+E*(0.2 if g else 0.25)
 elif ma and lM!='Standart_Base':jF='W_Kink_FL'if g else'M_Kink_FL';gg=eO if eO is not None else bh-E*0.2;gh=g8 if g8 is not None else bh+E*0.2
 elif oS and lM=='Standart_Base':jF=f'{eq}BlindSpot_FL';gg=M(la,bh-E*0.3)if g else bh-E*0.2;gh=bh+E*0.2 if g else N(la,bh+E*0.3)
 else:jF=f'{eq}Dar_FL';gg=eO if eO is not None else bh-E*0.22;gh=g8 if g8 is not None else bh+E*0.22
 hl['fl_turu']=jF;dS=bb if g else bc;cU=ak>=gg if g else ak<=gh
 if gg-E*0.2<=dS<=gh+E*0.2 and cU:jV=f'{a}_{jF}+{lM}';l6.append(jV);l7.append(f"[{a}] {('Bullish' if g else 'Bearish')} {jF} (Magic Line: {bh:.4f} | Swing: {hl['swing_modeli']} | Sniper DP: {lM} [{gg:.4f}-{gh:.4f}]) (10,11,12.pdf & YT-Part4)");l8.append(('BB/FL',fJ if fJ else bP,gg,gh));l9=gg if g else gh
 return(l6,l9,l7,l8,hl)
def quasimodo_mpl_analizi(df,z,C,a='1H',B='BULLISH'):
 lc,iC,iD,dO=([],[],[],None);dg={'qm_tipi':'YOK','qml_seviyesi':None,'mpl_seviyesi':None,'yaklasim_modeli':'Standart','karsi_fresh_hedef':None};aa,ar=(z.get('highs',[]),z.get('lows',[]))
 if L(df)<22 or L(aa)<3 or L(ar)<3:return(lc,dO,iC,iD,dg)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);(hS,H0),(gd,H1),(hf,H2)=(aa[-3],aa[-2],aa[-1]);(hT,L0),(ge,L1),(hg,L2)=(ar[-3],ar[-2],ar[-1]);d0,d4=swing_noktalarini_bul(df.iloc[-26:],1);cu=[];g=B=='BULLISH';aX='Bullish'if g else'Bearish';dg['karsi_fresh_hedef']=R(M(H1,H2)if g else N(L1,L2),5);k4=d4 if g else d0;de=bb if g else bc
 if L(k4)>=2:
  nV=[v for _,v in k4[-4:]];fK=sum((1 for u in nV[:-1]if A(u-nV[-1])<=E*0.28))
  if fK>=1 and(bb<N(nV[:-1])if g else bc>M(nV[:-1]))and(L(C)>0):cu.append(f"Fakeout_{('S1S' if g else 'R1R')}{fK + 1}")
 if L(d4)>=2 and L(d0)>=2:
  if(d4[-1][1]<d4[-2][1]and d0[-1][1]>d0[-2][1])if g else(d0[-1][1]>d0[-2][1]and d4[-1][1]<d4[-2][1]):cu.append('Fakeout+QML_Kombo'if any(('Fakeout'in y for y in cu))else'QML_Yaklasimi')
 nK=df.iloc[-9:-2];cw,cP=(nK['high'].values,nK['low'].values);dT=F((nK['high']-nK['low']).mean());eG=_f(df,'open',-3)-_f(df,'close',-3)if g else _f(df,'close',-3)-_f(df,'open',-3)
 if L(cw)>=5 and(cw[-1]<cw[0]and cP[-1]<cP[0]if g else cw[-1]>cw[0]and cP[-1]>cP[0])and(dT<=E*1.15):cu.append('CPLQ_Compression+Liq'if eG>=E*0.7 else'CP_Compression')
 if L(k4)>=3:
  d1,d2,d3=(k4[-3][1],k4[-2][1],k4[-1][1])
  if d1>d2>d3 if g else d1<d2<d3:cu.append('ThreeDrive_3D')
 if L(d0)>=2 and L(d4)>=2:
  if(F(df['high'].iloc[-6:-2].max())>d0[-2][1]if g else bc>d0[-2][1])and(bb<d4[-2][1]if g else F(df['low'].iloc[-6:-2].min())<d4[-2][1]):cu.append('Diamond_PO3_Box')
 fw=(L2<L1 and(H2>H1 or ak>H1))if g else(H2>H1 and(L2<L1 or ak<L1))
 if fw:
  ku,gi,ol=(L1,ge,L2)if g else(H1,gd,H2);md=(L1>L0 and H1>H0)if g else(H1<H0 and L1<L0);dg['qml_seviyesi']=R(ku,5)
  cap_say=sum((1 for d_c in G(M(0,gi-3),N(L(df)-2,gi+4))if A(_f(df,'low'if g else'high',d_c)-ku)<=E*0.30))
  ist_imb=any((gi<=fi<=M(hg,hf)+2 and(_f(df,'low',N(L(df)-1,fi+1))<ku-E*0.10 if g else _f(df,'high',N(L(df)-1,fi+1))>ku+E*0.10))for fi in C)
  dg['istisnai_ob_uyarisi']=bool(ist_imb and A(ol-ku)>=E*0.35);dg['istisnai_ob_seviyesi']=R(ol,5)if dg['istisnai_ob_uyarisi']else None
  jW=(L0<L1 and L0<L2 and A(ku-(L0+(L2-L0)/M(hg-hT,1)*M(L(df)-2-hT,1)))<=E*0.45)if g else(H0>H1 and H0>H2 and A(ku-(H0+(H2-H0)/M(hf-hS,1)*M(L(df)-2-hS,1)))<=E*0.45);aE=''if g else'Bear_';pi=f'{aE}QMC_Hibrit'if md and jW else f'{aE}QMC'if md else(f'{aE}QMR_Cap'if cap_say>=3 else f'{aE}QMR')
  if(A(de-ku)<=E*0.5 or(dg['istisnai_ob_uyarisi']and(ol-E*0.2<=de<=ku+E*0.2 if g else ku-E*0.2<=de<=ol+E*0.2)))and(ak>=L2 if g else ak<=H2):
   dg['qm_tipi']=pi;lc.append(f"{a}_{('Bull_' if g else '')}{pi}")
   if dg['istisnai_ob_uyarisi']:lc.append(f"{a}_{aE}QML_Ustu_Imb_IstisnaiOB")
   pQ=(' | İstisnai OB Ayrışması: '+f'{ol:.4f}'if dg['istisnai_ob_uyarisi']else'')+(' | Yaklaşım: '+'+'.join(cu)if cu else'')
   iC.append(f'[{a}] {aX} {pi} (Sol Omuz QML: {ku:.4f}, Baş/OB: {ol:.4f}{pQ}) (13,14.pdf & YT-Part5)');iD.append(('QML',gi,N(ku-E*0.18,ol)if dg['istisnai_ob_uyarisi']and g else ku-E*0.18,M(ku+E*0.18,ol)if dg['istisnai_ob_uyarisi']and not g else ku+E*0.18));dO=ol if dO is None else(N(dO,ol)if g else M(dO,ol))
 jG=(H1>H0 and L1<L0 and ak>H0 and F(df['close'].iloc[M(gd,ge):-1].max())>H1 and A(bb-H0)<=E*0.42)if g else(L1<L0 and H1>H0 and ak<L0 and F(df['close'].iloc[M(gd,ge):-1].min())<L1 and A(bc-L0)<=E*0.42)
 if jG:lq,mV=(H0,hS)if g else(L0,hT);dg['qm_tipi'],dg['qml_seviyesi']=('QMM_Flip'if g else'Bear_QMM_Flip',R(lq,5));lc.append(f"{a}_{('Bull' if g else 'Bear')}_QMM_Flip");iC.append(f'[{a}] {aX} QMM (Çalışmayan QML/OBO-TOBO [{lq:.4f}] kırıldı ve Flip oldu!) (YT-Part5)');iD.append(('QML',mV,lq-E*0.18,lq+E*0.18));pj=lq-E*0.4 if g else lq+E*0.4;dO=pj if dO is None else(N(dO,pj)if g else M(dO,pj))
 for k in G(M(4,L(df)-24),L(df)-4):
  ld=df.iloc[k+1]
  if g:
   lv,je=(_f(df,'low',k-2),_f(df,'low',k))
   if je<lv and F(ld['close'])-F(ld['open'])>E*0.55 and F(ld['close'])>_f(df,'high',k-1):
    oB=F(df['close'].iloc[k+2:-2].min())if k+2<L(df)-2 else lv
    if oB>=je and je-E*0.15<=bb<=lv+E*0.2 and ak>=je:dg['mpl_seviyesi']=R(lv,5);dg['qm_tipi']='MPL_IntermediateQML'if dg['qm_tipi']=='YOK'else dg['qm_tipi'];lc.append(f'{a}_Bull_MPL');iC.append(f'[{a}] Bullish MPL (Intermediate QML: {lv:.4f}, Stop: {je:.4f}) (15.pdf & YT-Part5)');iD.append(('QML',k,je,lv));dO=je if dO is None else N(dO,je);break
  else:
   lx,jf=(_f(df,'high',k-2),_f(df,'high',k))
   if jf>lx and F(ld['open'])-F(ld['close'])>E*0.55 and F(ld['close'])<_f(df,'low',k-1):
    oC=F(df['close'].iloc[k+2:-2].max())if k+2<L(df)-2 else lx
    if oC<=jf and lx-E*0.2<=bc<=jf+E*0.15 and ak<=jf:dg['mpl_seviyesi']=R(lx,5);dg['qm_tipi']='Bear_MPL_IntermediateQML'if dg['qm_tipi']=='YOK'else dg['qm_tipi'];lc.append(f'{a}_Bear_MPL');iC.append(f'[{a}] Bearish MPL (Intermediate QML: {lx:.4f}, Stop: {jf:.4f}) (15.pdf & YT-Part5)');iD.append(('QML',k,lx,jf));dO=jf if dO is None else M(dO,jf);break
 if cu:dg['yaklasim_modeli']=' + '.join(cu)
 return(lc,dO,iC,iD,dg)
def imbalance_fvg_koku_analizi(df,z,C,a='1H',B='BULLISH'):
 hu,hv,jX,dp=([],[],[],None);g4={'imbalance_tipi':'YOK','acik_imbalance_sayisi':L(C),'fvg_origin_koku':None,'erken_donus_fake_choch_uyarisi':False,'three_drive_d3_onay':False}
 if L(df)<25:return(hu,dp,hv,jX,g4)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);aa,ar=(z.get('highs',[]),z.get('lows',[]));a6=z.get('strong_point');g=B=='BULLISH';aX='Bullish'if g else'Bearish'
 for i in G(M(3,L(df)-36),L(df)-3):
  m0,m1,m2=(df.iloc[i-1],df.iloc[i],df.iloc[i+1]);c5,c6=(F(m0['high']),F(m0['low']));bB,cD,bC,bD=_r(m1,'open','close','high','low');aM,aD,cG,cH=_r(m2,'open','close','high','low');iF=df['low'if g else'high'].iloc[i+2:-2];jY=(cH>c5 and cD-bB>E*0.45 and not(not iF.empty and F(iF.min())<=c5))if g else(c6>cG and bB-cD>E*0.45 and not(not iF.empty and F(iF.max())>=c6))
  if jY:
   jg,ji=(N(c6,bD),c5)if g else(c6,M(c5,bC));g4['fvg_origin_koku']=R(ji if g else jg,5)
   if(jg-E*0.15<=bb<=ji+E*0.2 and ak>=jg)if g else(jg-E*0.2<=bc<=ji+E*0.15 and ak<=ji):g4['imbalance_tipi']=f"{('' if g else 'Bear_')}FVG+OriginKoku";hu.append(f"{a}_{('' if g else 'Bear_')}FVG_OriginKoku");hv.append(f'[{a}] {aX} FVG + Orijin Kök Testi ({jg:.4f}-{ji:.4f}) (19.pdf & YT-Part6)');jX.append(('FVG',i-1,jg,ji));dp=(jg if dp is None else N(dp,jg))if g else(ji if dp is None else M(dp,ji));break
  me=(cD>bB and aD>aM and aD-bB>=E*1.15 and cH<=c5 and not(not iF.empty and F(iF.min())<=bB))if g else(cD<bB and aD<aM and bB-aD>=E*1.15 and cG>=c6 and not(not iF.empty and F(iF.max())>=bB))
  if me:
   kI,kJ=(c6,bB)if g else(bB,c5)
   if(kI-E*0.15<=bb<=kJ+E*0.2 and ak>=kI)if g else(kI-E*0.2<=bc<=kJ+E*0.15 and ak<=kJ):g4['imbalance_tipi']=f"{('' if g else 'Bear_')}LiquidityVoid+OriginKoku";hu.append(f"{a}_{('' if g else 'Bear_')}LiqVoid_OriginKoku");hv.append(f'[{a}] {aX} Liquidity Void (2 Mumluk Boşluk) + Orijin Kök Testi ({kI:.4f}-{kJ:.4f}) (YT-Part6)');jX.append(('FVG',i-1,kI,kJ));dp=(kI if dp is None else N(dp,kI))if g else(kJ if dp is None else M(dp,kJ));break
 for i in G(M(4,L(df)-34),L(df)-6):
  nW=df.iloc[i];hw=A(F(nW['close'])-F(nW['open']));bV,bU=(F(nW['low']),F(nW['high']));fL=df.iloc[i+2:N(L(df)-2,i+14)];mf=(_f(df,'open',i-1)-_f(df,'close',i-1))if g else(_f(df,'close',i-1)-_f(df,'open',i-1));jZ=(_f(df,'open',i+1)-_f(df,'close',i+1))if g else(_f(df,'close',i+1)-_f(df,'open',i+1))
  if mf>E*0.45 and hw<=E*0.5 and jZ>E*0.45:
   gj=any((_f(fL,'close',m)>bU+E*0.15 and _f(fL,'close',m)-_f(fL,'open',M(0,m-1))>E*0.9 for m in G(L(fL))))if g else any((_f(fL,'close',m)<bV-E*0.15 and _f(fL,'open',M(0,m-1))-_f(fL,'close',m)>E*0.9 for m in G(L(fL))))
   if gj and(bV-E*0.15<=(bb if g else bc)<=bU+E*0.15)and(ak>=bV if g else ak<=bU):jj='TersBayrak_DBD_Flip'if g else'Bear_TersBayrak_RBR_Flip';g4['imbalance_tipi']=jj;hu.append(f'{a}_{jj}');hv.append(f'[{a}] {aX} Ters Bayrak (Kırılan DBD/RBR Base / IFVG Kaynağı: {bV:.4f}-{bU:.4f}) Flip Oldu! (YT-Part6)');jX.append(('IFVG',i,bV,bU));dp=(bV if dp is None else N(dp,bV))if g else(bU if dp is None else M(dp,bU));break
 nL=ar if g else aa
 if L(nL)>=3:
  d1,d2,d3=(nL[-3][1],nL[-2][1],nL[-1][1])
  if(d1>d2>d3 if g else d1<d2<d3)and(L(hu)>0 or(a6 and A((bb if g else bc)-a6)<=E*0.6)):g4['three_drive_d3_onay']=True;hu.append(f"{a}_{('' if g else 'Bear_')}ThreeDrive_D3_FreshPOI");hv.append(f'[{a}] {aX} Three Drive ({d1:.4f}->{d2:.4f}->{d3:.4f}) 3. Adımı Taze POI Bölgesiyle Çakıştı (YT-Part6)')
 if a6 and L(C)>0:
  nX=F(df['low'].iloc[-8:-2].min())if g else F(df['high'].iloc[-8:-2].max());fM=(a6+E*0.25<nX<=a6+E*1.15 and bb<=nX)if g else(a6-E*1.15<=nX<a6-E*0.25 and bc>=nX)
  if fM:hu.append(f"{a}_{('' if g else 'Bear_')}FakeCHoCH_Sweep_Onayi");hv.append(f'[{a}] {aX} Erken Dönüş Likiditesi Süpürüldü: Ana bölge ({a6:.4f}) önü stop birikimi temizlendi! (YT-Part6)')
  elif(bb>a6+E*0.35 if g else bc<a6-E*0.35)and L(hu)==0:g4['erken_donus_fake_choch_uyarisi']=True
 return(hu,dp,hv,jX,g4)
def gap_vib_fibo_analizi(df,z,Z,a='1H',B='BULLISH'):
 g9,fl,lf,fm=([],[],[],None);er={'gap_vib_durumu':'YOK','fibo_05_saygi':False,'fibo_istasyon_uyumu':'YOK','manipulasyon_236_382':False}
 if L(df)<25:return(g9,fm,fl,lf,er)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);hb,fN=(z.get('swing_max',0.0),z.get('swing_min',0.0));dU=hb-fN;qP=z.get('break_line_fl');g=B=='BULLISH';aX='Bullish'if g else'Bearish';de=bb if g else bc
 if dU>E*1.5 and sum((1 for k in G(M(2,L(df)-32),L(df)-4)if A(_f(df,'close',k)-(fN+dU*0.5))<=E*0.28))>=2:er['fibo_05_saygi']=True
 for i in G(M(3,L(df)-30),L(df)-3):
  c1,c2=(df.iloc[i-1],df.iloc[i]);a0,bi,cg,ch=_r(c1,'open','close','high','low');br,a8,cI,cJ=_r(c2,'open','close','high','low');nY=br-bi;cP,cw=(N(bi,br),M(bi,br));fo=df['low'if g else'high'].iloc[i+1:-2];j0=(nY>=E*0.08 and a8>bi and not(not fo.empty and F(fo.min())<cP-E*0.05))if g else(nY<=-E*0.08 and a8<bi and not(not fo.empty and F(fo.max())>cw+E*0.05))
  if j0 and cP-E*0.2<=de<=cw+E*0.2 and(ak>=cP if g else ak<=cw):rh=cJ>cg if g else cI<ch;r6=qP is not None and A((cP if g else cw)-qP)<=E*0.6;aE=''if g else'Bear_';lr=f'{aE}Breakaway_Gap'if rh and r6 else f'{aE}Runaway_Gap'if rh else f"{('Bull' if g else 'Bear')}_VIB";er['gap_vib_durumu']=lr;g9.append(f'{a}_{lr}');fl.append(f'[{a}] {aX} {lr} Testi ({cP:.4f}-{cw:.4f}) (20.pdf & YT-Part7)');lf.append(('FVG',i,cP,cw));fm=(cP if fm is None else N(fm,cP))if g else(cw if fm is None else M(fm,cw));break
  hx=(nY<=-E*0.08 and a8>cg and cP-E*0.18<=bb<=cw+E*0.18 and ak>=cP)if g else(nY>=E*0.08 and a8<ch and cP-E*0.18<=bc<=cw+E*0.18 and ak<=cw)
  if hx:lr='Bull_VIB_Flip'if g else'Bear_VIB_Flip';er['gap_vib_durumu']=lr;g9.append(f'{a}_{lr}');fl.append(f'[{a}] {aX} VIB Flip ({cP:.4f}-{cw:.4f}): Ters Volume Imbalance yutulup Flip oldu! (YT-Part7)');lf.append(('IFVG',i,cP,cw));fm=(cP if fm is None else N(fm,cP))if g else(cw if fm is None else M(fm,cw));break
 ff=z.get('geri_cekilme_oran'if g else'fibo_oran',0.5);nM=' + 0.50 AvgPrice Saygılı'if er['fibo_05_saygi']else''
 if 0.21<=ff<=0.41 and any((x in p for p in Z for x in('FTR','FirstObstacle_FO'))):er['fibo_istasyon_uyumu']=f'GucluTrend_236_382_FTR_FO({ff:.3f})';g9.append(f'{a}_Fibo236_382_GucluTrend_FTR_FO');fl.append(f'[{a}] Güçlü Trend 0.236-0.382 ({ff:.3f}) + FTR/FO Eşleşmesi{nM} (YT-Part7)')
 elif 0.48<=ff<=0.64 and any((x in p for p in Z for x in('FL','BB/FL','TersBayrak'))):er['fibo_istasyon_uyumu']=f'GoldenZone_05_618_FL({ff:.3f})';g9.append(f'{a}_Fibo05_618_FL_Onayi');fl.append(f'[{a}] Sihirli Fibo 0.50-0.618 ({ff:.3f}) + Flag Limit Eşleşmesi{nM} (YT-Part7)')
 elif 0.68<=ff<=0.82 and any((x in p for p in Z for x in('OB','Valid','QML','QMR','QMC','ITZ','MPL'))):er['fibo_istasyon_uyumu']=f'OTE_705_786_OB_QML_ITZ({ff:.3f})';g9.append(f'{a}_Fibo705_786_OB_QML_Onayi');fl.append(f'[{a}] Sihirli Fibo OTE 0.705-0.786 ({ff:.3f}) + OB/QML/ITZ/Valid Eşleşmesi{nM} (YT-Part7)')
 elif 0.84<=ff<=0.94 and any((x in p for p in Z for x in('OB','Valid','QML','QMR'))):er['fibo_istasyon_uyumu']=f'Istisnai_886_DerinOB({ff:.3f})';g9.append(f'{a}_Fibo886_Istisnai_DerinOB');fl.append(f'[{a}] Sihirli Fibo 0.886 ({ff:.3f}) İstisnai Derin OB{nM} (YT-Part7)')
 if dU>E*2.0 and L(df)>=28:
  q2=df.iloc[-16:-4];mW,mX=(F(q2['high'].max()),F(q2['low'].min()))
  if mW-mX<=E*3.2:
   if g and mX<=fN+dU*0.382 and bb<mX and ak>=mX:er['manipulasyon_236_382']=True;g9.append(f'{a}_Bull_236_382_Manipulasyon_PO3');fl.append(f'[{a}] Bullish 0.236-0.382 Sıkıştırma Manipülasyonu & -0.236 Devyasyon Dönüşü ({mX:.4f}) (YT-Part7)')
   elif not g and mW>=hb-dU*0.382 and bc>mW and ak<=mW:er['manipulasyon_236_382']=True;g9.append(f'{a}_Bear_236_382_Manipulasyon_PO3');fl.append(f'[{a}] Bearish 0.236-0.382 Sıkıştırma Manipülasyonu & -0.236 Devyasyon Dönüşü ({mW:.4f}) (YT-Part7)')
 return(g9,fm,fl,lf,er)
def likidite_ve_sfp_analizi(bJ,af,a2,Z,B='BULLISH'):
 lg,lh,li=([],[],0);dh={'external_likidite_hedefi':None,'internal_ilk_engel_hedefi':None,'sfp_durumu':'YOK','likidite_turu':'YOK','akis_protokolu_onay':False}
 if L(bJ)<20 or L(af)<20:return(li,lg,lh,dh)
 pl,pm=(a2.get('highs',[]),a2.get('lows',[]));nZ,n0=swing_noktalarini_bul(af,n=2);d0,d4=swing_noktalarini_bul(af,n=1);lN=af.iloc[-2];d6,iG,n1,n2=(F(lN['close']),F(lN['open']),F(lN['high']),F(lN['low']));jH=M(F(lN['atr']),d6*0.001);qQ=M(_f(bJ,'atr',-2),d6*0.001);a6=a2.get('strong_point');g=B=='BULLISH';nN=M([h for _,h in pl[-3:]],default=d6*1.03)if g else N([l for _,l in pm[-3:]],default=d6*0.97);dh['external_likidite_hedefi']=R(nN,5);fx=[h for _,h in nZ[-4:]if d6+jH*0.5<h<nN]if g else[l for _,l in n0[-4:]if nN<l<d6-jH*0.5];dh['internal_ilk_engel_hedefi']=R((N(fx)if g else M(fx))if fx else nN,5);k5=n0 if g else nZ;fy=d4 if g else d0
 if L(k5)>=2:
  u1,u2=(k5[-1][1],k5[-2][1]);n3=A(u1-u2)<=jH*0.28;mg=(N(u1,u2)if g else M(u1,u2))if n3 else u1;j1=(n2<mg and d6>mg and N(iG,d6)-n2>=jH*0.2)if g else(n1>mg and d6<mg and n1-M(iG,d6)>=jH*0.2)
  if j1:pR=('Bull_EQL_SFP'if n3 else'Bull_OldLow_SFP')if g else('Bear_EQH_SFP'if n3 else'Bear_OldHigh_SFP');dh['sfp_durumu'],dh['likidite_turu']=(pR,('EQL'if g else'EQH')+'_StopPool'if n3 else('OldLow'if g else'OldHigh')+'_StopPool');lg.append(pR);lh.append(f'[{LTF_PERIYOT}] {pR}: {mg:.4f} likiditesi iğneyle süpürüldü ve içeride ({d6:.4f}) kapandı! (23.pdf & YT-Part8)');li+=6
 if a6 and L(fy)>=2:
  om,on=(fy[-1][1],fy[-2][1]);mh=N(om,on)if g else M(om,on);fO=(A(om-on)<=jH*0.3 and a6<mh<=a6+qQ*1.1 and n2<mh and d6>=a6)if g else(A(om-on)<=jH*0.3 and a6-qQ*1.1<=mh<a6 and n1>mh and d6<=a6)
  if fO:dh['likidite_turu']='Yakin_EQL+Imbalance_Sweep'if g else'Yakin_EQH+Imbalance_Sweep';lg.append('Bull_YakinEQL_Imb_Sweep'if g else'Bear_YakinEQH_Imb_Sweep');lh.append(f'[{MTF_PERIYOT.upper()}/{LTF_PERIYOT}] Valid Bölge ({a6:.4f}) Önü Yakın EQL/EQH ({mh:.4f}) + Imbalance İğneyle Süpürüldü! (YT-Part8)');li+=5
 if L(k5)>=3:
  (x0,y0),(x1,y1)=(k5[-3],k5[-2])
  if(y1>y0 if g else y1<y0)and x1>x0:
   gl=y1+(y1-y0)/M(x1-x0,1)*M(L(af)-2-x1,1)
   if(n2<gl and d6>gl)if g else(n1>gl and d6<gl):
    if dh['likidite_turu']=='YOK':dh['likidite_turu']='Trendline_Liquidity_Sweep'if g else'Bear_Trendline_Liquidity_Sweep'
    lg.append('Bull_TrendlineLiq_SFP'if g else'Bear_TrendlineLiq_SFP');lh.append(f'[{LTF_PERIYOT}] Trend Çizgisi Likiditesi ({gl:.4f}) iğneyle süpürüldü ve içeride kapandı! (YT-Part8)');li+=4
 if L(Z)>0 and(dh['sfp_durumu']!='YOK'or dh['likidite_turu']!='YOK'):dh['akis_protokolu_onay']=True;lg.append('AkisProtokolu_POI+LiqSweep'if g else'Bear_AkisProtokolu_POI+LiqSweep');lh.append(f"[{MTF_PERIYOT.upper()}/{LTF_PERIYOT}] 4 Adımlı Akış Protokolü: Taze POI + Likidite Süpürmesi -> İlk Engel: {dh['internal_ilk_engel_hedefi']}, Ext Hedef: {dh['external_likidite_hedefi']} (YT-Part8)");li+=4
 return(li,lg,lh,dh)
def range_po3_tt3_analizi(df,z,C,a='1H',B='BULLISH'):
 hy,fP,iH,cX=([],[],[],None);fg={'range_aktif':False,'r_low':None,'r_high':None,'r_050_avg':None,'r_025':None,'r_075':None,'dev_272_ust':None,'dev_272_alt':None,'dev_500_ust':None,'dev_500_alt':None,'avg_050_saygi':False,'range_modu':'YOK','tt3_durumu':'YOK','asya_monday_po3':'YOK','dinamit_hedef':False}
 if L(df)<26:return(hy,cX,fP,iH,fg)
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);aa,ar=(z.get('highs',[]),z.get('lows',[]));g=B=='BULLISH';aX='Bullish'if g else'Bearish';aE=''if g else'Bear_';qR=df.iloc[-28:-5];hc,cx=(F(qR['high'].max()),F(qR['low'].min()));fh=hc-cx;qS=sum((1 for _,v in aa[-5:]if A(v-hc)<=E*0.45));qT=sum((1 for _,v in ar[-5:]if A(v-cx)<=E*0.45));de=bb if g else bc
 if E*1.6<=fh<=E*9.5 and qS+qT>=3:
  hW,mY,mZ=(cx+fh*0.5,cx+fh*0.25,cx+fh*0.75);ri,rj=(cx+fh*1.272,cx-fh*0.272);rk,rl,rm,rn=(cx+fh*1.414,cx+fh*1.618,cx-fh*0.414,cx-fh*0.618);pS,pT=(cx+fh*1.5,cx-fh*0.5);q3=sum((1 for k in G(M(2,L(df)-26),L(df)-3)if A(_f(df,'close',k)-hW)<=E*0.25 or A(_f(df,'low',k)-hW)<=E*0.18 or A(_f(df,'high',k)-hW)<=E*0.18))>=3;fg.update({'range_aktif':True,'r_low':R(cx,5),'r_high':R(hc,5),'r_050_avg':R(hW,5),'r_025':R(mY,5),'r_075':R(mZ,5),'dev_272_ust':R(ri,5),'dev_272_alt':R(rj,5),'dev_500_ust':R(pS,5),'dev_500_alt':R(pT,5),'avg_050_saygi':q3,'dinamit_hedef':bool((qS>=2 if g else qT>=2)and L(C)>0)});oo,op=(F(df['low'].iloc[-6:-1].min()),F(df['high'].iloc[-6:-1].max()));eP=rj if g else ri;n4=cx if g else hc
  if A(de-eP)<=E*0.35 and(ak>=cx if g else ak<=hc):fg['range_modu']=f'{aE}RangeDev_272_SFP';hy.append(f'{a}_{aE}RangeDev_272_SFP');fP.append(f'[{a}] {aX} Range 272 Devyasyon İğne/SFP Dönüşü ({eP:.4f} -> Sınır:{n4:.4f}, Avg:{hW:.4f}) (24,25.pdf & YT-Part9)');iH.append(('BB/FL',L(df)-4,N(eP,n4),M(eP,n4)));cX=eP-E*0.25 if g else eP+E*0.25
  elif(rn-E*0.2<=bb<=rm+E*0.2 and ak>=pT)if g else(rk-E*0.2<=bc<=rl+E*0.2 and ak<=pS):qv,rJ,rK=(pT,rn,rm)if g else(pS,rk,rl);fg['range_modu']=f'{aE}RangeDev_414_618_ABCD';hy.append(f'{a}_{aE}RangeDev_414_618_ABCD');fP.append(f'[{a}] {aX} Range 414/500/618 Yarım Devyasyon (AB=CD) + POI Dönüşü ({qv:.4f}) (YT-Part9)');iH.append(('OB',L(df)-4,rJ,rK));cX=rJ-E*0.25 if g else rK+E*0.25
  q4=sum((1 for k in G(-6,-2)if(_f(df,'low',k)<cx if g else _f(df,'high',k)>hc)));d7=(F(df['high'].iloc[-14:-5].max())>hc)if g else(F(df['low'].iloc[-14:-5].min())<cx);d8=(oo<cx and ak>cx and cx-E*0.18<=bb<=mY+E*0.12)if g else(op>hc and ak<hc and mZ-E*0.12<=bc<=hc+E*0.18)
  if d8:pU=f'{aE}PO3_Igne+Devyasyon_ReEntry'if d7 and q4>=2 else f'{aE}PO3_Box_ReEntry_Test'if q4>=2 else f'{aE}Range_ReEntry_Test';fg['range_modu']=pU;hy.append(f'{a}_{pU}');fP.append(f'[{a}] {aX} {pU}: Range sınırı ({n4:.4f}) manipülasyonu sonrası içeri girildi ve sınır testi tamamlandı! (25.pdf & YT-Part9)');iH.append(('BB/FL',L(df)-5,oo if g else mZ,mY if g else op));cX=(oo if cX is None else N(cX,oo))if g else(op if cX is None else M(cX,op))
  if q3 and A(de-hW)<=E*0.28 and(ak>=hW if g else ak<=hW)and L(C)>0:fg['range_modu']=f'{aE}Range_050_AvgPrice_Kalp_POI';hy.append(f'{a}_{aE}Range_050_AvgPrice_POI');fP.append(f"[{a}] {aX} Range'in Kalbi 0.50 Average Price ({hW:.4f}) + Taze POI Onayı (YT-Part9)");cX=(mY if cX is None else N(cX,mY))if g else(mZ if cX is None else M(cX,mZ))
 oT=ar if g else aa
 if L(oT)>=2:
  (qp,e9),(r8,cj)=(oT[-2],oT[-1]);d9=(e9-cj)if g else(cj-e9)
  if 0<d9<=E*1.1 and(A(de-e9)<=E*0.32 or A(de-cj)<=E*0.28)and(ak>=cj if g else ak<=cj):gm='+Imbalance'if L(C)>0 else'';gn=f"{('Bull' if g else 'Bear')}_TT3_ThreeTap{gm}";fg['tt3_durumu']=gn;hy.append(f'{a}_{gn}');fP.append(f'[{a}] {aX} Three Tap Setup (TT3: 1.Temas {e9:.4f} -> 2.Temas Sweep {cj:.4f} -> 3.Temas Giriş{gm}) (27.pdf & YT-Part9)');iH.append(('QML',qp,N(e9,cj),M(e9,cj)));cX=(cj-E*0.25 if cX is None else N(cX,cj-E*0.25))if g else(cj+E*0.25 if cX is None else M(cX,cj+E*0.25))
 if'timestamp'in df.columns:
  try:
   e6=pd.to_datetime(df['timestamp'],unit='ms',utc=True);oq=e6.iloc[-2];ro=int(oq.hour);pV=df.loc[(e6.dt.date==oq.date())&(e6.dt.hour<6)]
   if L(pV)>=3 and 6<=ro<=17:
    nw,nx=(F(pV['high'].max()),F(pV['low'].min()));gC=nw-nx
    if E*0.8<=gC<=E*4.5:
     jt='Londra_Killzone'if ro<=11 else'NY_Killzone';ju=df.loc[(e6.dt.date==oq.date())&(e6.dt.hour>=6)];ih=(F(ju['low'].min())<nx and ak>nx and bb<=nx+gC*0.5)if g else(F(ju['high'].max())>nw and ak<nw and bc>=nw-gC*0.5)
     if ih:rT=f"Asya_{jt}_{('Bull' if g else 'Bear')}_PO3";fg['asya_monday_po3']=rT;hy.append(f'{a}_{rT}');fP.append(f'[{a}] Asya Range ({nx:.4f}-{nw:.4f}) {jt} Manipülasyonu & PO3 İçeri Giriş! (26.pdf & YT-Part9)')
   pW=df.loc[e6.dt.weekday==0]
   if oq.weekday()in(1,2,3,4)and L(pW)>=3:
    oL,oM=(F(pW['high'].max()),F(pW['low'].min()));kK=(F(df['low'].iloc[-8:-1].min())<oM and ak>oM and A(bb-oM)<=E*0.8)if g else(F(df['high'].iloc[-8:-1].max())>oL and ak<oL and A(bc-oL)<=E*0.8)
    if kK:gN=f"Monday_Range_{('Bull' if g else 'Bear')}_PO3";fg['asya_monday_po3']=gN;hy.append(f'{a}_{gN}');fP.append(f'[{a}] Monday Range ({oM:.4f}-{oL:.4f}) Devyasyon Süpürmesi & PO3 İçeri Giriş! (YT-Part9)')
   # YT-Part14: Day Open (Kripto UTC 00:00 / TR 03:00) & ATC Stratejisi (Frankfurt 05:50, London 06:50, CME 12:20, NY 13:20, NY Close 20:50, Tokyo 23:50 UTC)
   gun_acilisi_df=df.loc[(e6.dt.date==oq.date())&(e6.dt.hour==0)]
   if not gun_acilisi_df.empty:
    day_open_v=F(gun_acilisi_df['open'].iloc[0]);fg['day_open']=R(day_open_v,5)
    if A(de-day_open_v)<=E*0.32 and(ak>=day_open_v if g else ak<=day_open_v)and L(C)>0:
     do_kod=f"DayOpen_ATC_{('Bull'if g else'Bear')}_Test"
     hy.append(f'{a}_{do_kod}');fP.append(f'[{a}] Günlük Açılış (Day Open TR 03:00 / UTC 00:00: {day_open_v:.4f}) + Taze POI Testi! (36.pdf & YT-Part14)')
   atc_saatleri=[(6,'Frankfurt_ATC'),(7,'London_ATC'),(12,'CME_Chicago_ATC'),(13,'NewYork_ATC'),(21,'NY_Close_ATC'),(0,'Tokyo_ATC')]
   for atc_h,atc_ad in atc_saatleri:
    atc_dilim=df.loc[(e6.dt.hour==atc_h)&(e6.index<L(df)-3)].tail(4)
    if L(atc_dilim)>=1:
     atc_idx=int(atc_dilim.index[-1])
     if 2<=atc_idx<=L(df)-4:
      atc_lo,atc_hi=(F(df['low'].iloc[atc_idx]),F(df['high'].iloc[atc_idx]))
      sonraki_c=F(df['close'].iloc[N(L(df)-2,atc_idx+2)])
      imb_cikis=(sonraki_c>atc_hi+E*0.45)if g else(sonraki_c<atc_lo-E*0.45)
      if imb_cikis and(atc_lo-E*0.20<=de<=atc_hi+E*0.20)and(ak>=atc_lo if g else ak<=atc_hi):
       atc_k=f"{atc_ad}_{('Bull'if g else'Bear')}_Retest"
       fg['atc_bolgesi']=f"{atc_ad}[{atc_lo:.4f}-{atc_hi:.4f}]"
       hy.append(f'{a}_{atc_k}');fP.append(f'[{a}] {atc_ad} Algoritmik Eşleşme Bölgesi ({atc_lo:.4f}-{atc_hi:.4f}) İmbalanslı Çıkış Sonrası Retest Onayı! (YT-Part14)')
       iH.append(('BB/FL',atc_idx,atc_lo,atc_hi));cX=(atc_lo-E*0.20 if cX is None else N(cX,atc_lo-E*0.20))if g else(atc_hi+E*0.20 if cX is None else M(cX,atc_hi+E*0.20));break
  except X:pass
 return(hy,cX,fP,iH,fg)
def bobin_atnali_mw_analizi(df,z,C,a='1H',B='BULLISH'):
 cy,b9,cz,aL=([],[],[],None);bQ={'bobin_durumu':'YOK','bobin_alt':None,'bobin_ust':None,'atnali_testere':'YOK','mw_modeli':'YOK','momentum_marubozu':'YOK','yingyang_hidden_base':'YOK','giris_onay_tipi':'YOK'}
 if L(df)<24:return(cy,aL,b9,cz,bQ)
 bb,bc,ak,pn=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2),_f(df,'open',-2));E=M(_f(df,'atr',-2),ak*0.001);aa,ar=(z.get('highs',[]),z.get('lows',[]));g=B=='BULLISH';aX='Bullish'if g else'Bearish';aE=''if g else'Bear_';de=bb if g else bc
 for i in G(M(4,L(df)-26),L(df)-3):
  if i+3>=L(df)-1:break
  po=df.iloc[i:i+4];iI=[1 if F(r['close'])>=F(r['open'])else-1 for _,r in po.iterrows()];bU=F(po[['open','close']].max(axis=1).max());bV=F(po[['open','close']].min(axis=1).min());mi=bU-bV;cY=all((iI[k]!=iI[k+1]for k in G(L(iI)-1)))or(L(set(iI[:3]))==2 and iI[0]==iI[2]and iI[0]!=iI[1])
  if cY and E*0.18<=mi<=E*1.85:
   bQ['bobin_alt'],bQ['bobin_ust']=(R(bV,5),R(bU,5));pX=i+3
   if pX>=L(df)-4:
    ia=(ak>bU and(bb<=bU+E*0.18 or _f(df,'low',-3)<=bU+E*0.18))if g else(ak<bV and(bc>=bV-E*0.18 or _f(df,'high',-3)>=bV-E*0.18))
    if ia:gO=f'{aE}Bobin_Cozulme_IgneTest';bQ['bobin_durumu']=gO;cy.append(f'{a}_{gO}');b9.append(f'[{a}] {aX} Bobin (3-4 Mumlu Gövde Kümesi: {bV:.4f}-{bU:.4f}) Çözüldü & Anlık İğne Testi Tamamlandı! (28-bobinler.pdf & YT-Part10)');cz.append(('BB/FL',i,bV,bU));aL=(bV-E*0.2 if aL is None else N(aL,bV-E*0.2))if g else(bU+E*0.2 if aL is None else M(aL,bU+E*0.2))
   else:
    fo=df.iloc[pX+1:-2];gj=any((F(r['close'])>bU+E*0.35 if g else F(r['close'])<bV-E*0.35 for _,r in fo.iterrows()));qa=any((F(r['close'])<bV-E*0.15 if g else F(r['close'])>bU+E*0.15 for _,r in fo.iterrows()))
    if gj and not qa and bV-E*0.2<=de<=bU+E*0.2 and(ak>=bV if g else ak<=bU):gO=f'{aE}Bobin_Bolge_Testi_POI';bQ['bobin_durumu']=gO;cy.append(f'{a}_{gO}');b9.append(f'[{a}] {aX} Bobin Bölge Testi (HTF Bobin = LTF Range Gövde Kutusu: {bV:.4f}-{bU:.4f}) Taze POI Olarak Çalıştı! (28.pdf & YT-Part10)');cz.append(('OB',i,bV,bU));aL=(bV-E*0.2 if aL is None else N(aL,bV-E*0.2))if g else(bU+E*0.2 if aL is None else M(aL,bU+E*0.2))
    for r9 in G(pX+1,L(df)-2):
     tm=df.iloc[r9];nE,nF,k2,k3=_r(tm,'open','close','high','low');ep=(k3<bV-E*0.15 and N(nE,nF)>=bV and ak>bU)if g else(k2>bU+E*0.15 and M(nE,nF)<=bU and ak<bV)
     if ep:nG=f'{aE}Testere_DerinIgne_Bobin';bQ['atnali_testere']=nG;cy.append(f'{a}_{nG}');b9.append(f'[{a}] {aX} Testere (Bobin [{bV:.4f}-{bU:.4f}] Derin İğneyle Yıpratıldı ve Karşı Yöne Dolduruldu!) (28.pdf & YT-Part10)');aL=(k3-E*0.15 if aL is None else N(aL,k3-E*0.15))if g else(k2+E*0.15 if aL is None else M(aL,k2+E*0.15));break
 for k in G(M(4,L(df)-16),L(df)-2):
  if k+3>=L(df)-1:break
  c0,c1,c2,c3=(df.iloc[k],df.iloc[k+1],df.iloc[k+2],df.iloc[k+3]);hX,m4,a0,bi,br,a8,m5,hY=(F(c0['open']),F(c0['close']),F(c1['open']),F(c1['close']),F(c2['open']),F(c2['close']),F(c3['open']),F(c3['close']));pY,pZ=(M(F(c0['high']),F(c1['high'])),N(F(c0['low']),F(c1['low'])));p0,p5=(M(F(c2['high']),F(c3['high'])),N(F(c2['low']),F(c3['low'])));eQ=(m4<hX and bi<=a0 and a8>=br and hY>m5 and hY>M(hX,a0))if g else(m4>hX and bi>=a0 and a8<=br and hY<m5 and hY<N(hX,a0))
  if eQ:
   go='Extended_AtNali'if(p5<pZ if g else p0>pY)else'ShortFormed_AtNali'if(p5>pZ+E*0.05 if g else p0<pY-E*0.05)else'Simple_AtNali';lt=M(a0,a8)if g else N(a0,a8);kw=N(pZ,p5)if g else M(pY,p0)
   if A(de-lt)<=E*0.45 and(ak>=lt if g else ak<=lt):jk=f'{aE}{go}_U_Turn';bQ['atnali_testere']=jk;cy.append(f'{a}_{jk}');b9.append(f'[{a}] {aX} {go} (4 Mumlu U-Dönüşü = LTF M/W Kırılımı | Giriş:{lt:.4f}, Stop:{kw:.4f}) (28,29.pdf & YT-Part10)');cz.append(('QML',k+1,N(kw,lt),M(kw,lt)));aL=(kw-E*0.15 if aL is None else N(aL,kw-E*0.15))if g else(kw+E*0.15 if aL is None else M(aL,kw+E*0.15));break
 fz=ar if g else aa
 if L(fz)>=2:
  (qq,da),(sa,ck)=(fz[-2],fz[-1]);pp=(ck-da)if g else(da-ck)
  if A(pp)<=E*1.35 and A(de-ck)<=E*0.42 and(ak>=ck if g else ak<=ck):p6='W'if g else'M';p7=f'Simple_{p6}_Trade'if A(pp)<=E*0.22 else f'ShortFormed_{p6}_2ndLeg'if pp>0 else f'Extended_{p6}_TurtleSoup_SFP';kx=z.get('ote_bull_mu'if g else'ote_bear_mu',False);p8=('+OTE'if kx else'')+('+FVG'if L(C)>0 else'');bQ['mw_modeli']=f'{p7}{p8}';cy.append(f'{a}_{p7}{p8}');b9.append(f'[{a}] {aX} {p7}{p8} (1.Bacak:{da:.4f} -> 2.Bacak Giriş:{ck:.4f} | HTF At Nalı Karşılığı) (29-m-w-trade.pdf & YT-Part10)');cz.append(('QML',qq,N(da,ck),M(da,ck)));aL=(N(da,ck)-E*0.22 if aL is None else N(aL,N(da,ck)-E*0.22))if g else(M(da,ck)+E*0.22 if aL is None else M(aL,M(da,ck)+E*0.22))
 for j in G(M(3,L(df)-18),L(df)-2):
  mj=df.iloc[j];c8,c9,hZ,h4=_r(mj,'open','close','high','low');j2=A(c9-c8);ot,ou=(hZ-M(c8,c9),N(c8,c9)-h4);ml=(c9>c8)if g else(c9<c8);cZ=ml and j2>=E*0.65 and((ou>=j2*0.35 and ou>ot*1.6)if g else(ot>=j2*0.35 and ot>ou*1.6))
  if cZ:
   ly,lz=(h4,c8)if g else(c8,hZ)
   if ly-E*0.18<=de<=lz+E*0.18 and(ak>=ly if g else ak<=lz):jm=f'{aE}TersIgneli_Momentum_POI';bQ['momentum_marubozu']=jm;cy.append(f'{a}_{jm}');b9.append(f'[{a}] {aX} Ters İğneli Momentum Mumu İğne İçi Gizli POI Testi ({ly:.4f}-{lz:.4f}) (35.pdf & YT-Part10)');cz.append(('BB/FL',j,ly,lz));aL=(ly-E*0.15 if aL is None else N(aL,ly-E*0.15))if g else(lz+E*0.15 if aL is None else M(aL,lz+E*0.15));break
  if j+1<L(df)-2:
   mn=df.iloc[j+1];fa,nl,kL,kM=_r(mn,'open','close','high','low');h5=(c9>c8 and nl>fa and ot>E*0.18 and fa-kM>E*0.18 and kM<=hZ)if g else(c9<c8 and nl<fa and ou>E*0.18 and kL-fa>E*0.18 and kL>=h4)
   if h5:
    lD,lE=(N(kM,c9),M(hZ,fa))if g else(N(h4,fa),M(kL,c9))
    if lD-E*0.15<=de<=lE+E*0.15 and(ak>=lD if g else ak<=lE):jv=f'{aE}YingYang_HiddenBase_Test';bQ['yingyang_hidden_base']=jv;cy.append(f'{a}_{jv}');b9.append(f'[{a}] {aX} Ying-Yang (Hidden Base İğne Kesişimi: {lD:.4f}-{lE:.4f}) Bölge Testi! (35-ying-yang.pdf & YT-Part10)');cz.append(('BB/FL',j,lD,lE));aL=(lD-E*0.15 if aL is None else N(aL,lD-E*0.15))if g else(lE+E*0.15 if aL is None else M(aL,lE+E*0.15));break
 mp,mc=(df.iloc[-3],df.iloc[-2]);eR,eS,pq,pr=_r(mp,'open','close','high','low');eT,eU,ps,pt=_r(mc,'open','close','high','low');eH=A(eU-eT);iJ,iK=(ps-M(eT,eU),N(eT,eU)-pt);mm,mo=(pq-M(eR,eS),N(eR,eS)-pr);dV=(eU>eT and eH>=E*0.48 and iK<=eH*0.08 and(eS<eR and mo<=A(eS-eR)*0.12 or iJ<=eH*0.12))if g else(eU<eT and eH>=E*0.48 and iJ<=eH*0.08 and(eS>eR and mm<=A(eS-eR)*0.12 or iK<=eH*0.12))
 if dV:iL=f"{('Bull' if g else 'Bear')}_Istekli_Marubozu";bQ['momentum_marubozu']=iL;cy.append(f'{a}_{iL}');b9.append(f'[{a}] {aX} İstekli Mum / Marubozu Open (Bölgeden İğnesiz Sıfır Mukavemetli Çıkış: {eT:.4f}->{eU:.4f}) (35.pdf & YT-Part10)')
 return(cy,aL,b9,cz,bQ)
def engulf_pinbar_analizi(df,z,C,a='1H',B='BULLISH'):
 bW,bA,dq,aS=([],[],[],None);bl={'engulf_outside_mera':'YOK','star_turu':'YOK','pinbar_spike':'YOK','railroad_tracks':'YOK','bosalt_doldur_kademe':'YOK','kombo_patern':'YOK','sentetik_mum':'YOK'}
 if L(df)<20:return(bW,aS,bA,dq,bl)
 bb,bc,ak,pn=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2),_f(df,'open',-2));E=M(_f(df,'atr',-2),ak*0.001);g=B=='BULLISH';aX='Bullish'if g else'Bearish';aE='Bull'if g else'Bear';de=bb if g else bc;m0,m1,m2,m3=(df.iloc[-5],df.iloc[-4],df.iloc[-3],df.iloc[-2]);o0,c0,h0,l0,o1,c1,h1,l1=(*_r(m0,'open','close','high','low'),*_r(m1,'open','close','high','low'));o2,c2,h2,l2,o3,c3,h3,l3=(*_r(m2,'open','close','high','low'),*_r(m3,'open','close','high','low'));g1,g2,g3=(A(c1-o1),A(c2-o2),A(c3-o3));mq,mr,n5,n6=(M(o2,c2),N(o2,c2),M(o3,c3),N(o3,c3));pv,pw,n7,n8=(h2-mq,mr-l2,h3-n5,n6-l3);oU=(c2<o2 and c3>o3 and n5>=mq and n6<=mr)if g else(c2>o2 and c3<o3 and n5>=mq and n6<=mr);oV=h3>=h2 and l3<=l2 and(h3>h2 or l3<l2)and(c3>o3 if g else c3<o3);hn=h3>=h2 and l3<=l2 and((n8>=g2*0.75 and mr>=l3 and mq<=n6+E*0.12 and l3<l2 and(c3>o3 or c3>=l3+(h3-l3)*0.6))or(c2<o2 and c3>h2 and l3<=l2)if g else(n7>=g2*0.75 and mq<=h3 and mr>=n5-E*0.12 and h3>h2 and(c3<o3 or c3<=h3-(h3-l3)*0.6))or(c2>o2 and c3<l2 and h3>=h2))
 if hn:ad=f'{aE}_MeraMera_Outside_QML';bl['engulf_outside_mera']=ad;bW.append(f'{a}_{ad}');bA.append(f'[{a}] {aX} Mera Mera (Outside Bar + İğne İçi Gövde Yutuşu = LTF Gizli QML) (30.pdf & YT-Part11)');dq.append(('QML',L(df)-3,l3 if g else mr,mq if g else h3));aS=l3-E*0.18 if g else h3+E*0.18
 elif oU and oV:ad=f'{aE}_Engulf+Outside_Super';bl['engulf_outside_mera']=ad;bW.append(f'{a}_{ad}');bA.append(f'[{a}] {aX} Çifte Güçlü Engulf + Outside Bar (Hem Gövde Hem High-Low Yutuldu!) (30.pdf & YT-Part11)');dq.append(('OB',L(df)-3,N(l2,l3)if g else o2,o2 if g else M(h2,h3)));aS=N(l2,l3)-E*0.18 if g else M(h2,h3)+E*0.18
 elif oU:gD=g3>=g2*1.45 and g3>=E*0.45;ad=f"{aE}_{('Kaliteli_Imb_Engulf' if gD else 'Weak_Engulf')}";bl['engulf_outside_mera']=ad;bW.append(f'{a}_{ad}');bA.append(f'[{a}] {aX} {ad} (Zıt Renkli Gövde Yutuşu: {o3:.4f}->{c3:.4f}) (30.pdf & YT-Part11)');aS=N(l2,l3)-E*0.18 if g else M(h2,h3)+E*0.18
 elif oV:ad=f'{aE}_OutsideBar_HL';bl['engulf_outside_mera']=ad;bW.append(f'{a}_{ad}');bA.append(f'[{a}] {aX} Outside Bar (High-Low Yutuşu: {l3:.4f}-{h3:.4f}) (30.pdf & YT-Part11)');aS=l3-E*0.18 if g else h3+E*0.18
 jI=(c1<o1 and g1>=E*0.4 and g2<=g1*0.5 and c3>o3)if g else(c1>o1 and g1>=E*0.4 and g2<=g1*0.5 and c3<o3)
 if jI:
  q5=(c3>=o1)if g else(c3<=o1);j3=(c3>=o1-g1*0.35)if g else(c3<=o1+g1*0.35)
  if q5 or j3:p9=f"{aE}_{('Strong_Engulf_Star' if q5 else 'Railroad_Star_70pct')}";bl['star_turu']=p9;bW.append(f'{a}_{p9}');bA.append(f"[{a}] {aX} {('Sabah' if g else 'Akşam')} Yıldızı ({p9}: 3 Mum Toplamı = Sentetik Pinbar) (YT-Part11)");oB,oC=(N(l1,l2,l3),M(h1,h2,h3));aS=(oB-E*0.18 if aS is None else N(aS,oB-E*0.18))if g else(oC+E*0.18 if aS is None else M(aS,oC+E*0.18))
 lO=(c2<o2 and c3>o3 and g2>=E*0.45 and g2*0.62<=g3<g2*1.02)if g else(c2>o2 and c3<o3 and g2>=E*0.45 and g2*0.62<=g3<g2*1.02)
 if lO:n9=(N(l2,l3)+M(h2,h3))/2.0;ad=f'{aE}_Railroad_Tracks_Pinbar';bl['railroad_tracks']=ad;bl['sentetik_mum']=f'2Mum_RR_Pinbar(50%:{n9:.4f})';bW.append(f'{a}_{ad}');bA.append(f'[{a}] {aX} Railroad Tracks (%65-%98 Gövde Dönüşü = Sentetik Pinbar | %50 Seviyesi: {n9:.4f}) (31.pdf & YT-Part11)');dq.append(('BB/FL',L(df)-3,N(l2,l3)if g else n9,n9 if g else M(h2,h3)));aS=(N(l2,l3)-E*0.18 if aS is None else N(aS,N(l2,l3)-E*0.18))if g else(M(h2,h3)+E*0.18 if aS is None else M(aS,M(h2,h3)+E*0.18))
 jJ=(n8>=M(g3*1.55,E*0.32)and n8>n7*1.35)if g else(n7>=M(g3*1.55,E*0.32)and n7>n8*1.35);k6=(pw>=M(g2*1.55,E*0.32)and pw>pv*1.35)if g else(pv>=M(g2*1.55,E*0.32)and pv>pw*1.35)
 if jJ or k6:mt=((l3+h3)/2.0)if jJ else((l2+h2)/2.0);eV=(c3>=o3 if jJ else c2>=o2)if g else(c3<=o3 if jJ else c2<=o2);iM='50pct_Retest'if k6 and not jJ and(l2<=bb<=mt+E*0.12 if g else mt-E*0.12<=bc<=h2)and(ak>=mt if g else ak<=mt)else'Break_Entry'if k6 and(ak>h2 if g else ak<l2)else'Kapanis_Onayli'if eV else'Spike_Tepki';iN=f'{aE}_Pinbar_{iM}';bl['pinbar_spike']=iN;bW.append(f'{a}_{iN}');bA.append(f'[{a}] {aX} Reversal Pinbar ({iM} | %50 HL:{mt:.4f}) (31-spike-pinbar.pdf & YT-Part11)');hz=(N(l2,l3)-E*0.18)if g else(M(h2,h3)+E*0.18);aS=(hz if aS is None else N(aS,hz))if g else(hz if aS is None else M(aS,hz))
 if k6 and jJ:iO=f'{aE}_Double_Pinbar_Combo';bl['kombo_patern']=iO;bW.append(f'{a}_{iO}');bA.append(f'[{a}] {aX} Double Pinbar (Çift İğne Reddiyesi Kombo Patern!) (YT-Part11)')
 elif k6 and(oU or oV):iO=f'{aE}_Pinbar+Engulf_Outside_Combo';bl['kombo_patern']=iO;bW.append(f'{a}_{iO}');bA.append(f'[{a}] {aX} Pinbar + Engulf/Outside Bar Çifte Kanıt Kombo Patern! (YT-Part11)')
 elif(jJ and h3<=h2 and l3>=l2)or(k6 and h3<=h2 and l3>=l2 and(c3>o3 if g else c3<o3)):iO=f'{aE}_Pinbar+InsideBar_Combo';bl['kombo_patern']=iO;bW.append(f'{a}_{iO}');bA.append(f'[{a}] {aX} Pinbar + Inside Bar Kombo Patern! (YT-Part11)')
 for k in G(M(4,L(df)-14),L(df)-2):
  mk=df.iloc[k];ko,kc,kh,kl=_r(mk,'open','close','high','low');kg=A(kc-ko);lj=df.iloc[M(0,k-4):k];fQ=F((lj['high']-lj[['open','close']].max(axis=1)).max());hA=F(lj['high'].max());fR=F((lj[['open','close']].min(axis=1)-lj['low']).max());hB=F(lj['low'].min());fS=(kc>ko and kg>=E*0.58 and fQ>=E*0.22 and kc>=hA-E*0.08)if g else(kc<ko and kg>=E*0.58 and fR>=E*0.22 and kc<=hB+E*0.08)
  if fS:
   if k==L(df)-2:nm=f'{aE}_BosaltDoldur_Kademe2_Doldurma';bl['bosalt_doldur_kademe']=nm;bW.append(f'{a}_{nm}');bA.append(f'[{a}] {aX} Boşalt-Doldur (2.Kademe: İğnelenmiş Bölge Momentum Mumla Dolduruldu!) (32.pdf & YT-Part11)');aS=(ko-E*0.18 if aS is None else N(aS,ko-E*0.18))if g else(ko+E*0.18 if aS is None else M(aS,ko+E*0.18));break
   elif(ko-E*0.12<=bb<=kc and ak>=ko)if g else(kc<=bc<=ko+E*0.12 and ak<=ko):nm=f'{aE}_BosaltDoldur_Kademe3_TersIgne_Sniper';bl['bosalt_doldur_kademe']=nm;bW.append(f'{a}_{nm}');bA.append(f'[{a}] {aX} Boşalt-Doldur (3.Kademe Sniper: Dolduran Momentum Mumuna [{ko:.4f}-{kc:.4f}] Ters İğne Testi!) (32-bosalt-doldur.pdf & YT-Part11)');dq.append(('BB/FL',k,N(ko,kc),M(ko,kc)));aS=(ko-E*0.18 if aS is None else N(aS,ko-E*0.18))if g else(ko+E*0.18 if aS is None else M(aS,ko+E*0.18));break
 if bl['sentetik_mum']=='YOK':
  ky,kA,m6,m7=(o2,c3,M(h2,h3),N(l2,l3));mu=A(kA-ky);gp,gq=(N(ky,kA)-m7,m6-M(ky,kA))
  if(gp>=M(mu*1.6,E*0.35)and gp>gq*1.4)if g else(gq>=M(mu*1.6,E*0.35)and gq>gp*1.4):bl['sentetik_mum']=f'{aE}_2Mum_Toplam_Pinbar({(m7+m6)/2.0:.4f})'
  elif(c1>o1 and c2>o2 and c3>o3 and c3-o1>=E*1.1)if g else(c1<o1 and c2<o2 and c3<o3 and o1-c3>=E*1.1):bl['sentetik_mum']=f'{aE}_3Mum_Sentetik_Marubozu_LiqVoid'
 return(bW,aS,bA,dq,bl)
def ib_fakey_smt_analizi(df,z,C,a='1H',B='BULLISH',J='BTC/USDT'):
 ca,cA,ea=([],[],[]);fA=None;bg={'inside_bar_durumu':'YOK','fake_setup_tipi':'YOK','dvg_durumu':'YOK','smt_durumu':'YOK','dar_sl_4r':False,'gelis_atr':0.0,'mb_high':None,'mb_low':None,'ib_high':None,'ib_low':None,'fake_idx':None}
 if L(df)<20:return(ca,fA,cA,ea,bg)
 bb,bc,ak,pn=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2),_f(df,'open',-2));eI=F(df['atr'].iloc[-10:-1].mean())if'atr'in df.columns and L(df)>=12 else M(_f(df,'atr',-2),ak*0.001);E=M(eI,ak*0.001);bg['gelis_atr']=R(E,5);g=B=='BULLISH'
 for dN in G(M(4,L(df)-16),L(df)-2):
  bm,bn,m8,m9=(_f(df,'high',dN),_f(df,'low',dN),_f(df,'open',dN),_f(df,'close',dN));c4=bm-bn
  if c4<E*0.65:continue
  iS,b3,b4=(0,-1e18,1e18)
  for j in G(dN+1,N(L(df)-1,dN+5)):
   jh,jl=(_f(df,'high',j),_f(df,'low',j))
   if jh<=bm and jl>=bn:iS+=1;b3=M(b3,jh);b4=N(b4,jl)
   else:break
  if iS==0:continue
  fU=dN+iS;j4=M(b3-b4,1e-9);bO=j4/M(c4,1e-9);uF=m9>m8 and b4>=bn+c4*0.42;aF=m9<m8 and b3<=bm-c4*0.42;dr=bO<=0.55 and((uF if g else aF)or bO<=0.38);aI=any((dN-3<=fi<=dN for fi in C));bg['mb_high'],bg['mb_low'],bg['ib_high'],bg['ib_low']=(R(bm,5),R(bn,5),R(b3,5),R(b4,5))
  if fU<L(df)-1:
   bp=fU+1;db,bL,cK,cM=(_f(df,'open',bp),_f(df,'close',bp),_f(df,'high',bp),_f(df,'low',bp));kB=cK-cM
   if(bL>bm if g else bL<bn):
    fb=kB>E*1.65;fc=(bn<=bb<=bm+E*0.18 and ak>=b4)if g else(bn-E*0.18<=bc<=bm and ak<=b3)
    if bp==L(df)-2 and not fb or(fc and bp<L(df)-2):
     iE=f"{a}_{('Kaliteli_Flama_InsideBar_Brk' if dr else 'InsideBar_Breakout_Retest' if bp<L(df)-2 else 'InsideBar_Breakout_Close')}"
     if iE not in ca:
      ca.append(iE);bg['inside_bar_durumu']=f"{iE}({iS}Bar,Oran:%{bO*100:.0f})"
      if not aI:bg['dar_sl_4r']=True;ca.append(f'{a}_InsideBar_DarSL_4R')
      cA.append(f"[{a}] {('Bullish' if g else 'Bearish')} {iE} (AnaBar:{bn:.4f}-{bm:.4f}, {iS}x InsideBar Oran:%{bO*100:.0f}{', Flama Konumu' if uF or aF else ''}{', Arkada Açık Imb Yok -> Dar SL 2R->4R!' if not aI else ''}) (33-inside-bar.pdf & YT-Part12)");ea.append(('IB_MB',dN,bn,bm));fA=(b4 if not aI else bn)if g else(b3 if not aI else bm)
   gE,gF=(cK-M(bL,db),N(bL,db)-cM)
   if(cM<bn and bL>=bn and gF>A(bL-db)*1.2)if g else(cK>bm and bL<=bm and gE>A(bL-db)*1.2):
    cr=(bL>=b4)if g else(bL<=b3);uK=(bL>b3)if g else(bL<b4)
    if cr and(bp>=L(df)-3 or(bn<=bb<=bm and ak>=b4 if g else bn<=bc<=bm and ak<=b3)):
     fT='Kuralli_Pinbarli_FakeSetup_GucluUst'if uK else'Kuralli_Pinbarli_FakeSetup_IcKapanis';jw=f'{a}_{fT}'
     if jw not in ca:ca.append(jw);bg['fake_setup_tipi'],bg['fake_idx']=(fT,bp);oO=(cM+cK)/2.0;gS='%50 İğne Retest'if(cM<=bb<=oO and ak>=oO if g else oO<=bc<=cK and ak<=oO)else'Pinbar Kapanış/Kırılım';cA.append(f"[{a}] {('Bullish' if g else 'Bearish')} {fT}: Ana Bar ({(bn if g else bm):.4f}) iğneyle süpürüldü ve Inside Bar {('üstünde/altında kırarak' if uK else 'içinde')} kurallı kapandı! Giriş: {gS} (34-fake-setup.pdf & YT-Part12)");ea.append(('FAKEY_PIN',dN,N(bn,cM),M(bm,cK)));fA=cM if g else cK
    elif not cr and bp>=L(df)-3:bg['fake_setup_tipi']='Kuralsiz_Pinbarli_FakeSetup_Zayif'
   if bp+1<L(df):
    fd=bp+1;kW,dc,ny,nz=(_f(df,'open',fd),_f(df,'close',fd),_f(df,'high',fd),_f(df,'low',fd));nA,nB=(A(dc-kW),A(bL-db));gG=(bL<db and dc>kW)if g else(bL>db and dc<kW);dJ=(cM<bn and dc>=b4 and(dc>=b3 or nA>=nB*0.75))if g else(cK>bm and dc<=b3 and(dc<=b4 or nA>=nB*0.75))
    if gG and dJ and(fd>=L(df)-3 or(bn<=bb<=bm and ak>=b4 if g else bn<=bc<=bm and ak<=b3)):
     aK='Engulf_Outside'if(dc>=db if g else dc<=db)else'Railroad_AtNali';jx=f'{a}_Pinbarsiz_FakeSetup_{aK}'
     if jx not in ca:ca.append(jx);bg['fake_setup_tipi'],bg['fake_idx']=(f'Pinbarsiz_FakeSetup_{aK}_PO3',fd);cA.append(f"[{a}] {('Bullish' if g else 'Bearish')} Pinbarsız Fake Setup ({aK} / PO3 Box): 3.Mum Ana Barı ihlal etti, 4.Mum zıt renkle Inside Barı yutarak içeri döndü! (34-fake-setup.pdf & YT-Part12)");ea.append(('FAKEY_NOPIN',dN,N(bn,cM,nz),M(bm,cK,ny)));fA=N(cM,nz)if g else M(cK,ny)
 aa,ar=(z.get('highs',[]),z.get('lows',[]));cV=ar if g else aa
 if L(cV)>=2 and'rsi'in df.columns:
  (i1,w1),(i2,w2)=(cV[-2],cV[-1]);c1,c2=(_f(df,'close',i1),_f(df,'close',i2));bY,ci,gr,kC,gt,gu=(_f(df,'rsi',i1),_f(df,'rsi',i2),_f(df,'ao',i1),_f(df,'ao',i2),_f(df,'cvd',i1),_f(df,'cvd',i2));rO=(bY<=40.0)if g else(bY>=60.0);cp=(c2<c1*0.999 and ci>bY+1.8)if g else(c2>c1*1.001 and ci<bY-1.8);dt=(w2<w1*0.999 and((kC>gr and gr<0)or gu>gt))if g else(w2>w1*1.001 and((kC<gr and gr>0)or gu<gt));eW=A(w2-w1)/M(w1,1e-9)<=0.0038 and((ci>bY+1.5 or kC>gr)if g else(ci<bY-1.5 or kC<gr));du=(w2<w1*0.9985 if g else w2>w1*1.0015)and A(ci-bY)<=0.9;eb=(w2>w1*1.002 and ci<bY-2.0)if g else(w2<w1*0.998 and ci>bY+2.0)
  if cp or dt:
   kY='RSI_Close'if cp else'AO_CVD_Wick';dE=f'{a}_Strong_Regular_DVG_{kY}'
   if rO:dE+='+RSIOver_2_3_Ayak'
   ca.append(dE);bg['dvg_durumu']=dE;cA.append(f"[{a}] {('Pozitif (Bullish)' if g else 'Negatif (Bearish)')} Strong Regular Divergence ({kY}: RSI Kapanış {bY:.1f}->{ci:.1f}{', 1.Ayak RSI Over 2./3.Ayak Onaylı!' if rO else ''}) (38-dvg.pdf & YT-Part12)")
  elif eW:dE=f"{a}_Medium_{('IkiliDip_EQL' if g else 'IkiliTepe_EQH')}_DVG";ca.append(dE);bg['dvg_durumu']=f'{dE}(KisaInternalHedef)';cA.append(f"[{a}] Medium Regular Divergence ({('İkili Dip EQL' if g else 'İkili Tepe EQH')} + Osilatör Uyumsuzluğu -> Arkada Likidite Bıraktığı İçin Kısa/Internal Hedef Odaklı) (38-dvg.pdf & YT-Part12)")
  elif du:bg['dvg_durumu']='Weak_EsitOsilator_DVG(TercihEdilmez)'
  elif eb:bg['dvg_durumu']='Hidden_Gizli_DVG_Red(FailureSwing_Kullanilmaz)'
 eF=J.split(':')[0];rA='ETH/USDT'if eF=='BTC/USDT'else'BTC/USDT';bj=an.get(a.lower(),an.get(LTF_PERIYOT,an.get('15m',{}))).get(rA)
 if bj is not None and L(bj)>=18 and L(df)>=18:
  dv='low'if g else'high';fV=F(df[dv].iloc[-16:-6].min()if g else df[dv].iloc[-16:-6].max());fW=F(df[dv].iloc[-6:-1].min()if g else df[dv].iloc[-6:-1].max());fX=F(bj[dv].iloc[-16:-6].min()if g else bj[dv].iloc[-16:-6].max());fY=F(bj[dv].iloc[-6:-1].min()if g else bj[dv].iloc[-6:-1].max());pL=(fW<fV)if g else(fW>fV);ec=(fY<fX)if g else(fY>fX);iP=A(_f(df,'close',-2)-_f(df,'close',-6))/M(E*4.0,1e-9);mv=M(_f(bj,'atr',-2),_f(bj,'close',-2)*0.001);iQ=A(_f(bj,'close',-2)-_f(bj,'close',-6))/M(mv*4.0,1e-9);hU=M(iP,iQ)/M(N(iP,iQ),0.05)>=1.55
  if pL!=ec:sR='POIye_Takilan_DusukRiskSL'if not pL else'Likidite_Alan_Devyasyon';sE=f'{a}_SMT_{sR}';ca.append(sE);bg['smt_durumu']=f"{sE}({rA}{',HizFarki' if hU else ''})";cA.append(f"[{a}] {rA} ile {('Pozitif (Bullish)' if g else 'Negatif (Bearish)')} SMT: {('Bu parite Fresh POIye takıldı (Düşük Riskli Net Stop!), ' + rA + ' likidite aldı' if not pL else 'Bu parite likiditeyi süpürdü (Devyasyon), ' + rA + ' POIye takıldı')}{' + Hız/İvme Farkı Onaylı' if hU else ''} -> TP1: En Yakın Internal FTR/FL! (39-smt.pdf & YT-Part12)")
  elif hU:bg['smt_durumu']=f'SMT_Hiz_Farki_ErkenUyari({rA})'
 return(ca,fA,cA,ea,bg)
def entry_mtf_3r_analizi(df,z,Z,C,a='1H',B='BULLISH'):
 dw,cC,fZ=([],[],[]);eJ=None;bv={'aktif_entry_modeli':'Beklemede','istisnai_ob_durumu':'YOK','fvgli_choch_entry_alani':'YOK','zayif_choch_filtresi':'YOK','atr_stop_kalkani':'YOK','dogal_rr_orani':0.0,'mtf_ahenk_durumu':'Ahenkli','basabas_winrate':'%25 (1:3 R:R)'}
 if L(df)<20:return(dw,eJ,cC,fZ,bv)
 bb,bc,ak,pn=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2),_f(df,'open',-2));lP=F(df['atr'].iloc[-10:-1].mean())if'atr'in df.columns and L(df)>=12 else M(_f(df,'atr',-2),ak*0.001);E=M(lP,ak*0.001);g=B=='BULLISH';cb,j5,aV=(z.get('qm_meta',{}),z.get('v6_meta',{}),z.get('v12_meta',{}));g5=z.get('uc_istasyon',{});bx,eX=(z.get('strong_point'),z.get('weak_point'));co=cb.get('qml_seviyesi')
 if I(co,(int,F))and I(bx,(int,F))and L(C)>0:
  if(bx<co-E*0.35 if g else bx>co+E*0.35):
   bv['istisnai_ob_durumu']=f'Istisnai_OB({bx:.4f}_vs_QML_{co:.4f})'
   if(bx-E*0.2<=bb<=co+E*0.15 and ak>=bx)if g else(co-E*0.15<=bc<=bx+E*0.2 and ak<=bx):qr=f'{a}_Istisnai_OB_QML_Disi_Imb';dw.append(qr);eJ=bx;cC.append(f"[{a}] {('Bullish' if g else 'Bearish')} İstisnai Order Block ({bx:.4f}): QML ({co:.4f}) gerisinde açık Imbalance olduğu için OB uç noktada ayrıştı! (YT-Part13)")
 cN=z.get('internal_choch','YOK');es=L(C)>0 or any(('FVG'in p or'Imb'in p for p in Z));aT=aV.get('smt_durumu','YOK')!='YOK'or aV.get('dvg_durumu','YOK')!='YOK';fB=('BULL_STRONG_CHOCH'in cN or'BULL_IBOS'in cN)if g else('BEAR_STRONG_CHOCH'in cN or'BEAR_IBOS'in cN);fC=('BULL_WEAK_CHOCH'in cN)if g else('BEAR_WEAK_CHOCH'in cN);be,bF=(g5.get('FL'),g5.get('ITZ'))
 if fB and es:
  ed=N(be,bF)if I(be,(int,F))and I(bF,(int,F))else ak-E*0.6;ee=M(be,bF)if I(be,(int,F))and I(bF,(int,F))else ak+E*0.6;mw=f"{a}_FVGli_Guclu_CHoCH_EntryAlani{'_RetestSMT' if aT else ''}";dw.append(mw);bv['fvgli_choch_entry_alani']=f'{mw}[{ed:.4f}-{ee:.4f}]';bv['aktif_entry_modeli']='Model5_FVGli_CHoCH+RetestSMT'if aT else'Model5_FVGli_Guclu_CHoCH_EntryAlani';fZ.append(('ENTRY_ZONE',M(2,L(df)-6),ed,ee))
  if I(bF,(int,F)):eJ=(bF-E*0.35)if g else(bF+E*0.35)
  cC.append(f"[{a}] FVG'li Güçlü CHoCH Giriş Alanı (FL-ITZ-OB Entry Zone: {ed:.4f}-{ee:.4f}){' + Testte İkinci SMT/DVG Onayı!' if aT else ''} -> Stop HTF arkasına değil LTF kırılım yapısına çekildi! (41.pdf & YT-Part13)")
 elif fC:
  if L(Z)>0 and(es or aT):qs=f'{a}_AnaPOI_FVGli_ZayifCHoCH_Onay';dw.append(qs);bv['zayif_choch_filtresi']='Onayli_AnaPOI_FVGli_ZayifCHoCH';bv['aktif_entry_modeli']='Model5_AnaPOI_FVGli_Zayif_CHoCH';cC.append(f"[{a}] Ana POI İçinde FVG'li Zayıf CHoCH Onayı{' + SMT Destekli' if aT else ''}: Bölge taze ve güçlü olduğu için likiditesiz erken dönüş onaylandı! (YT-Part13)")
  else:bv['zayif_choch_filtresi']='RED_KitabinOrtasi_TersAkis_ZayifCHoCH_Tuzagi'
 elif aT and L(Z)>0:bv['aktif_entry_modeli']='Model2_FreshPOI_SMT_DVG_ErkenGiris';dw.append(f'{a}_FreshPOI_SMT_DVG_ErkenEntry');cC.append(f'[{a}] Fresh POI + SMT/DVG Destekli Erken Giriş: Kırılım beklemeden Imbalance giderildiği anda SMT onayıyla uçtan pozlanma! (YT-Part13)')
 iq=R(ak-E*1.5 if g else ak+E*1.5,5);lQ=R(ak-E*2.0 if g else ak+E*2.0,5);lR=R(ak-E*2.5 if g else ak+E*2.5,5);bv['atr_stop_kalkani']=f'1.5x:{iq}|2.0x:{lQ}(Safe)|2.5x:{lR}';jK=eJ if eJ is not None else(bx if I(bx,(int,F))else iq);dW=M(A(ak-jK),E*1.5);eu=cb.get('karsi_fresh_hedef')or eX or(ak+dW*3.2 if g else ak-dW*3.2);jL=A(F(eu)-ak);bR=R(jL/M(dW,1e-9),2);bv['dogal_rr_orani']=bR
 if bR>=3.0:dw.append(f'{a}_Dogal_3R_Ustu_Potansiyel({bR:.1f}R)');cC.append(f'[{a}] Doğal >= 3R Trade Planı Onayı ({bR:.1f}R -> Hedef: {F(eu):.4f}): Uydurma stop/TP olmadan doğal yapı >= 3R veriyor (%25 Başabaş / %30 Winrate ile +20R Kasa Disiplini)! (44,45.pdf & YT-Part13)')
 lS=cb.get('yaklasim_modeli','Standart');bv['pa_diyagrami_durumu']=f"1.Kalite({'OK' if L(Z)>0 else '-'})|2.Yaklasim({lS})|3.Giris({bv['aktif_entry_modeli']})"
 if L(Z)>0 and(bv['aktif_entry_modeli']!='Beklemede'or I(be,(int,F))or I(bF,(int,F))):dw.append(f'{a}_PA_Diyagrami_3Asama_Onay');cC.append(f"[{a}] Price Action Diyagramı 3 Aşama Onayı (OB->QML[ITZ/DP/MPL]->MagicLine/BB[B.Spot/FL]->FO/FTR | Yaklaşım: {lS} | Giriş: {bv['aktif_entry_modeli']}) (YT-Short Diyagram)")
 return(dw,eJ,cC,fZ,bv)
def _likidite_ve_sfp_yapilarini_bul(df,uH=None,uL=None,ts_arr=None):
 liq_list,sfp_list=([],[])
 meta={'aktif_eqh':[],'aktif_eql':[],'swept_eqh':[],'swept_eql':[],'aktif_idm_bsl':None,'aktif_idm_ssl':None,'swept_idm_bull':None,'swept_idm_bear':None,'son_bull_sfp':None,'son_bear_sfp':None,'ext_bsl':None,'ext_ssl':None,'trendline_bsl':[],'trendline_ssl':[]}
 if df is None or L(df)<10:return(liq_list,sfp_list,meta)
 ct=L(df);son_c=_f(df,'close',-1)
 E=M(_f(df,'atr',-2)if'atr'in df.columns else son_c*0.002,son_c*0.0008)
 tol_eq=N(M(E*EQH_EQL_TOL_ATR,son_c*0.0007),son_c*0.0038)
 ts=ts_arr if I(ts_arr,list)and L(ts_arr)==ct else list(G(ct))
 h_map,l_map=({},{})
 for i in G(2,ct-2):
  hi,li=(_f(df,'high',i),_f(df,'low',i))
  if hi>=_f(df,'high',i-1)and hi>=_f(df,'high',i-2)and hi>=_f(df,'high',i+1)and hi>=_f(df,'high',i+2):h_map[i]=hi
  if li<=_f(df,'low',i-1)and li<=_f(df,'low',i-2)and li<=_f(df,'low',i+1)and li<=_f(df,'low',i+2):l_map[i]=li
 for i,v in(uH or[]):
  if 0<=int(i)<ct:h_map[int(i)]=M(h_map.get(int(i),F(v)),F(v))
 for i,v in(uL or[]):
  if 0<=int(i)<ct:l_map[int(i)]=N(l_map.get(int(i),F(v)),F(v))
 jn=sorted(h_map.items(),key=lambda x:x[0]);jo=sorted(l_map.items(),key=lambda x:x[0])
 kul_h,kul_l,sfp_ek=(set(),set(),set())
 for k in G(L(jn)):
  i1,h1=jn[k]
  if i1 in kul_h:continue
  grup=[(i1,h1)]
  for m in G(k+1,N(L(jn),k+5)):
   im,hm=jn[m]
   if im-grup[-1][0]<3:continue
   if A(hm-h1)<=tol_eq:
    tavan_ara=M(h1,hm)
    if not any(_f(df,'high',b)>tavan_ara+E*0.08 for b in G(grup[-1][0]+1,im)):grup.append((im,hm))
  if L(grup)>=2:
   i_son=grup[-1][0];ort_h=sum(x[1]for x in grup)/L(grup);tavan_h=M(x[1]for x in grup)
   govde_kir,sw_idx,sw_hi=(False,None,0.0)
   for b in G(i_son+1,ct):
    cb,hb,ob=(_f(df,'close',b),_f(df,'high',b),_f(df,'open',b))
    if cb>tavan_h+E*0.10 or(hb>tavan_h+E*0.25 and cb>tavan_h):govde_kir=True;break
    if hb>tavan_h+E*0.02 and cb<=tavan_h+E*0.02 and(hb-M(ob,cb))>=E*SFP_MIN_IGNE_ATR:
     if sw_idx is None:sw_idx,sw_hi=(b,hb)
   if govde_kir:continue
   for idx_e,_ in grup:kul_h.add(idx_e)
   if sw_idx is not None:
    meta['swept_eqh'].append((i1,sw_idx,ort_h))
    if sw_idx>=ct-35:
     liq_list.append({'tip':'💧 EQH Sweep (SFP)','idx1':i1,'idx2':sw_idx,'t1':ts[i1],'t2':ts[sw_idx],'p1':ort_h,'p2':ort_h,'renk':'#f43f5e','aktif':False})
     sk=f'BEAR_{sw_idx}'
     if sk not in sfp_ek:
      sfp_ek.add(sk);sf_obj={'tip':'▼ Bear SFP (EQH)','idx':sw_idx,'time':ts[sw_idx],'price':sw_hi,'level':ort_h,'yon':'BEAR'}
      sfp_list.append(sf_obj);meta['son_bear_sfp']=sf_obj
   else:
    meta['aktif_eqh'].append((i1,ct-1,ort_h))
    et='$$$ 3x EQH (TT3 BSL)'if L(grup)>=3 else'$$$ EQH (BSL)'
    liq_list.append({'tip':et,'idx1':i1,'idx2':ct-1,'t1':ts[i1],'t2':ts[ct-1],'p1':ort_h,'p2':ort_h,'renk':'#fbbf24','aktif':True})
 for k in G(L(jo)):
  i1,l1=jo[k]
  if i1 in kul_l:continue
  grup=[(i1,l1)]
  for m in G(k+1,N(L(jo),k+5)):
   im,lm=jo[m]
   if im-grup[-1][0]<3:continue
   if A(lm-l1)<=tol_eq:
    taban_ara=N(l1,lm)
    if not any(_f(df,'low',b)<taban_ara-E*0.08 for b in G(grup[-1][0]+1,im)):grup.append((im,lm))
  if L(grup)>=2:
   i_son=grup[-1][0];ort_l=sum(x[1]for x in grup)/L(grup);taban_l=N(x[1]for x in grup)
   govde_kir,sw_idx,sw_lo=(False,None,1e18)
   for b in G(i_son+1,ct):
    cb,lb,ob=(_f(df,'close',b),_f(df,'low',b),_f(df,'open',b))
    if cb<taban_l-E*0.10 or(lb<taban_l-E*0.25 and cb<taban_l):govde_kir=True;break
    if lb<taban_l-E*0.02 and cb>=taban_l-E*0.02 and(N(ob,cb)-lb)>=E*SFP_MIN_IGNE_ATR:
     if sw_idx is None:sw_idx,sw_lo=(b,lb)
   if govde_kir:continue
   for idx_e,_ in grup:kul_l.add(idx_e)
   if sw_idx is not None:
    meta['swept_eql'].append((i1,sw_idx,ort_l))
    if sw_idx>=ct-35:
     liq_list.append({'tip':'💧 EQL Sweep (SFP)','idx1':i1,'idx2':sw_idx,'t1':ts[i1],'t2':ts[sw_idx],'p1':ort_l,'p2':ort_l,'renk':'#10b981','aktif':False})
     sk=f'BULL_{sw_idx}'
     if sk not in sfp_ek:
      sfp_ek.add(sk);sf_obj={'tip':'▲ Bull SFP (EQL)','idx':sw_idx,'time':ts[sw_idx],'price':sw_lo,'level':ort_l,'yon':'BULL'}
      sfp_list.append(sf_obj);meta['son_bull_sfp']=sf_obj
   else:
    meta['aktif_eql'].append((i1,ct-1,ort_l))
    et='$$$ 3x EQL (TT3 SSL)'if L(grup)>=3 else'$$$ EQL (SSL)'
    liq_list.append({'tip':et,'idx1':i1,'idx2':ct-1,'t1':ts[i1],'t2':ts[ct-1],'p1':ort_l,'p2':ort_l,'renk':'#38bdf8','aktif':True})
 for i_h,v_h in jn[-8:]:
  if i_h>=ct-2:continue
  ilk_g=next((b for b in G(i_h+1,ct)if _f(df,'high',b)>v_h+E*0.02),None)
  if ilk_g is not None and ilk_g>=M(i_h+2,ct-35):
   cb,hb,ob=(_f(df,'close',ilk_g),_f(df,'high',ilk_g),_f(df,'open',ilk_g))
   u_ig=hb-M(ob,cb);bozdu=any(_f(df,'close',m)>hb for m in G(ilk_g+1,ct));sk=f'BEAR_{ilk_g}'
   if cb<v_h and u_ig>=E*SFP_MIN_IGNE_ATR and not bozdu and sk not in sfp_ek:
    sfp_ek.add(sk);sf_obj={'tip':'▼ Bear SFP (İğne Avı)','idx':ilk_g,'time':ts[ilk_g],'price':hb,'level':v_h,'yon':'BEAR'}
    sfp_list.append(sf_obj);meta['son_bear_sfp']=sf_obj
    if i_h not in kul_h:liq_list.append({'tip':'💧 BSL Sweep (SFP)','idx1':i_h,'idx2':ilk_g,'t1':ts[i_h],'t2':ts[ilk_g],'p1':v_h,'p2':v_h,'renk':'#fb7185','aktif':False})
 for i_l,v_l in jo[-8:]:
  if i_l>=ct-2:continue
  ilk_g=next((b for b in G(i_l+1,ct)if _f(df,'low',b)<v_l-E*0.02),None)
  if ilk_g is not None and ilk_g>=M(i_l+2,ct-35):
   cb,lb,ob=(_f(df,'close',ilk_g),_f(df,'low',ilk_g),_f(df,'open',ilk_g))
   a_ig=N(ob,cb)-lb;bozdu=any(_f(df,'close',m)<lb for m in G(ilk_g+1,ct));sk=f'BULL_{ilk_g}'
   if cb>v_l and a_ig>=E*SFP_MIN_IGNE_ATR and not bozdu and sk not in sfp_ek:
    sfp_ek.add(sk);sf_obj={'tip':'▲ Bull SFP (İğne Avı)','idx':ilk_g,'time':ts[ilk_g],'price':lb,'level':v_l,'yon':'BULL'}
    sfp_list.append(sf_obj);meta['son_bull_sfp']=sf_obj
    if i_l not in kul_l:liq_list.append({'tip':'💧 SSL Sweep (SFP)','idx1':i_l,'idx2':ilk_g,'t1':ts[i_l],'t2':ts[ilk_g],'p1':v_l,'p2':v_l,'renk':'#34d399','aktif':False})
 if L(jn)>=2 and L(jo)>=2:
  son_hi,son_hv=jn[-1];son_li,son_lv=jo[-1]
  onceki_l=[x for x in jo if x[0]<son_hi]
  if onceki_l and son_hi<ct-2:
   orig_li,orig_lv=onceki_l[-1];bacak=son_hv-orig_lv
   if bacak>=E*1.6:
    for b in G(son_hi+1,ct-1):
     lb=_f(df,'low',b)
     if lb<=_f(df,'low',b-1)and lb<=_f(df,'low',b+1)and orig_lv+bacak*0.18<=lb<=orig_lv+bacak*0.72:
      sup=next((m for m in G(b+1,ct)if _f(df,'low',m)<lb-E*0.02 and _f(df,'close',m)>orig_lv),None)
      if sup is not None:
       meta['swept_idm_bull']=lb;liq_list.append({'tip':'💧 IDM Sweep (Yem Yutuldu ✓)','idx1':b,'idx2':sup,'t1':ts[b],'t2':ts[sup],'p1':lb,'p2':lb,'renk':'#2dd4bf','aktif':False})
      elif son_c>lb:
       meta['aktif_idm_ssl']=lb;liq_list.append({'tip':'🎣 IDM (Likidite Yemi SSL)','idx1':b,'idx2':ct-1,'t1':ts[b],'t2':ts[ct-1],'p1':lb,'p2':lb,'renk':'#e879f9','aktif':True})
      break
  onceki_h=[x for x in jn if x[0]<son_li]
  if onceki_h and son_li<ct-2:
   orig_hi,orig_hv=onceki_h[-1];bacak_b=orig_hv-son_lv
   if bacak_b>=E*1.6:
    for b in G(son_li+1,ct-1):
     hb=_f(df,'high',b)
     if hb>=_f(df,'high',b-1)and hb>=_f(df,'high',b+1)and son_lv+bacak_b*0.28<=hb<=orig_hv-bacak_b*0.18:
      sup=next((m for m in G(b+1,ct)if _f(df,'high',m)>hb+E*0.02 and _f(df,'close',m)<orig_hv),None)
      if sup is not None:
       meta['swept_idm_bear']=hb;liq_list.append({'tip':'💧 IDM Sweep (Yem Yutuldu ✓)','idx1':b,'idx2':sup,'t1':ts[b],'t2':ts[sup],'p1':hb,'p2':hb,'renk':'#fb7185','aktif':False})
      elif son_c<hb:
       meta['aktif_idm_bsl']=hb;liq_list.append({'tip':'🎣 IDM (Likidite Yemi BSL)','idx1':b,'idx2':ct-1,'t1':ts[b],'t2':ts[ct-1],'p1':hb,'p2':hb,'renk':'#e879f9','aktif':True})
      break
 taze_h=[(ih,vh)for ih,vh in jn if ih<ct-2 and vh>son_c and not any(_f(df,'high',b)>vh+E*0.03 for b in G(ih+1,ct))]
 if taze_h:
  ext_hi,ext_hv=max(taze_h,key=lambda x:x[1]);meta['ext_bsl']=ext_hv
  if all(A(ext_hv-lq['p1'])>tol_eq for lq in liq_list):
   liq_list.append({'tip':'$$$ Ext BSL (Eski Tepe)','idx1':ext_hi,'idx2':ct-1,'t1':ts[ext_hi],'t2':ts[ct-1],'p1':ext_hv,'p2':ext_hv,'renk':'#f59e0b','aktif':True})
 taze_l=[(il,vl)for il,vl in jo if il<ct-2 and vl<son_c and not any(_f(df,'low',b)<vl-E*0.03 for b in G(il+1,ct))]
 if taze_l:
  ext_li,ext_lv=min(taze_l,key=lambda x:x[1]);meta['ext_ssl']=ext_lv
  if all(A(ext_lv-lq['p1'])>tol_eq for lq in liq_list):
   liq_list.append({'tip':'$$$ Ext SSL (Eski Dip)','idx1':ext_li,'idx2':ct-1,'t1':ts[ext_li],'t2':ts[ct-1],'p1':ext_lv,'p2':ext_lv,'renk':'#0ea5e9','aktif':True})
 # 22-likidite.pdf & YT-Part8: 3 Temaslı İhlalsiz Dinamik Trend Çizgisi Likiditesi (Trendline BSL / SSL)
 if L(jn)>=3:
  for a_i in G(M(0,L(jn)-6),L(jn)-2):
   (x1_t,y1_t),(x2_t,y2_t),(x3_t,y3_t)=(jn[a_i],jn[a_i+1],jn[a_i+2])
   if y1_t>y2_t>y3_t and x3_t>x2_t>x1_t:
    slp=(y3_t-y1_t)/M(x3_t-x1_t,1);y2_hat=y1_t+slp*(x2_t-x1_t)
    if A(y2_t-y2_hat)<=E*0.45:
     y_now=y1_t+slp*(ct-1-x1_t)
     ihlalsiz=not any(_f(df,'close',b)>y1_t+slp*(b-x1_t)+E*0.15 for b in G(x3_t+1,ct))
     if ihlalsiz and y_now>0:
      meta['trendline_bsl'].append((x1_t,ct-1,R(y_now,6)))
      liq_list.append({'tip':'📐 3x Trendline BSL','idx1':x1_t,'idx2':ct-1,'t1':ts[x1_t],'t2':ts[ct-1],'p1':y1_t,'p2':y_now,'renk':'#f472b6','aktif':son_c<=y_now+E*0.2})
      break
 if L(jo)>=3:
  for a_i in G(M(0,L(jo)-6),L(jo)-2):
   (x1_t,y1_t),(x2_t,y2_t),(x3_t,y3_t)=(jo[a_i],jo[a_i+1],jo[a_i+2])
   if y1_t<y2_t<y3_t and x3_t>x2_t>x1_t:
    slp=(y3_t-y1_t)/M(x3_t-x1_t,1);y2_hat=y1_t+slp*(x2_t-x1_t)
    if A(y2_t-y2_hat)<=E*0.45:
     y_now=y1_t+slp*(ct-1-x1_t)
     ihlalsiz=not any(_f(df,'close',b)<y1_t+slp*(b-x1_t)-E*0.15 for b in G(x3_t+1,ct))
     if ihlalsiz and y_now>0:
      meta['trendline_ssl'].append((x1_t,ct-1,R(y_now,6)))
      liq_list.append({'tip':'📐 3x Trendline SSL','idx1':x1_t,'idx2':ct-1,'t1':ts[x1_t],'t2':ts[ct-1],'p1':y1_t,'p2':y_now,'renk':'#38bdf8','aktif':son_c>=y_now-E*0.2})
      break
 return(liq_list[-11:],sfp_list[-6:],meta)
def _arz_talep_ve_imbalance_sablon_hesapla(df,ts_arr,bos_list,E,qml_lvl=None):
 """03-supply-demand.pdf, 04-arz-talep-gucu.pdf, 05-arz-talep-yaklasimi.pdf, 07-ob-ve-valid-subdem.pdf, 08-ftr-ve-itz.pdf:
 4 Arz/Talep Modunu (DBR: Drop-Base-Rally Reversal Talep, RBR: Rally-Base-Rally Continue Talep,
 RBD: Rally-Base-Drop Reversal Arz, DBD: Drop-Base-Drop Continue Arz) ve 10 üzerinden Bölge Gücü Puanını
 (Çıkış Gücü 2p + Baz Süresi 2p + Tazelik/Fresh 3p + Karşı RR 3p + Yaklaşım Kalitesi) hatasız hesaplar."""
 arz_talep_list,imbalance_list=([],[])
 if df is None or L(df)<6:return(arz_talep_list,imbalance_list)
 ct=L(df);son_c=_f(df,'close',-1);ts=ts_arr if I(ts_arr,list)and L(ts_arr)==ct else list(G(ct))
 E=M(F(E or 0.0),son_c*0.001)
 # 1) ÖNCE IMBALANCE / FVG (BISI, SIBI, IFVG) TESPİTİ (Arz/Talep ve OB İmbalans Kökü İçin)
 eklenen_imb=set();fvg_bull_set=set();fvg_bear_set=set();fvg_koku_map={}
 for i in G(1,ct-1):
  h0,l0,c0=(_f(df,'high',i-1),_f(df,'low',i-1),_f(df,'close',i-1))
  o1,c1=(_f(df,'open',i),_f(df,'close',i))
  h2,l2=(_f(df,'high',i+1),_f(df,'low',i+1))
  govde1=c1-o1
  if l2>h0 and govde1>=E*0.32 and(l2-h0)>=E*0.08:
   alt_fvg,ust_fvg,gap_boy=(h0,l2,l2-h0)
   fvg_bull_set.add(i);fvg_koku_map[i]=alt_fvg
   kirildi,min_low,k_idx=(False,ust_fvg,None)
   for m in G(i+2,ct):
    if _f(df,'close',m)<alt_fvg:kirildi=True;k_idx=m;break
    if _f(df,'low',m)<min_low:min_low=_f(df,'low',m)
   if not kirildi:
    aktif_ust=M(alt_fvg,N(ust_fvg,min_low))
    if(aktif_ust-alt_fvg)>=gap_boy*0.22:
     durum='Taze'if min_low>=ust_fvg else'Kısmi';key=f"BISI_{alt_fvg:.4f}_{aktif_ust:.4f}"
     if key not in eklenen_imb:
      eklenen_imb.add(key);imbalance_list.append({'tip':'BISI_FVG','yon':'BULL','idx1':i-1,'t1':ts[i-1],'lo':alt_fvg,'hi':aktif_ust,'ce':(alt_fvg+aktif_ust)/2.0,'taze':min_low>=ust_fvg,'etiket':f"BISI FVG ({durum})"})
   elif k_idx is not None and k_idx>=ct-45:
    if all(_f(df,'close',m)<=ust_fvg+E*0.1 for m in G(k_idx+1,ct))and A(son_c-ust_fvg)<=E*4.5:
     imbalance_list.append({'tip':'IFVG','yon':'BEAR','idx1':k_idx,'t1':ts[k_idx],'lo':alt_fvg,'hi':ust_fvg,'ce':(alt_fvg+ust_fvg)/2.0,'taze':True,'etiket':'Bear IFVG (Flip)'})
  elif l0>h2 and(-govde1)>=E*0.32 and(l0-h2)>=E*0.08:
   alt_fvg,ust_fvg,gap_boy=(h2,l0,l0-h2)
   fvg_bear_set.add(i);fvg_koku_map[i]=ust_fvg
   kirildi,max_high,k_idx=(False,alt_fvg,None)
   for m in G(i+2,ct):
    if _f(df,'close',m)>ust_fvg:kirildi=True;k_idx=m;break
    if _f(df,'high',m)>max_high:max_high=_f(df,'high',m)
   if not kirildi:
    aktif_alt=N(ust_fvg,M(alt_fvg,max_high))
    if(ust_fvg-aktif_alt)>=gap_boy*0.22:
     durum='Taze'if max_high<=alt_fvg else'Kısmi';key=f"SIBI_{aktif_alt:.4f}_{ust_fvg:.4f}"
     if key not in eklenen_imb:
      eklenen_imb.add(key);imbalance_list.append({'tip':'SIBI_FVG','yon':'BEAR','idx1':i-1,'t1':ts[i-1],'lo':aktif_alt,'hi':ust_fvg,'ce':(aktif_alt+ust_fvg)/2.0,'taze':max_high<=alt_fvg,'etiket':f"SIBI FVG ({durum})"})
   elif k_idx is not None and k_idx>=ct-45:
    if all(_f(df,'close',m)>=alt_fvg-E*0.1 for m in G(k_idx+1,ct))and A(son_c-alt_fvg)<=E*4.5:
     imbalance_list.append({'tip':'IFVG','yon':'BULL','idx1':k_idx,'t1':ts[k_idx],'lo':alt_fvg,'hi':ust_fvg,'ce':(alt_fvg+ust_fvg)/2.0,'taze':True,'etiket':'Bull IFVG (Flip)'})
  # 20-volume-imbalance-gap.pdf & YT-Part7: Gerçek GAP (İğne Boşluklu Sıçrama) ve Volume Imbalance (VIB - İğne Dolgulu Kapanış/Açılış Boşluğu) Tespiti
  o0_v,c0_v=(_f(df,'open',i-1),_f(df,'close',i-1));l1_v,h1_v=(_f(df,'low',i),_f(df,'high',i))
  if o1>c0_v+E*0.06 and(c1>o1 or l1_v>h0):
   vib_lo,vib_hi=(h0,l1_v)if l1_v>h0 else(N(c0_v,o1),M(c0_v,o1))
   tam_gap_mi=bool(l1_v>h0)
   fvg_bull_set.add(i);fvg_koku_map.setdefault(i,vib_lo)
   if not any(_f(df,'close',m)<vib_lo for m in G(i+1,ct)):
    key_v=f"VIB_BULL_{vib_lo:.4f}_{vib_hi:.4f}"
    if key_v not in eklenen_imb:
     eklenen_imb.add(key_v);imbalance_list.append({'tip':'TRUE_GAP'if tam_gap_mi else'VIB_GAP','yon':'BULL','idx1':i-1,'t1':ts[i-1],'lo':vib_lo,'hi':vib_hi,'ce':(vib_lo+vib_hi)/2.0,'taze':True,'etiket':'Bull GAP'if tam_gap_mi else'Bull VIB'})
  elif o1<c0_v-E*0.06 and(c1<o1 or h1_v<l0):
   vib_lo,vib_hi=(h1_v,l0)if h1_v<l0 else(N(c0_v,o1),M(c0_v,o1))
   tam_gap_mi=bool(h1_v<l0)
   fvg_bear_set.add(i);fvg_koku_map.setdefault(i,vib_hi)
   if not any(_f(df,'close',m)>vib_hi for m in G(i+1,ct)):
    key_v=f"VIB_BEAR_{vib_lo:.4f}_{vib_hi:.4f}"
    if key_v not in eklenen_imb:
     eklenen_imb.add(key_v);imbalance_list.append({'tip':'TRUE_GAP'if tam_gap_mi else'VIB_GAP','yon':'BEAR','idx1':i-1,'t1':ts[i-1],'lo':vib_lo,'hi':vib_hi,'ce':(vib_lo+vib_hi)/2.0,'taze':True,'etiket':'Bear GAP'if tam_gap_mi else'Bear VIB'})
 # 2) 4 ARZ/TALEP MODU (DBR, RBR, RBD, DBD) VE 10 PUANLIK GÜÇ HESAPLAMA YARDIMCISI
 eklenen_at=set()
 def _bolge_degerlendir_ve_ekle(yon_b,oi,bi,rev_mi=False,bos_kaynakli=True):
  if oi<1 or oi>=ct-2:return
  bi=M(oi+1,N(ct-1,int(bi)))
  oncesi_bas=M(0,oi-4);oncesi_son=M(0,oi-1)
  oncesi_degisim=_f(df,'close',oncesi_son)-_f(df,'open',oncesi_bas)
  if not bos_kaynakli:
   # Kırılım (BOS/CHoCH) üretmemiş ara FVG bazları ASLA dönüş (DBR/RBD) bölgesi olamaz;
   # yalnızca mevcut dalga yönünde devam bazı (Bullish RBR / Bearish DBD) olabilir!
   if yon_b=='BULLISH'and oncesi_degisim<E*0.20:return
   if yon_b=='BEARISH'and oncesi_degisim>-E*0.20:return
  if yon_b=='BULLISH':
   # DBR (Drop-Base-Rally) vs RBR (Rally-Base-Rally) ayrımı (03-supply-demand.pdf)
   mod_kodu='DBR'if(bos_kaynakli and(rev_mi or oncesi_degisim<=-E*0.25))else'RBR'
   lo=N(_f(df,'low',oi),_f(df,'low',N(ct-1,oi+1))if oi+1<bi else _f(df,'low',oi))
   base_ust=M(_f(df,'open',oi),_f(df,'close',oi));ters_mum_var=(_f(df,'close',oi)<_f(df,'open',oi))or(_f(df,'close',M(0,oi-1))<_f(df,'open',M(0,oi-1)));patlama_ayrilis=False;ayrilis_idx=oi+1
   bas_j=M(0,oi-1)if A(_f(df,'close',M(0,oi-1))-_f(df,'open',M(0,oi-1)))<=E*0.55 else oi
   for j in G(bas_j,N(ct-1,oi+4)+1):
    oj,cj,hj=(_f(df,'open',j),_f(df,'close',j),_f(df,'high',j))
    if cj<oj:
     ters_mum_var=True
     base_ust=M(base_ust,oj,hj if(hj-lo)<=E*1.25 else oj)
    elif cj>oj and(cj-oj)>=E*0.50:
     if j>oi:
      ayrilis_idx=j
      if(cj-oj)>=E*1.05 or A(oj-_f(df,'close',M(0,j-1)))>=E*0.12:patlama_ayrilis=True
      break
     base_ust=M(base_ust,oj)
   hi=M(lo+E*0.22,N(base_ust,lo+E*1.35))
   fvg_imza=any((sd in fvg_bull_set for sd in G(oi,N(ct-1,oi+4)+1)))
   imb_koku=hi
   for sd in G(oi,N(ct-1,oi+3)+1):
    if sd in fvg_koku_map:imb_koku=M(hi,N(hi+E*0.35,F(fvg_koku_map[sd])));break
   baz_s=sum((1 for k in G(M(0,oi-1),N(ct-2,oi+5)+1)if lo-E*0.10<=_f(df,'close',k)<=hi+E*0.10))
   sonraki_max=F(df['high'].iloc[oi+1:ct].max())if oi+1<ct else hi
   cikis_mesafe=M(0.0,sonraki_max-lo)
   # Tazelik & Kırılım Kontrolü: Fiyat bölgeden ayrıldıktan sonra kaç kez test etti?
   ayrilis_sonu=N(ct-1,M(bi,ayrilis_idx)+1)
   if ayrilis_sonu>=ct-1 or sonraki_max<hi+E*0.55:return
   kirildi,test_say,k_idx,in_touch=(False,0,None,False)
   for m in G(ayrilis_sonu,ct):
    cm_v,lm_v=(_f(df,'close',m),_f(df,'low',m))
    if cm_v<lo-E*0.03:kirildi=True;k_idx=m;break
    # Son 3 mum (canlı/güncel bölge ziyareti) öncesi geçmiş testleri say
    if m<ct-3:
     if lm_v<=hi and cm_v>=lo:
      if not in_touch:test_say+=1;in_touch=True
     elif lm_v>hi+E*0.25:
      in_touch=False
   # 04-arz-talep-gucu.pdf: 10 Üzerinden Puanlama
   p_cikis=2.0 if(fvg_imza or patlama_ayrilis)and cikis_mesafe>=E*2.0 else(1.5 if cikis_mesafe>=E*1.75 else(1.0 if cikis_mesafe>=E*1.30 else 0.0))
   p_zaman=2.0 if baz_s<=3 else(1.0 if baz_s<=6 else 0.0)
   p_tazelik=3.0 if test_say==0 else(1.5 if test_say==1 else 0.0)
   kalinlik=M(hi-lo,E*0.22)
   rr_oran=(sonraki_max-hi)/kalinlik
   p_rr=3.0 if rr_oran>=3.0 else(2.0 if rr_oran>=2.2 else(1.5 if rr_oran>=1.6 else 0.5))
   # 05-arz-talep-yaklasimi.pdf: Bölgeye yaklaşım bonusu
   yak_puan=0.0
   if ct-ayrilis_sonu>=6 and baz_s<=3:yak_puan+=0.5
   if ct>=6:
    son_govdeler=F((df['close'].iloc[-5:-1]-df['open'].iloc[-5:-1]).abs().mean())
    if son_govdeler<=E*0.65:yak_puan+=0.5
   guc_10p=N(10.0,R(p_cikis+p_zaman+p_tazelik+p_rr+N(1.0,yak_puan),1))
   taze_mi=(test_say==0)
   yipranmis_mi=(test_say>=2)
   onceki_min_l=F(df['low'].iloc[M(0,oi-12):oi].min())if oi>=3 else lo
   likidite_aldi=bool(lo<onceki_min_l and _f(df,'close',N(ct-1,ayrilis_idx))>onceki_min_l)
   guclu_fresh=bool((not kirildi)and taze_mi and not yipranmis_mi and p_cikis>=1.0 and p_zaman>=1.0 and guc_10p>=6.5)
   ob_mi=bool((not kirildi)and not yipranmis_mi and ters_mum_var and(rev_mi or likidite_aldi or bos_kaynakli)and(fvg_imza or p_cikis>=1.5))
   key=f"D_{lo:.4f}_{hi:.4f}"
   if not kirildi and not yipranmis_mi and key not in eklenen_at and p_cikis>=1.0:
    eklenen_at.add(key);durum='Taze'if taze_mi else f"{test_say}x Test"
    kir_kaynak=('CHOCH'if rev_mi else'BOS')if bos_kaynakli else'ARA_BAZ'
    kalip=f"Talep ({mod_kodu}-{kir_kaynak})"if bos_kaynakli else f"Talep ({mod_kodu})"
    ob_kalip=f"Bull OB ({mod_kodu}) [{durum} | {guc_10p}/10]"
    arz_talep_list.append({'tur':'TALEP','alt_tur':'REVERSAL_OB'if(rev_mi or ob_mi)else'VALID_DEMAND','mod':mod_kodu,'bos_kaynakli':bool(bos_kaynakli),'kirilim_kaynagi':kir_kaynak,'idx1':oi,'t1':ts[oi],'lo':lo,'hi':hi,'eq':(lo+hi)/2.0,'imbalance_koku':imb_koku,'taze':taze_mi,'guclu_fresh':guclu_fresh,'ob_mi':ob_mi,'fvg_imza':fvg_imza,'guc_10p':guc_10p,'p_cikis':p_cikis,'p_zaman':p_zaman,'p_tazelik':p_tazelik,'p_rr':p_rr,'test':test_say,'etiket':f"Talep ({mod_kodu}) [{durum} | {guc_10p}/10]",'ob_etiket':ob_kalip})
   elif kirildi and k_idx is not None and k_idx<ct-2:
    if all(_f(df,'close',m)<=hi+E*0.1 for m in G(k_idx+1,ct))and A(son_c-hi)<=E*6.0 and key not in eklenen_at:
     eklenen_at.add(key);arz_talep_list.append({'tur':'ARZ','alt_tur':'FLIP_ARZ','mod':'FLIP_ARZ','idx1':k_idx,'t1':ts[k_idx],'lo':lo,'hi':hi,'eq':(lo+hi)/2.0,'imbalance_koku':lo,'taze':True,'guclu_fresh':False,'ob_mi':False,'fvg_imza':False,'guc_10p':6.0,'test':0,'etiket':'Flip Arz (Breaker)'})
  else:
   # RBD (Rally-Base-Drop) vs DBD (Drop-Base-Drop) ayrımı (03-supply-demand.pdf)
   mod_kodu='RBD'if(bos_kaynakli and(rev_mi or oncesi_degisim>=E*0.25))else'DBD'
   hi=M(_f(df,'high',oi),_f(df,'high',N(ct-1,oi+1))if oi+1<bi else _f(df,'high',oi))
   base_alt=N(_f(df,'open',oi),_f(df,'close',oi));ters_mum_var=(_f(df,'close',oi)>_f(df,'open',oi))or(_f(df,'close',M(0,oi-1))>_f(df,'open',M(0,oi-1)));patlama_ayrilis=False;ayrilis_idx=oi+1
   bas_j=M(0,oi-1)if A(_f(df,'close',M(0,oi-1))-_f(df,'open',M(0,oi-1)))<=E*0.55 else oi
   for j in G(bas_j,N(ct-1,oi+4)+1):
    oj,cj,lj=(_f(df,'open',j),_f(df,'close',j),_f(df,'low',j))
    if cj>oj:
     ters_mum_var=True
     base_alt=N(base_alt,oj,lj if(hi-lj)<=E*1.25 else oj)
    elif cj<oj and(oj-cj)>=E*0.50:
     if j>oi:
      ayrilis_idx=j
      if(oj-cj)>=E*1.05 or A(oj-_f(df,'close',M(0,j-1)))>=E*0.12:patlama_ayrilis=True
      break
     base_alt=N(base_alt,oj)
   lo=N(hi-E*0.22,M(base_alt,hi-E*1.35))
   fvg_imza=any((sd in fvg_bear_set for sd in G(oi,N(ct-1,oi+4)+1)))
   imb_koku=lo
   for sd in G(oi,N(ct-1,oi+3)+1):
    if sd in fvg_koku_map:imb_koku=N(lo,M(lo-E*0.35,F(fvg_koku_map[sd])));break
   baz_s=sum((1 for k in G(M(0,oi-1),N(ct-2,oi+5)+1)if lo-E*0.10<=_f(df,'close',k)<=hi+E*0.10))
   sonraki_min=F(df['low'].iloc[oi+1:ct].min())if oi+1<ct else lo
   cikis_mesafe=M(0.0,hi-sonraki_min)
   ayrilis_sonu=N(ct-1,M(bi,ayrilis_idx)+1)
   if ayrilis_sonu>=ct-1 or sonraki_min>lo-E*0.55:return
   kirildi,test_say,k_idx,in_touch=(False,0,None,False)
   for m in G(ayrilis_sonu,ct):
    cm_v,hm_v=(_f(df,'close',m),_f(df,'high',m))
    if cm_v>hi+E*0.03:kirildi=True;k_idx=m;break
    if m<ct-3:
     if hm_v>=lo and cm_v<=hi:
      if not in_touch:test_say+=1;in_touch=True
     elif hm_v<lo-E*0.25:
      in_touch=False
   p_cikis=2.0 if(fvg_imza or patlama_ayrilis)and cikis_mesafe>=E*2.0 else(1.5 if cikis_mesafe>=E*1.75 else(1.0 if cikis_mesafe>=E*1.30 else 0.0))
   p_zaman=2.0 if baz_s<=3 else(1.0 if baz_s<=6 else 0.0)
   p_tazelik=3.0 if test_say==0 else(1.5 if test_say==1 else 0.0)
   kalinlik=M(hi-lo,E*0.22)
   rr_oran=(lo-sonraki_min)/kalinlik
   p_rr=3.0 if rr_oran>=3.0 else(2.0 if rr_oran>=2.2 else(1.5 if rr_oran>=1.6 else 0.5))
   yak_puan=0.0
   if ct-ayrilis_sonu>=6 and baz_s<=3:yak_puan+=0.5
   if ct>=6:
    son_govdeler=F((df['close'].iloc[-5:-1]-df['open'].iloc[-5:-1]).abs().mean())
    if son_govdeler<=E*0.65:yak_puan+=0.5
   guc_10p=N(10.0,R(p_cikis+p_zaman+p_tazelik+p_rr+N(1.0,yak_puan),1))
   taze_mi=(test_say==0)
   yipranmis_mi=(test_say>=2)
   onceki_max_h=F(df['high'].iloc[M(0,oi-12):oi].max())if oi>=3 else hi
   likidite_aldi=bool(hi>onceki_max_h and _f(df,'close',N(ct-1,ayrilis_idx))<onceki_max_h)
   guclu_fresh=bool((not kirildi)and taze_mi and not yipranmis_mi and p_cikis>=1.0 and p_zaman>=1.0 and guc_10p>=6.5)
   ob_mi=bool((not kirildi)and not yipranmis_mi and ters_mum_var and(rev_mi or likidite_aldi or bos_kaynakli)and(fvg_imza or p_cikis>=1.5))
   key=f"S_{lo:.4f}_{hi:.4f}"
   if not kirildi and not yipranmis_mi and key not in eklenen_at and p_cikis>=1.0:
    eklenen_at.add(key);durum='Taze'if taze_mi else f"{test_say}x Test"
    kir_kaynak=('CHOCH'if rev_mi else'BOS')if bos_kaynakli else'ARA_BAZ'
    kalip=f"Arz ({mod_kodu}-{kir_kaynak})"if bos_kaynakli else f"Arz ({mod_kodu})"
    ob_kalip=f"Bear OB ({mod_kodu}) [{durum} | {guc_10p}/10]"
    arz_talep_list.append({'tur':'ARZ','alt_tur':'REVERSAL_OB'if(rev_mi or ob_mi)else'VALID_SUPPLY','mod':mod_kodu,'bos_kaynakli':bool(bos_kaynakli),'kirilim_kaynagi':kir_kaynak,'idx1':oi,'t1':ts[oi],'lo':lo,'hi':hi,'eq':(lo+hi)/2.0,'imbalance_koku':imb_koku,'taze':taze_mi,'guclu_fresh':guclu_fresh,'ob_mi':ob_mi,'fvg_imza':fvg_imza,'guc_10p':guc_10p,'p_cikis':p_cikis,'p_zaman':p_zaman,'p_tazelik':p_tazelik,'p_rr':p_rr,'test':test_say,'etiket':f"Arz ({mod_kodu}) [{durum} | {guc_10p}/10]",'ob_etiket':ob_kalip})
   elif kirildi and k_idx is not None and k_idx<ct-2:
    if all(_f(df,'close',m)>=lo-E*0.1 for m in G(k_idx+1,ct))and A(son_c-lo)<=E*6.0 and key not in eklenen_at:
     eklenen_at.add(key);arz_talep_list.append({'tur':'TALEP','alt_tur':'FLIP_TALEP','mod':'FLIP_TALEP','idx1':k_idx,'t1':ts[k_idx],'lo':lo,'hi':hi,'eq':(lo+hi)/2.0,'imbalance_koku':hi,'taze':True,'guclu_fresh':False,'ob_mi':False,'fvg_imza':False,'guc_10p':6.0,'test':0,'etiket':'Flip Talep (Breaker)'})
 # A) Yapı Kırılımı (BOS / CHoCH / MSB) Kaynaklı Arz/Talep Bölgeleri (DBR, RBR, RBD, DBD)
 for b in(bos_list or[]):
  oi=M(0,N(ct-3,int(b.get('orig_idx',b.get('idx1',0)))))
  bi=M(oi+1,N(ct-1,int(b.get('idx2',ct-1))))
  rev_mi='MSB'in str(b.get('tip',''))or'CHOCH'in str(b.get('tip',''))
  _bolge_degerlendir_ve_ekle('BULLISH'if b.get('yon')=='BULLISH'else'BEARISH',oi,bi,rev_mi,True)
 # B) İmbalans / FVG Bırakan Patlayıcı RBR / DBD / DBR / RBD Ara Bazlar (03-supply-demand.pdf & 08-ftr.pdf)
 for f_idx in sorted(list(fvg_bull_set))[-8:]:
  if f_idx>=2 and f_idx<ct-2:
   baz_i=f_idx-1
   _bolge_degerlendir_ve_ekle('BULLISH',baz_i,f_idx+1,False,False)
 for f_idx in sorted(list(fvg_bear_set))[-8:]:
  if f_idx>=2 and f_idx<ct-2:
   baz_i=f_idx-1
   _bolge_degerlendir_ve_ekle('BEARISH',baz_i,f_idx+1,False,False)
 arz_talep_list.sort(key=lambda z:(int(bool(z.get('guclu_fresh',False))),int(bool(z.get('taze',False))),F(z.get('guc_10p',0.0)),int(z.get('idx1',0))),reverse=True)
 tekil_at=[]
 for z_aday in arz_talep_list:
  cakisiyor=False
  for z_mevcut in tekil_at:
   if z_mevcut.get('tur')==z_aday.get('tur'):
    kes_alt=M(F(z_mevcut['lo']),F(z_aday['lo']));kes_ust=N(F(z_mevcut['hi']),F(z_aday['hi']))
    if(kes_ust-kes_alt)>=N(M(F(z_mevcut['hi'])-F(z_mevcut['lo']),1e-9),M(F(z_aday['hi'])-F(z_aday['lo']),1e-9))*0.25:
     if z_aday.get('ob_mi')and not z_mevcut.get('ob_mi'):
      z_mevcut['ob_mi']=True
      z_mevcut['ob_etiket']=z_aday.get('ob_etiket',z_mevcut.get('etiket','OB'))
     if z_aday.get('bos_kaynakli')and not z_mevcut.get('bos_kaynakli'):
      z_mevcut['bos_kaynakli']=True
      z_mevcut['kirilim_kaynagi']=z_aday.get('kirilim_kaynagi','BOS')
     if z_aday.get('fvg_imza')and not z_mevcut.get('fvg_imza'):
      z_mevcut['fvg_imza']=True
     cakisiyor=True;break
  if not cakisiyor:
   tekil_at.append(z_aday)
 tekil_at.sort(key=lambda z:(int(bool(z.get('guclu_fresh',False))),int(bool(z.get('taze',False))),F(z.get('guc_10p',0.0)),int(z.get('idx1',0))))
 return(tekil_at[-12:],imbalance_list[-12:])
def _hedef_yonde_alinmamis_likidite_analizi(bS,bw,aP,Q,ak,B='BULLISH'):
 """1. MOD 4. GÜÇ ARTIRICI FAKTÖR: İşlem yönünde (fiyatın gitmek isteyeceği mıknatıs yönde)
 ne kadar alınmamış likidite (EQH/EQL, Eski Swing Tepe/Dip BSL/SSL, Trendline Likiditesi, IDM) varsa
 işlem gücünü o derecede artırır."""
 g=(B=='BULLISH')
 E_htf=M(_f(bS,'atr',-2)if bS is not None and'atr'in bS.columns else ak*0.003,ak*0.001)
 tol=E_htf*0.25
 havuzlar=[]
 def _havuz_ekle(seviye,etiket,agirlik):
  sv=F(seviye or 0.0)
  if sv<=0:return
  if(g and sv<=ak+E_htf*0.10)or((not g)and sv>=ak-E_htf*0.10):return
  if any(A(sv-h['seviye'])<=tol for h in havuzlar):return
  havuzlar.append({'seviye':sv,'etiket':etiket,'agirlik':F(agirlik)})
 if bS is not None and I(aP,dict):
  try:
   _,_s,htf_lm=_likidite_ve_sfp_yapilarini_bul(bS,aP.get('highs'),aP.get('lows'))
   if g:
    for _,_,eq_v in htf_lm.get('aktif_eqh',[]):
     _havuz_ekle(eq_v,f"HTF_EQH({eq_v:.4f})",3.0)
    if htf_lm.get('aktif_idm_bsl'):
     _havuz_ekle(htf_lm['aktif_idm_bsl'],f"HTF_IDM_BSL({F(htf_lm['aktif_idm_bsl']):.4f})",2.0)
    if htf_lm.get('ext_bsl'):
     _havuz_ekle(htf_lm['ext_bsl'],f"HTF_ExtBSL({F(htf_lm['ext_bsl']):.4f})",2.5)
    ct_h=L(bS)
    for ih,vh in(aP.get('highs')or[]):
     if ih<ct_h-2 and F(vh)>ak+E_htf*0.15 and not any(_f(bS,'high',b)>F(vh)+E_htf*0.03 for b in G(int(ih)+1,ct_h)):
      _havuz_ekle(vh,f"HTF_BSL({F(vh):.4f})",2.0)
    for b_i in G(M(2,ct_h-45),ct_h-2):
     hb_i=_f(bS,'high',b_i)
     if hb_i>ak+E_htf*0.15 and hb_i>=_f(bS,'high',b_i-1)and hb_i>=_f(bS,'high',b_i+1):
      if not any(_f(bS,'high',m)>hb_i+E_htf*0.03 for m in G(b_i+1,ct_h)):
       _havuz_ekle(hb_i,f"Int_BSL({hb_i:.4f})",1.6)
   else:
    for _,_,eq_v in htf_lm.get('aktif_eql',[]):
     _havuz_ekle(eq_v,f"HTF_EQL({eq_v:.4f})",3.0)
    if htf_lm.get('aktif_idm_ssl'):
     _havuz_ekle(htf_lm['aktif_idm_ssl'],f"HTF_IDM_SSL({F(htf_lm['aktif_idm_ssl']):.4f})",2.0)
    if htf_lm.get('ext_ssl'):
     _havuz_ekle(htf_lm['ext_ssl'],f"HTF_ExtSSL({F(htf_lm['ext_ssl']):.4f})",2.5)
    ct_h=L(bS)
    for il,vl in(aP.get('lows')or[]):
     if il<ct_h-2 and F(vl)<ak-E_htf*0.15 and not any(_f(bS,'low',b)<F(vl)-E_htf*0.03 for b in G(int(il)+1,ct_h)):
      _havuz_ekle(vl,f"HTF_SSL({F(vl):.4f})",2.0)
    for b_i in G(M(2,ct_h-45),ct_h-2):
     lb_i=_f(bS,'low',b_i)
     if lb_i<ak-E_htf*0.15 and lb_i<=_f(bS,'low',b_i-1)and lb_i<=_f(bS,'low',b_i+1):
      if not any(_f(bS,'low',m)<lb_i-E_htf*0.03 for m in G(b_i+1,ct_h)):
       _havuz_ekle(lb_i,f"Int_SSL({lb_i:.4f})",1.6)
  except X:pass
 if bw is not None and I(Q,dict)and L(bw)>=10:
  try:
   _,_sm,mtf_lm=_likidite_ve_sfp_yapilarini_bul(bw,Q.get('highs'),Q.get('lows'))
   if g:
    for _,_,eq_v in mtf_lm.get('aktif_eqh',[]):
     _havuz_ekle(eq_v,f"MTF_EQH({eq_v:.4f})",2.2)
    if mtf_lm.get('ext_bsl'):
     _havuz_ekle(mtf_lm['ext_bsl'],f"MTF_BSL({F(mtf_lm['ext_bsl']):.4f})",1.5)
   else:
    for _,_,eq_v in mtf_lm.get('aktif_eql',[]):
     _havuz_ekle(eq_v,f"MTF_EQL({eq_v:.4f})",2.2)
    if mtf_lm.get('ext_ssl'):
     _havuz_ekle(mtf_lm['ext_ssl'],f"MTF_SSL({F(mtf_lm['ext_ssl']):.4f})",1.5)
  except X:pass
 top_agirlik=R(sum(h['agirlik']for h in havuzlar),2)
 return{'var_mi':L(havuzlar)>=1,'havuz_sayisi':L(havuzlar),'agirlik_puani':top_agirlik,'etiketler':[h['etiket']for h in havuzlar[:5]],'havuzlar':havuzlar}
def _karne_checklist_olustur(H,html_mi=False,yorum_on_eki=''):
 kFlt=H.get('konum_meta',{})if I(H,dict)and I(H.get('konum_meta'),dict)else{}
 chk=kFlt.get('checklist',{})if I(kFlt.get('checklist'),dict)else{}
 maddeler=[
  ('1. Şart [Zorunlu]: HTF Yön + Güçlü Fresh Arz/Talep',bool(chk.get('mod1_zorunlu_sart1',kFlt.get('htf_arz_talep_bolgesinde',False))),f"Yön:{H.get('yon_4h','-')} | Mod:{chk.get('arz_talep_modu','-')} ({chk.get('fresh_aralik','-')} | Güç:{chk.get('arz_talep_10p','-')}/10)"),
  ('Güç 1: HTF Order Block (OB) Bölgesi',bool(chk.get('ob',False)),str(chk.get('ob_aralik','-'))),
  ('Güç 2: HTF OTE (0.618-0.786) Bölgesi',bool(chk.get('ote',False)),str(chk.get('ote_aralik','-'))),
  ('Güç 3: HTF FVG / Imbalance Bölgesi',bool(chk.get('fvg',kFlt.get('htf_fvg_bolgesinde',False))),str(chk.get('fvg_aralik','-'))),
  ('Güç 4: İşlem Yönünde Alınmamış Likidite',bool(chk.get('hedef_yon_likidite_var',False)),f"{chk.get('hedef_yon_likidite_sayisi',0)} Havuz ({chk.get('hedef_yon_likidite_ozet','-')})"),
  ('Güç 5: HTF QML (Quasimodo) Bölgesi',bool(chk.get('qml',False)),str(chk.get('qml_fiyat','-'))),
  ('Parite Sıralama & Safe Derecesi',bool(chk.get('ilk_kontrol_gecti',False)),f"{chk.get('mod1_ek_sart_sayisi',0)}/5 Güç Faktörü ({chk.get('birincil_olcek_skoru',0)}/10000p | {chk.get('safe_derece','-')})"),
  ('2.Mod Ek Bölgeler (BOS/CHoCH/ITZ/Magic)',bool(kFlt.get('htf_ikincil_bolge_onay',False)),f"BOS:{chk.get('bos_fiyat','-')} | ITZ:{chk.get('itz_fiyat','-')} | FL:{chk.get('magic_fiyat','-')}"),
  ('LTF Giriş 1: Arz/Talep + OB + FVG/Imbalance',bool(chk.get('ltf_poi_fvg_onay',False)),str(chk.get('ltf_poi_fvg_ozet','Bekleniyor'))),
  ('LTF Giriş 2: Likidite + QML + Mum/Kırılım',bool(chk.get('ltf_herhangi_tetik',False)),str(chk.get('ltf_tetik_ozet','Bekleniyor')))
 ]
 if html_mi:
  satirlar=['<div style="background:#11111b;padding:6px 8px;border-radius:6px;margin-bottom:6px;border:1px solid #334155;">',f'<div style="color:#fde047;font-weight:bold;margin-bottom:3px;">🛡️ İşleme Giriş Kontrol Listesi ({GIRIS_STRATEJI_MODU.split(":")[0]}):</div>']
  for ad,ok_mu,dt in maddeler:
   ikon='✅'if ok_mu else'⬜';renk='#4ade80'if ok_mu else'#94a3b8'
   satirlar.append(f'<div style="font-size:11px;color:{renk};">{ikon} <b>{ad}:</b> {dt}</div>')
  satirlar.append('</div>')
  return''.join(satirlar)
 satirlar=[]
 for ad,ok_mu,dt in maddeler:
  ikon='[✅]'if ok_mu else'[⬜]'
  satirlar.append(f"{yorum_on_eki} {ikon} {ad:<42} : {dt}")
 return'\n'.join(satirlar)+'\n'
def market_yapisi_ve_fibo_analizi(df,n=SWING_PENCERE):
 aa,ar,kM=kirilim_yoksa_swing_yoktur_analizi(df,n);eK=ext_int_swing_ayristir(df,aa,ar);oW=wyckoff_analizi(df,aa,ar);a5={'yon':'NOTR','bos_var_mi':False,'kirilim_tipi':'YOK','discount_mu':False,'premium_mu':False,'ote_bull_mu':False,'ote_bear_mu':False,'guclu_trend_fibo':False,'range_low_yakin':False,'range_high_yakin':False,'fibo_oran':0.5,'geri_cekilme_oran':0.5,'swing_max':0.0,'swing_min':0.0,'fibo_hedefleri':{},'fibo_seviyeleri':{},'highs':aa,'lows':ar,'external_yon':eK['external_yon'],'strong_point':eK['strong_point'],'weak_point':eK['weak_point'],'break_line_fl':eK['break_line_fl'],'uc_istasyon':eK['uc_istasyon'],'internal_yon':eK['internal_yon'],'internal_choch':eK['internal_choch'],'external_msb':eK['external_msb'],'kuru_kafa_trendline_tuzagi':eK['kuru_kafa_trendline_tuzagi'],'wyckoff_fazi':oW['wyckoff_fazi'],'wyckoff_aciklama':oW['aciklama'],'egimli_flama_mi':oW['egimli_flama_mi'],'kysy_meta':kM,'kysy_onay':kM['kysy_onay'],'elenen_highs':kM['elenen_highs'],'elenen_lows':kM['elenen_lows'],'qml_seviyesi':kM.get('qml_seviyesi'),'qml_idx':kM.get('qml_idx')}
 if L(aa)<1 or L(ar)<1:return a5
 aa_p=([aa[0]]*(3-L(aa))+list(aa))if L(aa)<3 else list(aa)
 ar_p=([ar[0]]*(3-L(ar))+list(ar))if L(ar)<3 else list(ar)
 cl=_f(df,'close',-1);(hS,H0),(gd,H1),(hf,H2)=(aa_p[-3],aa_p[-2],aa_p[-1]);(hT,L0),(ge,L1),(hg,L2)=(ar_p[-3],ar_p[-2],ar_p[-1])
 ir=(H2>H1 and L2>L1)and cl>=L2
 it=L2<L1 and(cl>H2 or(H2>H1 and hf>hg and cl>=L2))
 iu=L1<L0 and L2>=L1 and(cl>H2 or(H2>H1 and hf>hg and cl>=L2))
 jM=cl>H2 and L2>=L1
 iv=(H2<H1 and L2<L1)and cl<=H2
 iw=H2>H1 and(cl<L2 or(L2<L1 and hg>hf and cl<=H2))
 ix=H1>H0 and H2<=H1 and(cl<L2 or(L2<L1 and hg>hf and cl<=H2))
 jN=cl<L2 and H2<=H1
 lh_ll_dusus=bool(H2<H1 and L2<L1 and cl<=H2)
 hh_hl_yukselis=bool(H2>H1 and L2>L1 and cl>=L2)
 kE=f" [Tüm Grafik Swingleri ({L(aa)}H/{L(ar)}L) | {kM['elenen_sayi']} İç Gürültü Elendi]"if kM['elenen_sayi']>0 else f" [Tüm Grafik Onaylı Swingler ({L(aa)}H/{L(ar)}L)]"
 if not kM['kysy_onay']and not(ir or it or iu or jM or iv or iw or ix or jN):
  a5['yon'],a5['bos_var_mi'],a5['kirilim_tipi']=('NOTR',False,'Kırılım Yok -> Swing Yok (06-no-bos-no-trade.pdf: İç Yapı Gürültüsü)')
 elif lh_ll_dusus or(kM['son_kirilim_yon']=='BEARISH'and cl<=H2 and not hh_hl_yukselis):
  a5['yon'],a5['bos_var_mi']=('BEARISH',True)
  a5['kirilim_tipi']=(('Bearish External MSB / QML Kırılımı -> Fresh Arz OB (RBD) Oluşturdu (YT-Part1,3,5)'if eK['external_msb']or H2>H1 else'Bearish Güçlü CHoCH (Likidite Alımlı Reversal -> Internal Bear OB - YT-Part2&3)')if iw else'Bearish Continue BOS / i-BOS -> Valid Supply (DBD/RBD) Oluşturdu (YT-Part1,2,3)')+kE
 elif hh_hl_yukselis or(kM['son_kirilim_yon']=='BULLISH'and cl>=L2 and not lh_ll_dusus and(H2>H1 or cl>H2 or(hf>hg and L2>L1))):
  a5['yon'],a5['bos_var_mi']=('BULLISH',True)
  a5['kirilim_tipi']=(('Bullish External MSB / QML Kırılımı -> Fresh Talep OB (DBR) Oluşturdu (YT-Part1,3,5)'if eK['external_msb']or L2<L1 else'Bullish Güçlü CHoCH (Likidite Alımlı Reversal -> Internal OB - YT-Part2&3)')if it else'Bullish Continue BOS / i-BOS -> Valid Demand (RBR/DBR) Oluşturdu (YT-Part1,2,3)')+kE
 elif iv or iw or ix or jN:
  a5['yon'],a5['bos_var_mi']=('BEARISH',True)
  a5['kirilim_tipi']='Bearish Yapı Kırılımı (LH + LL Düşüş Trendi)'+kE
 elif ir or it or iu or jM:
  a5['yon'],a5['bos_var_mi']=('BULLISH',True)
  a5['kirilim_tipi']='Bullish Yapı Kırılımı (HH + HL Yükseliş Trendi)'+kE
 hb,fN=(F(H2),F(L2))if F(H2)>F(L2)else(M(F(H1),F(H2)),N(F(L1),F(L2)))
 a5['swing_max'],a5['swing_min']=(hb,fN);dU=hb-fN
 if dU>0:
  j6=(cl-fN)/dU;j7=(hb-cl)/dU
  a5['fibo_oran'],a5['geri_cekilme_oran']=(R(j6,3),R(j7,3))
  a5['discount_mu'],a5['premium_mu']=(j6<=0.5,j6>0.5)
  a5['ote_bull_mu'],a5['ote_bear_mu']=(0.60<=j7<=0.886,0.60<=j6<=0.886)
  a5['guclu_trend_fibo']=bool((ir and 0.236<=j7<0.5)or(iv and 0.236<=j6<0.5))
  a5['range_low_yakin'],a5['range_high_yakin']=(j6<=0.22,j6>=0.78)
  a5['fibo_seviyeleri']={'0.0':R(fN if a5['yon']=='BEARISH'else hb,6),'0.236':R((fN+dU*0.236)if a5['yon']=='BEARISH'else(hb-dU*0.236),6),'0.382':R((fN+dU*0.382)if a5['yon']=='BEARISH'else(hb-dU*0.382),6),'0.50_EQ':R(fN+dU*0.5,6),'0.618_OTE':R((fN+dU*0.618)if a5['yon']=='BEARISH'else(hb-dU*0.618),6),'0.705_Sniper':R((fN+dU*0.705)if a5['yon']=='BEARISH'else(hb-dU*0.705),6),'0.786_OTE':R((fN+dU*0.786)if a5['yon']=='BEARISH'else(hb-dU*0.786),6),'0.886_DerinOB':R((fN+dU*0.886)if a5['yon']=='BEARISH'else(hb-dU*0.886),6),'1.0':R(hb if a5['yon']=='BEARISH'else fN,6)}
  a5['fibo_hedefleri']={'TP1_Zero':R(fN,5),'TP2_0236':R(M(0.0,fN-dU*0.236),5),'TP3_050_Simetrik':R(M(0.0,fN-dU*0.50),5),'TP3_Simetrik':R(M(0.0,fN-dU*0.618),5),'TP4_ABCD':R(M(0.0,fN-dU*1.0),5)}if a5['yon']=='BEARISH'else{'TP1_Zero':R(hb,5),'TP2_0236':R(hb+dU*0.236,5),'TP3_050_Simetrik':R(hb+dU*0.50,5),'TP3_Simetrik':R(hb+dU*0.618,5),'TP4_ABCD':R(hb+dU*1.0,5)}
 return a5
def poi_ve_bolge_analizi(df,z,a='1H',B='BULLISH'):
 bb,bc,ak=(_f(df,'low',-2),_f(df,'high',-2),_f(df,'close',-2));E=M(_f(df,'atr',-2),ak*0.001);aa,ar=(z['highs'],z['lows']);dP,K,az,U,px=([],[],[],None,0.0);C=set();g=B=='BULLISH'
 for i in G(M(2,L(df)-40),L(df)-2):
  bC,bD,aD,aM,cd,cc=(_f(df,'high',i-1),_f(df,'low',i-1),_f(df,'close',i),_f(df,'open',i),_f(df,'low',i+1),_f(df,'high',i+1))
  if(cd>bC and aD-aM>E*0.45)if g else(bD>cc and aM-aD>E*0.45):
   C.add(i);fo=df['low'if g else'high'].iloc[i+2:-2];kN,kO=(bC,cd)if g else(cc,bD);qa=(not fo.empty and F(fo.min())<bC-E*0.1)if g else(not fo.empty and F(fo.max())>bD+E*0.1)
   if not qa and(kN-E*0.25<=bb<=kO+E*0.15 and ak>=kN if g else kN-E*0.15<=bc<=kO+E*0.25 and ak<=kO):
    fvg_ce=(kN+kO)/2.0;ce_dokundu=A((bb if g else bc)-fvg_ce)<=E*0.22 or(kN<=ak<=kO)
    nn=f"{a}_{('FVG' if g else 'SIBI_FVG')}{'_50CE' if ce_dokundu else ''}"
    if nn not in dP:dP.append(nn);K.append(f"[{a}] Taze {('BISI' if g else 'Bearish SIBI')} FVG + %50 CE ({fvg_ce:.4f}) Mıknatıs Dönüşü ({kN:.4f}-{kO:.4f}) (19.pdf, YT-Part3 & Ders-06)");az.append(('FVG',i-1,kN,kO));U=(kN if U is None else N(U,kN))if g else(kO if U is None else M(U,kO))
  if(bD>cc and aM-aD>E*0.45 and ak>bD and cc-E*0.15<=bb<=bD+E*0.2)if g else(cd>bC and aD-aM>E*0.45 and ak<bC and bC-E*0.2<=bc<=cd+E*0.15):
   iW=f"{a}_{('IFVG' if g else 'Bear_IFVG')}";kP,kQ=(cc,bD)if g else(bC,cd)
   if iW not in dP:dP.append(iW);K.append(f"[{a}] {('Bullish' if g else 'Bearish')} Inversion FVG (IFVG Dönüşümü) (19-fvg.pdf)");az.append(('IFVG',i-1,kP,kQ));U=(kP if U is None else N(U,kP))if g else(kQ if U is None else M(U,kQ))
 pz,pA=(ar,aa)if g else(aa,ar);qU=N([h for _,h in aa[-4:]if h>ak*1.005],default=ak*1.05)if g else M([l for _,l in ar[-4:]if l<ak*0.995],default=ak*0.95)
 if L(pz)>=2:
  for bu,lu in pz[-4:]:
   if bu<2 or bu>=L(df)-3:continue
   ov=[kv for ki,kv in pA if ki<bu];e7=df.iloc[M(0,bu-1):N(L(df)-2,bu+2)]
   if g:
    gH=ov[-1]if ov else F(df['high'].iloc[:bu].max());no=F(df['high'].iloc[bu+1:-1].max());no_cl=F(df['close'].iloc[bu+1:].max())
    if no_cl<=gH:continue
    nq=e7[e7['close']<e7['open']];aH,aJ=(lu,F(nq['high'].max())if not nq.empty else lu+E*0.5);qt=no-aH
   else:
    gH=ov[-1]if ov else F(df['low'].iloc[:bu].min());no=F(df['low'].iloc[bu+1:-1].min());no_cl=F(df['close'].iloc[bu+1:].min())
    if no_cl>=gH:continue
    nq=e7[e7['close']>e7['open']];aH,aJ=(F(nq['low'].min())if not nq.empty else lu-E*0.5,lu);qt=aJ-no
   hi=rbr_dbd_analizi(df,bu,aH,aJ,B);qb=M(aJ,hi['imbalance_koku'])if g else N(aH,hi['imbalance_koku']);rp=2.0 if(any((bu<=sd<=bu+4 for sd in C))or hi['patlama_ayrilis'])and qt>=E*2.2 else 1.0 if qt>=E*1.5 else 0.0;jE=sum((1 for k in G(bu,N(L(df)-2,bu+6))if(_f(df,'close',k)<=aJ if g else _f(df,'close',k)>=aH)));rq=2.0 if hi['v_shape_1mum']or jE<=2 else 1.0 if jE<=5 else 0.0;oD,ry=(0,False)
   in_t_p=False
   for k in G(N(L(df)-2,bu+M(jE,2)+1),L(df)-3):
    if _f(df,'close',k)<aH-E*0.03 if g else _f(df,'close',k)>aJ+E*0.03:ry=True;break
    if(_f(df,'low',k)<=aJ and _f(df,'close',k)>=aH)if g else(_f(df,'high',k)>=aH and _f(df,'close',k)<=aJ):
     if not in_t_p:oD+=1;in_t_p=True
    elif(_f(df,'low',k)>aJ+E*0.22)if g else(_f(df,'high',k)<aH-E*0.22):
     in_t_p=False
   if ry or oD>=2:continue
   rr=3.0 if oD==0 else 1.5 if oD==1 else 0.0;rt=(qU-aJ if g else aH-qU)/M(aJ-aH,E*0.25);na=3.0 if rt>=3.0 else 1.5 if rt>=2.0 else 0.5;mD=N(10.0,R(rp+rq+rr+na+N(1.0,hi['yaklasim_ek_puan']*0.5),1));qc=[av for ai,av in pz if ai<bu];gv=L(qc)>0 and(lu<qc[-1]if g else lu>qc[-1]);ru='Ext'if a=='1H'else'Int';qd=f"{ru}_{('Reversal_OB' if g else 'Reversal_BearOB')}_{hi['kalip_adi']}"if gv else f"{ru}_{('Continue_ValidDem' if g else 'Continue_ValidSup')}_{hi['kalip_adi']}"
   if hi['hidden_base_dp']:qd+='+HiddenDP'
   if(aH-E*0.25<=bb<=qb+E*0.15 and ak>=aH)if g else(qb-E*0.15<=bc<=aJ+E*0.25 and ak<=aJ):
    ob_mt=(aH+aJ)/2.0;ob_fvg_imza=bool(rp>=1.0 and gv)
    px=M(px,N(10.0,mD+(0.5 if ob_fvg_imza else 0.0)));dP.append(f'{a}_{qd}({mD}/10)')
    if ob_fvg_imza and f'{a}_GercekOB_FVG_SonKale'not in dP:dP.append(f'{a}_GercekOB_FVG_SonKale')
    pQ=', Yaklaşım: '+'+'.join(hi['yaklasim_ipuclari'])if hi['yaklasim_ipuclari']else''
    K.append(f"[{a}] {('Bullish' if g else 'Bearish')} {qd} (%50 Mean Threshold: {ob_mt:.4f} | İmbalans Kökü: {qb:.4f}{' | Gerçek OB+FVG Son Kale İmzası!' if ob_fvg_imza else ''}) | Güç: {mD}/10 (Çıkış:{rp}p, V-Shape:{rq}p, Fresh:{rr}p, RR:{na}p{pQ}) (YT-Part1,2,3 & Ders-07)")
    az.append(('OB',bu,aH,aJ));U=(N(U,aH)if U else aH)if g else(M(U,aJ)if U else aJ);break
 if L(pA)>=2:
  for gw,ow in pA[-4:-1]:
   if gw<2 or gw>=L(df)-5:continue
   fL=df.iloc[gw+1:N(L(df)-2,gw+12)];kR,kS=((_f(df,'open',gw)if _f(df,'close',gw)>_f(df,'open',gw)else ow-E*0.35),ow)if g else(ow,(_f(df,'open',gw)if _f(df,'close',gw)<_f(df,'open',gw)else ow+E*0.35));h6=any((F(r['close'])>kS+E*0.12 and F(r['close'])-F(r['open'])>E*0.5 for _,r in fL.iterrows()))if g else any((F(r['close'])<kR-E*0.12 and F(r['open'])-F(r['close'])>E*0.5 for _,r in fL.iterrows()))
   if h6 and(kR-E*0.2<=(bb if g else bc)<=kS+E*0.2)and(ak>=kR if g else ak<=kS):dP.append(f"{a}_{('TersFlag_Flip' if g else 'Bear_TersFlag_Flip')}");K.append(f"[{a}] {('Bullish' if g else 'Bearish')} Flip Bölge / Ters Flag ({(kS if g else kR):.4f}) (YT-Part1,2,3)");az.append(('BB/FL',gw,kR,kS));U=(kR if U is None else N(U,kR))if g else(kS if U is None else M(U,kS));break
 j8,f0,f1,hC,_=ftr_fo_itz_taramasi(df,z,C,a,B);eY,dx,dy,ef,eg=dp_ve_fl_analizi(df,z,C,a,B);j9,mx,iC,iD,dg=quasimodo_mpl_analizi(df,z,C,a,B);ka,eh,hv,jX,g4=imbalance_fvg_koku_analizi(df,z,C,a,B);z['fl_dp_meta'],z['qm_meta'],z['v6_meta']=(eg,dg,g4)
 for kb,f2,kd,hD in[(j8,f0,f1,hC),(eY,dx,dy,ef),(j9,mx,iC,iD),(ka,eh,hv,jX)]:
  for eZ in kb:
   if eZ not in dP:dP.append(eZ)
  K.extend(kd);az.extend(hD)
  if f2 is not None:U=f2 if U is None else N(U,f2)if g else M(U,f2)
 ke,ei,fl,lf,er=gap_vib_fibo_analizi(df,z,dP,a,B);kf,ej,fP,iH,fg=range_po3_tt3_analizi(df,z,C,a,B);hE,dz,b9,cz,bQ=bobin_atnali_mw_analizi(df,z,C,a,B);hF,dA,bA,dq,bl=engulf_pinbar_analizi(df,z,C,a,B);ev,dB,cA,ea,bg=ib_fakey_smt_analizi(df,z,C,a,B,z.get('sembol','BTC/USDT'));z['v7_meta'],z['v9_meta'],z['v10_meta'],z['v11_meta'],z['v12_meta']=(er,fg,bQ,bl,bg);hG,dC,cC,fZ,bv=entry_mtf_3r_analizi(df,z,dP+ev,C,a,B);z['v13_meta']=bv
 for rX,jS,ph,rY in[(ke,ei,fl,lf),(kf,ej,fP,iH),(hE,dz,b9,cz),(hF,dA,bA,dq),(ev,dB,cA,ea),(hG,dC,cC,fZ)]:
  for vp in rX:
   if vp not in dP:dP.append(vp)
  K.extend(ph);az.extend(rY)
  if jS is not None:U=jS if U is None else N(U,jS)if g else M(U,jS)
 return(dP,U,K,az,px)
def likidite_smt_analizi(J,bJ,af,a2,B='BULLISH'):
 iR,K,a3=([],[],0);pl,pm=(a2['highs'],a2['lows']);nZ,n0=swing_noktalarini_bul(af,n=2,kirilim_sarti=False);cl=_f(af,'close',-2);eF=J.split(':')[0];qV='ETH/USDT'if eF=='BTC/USDT'else'BTC/USDT';k7=an.get(LTF_PERIYOT,an.get('15m',{})).get(qV);oX=a2.get('wyckoff_fazi','');g=B=='BULLISH'
 if(g and oX in('ACCUMULATION_SPRING','RE_ACCUMULATION'))or(not g and oX in('DISTRIBUTION_UTAD','RE_DISTRIBUTION')):iR.append(oX);K.append(f"[{MTF_PERIYOT.upper()}] {a2.get('wyckoff_aciklama', 'Wyckoff Yakıt Operasyonu')}");a3+=7
 hH,pB=(n0 if g else nZ,pm if g else pl)
 _,_,ltf_lmeta=_likidite_ve_sfp_yapilarini_bul(af)
 _,_,mtf_lmeta=_likidite_ve_sfp_yapilarini_bul(bJ,pl,pm)
 sfp_ltf_obj=ltf_lmeta.get('son_bull_sfp'if g else'son_bear_sfp')
 if sfp_ltf_obj and int(sfp_ltf_obj.get('idx',0))>=L(af)-6:
  my=F(sfp_ltf_obj.get('level')or sfp_ltf_obj.get('price')or cl)
  iR.append('Bull_SFP'if g else'Bear_SFP');K.append(f"[{LTF_PERIYOT}] {('Bullish' if g else 'Bearish')} SFP (İğne Avı): Kırılmamış {my:.4f} likiditesi iğneyle süpürüldü ve içeride kapandı (23-sfp.pdf & Ders-02/04)");a3+=9
 idm_sw_obj=(mtf_lmeta.get('swept_idm_bull')or ltf_lmeta.get('swept_idm_bull'))if g else(mtf_lmeta.get('swept_idm_bear')or ltf_lmeta.get('swept_idm_bear'))
 if idm_sw_obj is not None:
  iR.append('IDM_Sweep_Bull'if g else'IDM_Sweep_Bear');K.append(f"[{MTF_PERIYOT.upper()}/{LTF_PERIYOT}] Inducement (IDM Likidite Yemi: {F(idm_sw_obj):.4f}) Süpürüldü ✓ (Ders-03 & 22.pdf)");a3+=6
 if L(pB)>=2:
  u1,u2=(pB[-2][1],pB[-1][1])
  if A(u2-u1)/M(u1,1e-09)<=0.004:iR.append('EQL_Fakeout'if g else'EQH_Fakeout');K.append(f"[{MTF_PERIYOT.upper()}] {('EQL' if g else 'EQH')} Fake-Out Likiditesi (16-fakeout.pdf)");a3+=5
  if(_f(bJ,'low',-2)<u2 and _f(bJ,'close',-2)>u2)if g else(_f(bJ,'high',-2)>u2 and _f(bJ,'close',-2)<u2):iR.append('HTF_TT3/SFP'if g else'HTF_BearTT3');K.append(f'[{MTF_PERIYOT.upper()}] Three Tap Setup (TT3) / HTF Sapma Dönüşü (27-tt3.pdf)');a3+=8
 if L(hH)>=3:
  d1,d2,d3=(hH[-3][1],hH[-2][1],hH[-1][1])
  if(d1>d2>d3 and d1-d2>0 and 0.45<=(d2-d3)/(d1-d2)<=1.65)if g else(d1<d2<d3 and d2-d1>0 and 0.45<=(d3-d2)/(d2-d1)<=1.65):iR.append('3D_Bull'if g else'3D_Bear');K.append(f"[{LTF_PERIYOT}] {('Bullish' if g else 'Bearish')} Three Drive (3D) Yorulma Yaklaşımı (17.pdf)");a3+=5
 if L(hH)>=2:
  (ib,u1),(ic,u2)=(hH[-2],hH[-1]);nb,nc=(_f(af,'close',ib),_f(af,'close',ic));bY,ci,gr,kC,gt,gu=(_f(af,'rsi',ib),_f(af,'rsi',ic),_f(af,'ao',ib),_f(af,'ao',ic),_f(af,'cvd',ib),_f(af,'cvd',ic));f3=(nc<=nb*1.001 and ci>bY+1.8)if g else(nc>=nb*0.999 and ci<bY-1.8);hI=(u2<=u1*1.0015 and((kC>gr and gr<0)or gu>gt))if g else(u2>=u1*0.9985 and((kC<gr and gr>0)or gu<gt))
  if f3 or hI:gx='Medium_EQ_DVG'if A(u2-u1)/M(u1,1e-9)<=0.0035 else'Strong_Regular_DVG';iR.append(f"{('Bull' if g else 'Bear')}_{gx}");K.append(f"[{LTF_PERIYOT}] {('Bullish' if g else 'Bearish')} {gx} ({'RSI Kapanış' if f3 else 'AO/CVD İğne'} {bY:.0f}->{ci:.0f}) (38-dvg.pdf & YT-Part12)");a3+=7 if'Strong'in gx else 5
 if k7 is not None and L(k7)>=18 and L(af)>=18:
  dv='low'if g else'high';ox,oy=(F(af[dv].iloc[-16:-6].min()if g else af[dv].iloc[-16:-6].max()),F(af[dv].iloc[-6:-1].min()if g else af[dv].iloc[-6:-1].max()));oz,oA=(F(k7[dv].iloc[-16:-6].min()if g else k7[dv].iloc[-16:-6].max()),F(k7[dv].iloc[-6:-1].min()if g else k7[dv].iloc[-6:-1].max()))
  if(oy<ox and oA>=oz or(oy>=ox and oA<oz))if g else(oy>ox and oA<=oz or(oy<=ox and oA>oz)):iR.append('Bull_SMT'if g else'Bear_SMT');K.append(f"[{LTF_PERIYOT}] {qV} ile {('Pozitif (Bullish)' if g else 'Negatif (Bearish)')} SMT Uyuşmazlığı (39-smt.pdf & YT-Part10)");a3+=6
 return(N(25,a3),iR,K)
def ltf_pa_ve_giris_tetikleyici(af,U=None,B='BULLISH'):
 aa,ar=swing_noktalarini_bul(af,n=2)
 if L(aa)<2 or L(ar)<2 or L(af)<8:return(0,[],[],None,None)
 m0,m1,m2,m3=(af.iloc[-5],af.iloc[-4],af.iloc[-3],af.iloc[-2]);g6=_f(af,'close',-1);E=M(F(m3['atr']),g6*0.001);rZ,r0,c5,c6,bB,cD,bC,bD=(*_r(m0,'open','close','high','low'),*_r(m1,'open','close','high','low'));aM,aD,cG,cH,bf,at,cc,cd=(*_r(m2,'open','close','high','low'),*_r(m3,'open','close','high','low'));hJ,cq,ce=(A(cD-bB),A(aD-aM),A(at-bf));mz,mA=(N(at,bf)-cd,cc-M(at,bf));pC,pD=(cG-M(aD,aM),N(aD,aM)-cH);f4,lk,f5,ll=(aa[-1][1],aa[-2][1],ar[-1][1],ar[-2][1]);pE,q6=(cG<=bC and cH>=bD,bC<=c5 and bD>=c6);el,K,a3=([],[],0);g=B=='BULLISH';eq,aX=('Bull'if g else'Bear','Bullish'if g else'Bearish');oY=(aD<aM and at>cG)if g else(aD>aM and at<cH);jO=(aD<aM and at>bf and at>=aM and ce>cq*1.05)if g else(aD>aM and at<bf and at<=aM and ce>cq*1.05);ho=cc>cG and cd<cH and(at>bf if g else at<bf)
 if oY:el.append(f'{eq}_MeraMera_QML_DP');K.append(f'[{LTF_PERIYOT}] {aX} Mera Mera / Outside Engulf Karar Noktası (DP = LTF Gizli QML) (10, 30.pdf & YT-Part4&5)');a3+=13
 elif jO or ho:el.append(f'{eq}_Engulf/OB');K.append(f'[{LTF_PERIYOT}] {aX} Engulfing / Outside Bar Onay Mumu (30-engulf.pdf)');a3+=12
 jP=(mz>ce*1.6 and mz>mA*1.4 and at>=bf)if g else(mA>ce*1.6 and mA>mz*1.4 and at<=bf);fD=(aD<aM and at>bf if g else aD>aM and at<bf)and cq>E*0.45 and ce>E*0.45 and A(ce-cq)<=cq*0.3
 if jP:el.append(f'{eq}_Pinbar');K.append(f'[{LTF_PERIYOT}] {aX} Tepki Spike / Pinbar Reddiyesi (31-spike-pinbar.pdf)');a3+=10
 elif fD:el.append(f'{eq}_Railroad');K.append(f'[{LTF_PERIYOT}] {aX} Railroad Tracks Dönüş Formasyonu (31-railroad.pdf)');a3+=10
 lT=(aM-aD>E*0.6 and at-bf>E*0.6 and at>=aM or(aD>aM and cq>E*0.55 and aD>bC and aM<=cd<=aD and at>=aD))if g else(aD-aM>E*0.6 and bf-at>E*0.6 and at<=aM or(aD<aM and cq>E*0.55 and aD<bD and aD<=cc<=aM and at<=aD))
 if lT:el.append(f'{eq}_BosaltDoldur');K.append(f'[{LTF_PERIYOT}] {aX} Boşalt-Doldur Momentum + Ters İğne Onayı (32-bosalt-doldur.pdf)');a3+=14
 b1=(pE and cd<bD and at>=cH)if g else(pE and cc>bC and at<=cG);dm=(q6 and cH<c6 and aD<aM and at>bf and at>=bD)if g else(q6 and cG>c5 and aD>aM and at<bf and at<=bC)
 if b1 or dm:el.append(f"{eq}_{('Kuralli_Pinbarli_Fakey' if b1 else 'Pinbarsiz_Fakey_PO3')}");K.append(f"[{LTF_PERIYOT}] {aX} {('Kurallı Pinbarlı Fake Setup (Inside Bar İçinde/Üstünde Kapandı)' if b1 else 'Pinbarsız 4-Mum Fake Setup (Zıt Renkli Dönüş)')} (34-fake-setup.pdf & YT-Part12)");a3+=15
 elif pE and(at>bC if g else at<bD):el.append(f'{eq}_InsideBrk');K.append(f'[{LTF_PERIYOT}] {aX} Inside Bar Kırılımı (33-inside-bar.pdf)');a3+=10
 lU=(aD>aM and at>bf and pC>pD*1.25 and aM<=cd<=aD and at>cG)if g else(aD<aM and at<bf and pD>pC*1.25 and aD<=cc<=aM and at<cH)
 if lU:el.append(f'{eq}_YingYang_HiddenBase');K.append(f'[{LTF_PERIYOT}] {aX} Ying-Yang (Hidden Base) Momentum Devam Formasyonu (35.pdf & YT-Part10)');a3+=12
 eL=(at>bf and ce>=E*0.5 and mz<=ce*0.09 and(aD<aM and pD<=cq*0.12 or mA<=ce*0.1))if g else(at<bf and ce>=E*0.5 and mA<=ce*0.09 and(aD>aM and pC<=cq*0.12 or mz<=ce*0.1))
 if eL:el.append(f'{eq}_Istekli_Marubozu');K.append(f'[{LTF_PERIYOT}] {aX} İstekli Mum / Marubozu (Bölgeden İğnesiz Sıfır Mukavemetli Dönüş) (35.pdf & YT-Part10)');a3+=12
 if(cD<bB and hJ>E*0.45 and cq<=hJ*0.45 and at>bf and at>=(bB+cD)/2.0)if g else(cD>bB and hJ>E*0.45 and cq<=hJ*0.45 and at<bf and at<=(bB+cD)/2.0):el.append('Bull_MorningStar_Doji'if g else'Bear_EveningStar_Doji');K.append(f"[{LTF_PERIYOT}] {aX} {('Sabah' if g else 'Akşam')} Yıldızı (Doji + Güçlü Dönüş Mumu) (YT-Part2&3)");a3+=11
 if g:
  if A(f5-ll)/M(ll,1e-09)<=0.0085 and at>bf and at>f5+E*0.28:iX='Simple_W_Trade'if A(f5-ll)<=E*0.2 else'ShortFormed_W_Trade'if f5>ll else'Extended_W_Trade';el.append(iX);K.append(f'[{LTF_PERIYOT}] {iX} (2. Bacak Onayı + W-Kink Dönüşü) (29.pdf & YT-Part10)');a3+=11
  if f4>lk and any((_f(af,'close',k_c)>lk for k_c in G(M(0,int(aa[-2][0])+1),L(af))))and(f4-f5)>E*0.5 and int(aa[-1][0])<=L(af)-3 and f5<=g6<=f5+(f4-f5)*0.60 and(_f(af,'close',-1)>_f(af,'open',-1)or at>bf):
   kD=f5<ll;el.append('LTF_Strong_Bull_CHoCH'if kD else'LTF_Weak_Bull_CHoCH');K.append(f"[{LTF_PERIYOT}] LTF {('Güçlü' if kD else 'Zayıf')} Bullish CHoCH + Retest Onayı (> {lk:.4f}) (YT-Part1,2,3,10)");a3+=13 if kD else 9
  r1=N(f5,ll if f5>=g6*0.996 else f5,F(af['low'].iloc[-15:].min()));al=R(N(r1-M(E*0.5,g6*0.0025),g6*0.996),6)
  if g6<cd:a3=0
 else:
  if A(f4-lk)/M(lk,1e-09)<=0.0085 and at<bf and at<f4-E*0.28:iY='Simple_M_Trade'if A(f4-lk)<=E*0.2 else'ShortFormed_M_Trade'if f4<lk else'Extended_M_Trade';el.append(iY);K.append(f'[{LTF_PERIYOT}] {iY} (2. Bacak Onayı + M-Kink Dönüşü) (29.pdf & YT-Part10)');a3+=11
  if f5<ll and any((_f(af,'close',k_c)<ll for k_c in G(M(0,int(ar[-2][0])+1),L(af))))and(f4-f5)>E*0.5 and int(ar[-1][0])<=L(af)-3 and f4-(f4-f5)*0.60<=g6<=f4 and(_f(af,'close',-1)<_f(af,'open',-1)or at<bf):
   kD=f4>lk;el.append('LTF_Strong_Bear_CHoCH'if kD else'LTF_Weak_Bear_CHoCH');K.append(f"[{LTF_PERIYOT}] LTF {('Güçlü' if kD else 'Zayıf')} Bearish CHoCH + Retest Onayı (< {ll:.4f}) (YT-Part1,2,3,10)");a3+=13 if kD else 9
  r2=M(f4,lk if f4<=g6*1.004 else f4,F(af['high'].iloc[-15:].max()));al=R(M(r2+M(E*0.5,g6*0.0025),g6*1.004),6)
  if g6>cc:a3=0
 return(N(25,a3),el,K,g6,al)
def ilk_kontrol_arz_talep_ob_ote_qml(bS,aP=None,anlik_fiyat=None,de_fiyat=None,B=None,f4h=None,hN=None,bw=None,Q=None,f6=None,q7=None):
 """1. MOD YENİ KURGU (ZORUNLU 1. ŞART + 4 GÜÇ ARTIRICI FAKTÖR & PARİTE PUANLAMA MOTORU):
 - 1. Şart (Zorunlu): HTF yönü BULLISH ise fiyatın HTF Güçlü Fresh Talep (DBR/RBR) bölgesinde olması,
   HTF yönü BEARISH ise fiyatın HTF Güçlü Fresh Arz (RBD/DBD) bölgesinde olması zorunludur.
 - Arz/Talep bölgesine geldikten sonra işlem gücünü ve safe derecesini artıran 4 Ek Şart:
   1) Bölge aynı zamanda OB (Order Block) bölgesi ise işlem gücünü artırır.
   2) Bölge aynı zamanda OTE (0.618-0.786) bölgesi ise işlem gücünü artırır.
   3) Bölge aynı zamanda QML (Quasimodo) bölgesi ise işlem gücünü artırır.
   4) İşlem yönünde ne kadar alınmamış likidite (EQH/EQL, BSL/SSL, Trendline Liq, IDM) varsa o yöne gitmek isteyeceği için gücünü artırır."""
 if bS is None or L(bS)<10:
  return{'ilk_kontrol_gecti':False,'mod1_zorunlu_sart1':False,'mod1_ek_sart_sayisi':0,'birincil_bolge_sayisi':0,'htf_arz_talep_bolgesinde':False,'htf_ob_bolgesinde':False,'htf_ote_bolgesinde':False,'htf_fvg_bolgesinde':False,'htf_qml_bolgesinde':False,'hedef_yon_likidite_var':False,'hedef_yon_likidite_sayisi':0,'hedef_yon_likidite_agirlik':0.0,'hedef_yon_likidite_etiketler':[],'aktif_at_modu':'-','aktif_at_guc_10p':0.0,'aktif_birincil_bolgeler':[],'oncelik_vektor':(0,0,0,0,0,0,0,0),'en_yakin_birincil_atr':99.0,'birincil_pusuda_onay':False,'birincil_radar_kademesi':0,'birincil_olcek_skoru':0,'birincil_olcek_carpani_etkin':0.35,'qml_lvl':0.0,'ote_lo':0.0,'ote_hi':0.0,'ob_lo':0.0,'ob_hi':0.0,'fvg_lo':0.0,'fvg_hi':0.0,'fresh_lo':0.0,'fresh_hi':0.0,'htf_at_list':[],'htf_imb_list':[],'htf_yon_at':[],'htf_ob_list':[],'sMax':0.0,'sMin':0.0,'dU':0.0,'E_htf':0.0,'hedef_yon':B or'BULLISH','htf_yon_ok':False}
 if not I(aP,dict)or not aP:
  aP=market_yapisi_ve_fibo_analizi(bS)
 htf_gercek_yon=aP.get('yon','NOTR')
 if B in('BULLISH','BEARISH'):
  hedef_B=B
 elif htf_gercek_yon in('BULLISH','BEARISH'):
  hedef_B=htf_gercek_yon
 else:
  hedef_B='NOTR'
 g=(hedef_B=='BULLISH')
 ak=F(anlik_fiyat)if anlik_fiyat is not None and F(anlik_fiyat)>0 else _f(bS,'close',-1)
 htf_highs=aP.get('highs',[])
 htf_lows=aP.get('lows',[])
 htf_son_kir_yon=aP.get('kysy_meta',{}).get('son_kirilim_yon','NOTR')
 yapisal_engel=False
 if L(htf_highs)>=2 and L(htf_lows)>=2:
  h1_v,h2_v=(F(htf_highs[-2][1]),F(htf_highs[-1][1]))
  l1_v,l2_v=(F(htf_lows[-2][1]),F(htf_lows[-1][1]))
  if g and((h2_v<h1_v and l2_v<l1_v and ak<=h2_v)or(htf_son_kir_yon=='BEARISH'and ak<=h2_v)):
   yapisal_engel=True
  elif(not g)and((h2_v>h1_v and l2_v>l1_v and ak>=l2_v)or(htf_son_kir_yon=='BULLISH'and ak>=l2_v)):
   yapisal_engel=True
 htf_yon_ok=bool(htf_gercek_yon in('BULLISH','BEARISH')and htf_gercek_yon==hedef_B and not yapisal_engel)
 son_dip_htf=N(_f(bS,'low',-3),_f(bS,'low',-2),_f(bS,'low',-1),ak)
 son_tepe_htf=M(_f(bS,'high',-3),_f(bS,'high',-2),_f(bS,'high',-1),ak)
 de=F(de_fiyat)if de_fiyat is not None and F(de_fiyat)>0 else(son_dip_htf if g else son_tepe_htf)
 de_uc=N(de,son_dip_htf)if g else M(de,son_tepe_htf)
 E_htf=M(_f(bS,'atr',-2)if'atr'in bS.columns else ak*0.003,ak*0.001)
 ts_htf=list(G(L(bS)))
 htf_bos_raw=list(aP.get('kysy_meta',{}).get('bos_list',[]))+list(aP.get('kysy_meta',{}).get('aday_arz_talep_bazlari',[]))
 bs_htf=[{'orig_idx':b[2],'idx2':b[0],'yon':b[4],'tip':b[5]}for b in htf_bos_raw]
 htf_qml_lvl=F(aP.get('qml_seviyesi')or aP.get('qm_meta',{}).get('qml_seviyesi')or aP.get('qm_meta',{}).get('mpl_seviyesi')or 0.0)
 if htf_qml_lvl<=0 and aP.get('highs')and aP.get('lows'):
  try:
   qm_c=_qml_yapisi_bul(aP.get('highs',[]),aP.get('lows',[]),hedef_B,bS)
   if qm_c:htf_qml_lvl=F(qm_c[1])
  except X:pass
 mtf_qml_lvl=F((Q.get('qml_seviyesi')or Q.get('qm_meta',{}).get('qml_seviyesi')or Q.get('qm_meta',{}).get('mpl_seviyesi')or 0.0)if I(Q,dict)else 0.0)
 if htf_qml_lvl<=0 and mtf_qml_lvl>0:htf_qml_lvl=mtf_qml_lvl
 htf_at_list,htf_imb_list=_arz_talep_ve_imbalance_sablon_hesapla(bS,ts_htf,bs_htf,E_htf,htf_qml_lvl if htf_qml_lvl>0 else None)
 hedef_tur='TALEP'if g else'ARZ'
 ters_tur='ARZ'if g else'TALEP'
 # Sadece yönümüze uygun (Bullish -> TALEP [DBR/RBR], Bearish -> ARZ [RBD/DBD]) bölgeler
 htf_yon_at=[z for z in htf_at_list if z.get('tur')==hedef_tur]
 htf_ters_at=[z for z in htf_at_list if z.get('tur')==ters_tur and z.get('taze',False)]
 # Görseldeki 4 Ön Koşul Alanı: Sadece BOS veya CHoCH kırılımını başlatan Swing Arz/Talep Bölgeleri (Bullish BOS/CHoCH Talep, Bearish BOS/CHoCH Arz)
 htf_guclu_fresh_at=[z for z in htf_yon_at if z.get('bos_kaynakli',True)and(z.get('guclu_fresh',False)or(z.get('taze',False)and F(z.get('guc_10p',0.0))>=6.0))and'FLIP'not in str(z.get('mod',''))]
 sMax,sMin=(F(aP.get('swing_max')or 0.0),F(aP.get('swing_min')or 0.0))
 dU=M(0.0,sMax-sMin)
 f4h_l=(f4h if I(f4h,list)else[])+(f6 if I(f6,list)else[])
 hN_l=(hN if I(hN,list)else[])+(q7 if I(q7,list)else[])
 # =========================================================================
 # 1. ŞART (ZORUNLU ÖN KOŞUL - HEM MOD 1 HEM MOD 2 İÇİN):
 # FİYAT HTF TAZE ARZ/TALEP KUTUSUNUN [zlo, zhi] İÇİNDE OLMAK ZORUNDADIR!
 # =========================================================================
 son1_dip_htf=N(_f(bS,'low',-1),ak)
 son1_tepe_htf=M(_f(bS,'high',-1),ak)
 temas_eden_guclu_at=[]
 for z in htf_guclu_fresh_at:
  zlo,zhi=(F(z['lo']),F(z['hi']))
  if zhi<=zlo or zlo<=0:continue
  # Fiyat (anlık kapanış ak veya aktif HTF mumunun iğnesi) bizzat HTF Arz/Talep kutusunun [zlo, zhi] içinde olmalı;
  # kutunun altında/üstünde havada (1.png ve 2.png'deki gibi) kesinlikle kabul edilmez!
  if g:
   kutu_icinde=(zlo-E_htf*0.02<=ak<=zhi)or(zlo-E_htf*0.02<=son1_dip_htf<=zhi and zlo<=ak<=zhi+E_htf*0.08)
  else:
   kutu_icinde=(zlo<=ak<=zhi+E_htf*0.02)or(zlo<=son1_tepe_htf<=zhi+E_htf*0.02 and zlo-E_htf*0.08<=ak<=zhi)
  if kutu_icinde:
   temas_eden_guclu_at.append(z)
 aktif_at_modu='-';aktif_at_guc_10p=0.0;fresh_lo,fresh_hi=(0.0,0.0);aktif_at_ob_mi=False;aktif_at_fvg_imza=False;aktif_htf_at_kutu=None
 if temas_eden_guclu_at:
  temas_eden_guclu_at.sort(key=lambda z:(F(z.get('guc_10p',0.0)),int(bool(z.get('ob_mi',False))),int(bool(z.get('fvg_imza',False))),int(z.get('idx1',0))),reverse=True)
  sec_z=temas_eden_guclu_at[0]
  aktif_htf_at_kutu=dict(sec_z)
  fresh_lo,fresh_hi=(F(sec_z['lo']),F(sec_z['hi']))
  aktif_at_modu=str(sec_z.get('mod','DBR'if g else'RBD'))
  aktif_at_guc_10p=F(sec_z.get('guc_10p',7.5))
  aktif_at_ob_mi=bool(sec_z.get('ob_mi',False))
  aktif_at_fvg_imza=bool(sec_z.get('fvg_imza',False))
 elif htf_guclu_fresh_at:
  # En yakın güçlü fresh bölgeyi referans olarak kaydet (henüz içinde değil)
  yakin_z=min(htf_guclu_fresh_at,key=lambda z:N(A(ak-F(z['lo'])),A(ak-F(z['hi']))))
  fresh_lo,fresh_hi=(F(yakin_z['lo']),F(yakin_z['hi']))
  aktif_at_modu=str(yakin_z.get('mod','DBR'if g else'RBD'))
  aktif_at_guc_10p=F(yakin_z.get('guc_10p',7.0))
 htf_arz_talep_bolgesinde=bool(L(temas_eden_guclu_at)>0)
 mod1_zorunlu_sart1=bool(htf_yon_ok and htf_arz_talep_bolgesinde)
 # =========================================================================
 # GÜÇ FAKTÖRÜ 1: OB (ORDER BLOCK) BÖLGESİ
 # =========================================================================
 htf_ob_list=[z for z in htf_yon_at if z.get('ob_mi',False)or z.get('alt_tur')=='REVERSAL_OB']
 ob_lo,ob_hi=(0.0,0.0)
 if htf_ob_list:
  ob_lo,ob_hi=(F(htf_ob_list[-1]['lo']),F(htf_ob_list[-1]['hi']))
 htf_ob_temas=(
  aktif_at_ob_mi
  or any((z['lo']-E_htf*0.25<=de<=z['hi']+E_htf*0.25 or z['lo']-E_htf*0.25<=de_uc<=z['hi']+E_htf*0.25 or z['lo']-E_htf*0.25<=ak<=z['hi']+E_htf*0.25)and(ak>=z['lo']-E_htf*0.08 if g else ak<=z['hi']+E_htf*0.08)for z in htf_ob_list)
  or any((lo-E_htf*0.25<=de<=hi+E_htf*0.25 or lo-E_htf*0.25<=ak<=hi+E_htf*0.25)for ktip,_,lo,hi in hN_l if'OB'in str(ktip).upper())
  or any(any(x in str(p)for x in('Reversal_OB','Reversal_BearOB','GercekOB'))for p in f4h_l)
 )
 htf_ob_bolgesinde=bool(htf_ob_temas)
 if htf_ob_bolgesinde and ob_hi<=ob_lo and fresh_hi>fresh_lo:
  ob_lo,ob_hi=(fresh_lo,fresh_hi)
 # =========================================================================
 # GÜÇ FAKTÖRÜ 2: OTE (0.618 - 0.705 - 0.786) BÖLGESİ
 # =========================================================================
 ote_lo,ote_hi=(0.0,0.0)
 if dU>0:
  ote_lo,ote_hi=(sMax-dU*0.79,sMax-dU*0.60)if g else(sMin+dU*0.60,sMin+dU*0.79)
  bolge_ote_kesisim=bool(fresh_hi>fresh_lo>0 and M(fresh_lo,N(ote_lo,ote_hi))<=N(fresh_hi,M(ote_lo,ote_hi))+E_htf*0.20)
  fiyat_ote_icinde=bool((ote_lo-E_htf*0.20<=de<=ote_hi+E_htf*0.20)or(ote_lo-E_htf*0.20<=de_uc<=ote_hi+E_htf*0.20)or(ote_lo-E_htf*0.20<=ak<=ote_hi+E_htf*0.20)or bool(aP.get('ote_bull_mu')if g else aP.get('ote_bear_mu')))
  htf_ote_bolgesinde=bool(fiyat_ote_icinde or(htf_arz_talep_bolgesinde and bolge_ote_kesisim))
 else:
  htf_ote_bolgesinde=False
 # =========================================================================
 # GÜÇ FAKTÖRÜ 3: FVG (FAIR VALUE GAP / IMBALANCE) BÖLGESİ
 # =========================================================================
 yon_imb_kisa='BULL'if g else'BEAR'
 htf_yon_imb=[im for im in htf_imb_list if im.get('yon')==yon_imb_kisa]
 fvg_lo,fvg_hi=(0.0,0.0)
 if htf_yon_imb:
  fvg_lo,fvg_hi=(F(htf_yon_imb[-1]['lo']),F(htf_yon_imb[-1]['hi']))
 bolge_fvg_kesisim=bool(
  aktif_at_fvg_imza
  or(fresh_hi>fresh_lo>0 and any(M(fresh_lo,F(im['lo']))<=N(fresh_hi,F(im['hi']))+E_htf*0.35 for im in htf_yon_imb))
 )
 fiyat_fvg_temas=bool(
  any((F(im['lo'])-E_htf*0.30<=de<=F(im['hi'])+E_htf*0.30 or F(im['lo'])-E_htf*0.30<=de_uc<=F(im['hi'])+E_htf*0.30 or F(im['lo'])-E_htf*0.30<=ak<=F(im['hi'])+E_htf*0.30)for im in htf_yon_imb)
  or any(any(x in str(p)for x in('FVG','IFVG','LiqVoid','VIB','Breakaway_Gap','Runaway_Gap'))for p in f4h_l)
 )
 htf_fvg_bolgesinde=bool(fiyat_fvg_temas or(htf_arz_talep_bolgesinde and bolge_fvg_kesisim))
 if htf_fvg_bolgesinde and fvg_hi<=fvg_lo and fresh_hi>fresh_lo:
  fvg_lo,fvg_hi=(fresh_lo,fresh_hi)
 # =========================================================================
 # GÜÇ FAKTÖRÜ 4: İŞLEM YÖNÜNDE ALINMAMIŞ LİKİDİTE OLMASI
 # =========================================================================
 hedef_liq=_hedef_yonde_alinmamis_likidite_analizi(bS,bw,aP,Q,ak,hedef_B)
 hedef_yon_likidite_var=bool(hedef_liq['var_mi'])
 hedef_yon_likidite_sayisi=int(hedef_liq['havuz_sayisi'])
 hedef_yon_likidite_agirlik=F(hedef_liq['agirlik_puani'])
 hedef_yon_likidite_etiketler=list(hedef_liq['etiketler'])
 # =========================================================================
 # GÜÇ FAKTÖRÜ 5: QML (QUASIMODO LEVEL) BÖLGESİ
 # =========================================================================
 bolge_qml_kesisim=bool(htf_qml_lvl>0 and fresh_hi>fresh_lo>0 and(fresh_lo-E_htf*0.35<=htf_qml_lvl<=fresh_hi+E_htf*0.35))
 fiyat_qml_temas=bool(
  (htf_qml_lvl>0 and(A(de-htf_qml_lvl)<=E_htf*0.55 or A(de_uc-htf_qml_lvl)<=E_htf*0.55 or A(ak-htf_qml_lvl)<=E_htf*0.55))
  or any('QM'in str(p)or'MPL'in str(p)for p in f4h_l)
 )
 htf_qml_bolgesinde=bool(fiyat_qml_temas or(htf_arz_talep_bolgesinde and bolge_qml_kesisim))
 # =========================================================================
 # MOD 1 vs MOD 2 KAPISI VE 5 BÖLGEYE GÖRE GÜÇ SIRALAMASI (1.OB > 2.OTE > 3.FVG > 4.LİKİDİTE > 5.QML)
 # =========================================================================
 mod2_aktif=('2. Mod'in str(GIRIS_STRATEJI_MODU)or bool(IKINCIL_BOLGE_GIRIS_AKTIF))
 mod1_ek_sart_sayisi=sum([int(htf_ob_bolgesinde),int(htf_ote_bolgesinde),int(htf_fvg_bolgesinde),int(hedef_yon_likidite_var),int(htf_qml_bolgesinde)])
 birincil_bolge_sayisi=(1+mod1_ek_sart_sayisi)if mod1_zorunlu_sart1 else 0
 # HEM 1. MODDA HEM 2. MODDA ZORUNLU ÖN KOŞUL: Fiyat HTF Arz/Talep Bölgesinde Olmalıdır!
 ilk_kontrol_gecti=bool(mod1_zorunlu_sart1)
 mesafe_adaylari=[]
 for z_m in htf_guclu_fresh_at:
  zlo,zhi=(F(z_m.get('lo',0)),F(z_m.get('hi',0)))
  if zhi>zlo>0:mesafe_adaylari.append(0.0 if zlo<=ak<=zhi else N(A(ak-zlo),A(ak-zhi))/M(E_htf,1e-09))
 en_yakin_birincil_atr=R(N(mesafe_adaylari),2)if mesafe_adaylari else 99.0
 birincil_pusuda_onay=bool((not mod1_zorunlu_sart1)and htf_yon_ok and en_yakin_birincil_atr<=1.35)
 aktif_birincil_bolgeler=[]
 if htf_arz_talep_bolgesinde:aktif_birincil_bolgeler.append(f"Fresh_{hedef_tur}({aktif_at_modu}:{aktif_at_guc_10p:.1f}p)")
 if htf_ob_bolgesinde:aktif_birincil_bolgeler.append('1.OB')
 if htf_ote_bolgesinde:aktif_birincil_bolgeler.append('2.OTE')
 if htf_fvg_bolgesinde:aktif_birincil_bolgeler.append('3.FVG')
 if hedef_yon_likidite_var:aktif_birincil_bolgeler.append(f"4.Liq({hedef_yon_likidite_sayisi}x)")
 if htf_qml_bolgesinde:aktif_birincil_bolgeler.append('5.QML')
 # Öncelik vektörü: (ÖnKoşul, 5 Bölge Sayısı, 1.OB, 2.OTE, 3.FVG, 4.Likidite, 5.QML, LikiditeHavuzSayısı)
 oncelik_vektor=(int(mod1_zorunlu_sart1),int(mod1_ek_sart_sayisi),int(htf_ob_bolgesinde),int(htf_ote_bolgesinde),int(htf_fvg_bolgesinde),int(hedef_yon_likidite_var),int(htf_qml_bolgesinde),int(hedef_yon_likidite_sayisi))
 olcek_k=M(1.5,F(BIRINCIL_BOLGE_OLCEK_CARPANI))/5.0
 if mod1_zorunlu_sart1:
  # Taban puan: BOS/CHoCH Arz/Talep bölgesi 10p kalitesinden gelir (2500 - 3500p)
  taban_puan=2500+int(R(aktif_at_guc_10p*100.0,0))
  # 5 Güçlendirici Faktör Puanları (Sırasıyla: 1.OB > 2.OTE > 3.FVG > 4.Likidite > 5.QML):
  p_ob=1350 if htf_ob_bolgesinde else 0
  p_ote=1200 if htf_ote_bolgesinde else 0
  p_fvg=1050 if htf_fvg_bolgesinde else 0
  p_liq=N(980,600+hedef_yon_likidite_sayisi*120+int(R(hedef_yon_likidite_agirlik*35.0,0)))if hedef_yon_likidite_var else 0
  p_qml=550 if htf_qml_bolgesinde else 0
  ham_skor=taban_puan+p_ob+p_ote+p_fvg+p_liq+p_qml
  birincil_olcek_skoru=N(9400,int(R(ham_skor*M(0.88,N(1.12,olcek_k)),0)))
  birincil_olcek_carpani_etkin=R((5.0 if mod1_ek_sart_sayisi>=4 else 4.3 if mod1_ek_sart_sayisi==3 else 3.6 if mod1_ek_sart_sayisi==2 else 3.0 if mod1_ek_sart_sayisi==1 else 2.4)*olcek_k,2)
  birincil_radar_kademesi=2
 elif mod2_aktif and birincil_bolge_sayisi>=1:
  birincil_olcek_skoru=N(6500,3200+birincil_bolge_sayisi*750)
  birincil_olcek_carpani_etkin=2.2
  birincil_radar_kademesi=2
 elif birincil_pusuda_onay:
  birincil_olcek_skoru=int(M(1200,R(3000-en_yakin_birincil_atr*1200,0)))
  birincil_olcek_carpani_etkin=1.2
  birincil_radar_kademesi=1
 else:
  birincil_olcek_skoru=0
  birincil_olcek_carpani_etkin=0.35
  birincil_radar_kademesi=0
 return{'ilk_kontrol_gecti':ilk_kontrol_gecti,'mod1_zorunlu_sart1':mod1_zorunlu_sart1,'mod1_ek_sart_sayisi':mod1_ek_sart_sayisi,'birincil_bolge_sayisi':birincil_bolge_sayisi,'htf_arz_talep_bolgesinde':htf_arz_talep_bolgesinde,'htf_ob_bolgesinde':htf_ob_bolgesinde,'htf_ote_bolgesinde':htf_ote_bolgesinde,'htf_fvg_bolgesinde':htf_fvg_bolgesinde,'htf_qml_bolgesinde':htf_qml_bolgesinde,'hedef_yon_likidite_var':hedef_yon_likidite_var,'hedef_yon_likidite_sayisi':hedef_yon_likidite_sayisi,'hedef_yon_likidite_agirlik':hedef_yon_likidite_agirlik,'hedef_yon_likidite_etiketler':hedef_yon_likidite_etiketler,'aktif_at_modu':aktif_at_modu,'aktif_at_guc_10p':aktif_at_guc_10p,'aktif_birincil_bolgeler':aktif_birincil_bolgeler,'oncelik_vektor':oncelik_vektor,'en_yakin_birincil_atr':en_yakin_birincil_atr,'birincil_pusuda_onay':birincil_pusuda_onay,'birincil_radar_kademesi':birincil_radar_kademesi,'birincil_olcek_skoru':birincil_olcek_skoru,'birincil_olcek_carpani_etkin':birincil_olcek_carpani_etkin,'qml_lvl':htf_qml_lvl,'ote_lo':ote_lo,'ote_hi':ote_hi,'ob_lo':ob_lo,'ob_hi':ob_hi,'fvg_lo':fvg_lo,'fvg_hi':fvg_hi,'fresh_lo':fresh_lo,'fresh_hi':fresh_hi,'aktif_htf_at_kutu':aktif_htf_at_kutu,'htf_at_list':htf_at_list,'htf_imb_list':htf_imb_list,'htf_yon_at':htf_yon_at,'htf_guclu_fresh_at':htf_guclu_fresh_at,'htf_ob_list':htf_ob_list,'sMax':sMax,'sMin':sMin,'dU':dU,'E_htf':E_htf,'hedef_yon':hedef_B,'htf_yon_ok':htf_yon_ok,'aP':aP}
def _htf_adimlari_ve_ltf_tetik_kontrolu(bS,bw,aY,aP,Q,aj,f4h,f6,q8,hN,q7,ra,kk,B='BULLISH'):
 g=B=='BULLISH';ak=_f(aY,'close',-1);bb=N(_f(aY,'low',-3),_f(aY,'low',-2),_f(aY,'low',-1));bc=M(_f(aY,'high',-3),_f(aY,'high',-2),_f(aY,'high',-1))
 de=bb if g else bc
 mod2_tum_girisler=('2. Mod'in str(GIRIS_STRATEJI_MODU)or bool(IKINCIL_BOLGE_GIRIS_AKTIF))
 E_ltf=M(_f(aY,'atr',-2)if'atr'in aY.columns else ak*0.0015,ak*0.0005)
 # ADIM 1: HTF YÖN + GÜÇLÜ FRESH ARZ/TALEP (1.ŞART) + 4 GÜÇ ARTIRICI (OB, OTE, QML, ALINMAMIŞ LİKİDİTE)
 ilk_k=ilk_kontrol_arz_talep_ob_ote_qml(bS,aP,ak,de,B,f4h,hN,bw,Q,f6,q7)
 htf_yon_ok=bool(ilk_k['htf_yon_ok'])
 E_htf=F(ilk_k['E_htf'])
 htf_qml_lvl=F(ilk_k['qml_lvl'])
 ote_lo,ote_hi=(F(ilk_k['ote_lo']),F(ilk_k['ote_hi']))
 ob_lo,ob_hi=(F(ilk_k['ob_lo']),F(ilk_k['ob_hi']))
 fresh_lo,fresh_hi=(F(ilk_k['fresh_lo']),F(ilk_k['fresh_hi']))
 sMax,sMin,dU=(F(ilk_k['sMax']),F(ilk_k['sMin']),F(ilk_k['dU']))
 htf_at_list,htf_imb_list,htf_yon_at=(ilk_k['htf_at_list'],ilk_k['htf_imb_list'],ilk_k['htf_yon_at'])
 htf_arz_talep_bolgesinde=bool(ilk_k['htf_arz_talep_bolgesinde'])
 htf_ob_bolgesinde=bool(ilk_k['htf_ob_bolgesinde'])
 htf_ote_bolgesinde=bool(ilk_k['htf_ote_bolgesinde'])
 htf_fvg_bolgesinde=bool(ilk_k.get('htf_fvg_bolgesinde',False))
 fvg_lo,fvg_hi=(F(ilk_k.get('fvg_lo',0.0)),F(ilk_k.get('fvg_hi',0.0)))
 htf_qml_bolgesinde=bool(ilk_k['htf_qml_bolgesinde'])
 mod1_zorunlu_sart1=bool(ilk_k['mod1_zorunlu_sart1'])
 mod1_ek_sart_sayisi=int(ilk_k['mod1_ek_sart_sayisi'])
 hedef_yon_likidite_var=bool(ilk_k['hedef_yon_likidite_var'])
 hedef_yon_likidite_sayisi=int(ilk_k['hedef_yon_likidite_sayisi'])
 hedef_yon_likidite_agirlik=F(ilk_k['hedef_yon_likidite_agirlik'])
 hedef_yon_likidite_etiketler=list(ilk_k['hedef_yon_likidite_etiketler'])
 aktif_at_modu=str(ilk_k['aktif_at_modu'])
 aktif_at_guc_10p=F(ilk_k['aktif_at_guc_10p'])
 htf_oncelikli_bolge_sayisi=int(ilk_k['birincil_bolge_sayisi'])
 htf_oncelikli_bolge_onay=bool(ilk_k['ilk_kontrol_gecti'])
 hedef_tur='TALEP'if g else'ARZ'
 htf_sp=F(aP.get('strong_point')or 0.0)
 htf_bos_raw=aP.get('kysy_meta',{}).get('bos_list',[])
 # ADIM 2 (SADECE 2. MOD ÖĞRENİLEN DİĞER GİRİŞ YERLERİ): BOS, CHoCH, ITZ, Magic Line / FL / FTR / FO
 choch_list=[b for b in htf_bos_raw if b[4]==B and('CHOCH'in str(b[5])or'MSB'in str(b[5]))]
 choch_lvl=F(choch_list[-1][1])if choch_list else 0.0
 choch_orig=F(choch_list[-1][3])if choch_list else 0.0
 htf_choch_noktasinda=bool(
  (choch_lvl>0 and(A(de-choch_lvl)<=E_htf*0.55 or A(ak-choch_lvl)<=E_htf*0.55))
  or(choch_orig>0 and(A(de-choch_orig)<=E_htf*0.75 or A(ak-choch_orig)<=E_htf*0.75))
 )
 bos_only_list=[b for b in htf_bos_raw if b[4]==B and'BOS'in str(b[5])and'CHOCH'not in str(b[5])]
 bos_lvl=F(bos_only_list[-1][1])if bos_only_list else 0.0
 bos_orig=F(bos_only_list[-1][3])if bos_only_list else 0.0
 htf_bos_noktasinda=bool(
  (bos_orig>0 and(A(de-bos_orig)<=E_htf*0.75 or A(ak-bos_orig)<=E_htf*0.75))
  or(bos_lvl>0 and(A(de-bos_lvl)<=E_htf*0.55 or A(ak-bos_lvl)<=E_htf*0.55))
 )
 htf_ist=aP.get('uc_istasyon',{})
 htf_itz_lvl=F(htf_ist.get('ITZ')or 0.0)
 htf_itz_bolgesinde=bool(
  (htf_itz_lvl>0 and(A(de-htf_itz_lvl)<=E_htf*0.55 or A(ak-htf_itz_lvl)<=E_htf*0.55))
 )
 htf_magic_lvl=F(aP.get('fl_dp_meta',{}).get('magic_line')or htf_ist.get('FL')or aP.get('break_line_fl')or 0.0)
 htf_magic_line_bolgesinde=bool(
  (htf_magic_lvl>0 and(A(de-htf_magic_lvl)<=E_htf*0.55 or A(ak-htf_magic_lvl)<=E_htf*0.55))
 )
 htf_ikincil_bolge_sayisi=sum([int(htf_bos_noktasinda),int(htf_choch_noktasinda),int(htf_itz_bolgesinde),int(htf_magic_line_bolgesinde)])
 htf_ikincil_bolge_onay=(htf_ikincil_bolge_sayisi>=1)
 htf_bolge_sayisi=htf_oncelikli_bolge_sayisi+(htf_ikincil_bolge_sayisi if mod2_tum_girisler else 0)
 # Mod 2 için aktif giriş bölgesini gerçek fiyat yakınlığıyla belirle.
 # Birincil POI'ler: Fresh Arz/Talep, OB, OTE, FVG, QML.
 # İkincil POI'ler: BOS/CHoCH kaynak-orijin noktaları, ITZ ve Magic Line.
 htf_mod2_zone_adaylari=[]
 def _htf_mod2_zone_ekle(etiket,alt,ust):
  alt,ust=F(alt),F(ust)
  if alt>0 and ust>=alt:
   htf_mod2_zone_adaylari.append((A(ak-(alt+ust)/2.0),str(etiket),alt,ust))
 if htf_arz_talep_bolgesinde:_htf_mod2_zone_ekle('Fresh Arz/Talep',fresh_lo,fresh_hi)
 if htf_ob_bolgesinde:_htf_mod2_zone_ekle('Order Block',ob_lo,ob_hi)
 if htf_ote_bolgesinde:_htf_mod2_zone_ekle('OTE',ote_lo,ote_hi)
 if htf_fvg_bolgesinde:_htf_mod2_zone_ekle('FVG/Imbalance',fvg_lo,fvg_hi)
 if htf_qml_bolgesinde and htf_qml_lvl>0:_htf_mod2_zone_ekle('QML',htf_qml_lvl-E_htf*0.55,htf_qml_lvl+E_htf*0.55)
 if htf_bos_noktasinda:
  if bos_lvl>0:_htf_mod2_zone_ekle('BOS',bos_lvl-E_htf*0.55,bos_lvl+E_htf*0.55)
  if bos_orig>0:_htf_mod2_zone_ekle('BOS Origin',bos_orig-E_htf*0.75,bos_orig+E_htf*0.75)
 if htf_choch_noktasinda:
  if choch_lvl>0:_htf_mod2_zone_ekle('CHoCH',choch_lvl-E_htf*0.55,choch_lvl+E_htf*0.55)
  if choch_orig>0:_htf_mod2_zone_ekle('CHoCH Origin',choch_orig-E_htf*0.75,choch_orig+E_htf*0.75)
 if htf_itz_bolgesinde and htf_itz_lvl>0:_htf_mod2_zone_ekle('ITZ',htf_itz_lvl-E_htf*0.55,htf_itz_lvl+E_htf*0.55)
 if htf_magic_line_bolgesinde and htf_magic_lvl>0:_htf_mod2_zone_ekle('Magic Line',htf_magic_lvl-E_htf*0.55,htf_magic_lvl+E_htf*0.55)
 htf_mod2_birincil_bolge_onay=bool(htf_arz_talep_bolgesinde or htf_ob_bolgesinde or htf_ote_bolgesinde or htf_fvg_bolgesinde or htf_qml_bolgesinde)
 htf_mod2_ikincil_bolge_onay=bool(htf_bos_noktasinda or htf_choch_noktasinda or htf_itz_bolgesinde or htf_magic_line_bolgesinde)
 htf_mod2_entry_zone_onay=bool(htf_yon_ok and htf_mod2_zone_adaylari)
 if htf_mod2_zone_adaylari:
  _,htf_mod2_entry_zone_adi,htf_mod2_entry_zone_lo,htf_mod2_entry_zone_hi=min(htf_mod2_zone_adaylari,key=lambda z:z[0])
 else:
  htf_mod2_entry_zone_adi='';htf_mod2_entry_zone_lo=0.0;htf_mod2_entry_zone_hi=0.0
 # Mod 1 aynı güçlü Fresh Arz/Talep şartını korur. Mod 2, HTF yönüyle uyumlu
 # herhangi bir doğrulanmış birincil/ikincil POI'de çalışabilir.
 htf_zorunlu_bolge_onay=bool(mod1_zorunlu_sart1 if not mod2_tum_girisler else htf_mod2_entry_zone_onay)
 yon_kisa='BULL'if g else'BEAR'
 htf_yon_imbalance=[im for im in htf_imb_list if im.get('yon')==yon_kisa]
 htf_imbalance_sayisi=L(htf_yon_imbalance)+sum(1 for p in f4h if'FVG'in p or'LiqVoid'in p or'VIB'in p or'Gap'in p)
 htf_lq_l,htf_sfp_l,htf_lq_m=_likidite_ve_sfp_yapilarini_bul(bS,aP.get('highs'),aP.get('lows'))
 eq_havuz=L(htf_lq_m.get('aktif_eqh',[]))+L(htf_lq_m.get('aktif_eql',[]))+L(htf_lq_m.get('swept_eql'if g else'swept_eqh',[]))
 tl_havuz=L(htf_lq_m.get('trendline_bsl',[]))+L(htf_lq_m.get('trendline_ssl',[]))
 idm_havuz=1 if(htf_lq_m.get('swept_idm_bull'if g else'swept_idm_bear')is not None or htf_lq_m.get('aktif_idm_ssl'if g else'aktif_idm_bsl')is not None)else 0
 sfp_htf=1 if(htf_lq_m.get('son_bull_sfp'if g else'son_bear_sfp')is not None)else 0
 ext_var=1 if(htf_lq_m.get('ext_bsl'if g else'ext_ssl')is not None)else 0
 htf_likidite_sayisi=M(hedef_yon_likidite_sayisi,eq_havuz+tl_havuz+idm_havuz+sfp_htf+ext_var)
 mtf_yon_onay=bool(Q.get('yon')==B or Q.get('external_yon')==B or Q.get('internal_yon')==B)
 # =========================================================================
 # ADIM 3: LTF İŞLEME GİRİŞ STRATEJİLERİ (ARZ/TALEP, OB, FVG/IMBALANCE, LİKİDİTE, QML, MUM & KIRILIM)
 # EĞER LTF'DE GİRİŞ İÇİN GERÇEK BİR EMARE YOKSA KESİNLİKLE İŞLEME GİRİLMEZ!
 # =========================================================================
 ltf_kysy=aj.get('kysy_meta',{})
 ltf_son_bos_yon=ltf_kysy.get('son_kirilim_yon','NOTR')
 ltf_son_kir_tip=str(ltf_kysy.get('son_kirilim_tipi',''))
 ltf_int_choch=str(aj.get('internal_choch','YOK'))
 ltf_bos_raw=ltf_kysy.get('bos_list',[])
 bs_ltf=[{'orig_idx':b[2],'idx2':b[0],'yon':b[4],'tip':b[5]}for b in(list(ltf_bos_raw)+list(ltf_kysy.get('aday_arz_talep_bazlari',[])))]
 ltf_at_list,ltf_imb_list=_arz_talep_ve_imbalance_sablon_hesapla(aY,list(G(L(aY))),bs_ltf,E_ltf)
 _,_,ltf_lmeta=_likidite_ve_sfp_yapilarini_bul(aY,aj.get('highs'),aj.get('lows'))
 de_ltf_6=F(aY['low'].iloc[-10:].min())if(g and L(aY)>=6)else(F(aY['high'].iloc[-10:].max())if L(aY)>=6 else de)
 # 3.1) LTF Arz/Talep Bölgeleri (DBR/RBR/RBD/DBD + Flip Arz/Talep Breaker)
 ltf_arz_talep_listesi=[]
 for z_l in ltf_at_list:
  if z_l.get('tur')==hedef_tur and(z_l.get('taze',False)or z_l.get('guclu_fresh',False)or'FLIP'in str(z_l.get('mod',''))):
   zlo_l,zhi_l=(F(z_l['lo']),F(z_l['hi']))
   temas_l=(zlo_l-E_ltf*0.45<=de<=zhi_l+E_ltf*0.45)or(zlo_l-E_ltf*0.45<=de_ltf_6<=zhi_l+E_ltf*0.45)or(zlo_l-E_ltf*0.45<=ak<=zhi_l+E_ltf*0.45)
   kirilmadi_l=(ak>=zlo_l-E_ltf*0.10)if g else(ak<=zhi_l+E_ltf*0.10)
   if temas_l and kirilmadi_l:
    ltf_arz_talep_listesi.append(f"LTF_{z_l.get('mod','AT')}({z_l.get('guc_10p',7.0):.1f}p)")
 for p_at in q8:
  if any(x in p_at for x in('ValidDem','ValidSup','DBR','RBR','RBD','DBD','1Mum_FTR','TersFlag_Flip','TersBayrak','Flip')):
   if p_at not in ltf_arz_talep_listesi:ltf_arz_talep_listesi.append(p_at)
 ltf_arz_talep_onay=bool(L(ltf_arz_talep_listesi)>0)
 # 3.2) LTF Order Block (OB)
 ltf_ob_listesi=[]
 for z_l in ltf_at_list:
  if z_l.get('tur')==hedef_tur and(z_l.get('ob_mi',False)or z_l.get('alt_tur')=='REVERSAL_OB'):
   zlo_l,zhi_l=(F(z_l['lo']),F(z_l['hi']))
   if(zlo_l-E_ltf*0.45<=de<=zhi_l+E_ltf*0.45 or zlo_l-E_ltf*0.45<=de_ltf_6<=zhi_l+E_ltf*0.45 or zlo_l-E_ltf*0.45<=ak<=zhi_l+E_ltf*0.45)and(ak>=zlo_l-E_ltf*0.10 if g else ak<=zhi_l+E_ltf*0.10):
    ltf_ob_listesi.append(f"LTF_OB_{z_l.get('mod','OB')}")
 for p_ob in q8:
  if any(x in p_ob for x in('Reversal_OB','Reversal_BearOB','GercekOB','Bobin_Bolge_Testi_POI','Istisnai_OB')):
   if p_ob not in ltf_ob_listesi:ltf_ob_listesi.append(p_ob)
 ltf_ob_onay=bool(L(ltf_ob_listesi)>0)
 # 3.3) LTF FVG / Imbalance
 ltf_fvg_listesi=[]
 for im_l in ltf_imb_list:
  if im_l.get('yon')==yon_kisa and(im_l['lo']-E_ltf*0.40<=de<=im_l['hi']+E_ltf*0.40 or im_l['lo']-E_ltf*0.40<=de_ltf_6<=im_l['hi']+E_ltf*0.40 or im_l['lo']-E_ltf*0.35<=ak<=im_l['hi']+E_ltf*0.40):
   ltf_fvg_listesi.append(f"LTF_{im_l.get('tip','FVG')}")
 for p_fvg in q8:
  if any(x in p_fvg for x in('FVG','IFVG','LiqVoid','VIB','Breakaway_Gap','Runaway_Gap','FVGli_Guclu_CHoCH')):
   if p_fvg not in ltf_fvg_listesi:ltf_fvg_listesi.append(p_fvg)
 ltf_fvg_imbalance_onay=bool(L(ltf_fvg_listesi)>0)
 # 3.4) LTF Likidite (SFP / EQL-EQH Sweep / IDM Sweep / TT3 / PO3)
 ltf_likidite_listesi=[]
 sfp_ltf_now=ltf_lmeta.get('son_bull_sfp'if g else'son_bear_sfp')
 if sfp_ltf_now and int(sfp_ltf_now.get('idx',0))>=L(aY)-8:
  ltf_likidite_listesi.append(f"LTF_{'Bull'if g else'Bear'}_SFP")
 if ltf_lmeta.get('swept_idm_bull'if g else'swept_idm_bear')is not None:
  ltf_likidite_listesi.append(f"LTF_IDM_Sweep")
 for p_lq in q8:
  if any(x in p_lq for x in('SFP','Sweep','TT3','PO3','Fakeout','236_382_Manipulasyon')):
   if p_lq not in ltf_likidite_listesi:ltf_likidite_listesi.append(p_lq)
 ltf_likidite_onay=bool(L(ltf_likidite_listesi)>0)
 # 3.5) LTF QML (Quasimodo / MPL / MeraMera QML DP)
 ltf_qml_lvl=F(aj.get('qml_seviyesi')or aj.get('qm_meta',{}).get('qml_seviyesi')or 0.0)
 ltf_qml_listesi=[]
 if ltf_qml_lvl>0 and(A(de-ltf_qml_lvl)<=E_ltf*1.45 or A(de_ltf_6-ltf_qml_lvl)<=E_ltf*1.45)and(ak>=ltf_qml_lvl-E_ltf*0.35 if g else ak<=ltf_qml_lvl+E_ltf*0.35):
  ltf_qml_listesi.append(f"LTF_QML({ltf_qml_lvl:.4f})")
 for p_qm in(q8+kk):
  if any(x in p_qm for x in('QMR','QMC','QMM','MPL','MeraMera')):
   if p_qm not in ltf_qml_listesi:ltf_qml_listesi.append(p_qm)
 ltf_qml_onay=bool(L(ltf_qml_listesi)>0)
 # 3.6) LTF Kırılım + Sarı OB (Order Block) Giriş Kuralı (cys2.png & CreedFx Video Step 3-4) ve LTF Mum Yapıları
 # KURAL (cys2.png & image_b4c95c.png DÜZELTMESİ):
 # 1) LTF'de kırılım mumunun tepesinde/dibinde (örn. image_b4c95c.png'deki 0.0780 gibi hiçbir özelliği olmayan havadaki yerde) ASLA işleme girilmez!
 # 2) LTF'de CHoCH/BOS kırılımı gerçekleştiğinde, kırılımı başlatan Sarı OB (Order Block: kırılım öncesi son ters mum / HL-LH OB kutusu, örn. cys2.png'deki 0.0769 OB bölgesi)
 #    veya önemli giriş noktalarına (Arz/Talep, OB, OTE, QML) fiyatın gelmesi / retest yapması beklenir ve o OB bölgesinden işleme girilir!
 # 3) Ayrıca fiyat Arz/Talep veya OB bölgesindeyken (kırılım tepesinde/dibinde havada DEĞİLKEN) öğrenilen LTF dönüş mum yapıları görüldüğünde işleme girilir!
 retest_uc=N(_f(aY,'low',-3),_f(aY,'low',-2),_f(aY,'low',-1),ak)if g else M(_f(aY,'high',-3),_f(aY,'high',-2),_f(aY,'high',-1),ak)
 son2_uc=N(_f(aY,'low',-2),_f(aY,'low',-1),ak)if g else M(_f(aY,'high',-2),_f(aY,'high',-1),ak)
 uclu_ters_mum_serisi=bool(L(aY)>=3 and((_f(aY,'close',-1)<_f(aY,'open',-1)and _f(aY,'close',-2)<_f(aY,'open',-2)and _f(aY,'close',-3)<_f(aY,'open',-3))if g else(_f(aY,'close',-1)>_f(aY,'open',-1)and _f(aY,'close',-2)>_f(aY,'open',-2)and _f(aY,'close',-3)>_f(aY,'open',-3))))
 son2_tepki_mumu_var=bool(L(aY)>=2 and not uclu_ters_mum_serisi and((_f(aY,'close',-1)>_f(aY,'open',-1)or _f(aY,'close',-2)>_f(aY,'open',-2))if g else(_f(aY,'close',-1)<_f(aY,'open',-1)or _f(aY,'close',-2)<_f(aY,'open',-2))))
 # image_b45080.png DÜZELTMESİ: Eski (sonrasında ters yöne kırılmış veya origin noktası delinmiş) kırılımlar KESİNLİKLE geçersizdir!
 son_ters_bos_idx=M([int(b_l[0])for b_l in ltf_bos_raw if b_l[4]!=B],default=-1)
 ltf_yon_boslar=[b_l for b_l in ltf_bos_raw if b_l[4]==B and int(b_l[0])>son_ters_bos_idx and int(b_l[0])>=M(0,L(aY)-22)]
 kir_var=False;kir_bar_idx=-1;kir_seviye=0.0;origin_idx=-1;origin_uc=0.0;impuls_uc_idx=-1;impuls_uc=0.0;kir_tip_etiket=''
 video_choch_ob_pullback=False;video_choch_ob_lo=0.0;video_choch_ob_hi=0.0;video_choch_ob_idx=-1;ltf_yapi_dip_tepe=0.0
 if ltf_yon_boslar:
  son_b=ltf_yon_boslar[-1]
  b_idx,b_lvl,o_idx,o_uc=(int(son_b[0]),F(son_b[1]),M(0,int(son_b[2])),F(son_b[3]))
  # Kırılım sonrasında origin_uc delinmediyse geçerlidir:
  origin_korundu=(F(aY['low'].iloc[b_idx:].min())>=o_uc-E_ltf*0.05)if g else(F(aY['high'].iloc[b_idx:].max())<=o_uc+E_ltf*0.05)
  if origin_korundu:
   kir_var=True;kir_bar_idx=b_idx;kir_seviye=b_lvl;origin_idx=o_idx;origin_uc=o_uc;kir_tip_etiket=str(son_b[5])
   alt_dilim=aY.iloc[origin_idx:]if origin_idx<L(aY)else aY.iloc[-15:]
   if g:
    rel_i=int(alt_dilim['high'].values.argmax())
    impuls_uc_idx=origin_idx+rel_i;impuls_uc=F(alt_dilim['high'].iloc[rel_i])
   else:
    rel_i=int(alt_dilim['low'].values.argmin())
    impuls_uc_idx=origin_idx+rel_i;impuls_uc=F(alt_dilim['low'].iloc[rel_i])
 # image_1c1c1b.png DÜZELTMESİ: LTF'de onaylı yapı kırılımı (son_ters_bos_idx) ters yöndeyse (örn. LTF'de yeşil kesikli çizgiyle HH kırılımı olmuşsa),
 # bu ters kırılımdan ÖNCEKİ mikro tepeler/dipler kesinlikle kırılım sayılmaz!
 if L(aY)>=8:
  d0_sw,d4_sw=swing_noktalarini_bul(aY,1,kirilim_sarti=False)
  if g and L(d0_sw)>=1 and L(d4_sw)>=1:
   min_lh_idx=M(0,L(aY)-20,son_ters_bos_idx)
   aday_lh=[(int(hi_s),F(hv_s))for hi_s,hv_s in d0_sw if min_lh_idx<=int(hi_s)<=L(aY)-2]
   for lh_i,lh_v in reversed(aday_lh[-5:]):
    kir_mumlar=[k_i for k_i in G(lh_i+1,L(aY))if _f(aY,'close',k_i)>lh_v]
    if not kir_mumlar:continue
    ilk_kir_i=kir_mumlar[0]
    alt_w_bas=M(0,lh_i-3)
    dip_rel=int(aY['low'].iloc[alt_w_bas:ilk_kir_i+1].values.argmin())
    dip_i=alt_w_bas+dip_rel
    dip_v=F(aY['low'].iloc[dip_i])
    kir_sonrasi_min_l=F(aY['low'].iloc[ilk_kir_i:].min())
    if kir_mumlar and(lh_v-dip_v)>=E_ltf*0.35 and kir_sonrasi_min_l>=dip_v-E_ltf*0.05 and ak>dip_v+E_ltf*0.15:
     if not kir_var or ilk_kir_i>=kir_bar_idx:
      kir_var=True;kir_bar_idx=ilk_kir_i;kir_seviye=lh_v;origin_idx=dip_i;origin_uc=dip_v
      alt_d=aY.iloc[origin_idx:]if origin_idx<L(aY)else aY.iloc[-12:]
      rel_i=int(alt_d['high'].values.argmax());impuls_uc_idx=origin_idx+rel_i;impuls_uc=F(alt_d['high'].iloc[rel_i])
      if not kir_tip_etiket or'CHoCH'not in kir_tip_etiket:kir_tip_etiket='Video_CHoCH'
     ters_mumlar=[k_i for k_i in G(M(0,origin_idx-1),N(L(aY),ilk_kir_i+1))if _f(aY,'close',k_i)<_f(aY,'open',k_i)]
     ob_idx=ters_mumlar[-1]if ters_mumlar else origin_idx
     video_choch_ob_idx=ob_idx
     video_choch_ob_lo=F(_f(aY,'low',ob_idx))
     video_choch_ob_hi=M(_f(aY,'open',ob_idx),_f(aY,'high',ob_idx))
     ltf_yapi_dip_tepe=N(dip_v,F(aY['low'].iloc[M(0,lh_i-4):N(L(aY),ilk_kir_i+2)].min()))
     break
  elif(not g)and L(d4_sw)>=1 and L(d0_sw)>=1:
   min_hl_idx=M(0,L(aY)-20,son_ters_bos_idx)
   aday_hl=[(int(li_s),F(lv_s))for li_s,lv_s in d4_sw if min_hl_idx<=int(li_s)<=L(aY)-2]
   for hl_i,hl_v in reversed(aday_hl[-5:]):
    kir_mumlar=[k_i for k_i in G(hl_i+1,L(aY))if _f(aY,'close',k_i)<hl_v]
    if not kir_mumlar:continue
    ilk_kir_i=kir_mumlar[0]
    ust_w_bas=M(0,hl_i-3)
    tepe_rel=int(aY['high'].iloc[ust_w_bas:ilk_kir_i+1].values.argmax())
    tepe_i=ust_w_bas+tepe_rel
    tepe_v=F(aY['high'].iloc[tepe_i])
    kir_sonrasi_max_h=F(aY['high'].iloc[ilk_kir_i:].max())
    if kir_mumlar and(tepe_v-hl_v)>=E_ltf*0.35 and kir_sonrasi_max_h<=tepe_v+E_ltf*0.05 and ak<tepe_v-E_ltf*0.15:
     if not kir_var or ilk_kir_i>=kir_bar_idx:
      kir_var=True;kir_bar_idx=ilk_kir_i;kir_seviye=hl_v;origin_idx=tepe_i;origin_uc=tepe_v
      alt_d=aY.iloc[origin_idx:]if origin_idx<L(aY)else aY.iloc[-12:]
      rel_i=int(alt_d['low'].values.argmin());impuls_uc_idx=origin_idx+rel_i;impuls_uc=F(alt_d['low'].iloc[rel_i])
      if not kir_tip_etiket or'CHoCH'not in kir_tip_etiket:kir_tip_etiket='Video_CHoCH'
     ters_mumlar=[k_i for k_i in G(M(0,origin_idx-1),N(L(aY),ilk_kir_i+1))if _f(aY,'close',k_i)>_f(aY,'open',k_i)]
     ob_idx=ters_mumlar[-1]if ters_mumlar else origin_idx
     video_choch_ob_idx=ob_idx
     video_choch_ob_lo=N(_f(aY,'open',ob_idx),_f(aY,'low',ob_idx))
     video_choch_ob_hi=F(_f(aY,'high',ob_idx))
     ltf_yapi_dip_tepe=M(tepe_v,F(aY['high'].iloc[M(0,hl_i-4):N(L(aY),ilk_kir_i+2)].max()))
     break
 if ltf_yapi_dip_tepe<=0 and L(aY)>=6:
  ltf_yapi_dip_tepe=F(aY['low'].iloc[-16:].min())if g else F(aY['high'].iloc[-16:].max())
 # cys2.png Sarı OB kutusunu LTF kutularına (ra) ekle ki grafikte sarı OB olarak çizilsin:
 if video_choch_ob_hi>video_choch_ob_lo>0 and video_choch_ob_idx>=0 and I(ra,list):
  if not any(kt=='OB'and A(klo-video_choch_ob_lo)<=E_ltf*0.15 for kt,_,klo,_ in ra):
   ra.append(('OB',video_choch_ob_idx,video_choch_ob_lo,video_choch_ob_hi))
 ltf_leg_boyu=A(impuls_uc-origin_uc)if(kir_var and impuls_uc>0 and origin_uc>0)else 0.0
 # Kırılım zirvesi/dibi (impuls_uc_idx) SONRASINDA gerçekleşen gerçek geri çekilme (pullback) ucu:
 zirve_sonrasi_uc=(F(aY['low'].iloc[impuls_uc_idx+1:].min())if g else F(aY['high'].iloc[impuls_uc_idx+1:].max()))if(kir_var and 0<=impuls_uc_idx<L(aY)-1)else ak
 # Sarı OB (Video CHoCH OB) içine geri çekilme (pullback/retest) kontrolü:
 if kir_var and impuls_uc_idx<=L(aY)-2 and video_choch_ob_hi>video_choch_ob_lo>0:
  if g and(video_choch_ob_lo-E_ltf*0.20<=zirve_sonrasi_uc<=video_choch_ob_hi+E_ltf*0.20 or video_choch_ob_lo-E_ltf*0.15<=ak<=video_choch_ob_hi+E_ltf*0.20)and ak<=video_choch_ob_hi+E_ltf*0.30 and ak>=ltf_yapi_dip_tepe-E_ltf*0.10 and ak<impuls_uc-ltf_leg_boyu*0.25 and son2_tepki_mumu_var:
   video_choch_ob_pullback=True
  elif(not g)and(video_choch_ob_lo-E_ltf*0.20<=zirve_sonrasi_uc<=video_choch_ob_hi+E_ltf*0.20 or video_choch_ob_lo-E_ltf*0.20<=ak<=video_choch_ob_hi+E_ltf*0.15)and ak>=video_choch_ob_lo-E_ltf*0.30 and ak<=ltf_yapi_dip_tepe+E_ltf*0.10 and ak>impuls_uc+ltf_leg_boyu*0.25 and son2_tepki_mumu_var:
   video_choch_ob_pullback=True
 if video_choch_ob_pullback and'Video_CHoCH_Sari_OB'not in ltf_ob_listesi:
  ltf_ob_listesi.insert(0,'Video_CHoCH_Sari_OB')
  ltf_ob_onay=True
 # LTF Kırılım Ayağının OTE (0.618 - 0.786) Seviyeleri:
 ltf_ote_lo,ltf_ote_hi=(0.0,0.0)
 if kir_var and ltf_leg_boyu>=E_ltf*0.55:
  ltf_ote_lo,ltf_ote_hi=((impuls_uc-ltf_leg_boyu*0.85,impuls_uc-ltf_leg_boyu*0.50)if g else(impuls_uc+ltf_leg_boyu*0.50,impuls_uc+ltf_leg_boyu*0.85))
 ltf_ote_retest_onay=bool(ltf_ote_hi>ltf_ote_lo>0 and((ltf_ote_lo-E_ltf*0.20<=son2_uc<=ltf_ote_hi+E_ltf*0.20 or ltf_ote_lo-E_ltf*0.20<=ak<=ltf_ote_hi+E_ltf*0.20)and(ak>=origin_uc-E_ltf*0.10 if g else ak<=origin_uc+E_ltf*0.10)))
 # Anlık olarak HTF veya LTF Önemli Giriş Noktalarında (Arz/Talep, OB, OTE, QML) bulunma kontrolü:
 htf_at_anlik=bool(htf_arz_talep_bolgesinde or(fresh_hi>fresh_lo>0 and((fresh_lo-E_htf*0.08<=retest_uc<=fresh_hi+E_htf*0.20 or fresh_lo-E_htf*0.08<=ak<=fresh_hi+E_htf*0.25)if g else(fresh_lo-E_htf*0.20<=retest_uc<=fresh_hi+E_htf*0.08 or fresh_lo-E_htf*0.25<=ak<=fresh_hi+E_htf*0.08))))
 htf_ob_anlik=bool(htf_ob_bolgesinde or(ob_hi>ob_lo>0 and((ob_lo-E_htf*0.10<=retest_uc<=ob_hi+E_htf*0.20 or ob_lo-E_htf*0.10<=ak<=ob_hi+E_htf*0.25)if g else(ob_lo-E_htf*0.20<=retest_uc<=ob_hi+E_htf*0.10 or ob_lo-E_htf*0.25<=ak<=ob_hi+E_htf*0.10))))
 htf_ote_anlik=bool(htf_ote_bolgesinde or(ote_hi>0 and ote_lo>0 and(N(ote_lo,ote_hi)-E_htf*0.15<=retest_uc<=M(ote_lo,ote_hi)+E_htf*0.15 or N(ote_lo,ote_hi)-E_htf*0.15<=ak<=M(ote_lo,ote_hi)+E_htf*0.15)))
 htf_qml_anlik=bool(htf_qml_bolgesinde or(htf_qml_lvl>0 and(A(retest_uc-htf_qml_lvl)<=E_htf*0.40 or A(ak-htf_qml_lvl)<=E_htf*0.40)))
 ltf_at_anlik=bool(ltf_arz_talep_onay)
 ltf_ob_anlik=bool(ltf_ob_onay)
 ltf_qml_anlik=bool(ltf_qml_onay)
 htf_onemli_giris_noktasinda=bool(htf_at_anlik or htf_ob_anlik or htf_ote_anlik or htf_qml_anlik)
 ltf_onemli_giris_noktasinda=bool(ltf_at_anlik or ltf_ob_anlik or ltf_ote_retest_onay or ltf_qml_anlik)
 onemli_giris_noktasinda_mi=bool(htf_onemli_giris_noktasinda or ltf_onemli_giris_noktasinda)
 # ERKEN GİRİŞ ENGELİ (image_b4c95c.png'deki gibi 0.0780 kırılım tepesinde/dibinde havada işleme girilmesinin engellenmesi):
 if g:
  son2_dipten_kopuk=bool(kir_var and ltf_leg_boyu>=E_ltf*0.8 and zirve_sonrasi_uc>origin_uc+ltf_leg_boyu*0.48)
  sari_ob_ustunde_havada=bool(video_choch_ob_hi>0 and ak>video_choch_ob_hi+E_ltf*0.25 and zirve_sonrasi_uc>video_choch_ob_hi+E_ltf*0.15)
  kirilim_tepesinde=bool(kir_var and(son2_dipten_kopuk or sari_ob_ustunde_havada)and(kir_bar_idx>=L(aY)-2 or impuls_uc_idx>=L(aY)-2 or ak>origin_uc+ltf_leg_boyu*0.60 or(kir_seviye>0 and ak>=kir_seviye)))
  ltf_kirilim_aninda_erken_mi=bool(kirilim_tepesinde and not video_choch_ob_pullback)
  ltf_retest_gerceklesti=bool(video_choch_ob_pullback or(kir_var and impuls_uc_idx<=L(aY)-2 and(L(aY)-1-impuls_uc_idx)<=22 and ltf_leg_boyu>=E_ltf*0.50 and zirve_sonrasi_uc<=impuls_uc-ltf_leg_boyu*0.35 and ak<=origin_uc+ltf_leg_boyu*0.65 and ak>origin_uc-E_ltf*0.15 and son2_tepki_mumu_var and onemli_giris_noktasinda_mi))
 else:
  son2_tepeden_kopuk=bool(kir_var and ltf_leg_boyu>=E_ltf*0.8 and zirve_sonrasi_uc<origin_uc-ltf_leg_boyu*0.48)
  sari_ob_altinda_havada=bool(video_choch_ob_lo>0 and ak<video_choch_ob_lo-E_ltf*0.25 and zirve_sonrasi_uc<video_choch_ob_lo-E_ltf*0.15)
  kirilim_dibinde=bool(kir_var and(son2_tepeden_kopuk or sari_ob_altinda_havada)and(kir_bar_idx>=L(aY)-2 or impuls_uc_idx>=L(aY)-2 or ak<origin_uc-ltf_leg_boyu*0.60 or(kir_seviye>0 and ak<=kir_seviye)))
  ltf_kirilim_aninda_erken_mi=bool(kirilim_dibinde and not video_choch_ob_pullback)
  ltf_retest_gerceklesti=bool(video_choch_ob_pullback or(kir_var and impuls_uc_idx<=L(aY)-2 and(L(aY)-1-impuls_uc_idx)<=22 and ltf_leg_boyu>=E_ltf*0.50 and zirve_sonrasi_uc>=impuls_uc+ltf_leg_boyu*0.35 and ak>=origin_uc-ltf_leg_boyu*0.65 and ak<origin_uc+E_ltf*0.15 and son2_tepki_mumu_var and onemli_giris_noktasinda_mi))
 ters_yon_str='BEARISH'if g else'BULLISH'
 ltf_ters_bos_aktif=bool(ltf_son_bos_yon==ters_yon_str and(not kir_var or kir_bar_idx<=son_ters_bos_idx))
 # Son 10-12 LTF mumunda bölge içi tepe/dip sonrası gerçek iç destek/direnç kırılımı + OB/bölge retest:
 if L(aY)>=8 and not ltf_retest_gerceklesti and not ltf_kirilim_aninda_erken_mi and not uclu_ters_mum_serisi:
  son8=aY.iloc[-12:]if L(aY)>=12 else aY.iloc[-8:]
  if not g:
   idx_max8=int(son8['high'].values.argmax())
   if 2<=idx_max8<=L(son8)-3:
    tepe_bar_high=F(son8['high'].iloc[idx_max8])
    oncesi_ic_dip=N(F(son8['low'].iloc[idx_max8-1]),F(son8['low'].iloc[idx_max8]))
    ara_min_l=F(son8['low'].iloc[idx_max8+1:].min())
    son_tepe_sonrasi=F(son8['high'].iloc[idx_max8+1:].max())
    # image_1c1c1b.png Koruması: Yalnızca tepe_bar_high ÖNCESİNDEKİ iç dip (oncesi_ic_dip) aşağı kırıldıysa ve retest tepenin %70'ini aşmadıysa geçerlidir!
    if ara_min_l<oncesi_ic_dip-E_ltf*0.15 and son_tepe_sonrasi<=tepe_bar_high and son2_uc>=ara_min_l+(tepe_bar_high-ara_min_l)*0.25 and ak<=ara_min_l+(tepe_bar_high-ara_min_l)*0.62 and not ltf_ters_bos_aktif and ak<tepe_bar_high-E_ltf*0.15 and onemli_giris_noktasinda_mi:
     ltf_retest_gerceklesti=True
     if not kir_tip_etiket:kir_tip_etiket='LTF_Bolge_Ici_Kirilim'
  else:
   idx_min8=int(son8['low'].values.argmin())
   if 2<=idx_min8<=L(son8)-3:
    dip_bar_low=F(son8['low'].iloc[idx_min8])
    oncesi_ic_tepe=M(F(son8['high'].iloc[idx_min8-1]),F(son8['high'].iloc[idx_min8]))
    ara_max_h=F(son8['high'].iloc[idx_min8+1:].max())
    son_dip_sonrasi=F(son8['low'].iloc[idx_min8+1:].min())
    if ara_max_h>oncesi_ic_tepe+E_ltf*0.15 and son_dip_sonrasi>=dip_bar_low and son2_uc<=ara_max_h-(ara_max_h-dip_bar_low)*0.25 and ak>=ara_max_h-(ara_max_h-dip_bar_low)*0.62 and not ltf_ters_bos_aktif and ak>dip_bar_low+E_ltf*0.15 and son2_tepki_mumu_var and onemli_giris_noktasinda_mi:
     ltf_retest_gerceklesti=True
     if not kir_tip_etiket:kir_tip_etiket='LTF_Bolge_Ici_Kirilim'
 ltf_kirilim_listesi=[]
 ltf_smt_dvg_onay=bool(any(x in p_sd for p_sd in q8 for x in('SMT','Strong_Regular_DVG','Medium_')))
 if mod2_tum_girisler:
  for p_k in(kk+q8):
   if'Weak'in p_k and'CHoCH'in p_k and not(htf_arz_talep_bolgesinde and(ltf_fvg_imbalance_onay or ltf_smt_dvg_onay)):
    continue
   if any(x in p_k for x in('CHoCH','MSB','BOS','InsideBrk','Fakey','FakeSetup','Simple_W','ShortFormed_W','Extended_W','Simple_M','ShortFormed_M','Extended_M','AtNali','QMM_Flip','TersBayrak','TersFlag_Flip','W_Kink','M_Kink')):
    if p_k not in ltf_kirilim_listesi:ltf_kirilim_listesi.append(p_k)
  if yon_kisa in ltf_int_choch and ltf_int_choch not in ltf_kirilim_listesi:
   if'WEAK_CHOCH'not in ltf_int_choch or(htf_arz_talep_bolgesinde and(ltf_fvg_imbalance_onay or ltf_smt_dvg_onay)):
    ltf_kirilim_listesi.append(ltf_int_choch)
 else:
  # MOD 1 KURALI (cys2.png): Kırılım sonrasında YALNIZCA Sarı OB bölgesine (Video_CHoCH_Sari_OB) veya önemli giriş noktalarına (OB, Arz/Talep, OTE, QML) RETEST/PULLBACK geldiğinde onay verilir!
  if ltf_retest_gerceklesti and not ltf_kirilim_aninda_erken_mi:
   if video_choch_ob_pullback:
    ltf_kirilim_listesi.append(f"{kir_tip_etiket or 'Video_CHoCH'}_Sari_OB_Giris({video_choch_ob_hi if g else video_choch_ob_lo:.4f})")
   retest_hedef_str=('LTF_Sari_OB'if video_choch_ob_pullback else'HTF_AT'if htf_at_anlik else'HTF_OB'if htf_ob_anlik else'HTF_OTE'if htf_ote_anlik else'HTF_QML'if htf_qml_anlik else'LTF_AT'if ltf_at_anlik else'LTF_OB'if ltf_ob_anlik else'LTF_QML'if ltf_qml_anlik else'LTF_OTE')
   ltf_kirilim_listesi.append(f"{kir_tip_etiket or 'LTF_CHoCH'}_Retest({retest_hedef_str})")
 ltf_reversal_kirilim_onay=bool(L(ltf_kirilim_listesi)>0)
 # Arz/Talep ve OB Bölgesinde Öğrenilen Tüm LTF Mum Yapıları (Kırılım tepesinde/dibinde havada DEĞİLKEN!):
 ltf_ham_mum_listesi=[]
 for p_m in(kk+q8):
  if any(x in p_m for x in('Engulf','Outside','MeraMera','Pinbar','Spike','Railroad','Star','MorningStar','EveningStar','BosaltDoldur','Marubozu','TersIgneli_Momentum','YingYang','Bobin','Testere','AtNali','Fakey','FakeSetup','InsideBrk','InsideBar','Simple_W','ShortFormed_W','Extended_W','Simple_M','ShortFormed_M','Extended_M')):
   if p_m not in ltf_ham_mum_listesi:ltf_ham_mum_listesi.append(p_m)
 if L(aY)>=4 and not uclu_ters_mum_serisi:
  for idx_c in(-2,-1):
   o_2,c_2,h_2,l_2=(_f(aY,'open',idx_c-2),_f(aY,'close',idx_c-2),_f(aY,'high',idx_c-2),_f(aY,'low',idx_c-2))
   o_p,c_p,h_p,l_p=(_f(aY,'open',idx_c-1),_f(aY,'close',idx_c-1),_f(aY,'high',idx_c-1),_f(aY,'low',idx_c-1))
   o_n,c_n,h_n,l_n=(_f(aY,'open',idx_c),_f(aY,'close',idx_c),_f(aY,'high',idx_c),_f(aY,'low',idx_c))
   gov_2,gov_p,gov_n=(A(c_2-o_2),A(c_p-o_p),A(c_n-o_n))
   alt_ig_n,ust_ig_n=(N(o_n,c_n)-l_n,h_n-M(o_n,c_n))
   if g:
    if c_p<o_p and c_n>o_n and c_n>=o_p and gov_n>=E_ltf*0.25 and'Bull_Engulf'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Engulf')
    if c_n>o_n and h_n>=h_p and l_n<=l_p and(h_n>h_p or l_n<l_p)and gov_n>=E_ltf*0.25 and'Bull_Outside_MeraMera'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Outside_MeraMera')
    if alt_ig_n>=M(gov_n*1.45,E_ltf*0.30)and alt_ig_n>ust_ig_n*1.3 and(c_n>=o_n or c_n>=l_n+(h_n-l_n)*0.55)and'Bull_Pinbar'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Pinbar')
    if c_p<o_p and c_n>o_n and gov_p>=E_ltf*0.35 and gov_n>=gov_p*0.60 and'Bull_Railroad_Tracks'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Railroad_Tracks')
    if c_2<o_2 and gov_2>=E_ltf*0.35 and gov_p<=gov_2*0.55 and c_n>o_n and c_n>=(o_2+c_2)/2.0 and'Bull_MorningStar'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_MorningStar')
    if c_n>o_n and gov_n>=E_ltf*0.48 and alt_ig_n<=gov_n*0.12 and'Bull_Istekli_Marubozu'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Istekli_Marubozu')
    if h_p<=h_2 and l_p>=l_2 and c_n>h_p and c_n>o_n and'Bull_InsideBar_Brk'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_InsideBar_Brk')
    if c_p<o_p and c_n>o_n and A(l_n-l_p)<=E_ltf*0.12 and gov_n>=E_ltf*0.25 and'Bull_Tweezer_Bottom'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Tweezer_Bottom')
    if c_p<o_p and gov_p>=E_ltf*0.35 and c_n>o_n and c_n>=(o_p+c_p)/2.0 and o_n<=c_p+E_ltf*0.10 and'Bull_Piercing_Mum'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bull_Piercing_Mum')
   else:
    if c_p>o_p and c_n<o_n and c_n<=o_p and gov_n>=E_ltf*0.25 and'Bear_Engulf'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Engulf')
    if c_n<o_n and h_n>=h_p and l_n<=l_p and(h_n>h_p or l_n<l_p)and gov_n>=E_ltf*0.25 and'Bear_Outside_MeraMera'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Outside_MeraMera')
    if ust_ig_n>=M(gov_n*1.45,E_ltf*0.30)and ust_ig_n>alt_ig_n*1.3 and(c_n<=o_n or c_n<=h_n-(h_n-l_n)*0.55)and'Bear_Pinbar'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Pinbar')
    if c_p>o_p and c_n<o_n and gov_p>=E_ltf*0.35 and gov_n>=gov_p*0.60 and'Bear_Railroad_Tracks'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Railroad_Tracks')
    if c_2>o_2 and gov_2>=E_ltf*0.35 and gov_p<=gov_2*0.55 and c_n<o_n and c_n<=(o_2+c_2)/2.0 and'Bear_EveningStar'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_EveningStar')
    if c_n<o_n and gov_n>=E_ltf*0.48 and ust_ig_n<=gov_n*0.12 and'Bear_Istekli_Marubozu'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Istekli_Marubozu')
    if h_p<=h_2 and l_p>=l_2 and c_n<l_p and c_n<o_n and'Bear_InsideBar_Brk'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_InsideBar_Brk')
    if c_p>o_p and c_n<o_n and A(h_n-h_p)<=E_ltf*0.12 and gov_n>=E_ltf*0.25 and'Bear_Tweezer_Top'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_Tweezer_Top')
    if c_p>o_p and gov_p>=E_ltf*0.35 and c_n<o_n and c_n<=(o_p+c_p)/2.0 and o_n>=c_p-E_ltf*0.10 and'Bear_DarkCloud_Mum'not in ltf_ham_mum_listesi:
     ltf_ham_mum_listesi.append('Bear_DarkCloud_Mum')
 # image_b45080.png DÜŞÜŞ ŞELALESİ ENGELİ:
 # Fiyat LTF'de yeni en düşük dip (Long için) veya yeni en yüksek tepe (Short için) yaparak şelale halinde akıyorsa
 # (henüz bir yapı kırılımı + HL/LH retesti oluşmamışsa ve son mum bir önceki mumun high/low seviyesini güçlü şekilde kırmamışsa)
 # ara duraksama mumları dönüş emaresi SAYILAMAZ!
 ltf_selale_akis_var=False
 ltf_net_mum_donusu_var=False
 if L(aY)>=10:
  son3_dip_l=F(aY['low'].iloc[-3:].min())
  onceki_dip_l=F(aY['low'].iloc[-12:-3].min())
  son3_tepe_h=F(aY['high'].iloc[-3:].max())
  onceki_tepe_h=F(aY['high'].iloc[-12:-3].max())
  c_0,o_0,h_0,l_0=(_f(aY,'close',-1),_f(aY,'open',-1),_f(aY,'high',-1),_f(aY,'low',-1))
  c_1,o_1,h_1,l_1=(_f(aY,'close',-2),_f(aY,'open',-2),_f(aY,'high',-2),_f(aY,'low',-2))
  o_2s,c_2s,h_2s,l_2s=(_f(aY,'open',-3),_f(aY,'close',-3),_f(aY,'high',-3),_f(aY,'low',-3))
  if g:
   kapanmis_onayli_mum=bool(c_1>o_1 and c_0>=N(o_1,c_1)-E_ltf*0.08 and((c_1>=M(o_2s,c_2s)and c_2s<o_2s and(c_1-o_1)>=E_ltf*0.28)or((N(o_1,c_1)-l_1)>=M(A(c_1-o_1)*1.5,E_ltf*0.32)and c_1>=l_1+(h_1-l_1)*0.55)or((c_1-o_1)>=E_ltf*0.50 and(o_1-l_1)<=(c_1-o_1)*0.12)))
   ltf_net_mum_donusu_var=bool((c_0>o_0 and c_0>=h_1 and(c_0-o_0)>=E_ltf*0.30 and(c_1>o_1 or c_0>=M(o_1,c_1)))or(kapanmis_onayli_mum and c_0>=o_0-E_ltf*0.08))
   if son3_dip_l<=onceki_dip_l+E_ltf*0.05 and(not ltf_net_mum_donusu_var or(c_0<o_0 and not kapanmis_onayli_mum)):
    ltf_selale_akis_var=True
   elif not ltf_retest_gerceklesti and c_0<o_0 and c_0<c_1:
    ltf_selale_akis_var=True
  else:
   kapanmis_onayli_mum=bool(c_1<o_1 and c_0<=M(o_1,c_1)+E_ltf*0.08 and((c_1<=N(o_2s,c_2s)and c_2s>o_2s and(o_1-c_1)>=E_ltf*0.28)or((h_1-M(o_1,c_1))>=M(A(c_1-o_1)*1.5,E_ltf*0.32)and c_1<=h_1-(h_1-l_1)*0.55)or((o_1-c_1)>=E_ltf*0.50 and(h_1-o_1)<=(o_1-c_1)*0.12)))
   ltf_net_mum_donusu_var=bool((c_0<o_0 and c_0<=l_1 and(o_0-c_0)>=E_ltf*0.30 and(c_1<o_1 or c_0<=N(o_1,c_1)))or(kapanmis_onayli_mum and c_0<=o_0+E_ltf*0.08))
   if son3_tepe_h>=onceki_tepe_h-E_ltf*0.05 and(not ltf_net_mum_donusu_var or(c_0>o_0 and not kapanmis_onayli_mum)):
    ltf_selale_akis_var=True
   elif not ltf_retest_gerceklesti and c_0>o_0 and c_0>c_1:
    ltf_selale_akis_var=True
 if ltf_selale_akis_var and not video_choch_ob_pullback:
  ltf_retest_gerceklesti=False
  ltf_kirilim_listesi=[]
  ltf_reversal_kirilim_onay=False
 # MOD 1 MUM KURALI: LTF mum yapıları YALNIZCA fiyat önemli giriş noktalarındayken, kırılım tepesinde DEĞİLKEN
 # ve şelale akışı yokken (ltf_reversal_kirilim_onay VEYA ltf_net_mum_donusu_var ile onaylıyken) geçerlidir!
 if not mod2_tum_girisler:
  ltf_mum_listesi=list(ltf_ham_mum_listesi)if(onemli_giris_noktasinda_mi and not ltf_kirilim_aninda_erken_mi and not uclu_ters_mum_serisi and not ltf_selale_akis_var and(ltf_reversal_kirilim_onay or ltf_net_mum_donusu_var))else[]
 else:
  ltf_mum_listesi=list(ltf_ham_mum_listesi)
 ltf_reversal_mum_onay=bool(L(ltf_mum_listesi)>0)
 ltf_son_mum_uyumlu=not ltf_selale_akis_var
 if L(aY)>=3:
  c_s1,o_s1=(_f(aY,'close',-2),_f(aY,'open',-2))
  c_s0,o_s0=(_f(aY,'close',-1),_f(aY,'open',-1))
  if g and(c_s0<o_s0 and(o_s0-c_s0)>E_ltf*1.45 and c_s1<o_s1 and(o_s1-c_s1)>E_ltf*1.25):ltf_son_mum_uyumlu=False
  elif(not g)and(c_s0>o_s0 and(c_s0-o_s0)>E_ltf*1.45 and c_s1>o_s1 and(c_s1-o_s1)>E_ltf*1.25):ltf_son_mum_uyumlu=False
 ltf_poi_fvg_onay=bool(ltf_arz_talep_onay or ltf_ob_onay or ltf_fvg_imbalance_onay)
 ltf_mum_veya_kirilim_zorunlu=bool(ltf_reversal_kirilim_onay or ltf_reversal_mum_onay)
 ltf_dogrudan_tetik=bool(ltf_mum_veya_kirilim_zorunlu or(mod2_tum_girisler and(ltf_qml_onay or ltf_likidite_onay)))
 ltf_mum_yon_ok=bool(L(aY)>=3 and((_f(aY,'close',-3)>_f(aY,'open',-3)or _f(aY,'close',-2)>_f(aY,'open',-2)or _f(aY,'close',-1)>_f(aY,'open',-1))if g else(_f(aY,'close',-3)<_f(aY,'open',-3)or _f(aY,'close',-2)<_f(aY,'open',-2)or _f(aY,'close',-1)<_f(aY,'open',-1))))
 # 1. Görsel (HTF Yapıya Göre Giriş) vs 2. Görsel (LTF Yapıya Göre Giriş):
 htf_mod_secili=('HTF'in str(STOP_BELIRLEME_MODU)and'Otomatik'not in str(STOP_BELIRLEME_MODU))
 htf_mum_reaksiyon=bool(mod1_zorunlu_sart1 and not ltf_kirilim_aninda_erken_mi and not uclu_ters_mum_serisi and L(bS)>=2 and((_f(bS,'close',-1)>_f(bS,'open',-1)or(_f(bS,'close',-1)-_f(bS,'low',-1))>=E_htf*0.25)if g else(_f(bS,'close',-1)<_f(bS,'open',-1)or(_f(bS,'high',-1)-_f(bS,'close',-1))>=E_htf*0.25)))
 if htf_mod_secili and htf_mum_reaksiyon and not ltf_mum_veya_kirilim_zorunlu:
  ltf_mum_listesi.append('HTF_ArzTalep_Bolge_Giris')
  ltf_reversal_mum_onay=True
  ltf_mum_veya_kirilim_zorunlu=True
 # MOD 1 KURALI: HTF şartları sağlandıktan sonra:
 # 1) LTF'de market kırılımı + önemli giriş noktalarına (Arz/Talep, OB, OTE, QML) RETEST gelmesi VEYA
 # 2) Önemli giriş noktalarında (Arz/Talep, OB, OTE, QML) daha önce öğrendiğimiz LTF mum hareketlerinin oluşması!
 # Kırılım anında (HH tepesinde / LL dibinde) erken giriş kesinlikle yasaktır!
 # KESİN VE İSTİSNASIZ HTF-LTF YÖN UYUMU KİLİDİ (image_b88e99.png & image_b88e40.png DÜZELTMESİ):
 # KURAL: HTF'de yön aşağı (BEARISH/SHORT) iken LTF grafiğinde yön yukarı (BULLISH / son kırılım BULLISH / son zigzag noktası HH) ise
 # VEYA HTF'de yön yukarı (BULLISH/LONG) iken LTF grafiğinde yön aşağı (BEARISH / son kırılım BEARISH / son zigzag noktası LL) ise
 # HİÇBİR İSTİSNA OLMADAN (mikro kırılım, retest veya mum ne olursa olsun) KESİNLİKLE İŞLEME GİRİLMEZ!
 ters_yon_str='BEARISH'if g else'BULLISH'
 ltf_h_zig=aj.get('highs',[])if I(aj,dict)else[]
 ltf_l_zig=aj.get('lows',[])if I(aj,dict)else[]
 ltf_son_zig_hh=bool(L(ltf_h_zig)>=2 and F(ltf_h_zig[-1][1])>F(ltf_h_zig[-2][1])and(not ltf_l_zig or int(ltf_h_zig[-1][0])>int(ltf_l_zig[-1][0])or(L(ltf_l_zig)>=2 and F(ltf_l_zig[-1][1])>F(ltf_l_zig[-2][1]))))
 ltf_son_zig_ll=bool(L(ltf_l_zig)>=2 and F(ltf_l_zig[-1][1])<F(ltf_l_zig[-2][1])and(not ltf_h_zig or int(ltf_l_zig[-1][0])>int(ltf_h_zig[-1][0])or(L(ltf_h_zig)>=2 and F(ltf_h_zig[-1][1])<F(ltf_h_zig[-2][1]))))
 ltf_ters_bos_kesin=bool(ltf_son_bos_yon==ters_yon_str)
 ltf_ters_ana_yapi_kesin=bool(aj.get('yon')==ters_yon_str)
 ltf_ters_zig_kesin=bool(ltf_son_zig_ll if g else ltf_son_zig_hh)
 ltf_ters_momentum=False
 if L(aY)>=6:
  if not g and _f(aY,'close',-1)>_f(aY,'open',-1)and _f(aY,'close',-1)>_f(aY,'close',-3)and _f(aY,'high',-1)>=F(aY['high'].iloc[-6:-1].max()):
   ltf_ters_momentum=True
  elif g and _f(aY,'close',-1)<_f(aY,'open',-1)and _f(aY,'close',-1)<_f(aY,'close',-3)and _f(aY,'low',-1)<=F(aY['low'].iloc[-6:-1].min()):
   ltf_ters_momentum=True
 ltf_yon_uyumlu=bool(not ltf_ters_bos_kesin and not ltf_ters_ana_yapi_kesin and not ltf_ters_zig_kesin and not ltf_ters_momentum)
 if not ltf_yon_uyumlu:
  ltf_reversal_kirilim_onay=False
  ltf_reversal_mum_onay=False
  ltf_kirilim_listesi=[]
  ltf_mum_listesi=[]
  ltf_mum_veya_kirilim_zorunlu=False
 ltf_herhangi_tetik=bool(ltf_yon_uyumlu and ltf_son_mum_uyumlu and((not ltf_kirilim_aninda_erken_mi and onemli_giris_noktasinda_mi and ltf_mum_veya_kirilim_zorunlu)if not mod2_tum_girisler else(ltf_dogrudan_tetik or(ltf_poi_fvg_onay and ltf_mum_yon_ok))))
 ltf_giris_emare_sayisi=sum([int(ltf_arz_talep_onay),int(ltf_ob_onay),int(ltf_fvg_imbalance_onay),int(ltf_likidite_onay),int(ltf_qml_onay),int(ltf_reversal_mum_onay),int(ltf_reversal_kirilim_onay)])
 if not ltf_herhangi_tetik:
  ltf_giris_emare_sayisi=0
 ltf_choch_var=bool(ltf_reversal_kirilim_onay)
 ltf_qml_temas=bool(ltf_qml_onay)
 ltf_ist=aj.get('uc_istasyon',{})
 ltf_fl_lvl=F(aj.get('fl_dp_meta',{}).get('magic_line')or ltf_ist.get('FL')or ltf_kysy.get('son_kirilim_seviye')or 0.0)
 ltf_itz_lvl=F(ltf_ist.get('ITZ')or 0.0)
 ltf_kirilim_yeri_temas=bool((ltf_fl_lvl>0 and A(de-ltf_fl_lvl)<=E_ltf*1.85)or(ltf_itz_lvl>0 and A(de-ltf_itz_lvl)<=E_ltf*1.85)or ltf_poi_fvg_onay or ltf_reversal_kirilim_onay)
 ltf_a_choch_kirilim_yeri=bool(ltf_reversal_kirilim_onay and ltf_kirilim_yeri_temas)
 ltf_b_choch_qml_seviyesi=bool((ltf_reversal_kirilim_onay or ltf_reversal_mum_onay)and ltf_qml_temas)
 ltf_c_mum_yapisi=bool(ltf_reversal_mum_onay)
 alt_tetik_kodlari=[]
 if ltf_arz_talep_onay:alt_tetik_kodlari.append(f"LTF_AT({'/'.join(ltf_arz_talep_listesi[:1])})")
 if ltf_ob_onay:alt_tetik_kodlari.append(f"LTF_OB({'/'.join(ltf_ob_listesi[:1])})")
 if ltf_fvg_imbalance_onay:alt_tetik_kodlari.append(f"LTF_FVG({'/'.join(ltf_fvg_listesi[:1])})")
 if ltf_likidite_onay:alt_tetik_kodlari.append(f"LTF_Liq({'/'.join(ltf_likidite_listesi[:1])})")
 if ltf_qml_onay:alt_tetik_kodlari.append(f"LTF_QML({'/'.join(ltf_qml_listesi[:1])})")
 if ltf_reversal_kirilim_onay:alt_tetik_kodlari.append(f"LTF_Kirilim({'/'.join(ltf_kirilim_listesi[:2])})")
 if ltf_reversal_mum_onay:alt_tetik_kodlari.append(f"LTF_Mum({'/'.join(ltf_mum_listesi[:2])})")
 # Mod 1: güçlü Fresh Arz/Talep zorunlu. Mod 2: HTF yönü + aktif POI zorunlu.
 mod2_htf_yon_kilidi=bool(mod2_tum_girisler and htf_yon_ok)
 sart1_htf_poi_giris=bool((mod1_zorunlu_sart1 if not mod2_tum_girisler else(mod2_htf_yon_kilidi and htf_arz_talep_bolgesinde)) and ltf_herhangi_tetik)
 sart2_htf_ob_giris=bool((mod1_zorunlu_sart1 if not mod2_tum_girisler else mod2_htf_yon_kilidi) and htf_ob_bolgesinde and ltf_herhangi_tetik)
 sart3_htf_ote_giris=bool((mod1_zorunlu_sart1 if not mod2_tum_girisler else mod2_htf_yon_kilidi) and htf_ote_bolgesinde and ltf_herhangi_tetik)
 sart4_htf_qml_giris=bool((mod1_zorunlu_sart1 if not mod2_tum_girisler else mod2_htf_yon_kilidi) and htf_qml_bolgesinde and ltf_herhangi_tetik)
 sart5_htf_choch_giris=bool(mod2_htf_yon_kilidi and htf_choch_noktasinda and ltf_herhangi_tetik)
 sart6_htf_bos_giris=bool(mod2_htf_yon_kilidi and htf_bos_noktasinda and ltf_herhangi_tetik)
 sart7_htf_itz_giris=bool(mod2_htf_yon_kilidi and htf_itz_bolgesinde and ltf_herhangi_tetik)
 sart8_htf_magic_giris=bool(mod2_htf_yon_kilidi and htf_magic_line_bolgesinde and ltf_herhangi_tetik)
 sart9_htf_fvg_giris=bool(mod2_htf_yon_kilidi and htf_fvg_bolgesinde and ltf_herhangi_tetik)
 oncelikli_giris_sart_sayisi=(1+mod1_ek_sart_sayisi if(mod1_zorunlu_sart1 and ltf_herhangi_tetik)else 0)if not mod2_tum_girisler else sum([int(sart1_htf_poi_giris),int(sart2_htf_ob_giris),int(sart3_htf_ote_giris),int(sart4_htf_qml_giris),int(sart9_htf_fvg_giris)])
 ikincil_giris_sart_sayisi=sum([int(sart5_htf_choch_giris),int(sart6_htf_bos_giris),int(sart7_htf_itz_giris),int(sart8_htf_magic_giris)])
 saglanan_giris_sart_sayisi=oncelikli_giris_sart_sayisi+(ikincil_giris_sart_sayisi if mod2_tum_girisler else 0)
 saglanan_alt_kural_sayisi=saglanan_giris_sart_sayisi*M(1,L(alt_tetik_kodlari))
 en_yakin_birincil_atr=F(ilk_k['en_yakin_birincil_atr'])
 birincil_pusuda_onay=bool(ilk_k['birincil_pusuda_onay'])
 birincil_olcek_carpani_etkin=F(ilk_k['birincil_olcek_carpani_etkin'])
 birincil_radar_kademesi=(3 if(htf_zorunlu_bolge_onay and ltf_herhangi_tetik)else(2 if htf_zorunlu_bolge_onay else(1 if birincil_pusuda_onay else 0)))
 if htf_oncelikli_bolge_onay:
  ltf_bonus=(250 if ltf_herhangi_tetik else 0)+ltf_giris_emare_sayisi*95
  birincil_olcek_skoru=N(10000,int(ilk_k['birincil_olcek_skoru'])+ltf_bonus)
 elif mod2_tum_girisler and htf_zorunlu_bolge_onay:
  birincil_olcek_skoru=N(4800,1500+(900 if htf_mod2_birincil_bolge_onay else 0)+htf_ikincil_bolge_sayisi*650+(500 if ltf_herhangi_tetik else 0))
 elif birincil_pusuda_onay:
  birincil_olcek_skoru=int(ilk_k['birincil_olcek_skoru'])
 else:
  birincil_olcek_skoru=0
 htf_safe_puan=N(100,int(R((18 if htf_yon_ok else 0)+(22 if htf_arz_talep_bolgesinde else 0)+(14 if htf_ob_bolgesinde else 0)+(12 if htf_ote_bolgesinde else 0)+(11 if htf_fvg_bolgesinde else 0)+N(12,hedef_yon_likidite_sayisi*4)+(9 if htf_qml_bolgesinde else 0)+(12 if ltf_herhangi_tetik else 0),0)))
 if mod1_zorunlu_sart1:
  if mod1_ek_sart_sayisi>=4:
   htf_safe_derecesi=f"💎 1.MOD ULTRA SAFE A++++ (BOS/CHoCH {hedef_tur} [{aktif_at_modu}] + {mod1_ek_sart_sayisi}/5 Güç Faktörü)"
  elif mod1_ek_sart_sayisi==3:
   htf_safe_derecesi=f"👑 1.MOD ÇOK SAFE A+++ (BOS/CHoCH {hedef_tur} [{aktif_at_modu}] + 3/5 Güç Faktörü)"
  elif mod1_ek_sart_sayisi==2:
   htf_safe_derecesi=f"🔥 1.MOD SAFE A++ (BOS/CHoCH {hedef_tur} [{aktif_at_modu}] + 2/5 Güç Faktörü)"
  elif mod1_ek_sart_sayisi==1:
   htf_safe_derecesi=f"🎯 1.MOD SAFE A+ (BOS/CHoCH {hedef_tur} [{aktif_at_modu}] + 1/5 Güç Faktörü)"
  else:
   htf_safe_derecesi=f"🛡️ 1.MOD BAZ SAFE A (BOS/CHoCH {hedef_tur} [{aktif_at_modu}] | 0/5 Güç Faktörü)"
 elif mod2_tum_girisler and htf_zorunlu_bolge_onay:
  htf_safe_derecesi="🧭 2.MOD ÖĞRENİLEN GİRİŞ BÖLGESİ"
 elif birincil_pusuda_onay:
  htf_safe_derecesi=f"🔭 GÜÇLÜ FRESH {hedef_tur} PUSUDA ({en_yakin_birincil_atr:.1f}x ATR Yakında)"
 else:
  htf_safe_derecesi=f"🔴 HTF BOS/CHoCH {hedef_tur} BÖLGESİ DIŞI (ELENDİ)"
 aktif_htf_bolgeler=[]
 aktif_birincil_bolgeler=list(ilk_k['aktif_birincil_bolgeler'])
 if htf_arz_talep_bolgesinde:aktif_htf_bolgeler.append(f"Fresh_{hedef_tur}_{aktif_at_modu}({aktif_at_guc_10p:.1f}p)")
 if htf_ob_bolgesinde:aktif_htf_bolgeler.append("1.OB")
 if htf_ote_bolgesinde:aktif_htf_bolgeler.append("2.OTE")
 if htf_fvg_bolgesinde:aktif_htf_bolgeler.append("3.FVG")
 if hedef_yon_likidite_var:aktif_htf_bolgeler.append(f"4.Liq({hedef_yon_likidite_sayisi}x)")
 if htf_qml_bolgesinde:aktif_htf_bolgeler.append(f"5.QML({htf_qml_lvl:.4f})"if htf_qml_lvl>0 else"5.QML")
 if mod2_tum_girisler:
  if htf_bos_noktasinda:aktif_htf_bolgeler.append("BOS_Noktasi")
  if htf_choch_noktasinda:aktif_htf_bolgeler.append("CHoCH_Noktasi")
  if htf_itz_bolgesinde:aktif_htf_bolgeler.append("ITZ")
  if htf_magic_line_bolgesinde:aktif_htf_bolgeler.append("MagicLine")
 oncelik_vektor=tuple(ilk_k['oncelik_vektor'])
 giris_oncelik_vektor=(int(mod1_zorunlu_sart1),int(mod1_ek_sart_sayisi),int(hedef_yon_likidite_sayisi),int(ltf_giris_emare_sayisi))
 ikincil_vektor=(int(htf_bos_noktasinda),int(htf_choch_noktasinda),int(htf_itz_bolgesinde),int(htf_magic_line_bolgesinde))
 en_yuksek_oncelik_sira=(1 if(mod1_zorunlu_sart1 and mod1_ek_sart_sayisi>=3)else 2 if(mod1_zorunlu_sart1 and mod1_ek_sart_sayisi==2)else 3 if(mod1_zorunlu_sart1 and mod1_ek_sart_sayisi==1)else 4 if mod1_zorunlu_sart1 else(5 if(mod2_tum_girisler and htf_zorunlu_bolge_onay)else(6 if birincil_pusuda_onay else 9)))
 en_yuksek_oncelik_etiket=(f"1.Mod Güçlü Fresh {hedef_tur} [{aktif_at_modu}] + {mod1_ek_sart_sayisi}/5 Güç Bölgesi ({'+'.join(aktif_birincil_bolgeler)})"if mod1_zorunlu_sart1 else('2.Mod Giriş Yeri'if(mod2_tum_girisler and htf_zorunlu_bolge_onay)else(f"Güçlü {hedef_tur} Pusuda ({en_yakin_birincil_atr:.1f}x ATR)"if birincil_pusuda_onay else'Bölge Dışı')))
 aktif_ltf_tetikler=list(alt_tetik_kodlari)
 ltf_poi_fvg_ozet='+'.join((ltf_arz_talep_listesi[:1]+ltf_ob_listesi[:1]+ltf_fvg_listesi[:1]))or'Bekleniyor'
 ltf_tetik_ozet='+'.join((ltf_likidite_listesi[:1]+ltf_qml_listesi[:1]+ltf_kirilim_listesi[:1]+ltf_mum_listesi[:1]))or'Bekleniyor'
 checklist_dict={'ilk_kontrol_gecti':bool(htf_oncelikli_bolge_onay),'mod1_zorunlu_sart1':bool(mod1_zorunlu_sart1),'mod1_ek_sart_sayisi':int(mod1_ek_sart_sayisi),'arz_talep_modu':aktif_at_modu,'arz_talep_10p':f"{aktif_at_guc_10p:.1f}",'yon_ok':bool(htf_yon_ok),'qml':bool(htf_qml_bolgesinde),'qml_fiyat':f"{htf_qml_lvl:.4f}"if htf_qml_lvl>0 else'-','ote':bool(htf_ote_bolgesinde),'ote_aralik':f"{N(ote_lo,ote_hi):.4f}-{M(ote_lo,ote_hi):.4f}"if ote_hi>0 and ote_lo>0 else'-','ob':bool(htf_ob_bolgesinde),'ob_aralik':f"{N(ob_lo,ob_hi):.4f}-{M(ob_lo,ob_hi):.4f}"if ob_hi>0 and ob_lo>0 else'-','fvg':bool(htf_fvg_bolgesinde),'fvg_aralik':f"{N(fvg_lo,fvg_hi):.4f}-{M(fvg_lo,fvg_hi):.4f}"if fvg_hi>0 and fvg_lo>0 else'-','fresh_arz_talep':bool(htf_arz_talep_bolgesinde),'fresh_aralik':f"{N(fresh_lo,fresh_hi):.4f}-{M(fresh_lo,fresh_hi):.4f}"if fresh_hi>0 and fresh_lo>0 else'-','hedef_yon_likidite_var':bool(hedef_yon_likidite_var),'hedef_yon_likidite_sayisi':int(hedef_yon_likidite_sayisi),'hedef_yon_likidite_ozet':', '.join(hedef_yon_likidite_etiketler[:3])or'Yok','choch_noktasi':bool(htf_choch_noktasinda),'choch_fiyat':f"{choch_lvl:.4f}"if choch_lvl>0 else(f"Origin:{choch_orig:.4f}"if choch_orig>0 else'-'),'bos_noktasi':bool(htf_bos_noktasinda),'bos_fiyat':f"{bos_lvl:.4f} (Origin:{bos_orig:.4f})"if bos_lvl>0 and bos_orig>0 else(f"{bos_orig:.4f}"if bos_orig>0 else'-'),'itz':bool(htf_itz_bolgesinde),'itz_fiyat':f"{htf_itz_lvl:.4f}"if htf_itz_lvl>0 else'-','magic_line':bool(htf_magic_line_bolgesinde),'magic_fiyat':f"{htf_magic_lvl:.4f}"if htf_magic_lvl>0 else'-','ltf_poi_fvg_onay':bool(ltf_poi_fvg_onay),'ltf_poi_fvg_ozet':ltf_poi_fvg_ozet,'ltf_herhangi_tetik':bool(ltf_herhangi_tetik),'ltf_tetik_ozet':ltf_tetik_ozet,'ltf_reversal_kirilim':bool(ltf_reversal_kirilim_onay),'ltf_reversal_mum':bool(ltf_reversal_mum_onay),'safe_sayisi':int(htf_bolge_sayisi),'safe_puan':int(htf_safe_puan),'safe_derece':htf_safe_derecesi,'birincil_olcek_skoru':int(birincil_olcek_skoru),'birincil_olcek_carpani':F(birincil_olcek_carpani_etkin)}
 # image_28564a.png vs image_5c98c9.png:
 # Asıl (Sniper) Retest Girişi (alttaki noktalı/kesikli çizgi OB/Talep/Arz tabanına [origin_uc..+%42] çekilme) vs Agresif Giriş (daha düşük TP/RR hedefi):
 alt_cizgi_retest_onay=bool(ltf_retest_gerceklesti and(video_choch_ob_pullback or(kir_var and ltf_leg_boyu>0 and((ak<=origin_uc+ltf_leg_boyu*0.45)if g else(ak>=origin_uc-ltf_leg_boyu*0.45)))))
 agresif_giris_mi=bool(ltf_herhangi_tetik and not alt_cizgi_retest_onay)
 etkin_rr_orani=R(M(1.15,N(1.50,F(RISK_ODUL_ORANI)*0.58)),2)if agresif_giris_mi else F(RISK_ODUL_ORANI)
 checklist_dict['giris_tipi']=('Agresif Giriş (Düşük Hedef '+str(etkin_rr_orani)+'R)'if agresif_giris_mi else'Sniper Retest Girişi (Tam Hedef '+str(etkin_rr_orani)+'R)')if ltf_herhangi_tetik else'Beklemede'
 htf_trend_degistiren_nokta=F(htf_bos_raw[-1][3])if htf_bos_raw else F(aP.get('strong_point')or(sMin if g else sMax))
 if g:
  if htf_sp>0 and htf_trend_degistiren_nokta>0:htf_trend_degistiren_nokta=N(htf_trend_degistiren_nokta,htf_sp,sMin if sMin>0 else htf_sp)
 else:
  if htf_sp>0 and htf_trend_degistiren_nokta>0:htf_trend_degistiren_nokta=M(htf_trend_degistiren_nokta,htf_sp,sMax if sMax>0 else htf_sp)
 return{'ilk_kontrol_birincil_4_bolge_mi':htf_oncelikli_bolge_onay,'mod1_zorunlu_sart1':mod1_zorunlu_sart1,'mod1_ek_sart_sayisi':mod1_ek_sart_sayisi,'aktif_at_modu':aktif_at_modu,'aktif_at_guc_10p':aktif_at_guc_10p,'fresh_lo':fresh_lo,'fresh_hi':fresh_hi,'aktif_htf_at_kutu':ilk_k.get('aktif_htf_at_kutu'),'hedef_yon_likidite_var':hedef_yon_likidite_var,'hedef_yon_likidite_sayisi':hedef_yon_likidite_sayisi,'hedef_yon_likidite_agirlik':hedef_yon_likidite_agirlik,'hedef_yon_likidite_etiketler':hedef_yon_likidite_etiketler,'hedef_yon':B,'htf_yon_ok':htf_yon_ok,'mtf_yon_onay':mtf_yon_onay,'htf_zorunlu_bolge_onay':htf_zorunlu_bolge_onay,'htf_arz_talep_bolgesinde':htf_arz_talep_bolgesinde,'htf_ob_bolgesinde':htf_ob_bolgesinde,'htf_ote_bolgesinde':htf_ote_bolgesinde,'htf_fvg_bolgesinde':htf_fvg_bolgesinde,'htf_qml_bolgesinde':htf_qml_bolgesinde,'htf_choch_noktasinda':htf_choch_noktasinda,'htf_bos_noktasinda':htf_bos_noktasinda,'htf_itz_bolgesinde':htf_itz_bolgesinde,'htf_magic_line_bolgesinde':htf_magic_line_bolgesinde,'htf_bolge_sayisi':htf_bolge_sayisi,'htf_safe_puan':htf_safe_puan,'htf_safe_derecesi':htf_safe_derecesi,'aktif_htf_bolgeler':aktif_htf_bolgeler,'htf_imbalance_sayisi':htf_imbalance_sayisi,'htf_likidite_sayisi':htf_likidite_sayisi,'ltf_arz_talep_onay':ltf_arz_talep_onay,'ltf_arz_talep_listesi':ltf_arz_talep_listesi,'ltf_ob_onay':ltf_ob_onay,'ltf_ob_listesi':ltf_ob_listesi,'ltf_fvg_imbalance_onay':ltf_fvg_imbalance_onay,'ltf_fvg_listesi':ltf_fvg_listesi,'ltf_likidite_onay':ltf_likidite_onay,'ltf_likidite_listesi':ltf_likidite_listesi,'ltf_qml_onay':ltf_qml_onay,'ltf_qml_listesi':ltf_qml_listesi,'ltf_giris_emare_sayisi':ltf_giris_emare_sayisi,'ltf_choch_var':ltf_choch_var,'ltf_reversal_kirilim_onay':ltf_reversal_kirilim_onay,'ltf_reversal_mum_onay':ltf_reversal_mum_onay,'ltf_kirilim_listesi':ltf_kirilim_listesi,'ltf_mum_listesi':ltf_mum_listesi,'ltf_herhangi_tetik':ltf_herhangi_tetik,'ltf_yon_uyumlu':ltf_yon_uyumlu,'ltf_kirilim_aninda_erken_mi':ltf_kirilim_aninda_erken_mi,'ltf_retest_gerceklesti':ltf_retest_gerceklesti,'alt_cizgi_retest_onay':alt_cizgi_retest_onay,'agresif_giris_mi':agresif_giris_mi,'etkin_rr_orani':etkin_rr_orani,'video_choch_ob_pullback':video_choch_ob_pullback,'video_choch_ob_lo':video_choch_ob_lo,'video_choch_ob_hi':video_choch_ob_hi,'ltf_yapi_dip_tepe':ltf_yapi_dip_tepe,'onemli_giris_noktasinda_mi':onemli_giris_noktasinda_mi,'ltf_qml_giris':ltf_b_choch_qml_seviyesi,'ltf_kirilim_yeri_giris':ltf_a_choch_kirilim_yeri,'ltf_mum_yapisi_giris':ltf_c_mum_yapisi,'aktif_ltf_tetikler':aktif_ltf_tetikler,'sart1_htf_poi_giris':sart1_htf_poi_giris,'sart2_htf_ob_giris':sart2_htf_ob_giris,'sart3_htf_ote_giris':sart3_htf_ote_giris,'sart4_htf_qml_giris':sart4_htf_qml_giris,'sart5_htf_choch_giris':sart5_htf_choch_giris,'sart6_htf_bos_giris':sart6_htf_bos_giris,'sart7_htf_itz_giris':sart7_htf_itz_giris,'sart8_htf_magic_giris':sart8_htf_magic_giris,'sart9_htf_fvg_giris':sart9_htf_fvg_giris,'htf_mod2_birincil_bolge_onay':htf_mod2_birincil_bolge_onay,'htf_mod2_ikincil_bolge_onay':htf_mod2_ikincil_bolge_onay,'htf_mod2_entry_zone_onay':htf_mod2_entry_zone_onay,'htf_mod2_entry_zone_adi':htf_mod2_entry_zone_adi,'htf_mod2_entry_zone_lo':htf_mod2_entry_zone_lo,'htf_mod2_entry_zone_hi':htf_mod2_entry_zone_hi,'htf_oncelikli_bolge_onay':htf_oncelikli_bolge_onay,'htf_oncelikli_bolge_sayisi':htf_oncelikli_bolge_sayisi,'oncelikli_giris_sart_sayisi':oncelikli_giris_sart_sayisi,'htf_ikincil_bolge_onay':htf_ikincil_bolge_onay,'htf_ikincil_bolge_sayisi':htf_ikincil_bolge_sayisi,'ikincil_giris_sart_sayisi':ikincil_giris_sart_sayisi,'oncelik_vektor':oncelik_vektor,'giris_oncelik_vektor':giris_oncelik_vektor,'ikincil_vektor':ikincil_vektor,'en_yuksek_oncelik_sira':en_yuksek_oncelik_sira,'en_yuksek_oncelik_etiket':en_yuksek_oncelik_etiket,'bolge_kademesi':(1 if mod1_zorunlu_sart1 else(2 if htf_zorunlu_bolge_onay else 0)),'saglanan_giris_sart_sayisi':saglanan_giris_sart_sayisi,'saglanan_alt_kural_sayisi':saglanan_alt_kural_sayisi,'htf_trend_degistiren_nokta':htf_trend_degistiren_nokta,'birincil_olcek_skoru':birincil_olcek_skoru,'birincil_olcek_carpani_etkin':birincil_olcek_carpani_etkin,'birincil_radar_kademesi':birincil_radar_kademesi,'birincil_pusuda_onay':birincil_pusuda_onay,'en_yakin_birincil_atr':en_yakin_birincil_atr,'aktif_birincil_bolgeler':aktif_birincil_bolgeler,'giris_strateji_modu':GIRIS_STRATEJI_MODU,'checklist':checklist_dict}
def konum_ve_karar_bolgesi_filtresi(bS,bw,aY,aP,Q,aj,f4h,f6,q8,hN,q7,ra,kk,B='BULLISH'):
 adim=_htf_adimlari_ve_ltf_tetik_kontrolu(bS,bw,aY,aP,Q,aj,f4h,f6,q8,hN,q7,ra,kk,B)
 konum_onay=bool(adim['htf_zorunlu_bolge_onay'])
 flip_var=any(x in p for p in(f4h+f6+q8)for x in('Flip','TersFlag','TersBayrak','QMM_Flip','VIB_Flip','Breakaway_Gap','1Mum_FTR','FirstObstacle_FO','IFVG'))
 if not konum_onay:
  if '2. Mod' in str(GIRIS_STRATEJI_MODU):
   durum='RED_HTF_MOD2_GIRIS_BOLGESI_DISI'
   senaryo='HTF_YON_VE_GECERLI_POI_BEKLENIYOR'
   aciklama=f"[2. MOD FİLTRESİ RED] HTF yönüyle uyumlu birincil (Fresh A/T, OB, OTE, FVG, QML) veya ikincil (BOS, CHoCH, ITZ, Magic Line) giriş bölgesine fiyat teması yok!"
  else:
   durum='RED_HTF_GUCLU_ARZ_TALEP_DISI_YASAK'
   senaryo='HTF_YON_VE_GUCLU_FRESH_ARZ_TALEP_BEKLENIYOR'
   aciklama=f"[1. MOD FİLTRESİ RED] Fiyat HTF ({HTF_PERIYOT.upper()}) yönüne uygun Güçlü Fresh {'Talep (DBR/RBR)' if B=='BULLISH' else 'Arz (RBD/DBD)'} bölgesinde değil!"
 else:
  bolge_str='+'.join(adim['aktif_htf_bolgeler'])
  kademe_str=f"1.MOD_GUC_{adim['mod1_ek_sart_sayisi']}_5({adim['birincil_olcek_skoru']}/10000p)"if adim['mod1_zorunlu_sart1']else f"2.MOD_GIRIS({adim['birincil_olcek_skoru']}/10000p)"
  durum=f"ONAY_{kademe_str}[{bolge_str}]"
  senaryo=f"{adim['htf_safe_derecesi']} | Güç:{adim['birincil_olcek_skoru']}/10000p"if adim['ltf_herhangi_tetik']else f"HTF_GUCLU_ARZ_TALEPTE({bolge_str})_LTF_EMARESI_BEKLENIYOR"
  aciklama=f"[{kademe_str} -> {adim['htf_safe_derecesi']}] LTF Giriş Emaresi ({adim['ltf_giris_emare_sayisi']}): {'+'.join(adim['aktif_ltf_tetikler'])or'LTF Giriş Emaresi Bekleniyor (İşleme Girilmez)'}"
 adim.update({'konum_onay':konum_onay,'konum_durumu':durum,'karar_senaryosu':senaryo,'htf_poi_aktif':adim['htf_arz_talep_bolgesinde']or adim['htf_ob_bolgesinde'],'mtf_poi_aktif':L(f6)>0 or L(q7)>0,'fibo_konum_uygun':adim['htf_ote_bolgesinde'],'flip_devam_mi':flip_var,'ters_bolge_engeli':not konum_onay,'tuzak_choch_mu':bool(adim['ltf_choch_var']and not konum_onay),'aciklama':aciklama})
 return adim
def stop_noktasi_belirle(bS,bw,aY,aP,Q,aj,kFlt,P,B='BULLISH',sl4h=None,f7=None,q9=None,al_ltf=None,mod=None):
 sec_mod=str(mod or STOP_BELIRLEME_MODU)
 g=(B=='BULLISH')
 E_htf=M(_f(bS,'atr',-2)if bS is not None and'atr'in bS.columns else P*0.003,P*0.0015)
 E_ltf=M(_f(aY,'atr',-2)if aY is not None and'atr'in aY.columns else P*0.0015,P*0.0008)
 fresh_lo=F(kFlt.get('fresh_lo')or 0.0)if I(kFlt,dict)else 0.0
 fresh_hi=F(kFlt.get('fresh_hi')or 0.0)if I(kFlt,dict)else 0.0
 ob_lo=F(kFlt.get('ob_lo')or 0.0)if I(kFlt,dict)else 0.0
 ob_hi=F(kFlt.get('ob_hi')or 0.0)if I(kFlt,dict)else 0.0
 kutu_boyu=M(fresh_hi-fresh_lo,E_htf*0.25)if fresh_hi>fresh_lo>0 else E_htf*0.6
 htf_emniyet_payi=M(kutu_boyu*0.28,E_htf*0.25,P*aW)
 htf_td=F(kFlt.get('htf_trend_degistiren_nokta')or 0.0)if I(kFlt,dict)else 0.0
 htf_sp=F(aP.get('strong_point')or 0.0)if I(aP,dict)else 0.0
 htf_poi_sl=F(sl4h or 0.0)if I(sl4h,(int,F))else 0.0
 # =========================================================================
 # 1. GÖRSEL KURGUSU (HTF YAPIYA GÖRE EMNİYETLİ STOP NOKTASI):
 # Aktif HTF Arz/Talep kutusu [fresh_lo, fresh_hi] varsa stop doğrudan kutunun
 # arka sınırının (Long: fresh_lo altı, Short: fresh_hi üstü) emniyet payı dışına konulur!
 # =========================================================================
 if g:
  kutu_alt_aday=[x for x in(fresh_lo,ob_lo if ob_lo>0 else 0.0)if 0<x<P]
  if kutu_alt_aday:
   htf_kutu_alt=N(kutu_alt_aday)
   son_htf_dip=N(_f(bS,'low',-2),_f(bS,'low',-1),htf_kutu_alt)if bS is not None and L(bS)>=2 else htf_kutu_alt
   htf_baz=N(htf_kutu_alt,son_htf_dip if son_htf_dip>=htf_kutu_alt-E_htf*0.8 else htf_kutu_alt)
   al_htf=R(N(htf_baz-htf_emniyet_payi,P*(1.0-aW)),6)
  else:
   htf_adaylar=[x for x in(htf_poi_sl,htf_sp,htf_td)if 0<x<P]
   htf_baz=M(htf_adaylar)if htf_adaylar else P*0.988
   al_htf=R(N(htf_baz-E_htf*0.22,P*(1.0-aW)),6)
 else:
  kutu_ust_aday=[x for x in(fresh_hi,ob_hi if ob_hi>0 else 0.0)if x>P]
  if kutu_ust_aday:
   htf_kutu_ust=M(kutu_ust_aday)
   son_htf_tepe=M(_f(bS,'high',-2),_f(bS,'high',-1),htf_kutu_ust)if bS is not None and L(bS)>=2 else htf_kutu_ust
   htf_baz=M(htf_kutu_ust,son_htf_tepe if son_htf_tepe<=htf_kutu_ust+E_htf*0.8 else htf_kutu_ust)
   al_htf=R(M(htf_baz+htf_emniyet_payi,P*(1.0+aW)),6)
  else:
   htf_adaylar=[x for x in(htf_poi_sl,htf_sp,htf_td)if x>P]
   htf_baz=N(htf_adaylar)if htf_adaylar else P*1.012
   al_htf=R(M(htf_baz+E_htf*0.22,P*(1.0+aW)),6)
 # =========================================================================
 # 2. GÖRSEL KURGUSU (LTF YAPIYA GÖRE EMNİYETLİ STOP NOKTASI):
 # Fiyat 1. görseldeki HTF Arz/Talep bölgesine geldikten sonra LTF'de 2. görseldeki
 # yapı oluştuğunda, stop noktası hem LTF dönüş tepesinin/dibinin hem de HTF Arz/Talep
 # kutusunun arka sınırının (Short: fresh_hi, Long: fresh_lo) DIŞINA konulur!
 # =========================================================================
 v10=aj.get('v10_meta',{})if I(aj,dict)else{}
 v12=aj.get('v12_meta',{})if I(aj,dict)else{}
 v13=aj.get('v13_meta',{})if I(aj,dict)else{}
 ltf_ist=aj.get('uc_istasyon',{})if I(aj,dict)else{}
 ltf_sp=F(aj.get('strong_point')or 0.0)if I(aj,dict)else 0.0
 ltf_itz=F(ltf_ist.get('ITZ')or 0.0)
 ltf_poi_sl=F(q9 or 0.0)if I(q9,(int,F))else 0.0
 ltf_pa_sl=F(al_ltf or 0.0)if I(al_ltf,(int,F))else 0.0
 ib_sl=0.0
 if v12.get('dar_sl_4r')and I(v12.get('ib_low'if g else'ib_high'),(int,F)):
  ib_sl=F(v12['ib_low'])-E_ltf*0.12 if g else F(v12['ib_high'])+E_ltf*0.12
 elif I(v12.get('mb_low'if g else'mb_high'),(int,F))and v12.get('inside_bar_durumu','YOK')!='YOK':
  ib_sl=F(v12['mb_low'])-E_ltf*0.15 if g else F(v12['mb_high'])+E_ltf*0.15
 bobin_sl=0.0
 if I(v10.get('bobin_alt'if g else'bobin_ust'),(int,F)):
  bobin_sl=F(v10['bobin_alt'])-E_ltf*0.18 if g else F(v10['bobin_ust'])+E_ltf*0.18
 ltf_sw_son=0.0
 if I(aj,dict):
  sw_l=aj.get('lows'if g else'highs',[])
  if sw_l:ltf_sw_son=F(sw_l[-1][1])
 ltf_mum_uc=0.0
 ltf_bolge_uc=F(kFlt.get('ltf_yapi_dip_tepe')or 0.0)if I(kFlt,dict)else 0.0
 if aY is not None and L(aY)>=6:
  ltf_mum_uc=F(aY['low'].iloc[-6:].min())-E_ltf*0.25 if g else F(aY['high'].iloc[-6:].max())+E_ltf*0.25
  son_n_ltf=aY.iloc[-16:]if L(aY)>=16 else aY
  if ltf_bolge_uc<=0:
   ltf_bolge_uc=F(son_n_ltf['low'].min())if g else F(son_n_ltf['high'].max())
 s_ob_pull=bool(I(kFlt,dict)and kFlt.get('video_choch_ob_pullback'))
 ltf_yapi_payi=M(E_ltf*0.40,P*0.0020)
 ltf_emniyet_payi=ltf_yapi_payi if s_ob_pull else M(kutu_boyu*0.22,E_ltf*0.35,E_htf*0.15,P*aW)
 min_ltf_mes=M(E_ltf*0.50,P*0.0025)
 max_ltf_mes=M(E_htf*2.6,E_ltf*4.5,P*(0.012 if ISLEM_TARZI_MODU=='Scalp'else 0.030))
 if g:
  if s_ob_pull and 0<ltf_bolge_uc<P:
   # cys2.png Kurgusu: Sarı OB'den girilen işlemde stop doğrudan LTF yapısal LL (0.0762) altına (0.0760) konulur!
   kutu_yakin=(0<fresh_lo<P and(ltf_bolge_uc-fresh_lo)<=E_ltf*1.8)
   baz_dip=N(ltf_bolge_uc,fresh_lo)if kutu_yakin else ltf_bolge_uc
   al_ltf_son=R(baz_dip-ltf_yapi_payi,6)
  else:
   ltf_ham_adaylar=[x for x in(ib_sl,ltf_poi_sl,ltf_itz-E_ltf*0.25 if ltf_itz>0 else 0.0,bobin_sl,ltf_sp-E_ltf*0.2 if ltf_sp>0 else 0.0,ltf_sw_son-E_ltf*0.2 if ltf_sw_son>0 else 0.0,ltf_mum_uc,ltf_pa_sl)if 0<x<P]
   ltf_sec=M(ltf_ham_adaylar)if v12.get('dar_sl_4r')and ib_sl>0 and ib_sl<P else(ltf_poi_sl if 0<ltf_poi_sl<P else(ltf_mum_uc if 0<ltf_mum_uc<P else(N(ltf_ham_adaylar)if ltf_ham_adaylar else P-min_ltf_mes)))
   emniyet_taban_aday=[x for x in(fresh_lo if 0<fresh_lo<P else 0.0,ltf_bolge_uc if 0<ltf_bolge_uc<P else 0.0)if 0<x<P and(P-x)<=max_ltf_mes]
   if emniyet_taban_aday:
    ltf_sec=N(ltf_sec,N(emniyet_taban_aday)-ltf_emniyet_payi)
   mes_ltf=M(min_ltf_mes,N(max_ltf_mes,P-ltf_sec))
   al_ltf_son=R(P-mes_ltf,6)
 else:
  if s_ob_pull and ltf_bolge_uc>P:
   kutu_yakin=(fresh_hi>P and(fresh_hi-ltf_bolge_uc)<=E_ltf*1.8)
   baz_tepe=M(ltf_bolge_uc,fresh_hi)if kutu_yakin else ltf_bolge_uc
   al_ltf_son=R(baz_tepe+ltf_yapi_payi,6)
  else:
   ltf_ham_adaylar=[x for x in(ib_sl,ltf_poi_sl,ltf_itz+E_ltf*0.25 if ltf_itz>0 else 0.0,bobin_sl,ltf_sp+E_ltf*0.2 if ltf_sp>0 else 0.0,ltf_sw_son+E_ltf*0.2 if ltf_sw_son>0 else 0.0,ltf_mum_uc,ltf_pa_sl)if x>P]
   ltf_sec=N(ltf_ham_adaylar)if v12.get('dar_sl_4r')and ib_sl>P else(ltf_poi_sl if ltf_poi_sl>P else(ltf_mum_uc if ltf_mum_uc>P else(M(ltf_ham_adaylar)if ltf_ham_adaylar else P+min_ltf_mes)))
   emniyet_tavan_aday=[x for x in(fresh_hi if fresh_hi>P else 0.0,ltf_bolge_uc if ltf_bolge_uc>P else 0.0)if x>P and(x-P)<=max_ltf_mes]
   if emniyet_tavan_aday:
    ltf_sec=M(ltf_sec,M(emniyet_tavan_aday)+ltf_emniyet_payi)
   mes_ltf=M(min_ltf_mes,N(max_ltf_mes,ltf_sec-P))
   al_ltf_son=R(P+mes_ltf,6)
 if'LTF'in sec_mod and'Otomatik'not in sec_mod:
  return(al_ltf_son,f'LTF Emniyetli Yapısal Stop (2.Görsel: {LTF_PERIYOT} Kırılım/Tepe-Dip + HTF Kutu Dışı Kalkanı)')
 if'Otomatik'in sec_mod:
  ltf_onay_aktif=bool((I(kFlt,dict)and kFlt.get('ltf_herhangi_tetik'))or v12.get('dar_sl_4r')or v13.get('aktif_entry_modeli','Beklemede')!='Beklemede'or ISLEM_TARZI_MODU=='Scalp')
  if ltf_onay_aktif:
   return(al_ltf_son,f'Otomatik -> LTF Emniyetli Stop (2.Görsel: {LTF_PERIYOT} Yapı + Kutu Dışı Kalkanı)')
  return(al_htf,f'Otomatik -> HTF Emniyetli Stop (1.Görsel: {HTF_PERIYOT.upper()} Arz/Talep Kutu Dışı)')
 return(al_htf,f'HTF Emniyetli Yapısal Stop (1.Görsel: {HTF_PERIYOT.upper()} Arz/Talep Kutu Dışı)')
def tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,B='BULLISH'):
 fj=[];bT=[];b2=0;aP['sembol'],Q['sembol'],aj['sembol']=(J,J,J)
 mod2_tum_girisler=('2. Mod'in str(GIRIS_STRATEJI_MODU)or bool(IKINCIL_BOLGE_GIRIS_AKTIF))
 f4h,sl4h,em4h,hN,e4h=poi_ve_bolge_analizi(bS,aP,HTF_PERIYOT.upper(),B);f6,f7,em,q7,e0=poi_ve_bolge_analizi(bw,Q,MTF_PERIYOT.upper(),B);q8,q9,dD,ra,en=poi_ve_bolge_analizi(aY,aj,LTF_PERIYOT,B);b8=f4h+f6+q8
 dn,hK,oa=likidite_smt_analizi(J,bw,aY,Q,B)
 hL,jQ,kj,dh=likidite_ve_sfp_analizi(bw,aY,Q,b8,B);Q['v8_meta']=dh
 for vs in jQ:
  if vs not in hK:hK.append(vs)
 oa.extend(kj)
 eM=sl4h if sl4h is not None else(f7 if f7 is not None else q9);mB_raw,kk,hM,P,al_ltf=ltf_pa_ve_giris_tetikleyici(aY,eM,B)
 son_kapanis_ltf=_f(aY,'close',-1)if L(aY)>0 else(_f(bw,'close',-1)if L(bw)>0 else 1.0)
 P=F(P)if I(P,(int,F))and F(P)>0 else F(son_kapanis_ltf)
 al_ltf=F(al_ltf)if I(al_ltf,(int,F))and F(al_ltf)>0 else R(P*(0.992 if B=='BULLISH'else 1.008),6)
 kFlt=konum_ve_karar_bolgesi_filtresi(bS,bw,aY,aP,Q,aj,f4h,f6,q8,hN,q7,ra,kk,B);Q['konum_meta'],aj['konum_meta']=(kFlt,kFlt)
 if'HTF'in str(STOP_BELIRLEME_MODU)and'Otomatik'not in str(STOP_BELIRLEME_MODU)and kFlt.get('mod1_zorunlu_sart1'):
  f_lo_g,f_hi_g=(F(kFlt.get('fresh_lo',0.0)),F(kFlt.get('fresh_hi',0.0)))
  if f_hi_g>f_lo_g>0:
   P=R(N(M(F(son_kapanis_ltf),f_lo_g),f_hi_g),6)
 oZ=M(e4h,e0,en,F(kFlt.get('aktif_at_guc_10p',0.0)))
 al,stop_kaynak_bilgi=stop_noktasi_belirle(bS,bw,aY,aP,Q,aj,kFlt,P,B,sl4h,f7,q9,al_ltf,STOP_BELIRLEME_MODU)
 kFlt['stop_kaynak_bilgi']=stop_kaynak_bilgi
 chk=kFlt.get('checklist',{})
 hedef_tur_ad='Talep (DBR/RBR)'if B=='BULLISH'else'Arz (RBD/DBD)'
 # 1. ATLI (0-25 Puan): HTF YÖN + GÜÇLÜ FRESH ARZ/TALEP (1.ŞART) + ARA TF UYUM
 if kFlt['htf_yon_ok']:
  b2+=15;fj.append(f"{HTF_PERIYOT.upper()}_YON:{B[:4]}");bT.append(f"✅ 1. Şart [HTF Yön - {HTF_PERIYOT.upper()}]: {aP['kirilim_tipi']} (+15p)")
 else:
  bT.append(f"⬜ 1. Şart [HTF Yön - {HTF_PERIYOT.upper()}]: HTF yönü {aP.get('yon')} ({B} ile uyumsuz) (0p)")
 if kFlt['mtf_yon_onay']:
  b2+=6;fj.append(f"{MTF_PERIYOT.upper()}_ONAY:{B[:4]}");bT.append(f"✅ Ara TF [{MTF_PERIYOT.upper()} Yön Onayı]: {Q['kirilim_tipi']} (+6p)")
 if kFlt['htf_arz_talep_bolgesinde']:
  b2+=4;fj.append(f"HTF_Fresh_{kFlt.get('aktif_at_modu','AT')}")
 b2=N(25,b2)
 # 2. ATLI (0-25 Puan): 1. ŞART (GÜÇLÜ FRESH ARZ/TALEP) + 4 GÜÇ ARTIRICI FAKTÖR (OB, OTE, QML, ALINMAMIŞ LİKİDİTE)
 aO=0
 ik_puan=12 if mod2_tum_girisler else 0
 htf_kriter_log=[
  (f"Ön Koşul: HTF BOS/CHoCH Kaynaklı {hedef_tur_ad}",kFlt['htf_arz_talep_bolgesinde'],f"{kFlt.get('aktif_at_modu','-')} | {chk.get('fresh_aralik','-')} ({kFlt.get('aktif_at_guc_10p',0):.1f}/10p)",15),
  ('Güç 1: HTF OB (Order Block) Bölgesi',kFlt['htf_ob_bolgesinde'],chk.get('ob_aralik','-'),6),
  ('Güç 2: HTF OTE (0.618-0.786) Bölgesi',kFlt['htf_ote_bolgesinde'],chk.get('ote_aralik','-'),5),
  ('Güç 3: HTF FVG (Imbalance) Bölgesi',kFlt.get('htf_fvg_bolgesinde',False),'Aktif FVG',5),
  ('Güç 4: İşlem Yönünde Alınmamış Likidite',kFlt['hedef_yon_likidite_var'],f"{kFlt.get('hedef_yon_likidite_sayisi',0)} Havuz ({chk.get('hedef_yon_likidite_ozet','-')})",N(6,kFlt.get('hedef_yon_likidite_sayisi',0)*3)),
  ('Güç 5: HTF QML Bölgesi',kFlt['htf_qml_bolgesinde'],chk.get('qml_fiyat','-'),4),
  ('BOS Yaptıran Nokta [2.Mod]',bool(mod2_tum_girisler and kFlt['htf_bos_noktasinda']),chk.get('bos_fiyat','-'),ik_puan),
  ('CHoCH Yapılan Nokta [2.Mod]',bool(mod2_tum_girisler and kFlt['htf_choch_noktasinda']),chk.get('choch_fiyat','-'),ik_puan),
  ('ITZ [2.Mod]',bool(mod2_tum_girisler and kFlt['htf_itz_bolgesinde']),chk.get('itz_fiyat','-'),ik_puan),
  ('Magic Line / FL [2.Mod]',bool(mod2_tum_girisler and kFlt['htf_magic_line_bolgesinde']),chk.get('magic_fiyat','-'),ik_puan)
 ]
 for k_ad,k_ok,k_fiyat,k_puan in htf_kriter_log:
  if k_ok and k_puan>0:
   aO+=k_puan;fj.append(f"HTF_{k_ad.split()[0]}");bT.append(f"✅ HTF Kriter [{k_ad}]: Sağlandı ({k_fiyat}) (+{k_puan}p)")
  elif'2.Mod'not in k_ad or mod2_tum_girisler:
   bT.append(f"⬜ HTF Kriter [{k_ad}]: Sağlanmadı ({k_fiyat})")
 if kFlt['mod1_zorunlu_sart1']:
  aO=N(25,M(16+kFlt['mod1_ek_sart_sayisi']*2,aO))
 elif mod2_tum_girisler and(kFlt['htf_oncelikli_bolge_onay']or kFlt['htf_ikincil_bolge_onay']):
  aO=N(25,M(18,aO))
 else:
  aO=0;bT.append(f"⛔ {kFlt['aciklama']}")
 bT.append(f"🛡️ AKTİF MOD [{GIRIS_STRATEJI_MODU}]: 1.Şart(Güçlü A/T)={'✅'if kFlt['mod1_zorunlu_sart1']else'⬜'} | Güç Bölgesi:{kFlt['mod1_ek_sart_sayisi']}/5 (1.OB+2.OTE+3.FVG+4.Liq:{kFlt['hedef_yon_likidite_sayisi']}x+5.QML) -> {kFlt['htf_safe_derecesi']} | Parite Güç Puanı:{kFlt['birincil_olcek_skoru']}/10000p | Stop: {al:.4f}")
 bT.extend([f'HTF/MTF Bölge Detayı: {k}'for k in em4h+em+dD])
 # 3. ATLI (0-25 Puan): 4 EK GÜÇ ŞARTI YOĞUNLUĞU + İŞLEM YÖNÜNDE ALINMAMIŞ LİKİDİTE MIKNATISI + IMBALANCE
 ek_sart_puan=kFlt['mod1_ek_sart_sayisi']*4+(4 if kFlt['mod1_zorunlu_sart1']else(kFlt['htf_ikincil_bolge_sayisi']*4 if(mod2_tum_girisler and kFlt['htf_ikincil_bolge_onay'])else 0))
 alinmamis_liq_puan=N(10,kFlt['hedef_yon_likidite_sayisi']*3+int(R(kFlt['hedef_yon_likidite_agirlik'],0)))
 imb_puan=N(5,kFlt['htf_imbalance_sayisi']*2)
 dn_toplam=N(25,ek_sart_puan+alinmamis_liq_puan+imb_puan)
 fj.extend(hK);bT.extend([f'Likidite/SMT Detayı: {k}'for k in oa])
 # 4. ATLI (0-25 Puan): LTF İŞLEME GİRİŞ STRATEJİLERİ (ARZ/TALEP, OB, FVG/IMBALANCE, LİKİDİTE, QML, MUM & KIRILIM)
 mB=0
 if kFlt['ltf_arz_talep_onay']:
  mB+=6;fj.append(f"{LTF_PERIYOT}_ArzTalep");bT.append(f"✅ LTF Giriş [Arz/Talep Bölgesi]: {', '.join(kFlt['ltf_arz_talep_listesi'][:2])} (+6p)")
 if kFlt['ltf_ob_onay']:
  mB+=6;fj.append(f"{LTF_PERIYOT}_OB");bT.append(f"✅ LTF Giriş [Order Block (OB)]: {', '.join(kFlt['ltf_ob_listesi'][:2])} (+6p)")
 if kFlt['ltf_fvg_imbalance_onay']:
  mB+=5;fj.append(f"{LTF_PERIYOT}_FVG_Imb");bT.append(f"✅ LTF Giriş [FVG / Imbalance]: {', '.join(kFlt['ltf_fvg_listesi'][:2])} (+5p)")
 if kFlt['ltf_likidite_onay']:
  mB+=7;fj.append(f"{LTF_PERIYOT}_Likidite");bT.append(f"✅ LTF Giriş [Likidite Sweep / SFP]: {', '.join(kFlt['ltf_likidite_listesi'][:2])} (+7p)")
 if kFlt['ltf_qml_onay']:
  mB+=7;fj.append(f"{LTF_PERIYOT}_QML");bT.append(f"✅ LTF Giriş [LTF QML / MPL]: {', '.join(kFlt['ltf_qml_listesi'][:2])} (+7p)")
 if kFlt['ltf_reversal_kirilim_onay']:
  mB+=10;fj.append(f"{LTF_PERIYOT}_Kirilim");bT.append(f"✅ LTF Giriş [Yapı Kırılımı CHoCH/BOS]: {', '.join(kFlt['ltf_kirilim_listesi'][:3])} (+10p)")
 if kFlt['ltf_reversal_mum_onay']:
  mB+=10;fj.append(f"{LTF_PERIYOT}_Mum");bT.append(f"✅ LTF Giriş [Mum Stratejileri]: {', '.join(kFlt['ltf_mum_listesi'][:3])} (+10p)")
 if not kFlt['ltf_herhangi_tetik']:
  mB=0
  bT.append(f"⛔ LTF Giriş Kontrolü: LTF'de (Arz/Talep, OB, FVG, Likidite, QML, Mum/Kırılım) henüz giriş emaresi YOK -> İşleme girilmez!")
 elif not kFlt['htf_zorunlu_bolge_onay']:
  mB=N(6,mB)
 else:
  mB=N(25,M(14,mB))
 kural_ozet_str=f"{GIRIS_STRATEJI_MODU.split(':')[0]} | HTF Bölge:{'OK'if kFlt['htf_zorunlu_bolge_onay']else'YOK'} | Fresh:{'OK'if kFlt['mod1_zorunlu_sart1']else'YOK'} | Güç:{kFlt['mod1_ek_sart_sayisi']}/5 | Liq:{kFlt['hedef_yon_likidite_sayisi']}x | LTF Emare:{kFlt['ltf_giris_emare_sayisi']}"
 bT.insert(0,f"📊 [{GIRIS_STRATEJI_MODU.split(':')[0]} ÖZETİ]: 1.Şart(HTF Yön+Güçlü A/T):{'✅ '+kFlt.get('aktif_at_modu','-')if kFlt['mod1_zorunlu_sart1']else'⬜ Yok'} | 5 Güç Bölgesi ({kFlt['mod1_ek_sart_sayisi']}/5): {'+'.join(kFlt['aktif_htf_bolgeler'])or'Yok'} | LTF Giriş Emaresi ({kFlt['ltf_giris_emare_sayisi']}): {'✅ '+'+'.join(kFlt['aktif_ltf_tetikler'][:3])if kFlt['ltf_herhangi_tetik']else'⬜ Yok (Girilmez)'}")
 bT.extend([f'LTF Mum/PA Detayı: {k}'for k in hM])
 fj.insert(0,f"Güç:{kFlt['birincil_olcek_skoru']}p({kFlt['mod1_ek_sart_sayisi']}/5)")
 fj.extend(b8);fj.extend(kk)
 olcek_carp=M(0.8,F(BIRINCIL_BOLGE_OLCEK_CARPANI)/5.0)
 birincil_olcek_bonusu=int(R((8+kFlt['mod1_ek_sart_sayisi']*5+N(6,kFlt['hedef_yon_likidite_sayisi']*2))*olcek_carp,0))if(kFlt['mod1_zorunlu_sart1']and kFlt['ltf_herhangi_tetik'])else(10 if(mod2_tum_girisler and kFlt['htf_zorunlu_bolge_onay']and kFlt['ltf_herhangi_tetik'])else 0)
 nO=N(100,b2+aO+dn_toplam+mB+birincil_olcek_bonusu)
 if not kFlt['htf_zorunlu_bolge_onay']:
  nO=N(45,nO)
  di=f"🔭 Güçlü A/T Pusuda ({kFlt.get('en_yakin_birincil_atr',9.9):.1f}x ATR)"if kFlt.get('birincil_pusuda_onay')else f"HTF Güçlü Fresh A/T Dışı ({GIRIS_STRATEJI_MODU.split(':')[0]})"
 elif kFlt['ltf_herhangi_tetik']:
  if kFlt['mod1_zorunlu_sart1']:
   nO=N(100,M(nO,MIN_CONFLUENCE_SKORU+2+kFlt['mod1_ek_sart_sayisi']*5+N(6,kFlt['hedef_yon_likidite_sayisi']*2)))
   di=f"🔥 1.MOD [{kFlt.get('aktif_at_modu','AT')} + {kFlt['mod1_ek_sart_sayisi']}/5 Güç | {kFlt['birincil_olcek_skoru']}p] + {'/'.join(kFlt['aktif_ltf_tetikler'][:2])}"
  elif mod2_tum_girisler and kFlt['htf_zorunlu_bolge_onay']:
   if kFlt['htf_yon_ok']:
    nO=N(100,M(nO,MIN_CONFLUENCE_SKORU+2+kFlt['htf_bolge_sayisi']*3))
   di=f"🧭 2.MOD [{'+'.join(kFlt['aktif_htf_bolgeler'][:3])}] + {'/'.join(kFlt['aktif_ltf_tetikler'][:2])}"
  else:
   nO=N(45,nO)
   di=f"HTF Bölge Dışı ({GIRIS_STRATEJI_MODU.split(':')[0]})"
 else:
  # HTF Güçlü Fresh Arz/Talep bölgesinde ama LTF'de giriş emaresi YOK -> Skor eşik altında tutulur ve BEKLE kalır!
  nO=N(M(58 if kFlt['mod1_zorunlu_sart1']else 46,MIN_CONFLUENCE_SKORU-3),nO)
  di=(f"🎯 1.MOD GÜÇLÜ A/T [{kFlt.get('aktif_at_modu','AT')} | {kFlt['mod1_ek_sart_sayisi']}/5 Güç | {kFlt['birincil_olcek_skoru']}p] -> {LTF_PERIYOT} Giriş Emaresi Bekleniyor"if kFlt['mod1_zorunlu_sart1']else f"🧭 2.Mod Bölgede ({'+'.join(kFlt['aktif_htf_bolgeler'][:3])}) -> {LTF_PERIYOT} Onay Bekleniyor")
 dX=aj.get('v10_meta',Q.get('v10_meta',{}));dX['giris_onay_tipi']='+'.join(kFlt['aktif_ltf_tetikler'])if kFlt['aktif_ltf_tetikler']else'Beklemede'
 return{'hedef_yon':B,'skor':nO,'bolge_10p_skor':oZ,'giris_modeli':di,'atli_puanlar':(b2,aO,dn_toplam,mB),'giris':P,'sl':al,'detay_etiketleri':fj,'detayli_kurallar':bT,'kutular':ra+q7[:2],'kutular_15m':ra,'kutular_1h':q7,'kutular_4h':hN,'poi_4h':f4h,'poi_1h':f6,'poi_15m':q8,'konum_meta':kFlt,'uygun_kural_sayisi':kFlt['htf_bolge_sayisi'],'uygun_alt_kural_sayisi':kFlt['saglanan_alt_kural_sayisi'],'kural_ozeti':kural_ozet_str}
def mahserin_4_atlisi_confluence_analizi(J,bS,bw,aY,D=None):
 jR=D if D else'spot'if PIYASA_MODU=='spot'else'future';aP=market_yapisi_ve_fibo_analizi(bS);Q=market_yapisi_ve_fibo_analizi(bw);aj=market_yapisi_ve_fibo_analizi(aY,n=2)
 mod1_sadece_birincil=('1. Mod'in str(GIRIS_STRATEJI_MODU)or not IKINCIL_BOLGE_GIRIS_AKTIF)
 if mod1_sadece_birincil:
  if aP.get('yon')=='BULLISH':
   dQ=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BULLISH')
  elif aP.get('yon')=='BEARISH'and jR=='future':
   dQ=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BEARISH')
  else:
   dQ=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BULLISH')
   dQ['skor']=min(dQ.get('skor',0),45)
 else:
  if jR!='future'or aP['yon']=='BULLISH':
   dQ=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BULLISH')
  elif aP['yon']=='BEARISH':
   dQ=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BEARISH')
  else:
   o5=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BULLISH');qe,qf=(dict(Q),dict(aj));rc=tek_yon_4_atli_hesapla(J,bS,bw,aY,aP,Q,aj,'BEARISH')
   if rc['skor']>o5['skor']:dQ=rc
   else:dQ=o5;Q.update(qe);aj.update(qf)
 iy=dQ['hedef_yon'];p1,p2,p3,p4=dQ['atli_puanlar'];nO=dQ['skor'];kFlt=dQ.get('konum_meta',{'konum_onay':False,'htf_zorunlu_bolge_onay':False,'saglanan_giris_sart_sayisi':0});kysy_ok=bool(aP.get('kysy_onay',True))
 if aP['yon']=='BEARISH'and Q['yon']=='BEARISH':mC='BEARISH'
 elif aP['yon']=='BULLISH'and Q['yon']=='BULLISH':mC='BULLISH'
 else:mC=aP['yon']if aP['yon']in('BULLISH','BEARISH')else iy
 mod1_sadece_birincil=('1. Mod'in str(GIRIS_STRATEJI_MODU)or not IKINCIL_BOLGE_GIRIS_AKTIF)
 # Her iki modda da mod1_zorunlu_sart1 (HTF Arz/Talep bölgesinde olmak) zorunlu ön koşuldur:
 htf_bolge_ve_ltf_onay_ok=bool(kFlt.get('htf_zorunlu_bolge_onay',False)and kFlt.get('ltf_herhangi_tetik',False)and kFlt.get('ltf_giris_emare_sayisi',0)>=1)
 aU='BEKLE'
 ltf_yon_m=aj.get('yon','NOTR')if I(aj,dict)else'NOTR'
 ltf_bos_yon_m=aj.get('kysy_meta',{}).get('son_kirilim_yon','NOTR')if I(aj,dict)else'NOTR'
 ltf_uyum_m=bool(kFlt.get('ltf_yon_uyumlu',True)and((ltf_yon_m!='BEARISH'and ltf_bos_yon_m!='BEARISH')if iy=='BULLISH'else(ltf_yon_m!='BULLISH'and ltf_bos_yon_m!='BULLISH')))
 if not ltf_uyum_m:
  nO=N(58,nO);dQ['skor']=nO;htf_bolge_ve_ltf_onay_ok=False
 if htf_bolge_ve_ltf_onay_ok and ltf_uyum_m and kysy_ok and(nO>=MIN_CONFLUENCE_SKORU):
  if iy=='BULLISH'and aP['yon']=='BULLISH':aU='LONG';mC='BULLISH'
  elif iy=='BEARISH'and jR=='future'and aP['yon']=='BEARISH':aU='SHORT';mC='BEARISH'
 dY=' + '.join(dQ['detay_etiketleri'][:5])if dQ['detay_etiketleri']else'Kurulum Bekleniyor';hN=dQ.get('kutular_4h')or poi_ve_bolge_analizi(bS,aP,HTF_PERIYOT.upper(),iy)[3];o6={'sembol':J,'piyasa':jR,'htf_periyot':HTF_PERIYOT,'mtf_periyot':MTF_PERIYOT,'ltf_periyot':LTF_PERIYOT,'mtf_sablonu':AKTIF_MTF_SABLONU,'yon_4h':aP['yon'],'yon_1h':Q['yon'],'ana_yon':mC,'skor':nO,'bolge_10p_skor':dQ['bolge_10p_skor'],'giris_modeli':dQ['giris_modeli'],'atli_puanlar':dQ['atli_puanlar'],'sinyal':aU,'giris':dQ['giris'],'sl':dQ['sl'],'ozet':dY,'detayli_kurallar':dQ['detayli_kurallar'],'df_4h_full':bS,'df_1h_full':bw,'df_15m_full':aY,'df_4h':bS,'df_1h':bw,'df_5m':aY,'df_15m':aY,'yapi_4h':aP,'yapi_1h':Q,'yapi_5m':aj,'yapi_15m':aj,'kutular_4h':hN,'kutular_1h':dQ.get('kutular_1h',[]),'kutular_5m':dQ['kutular'],'cizim_kutulari_4h':hN,'cizim_kutulari_1h':dQ.get('kutular_1h',[]),'cizim_kutulari_15m':dQ['kutular'],'cizim_kutulari_ltf_saf':dQ.get('kutular_15m',[]),'fibo_oran':Q['fibo_oran'],'fibo_hedefleri':Q['fibo_hedefleri'],'wyckoff_fazi':Q.get('wyckoff_fazi','TREND_IMPULSIVE'),'strong_point':Q.get('strong_point'),'weak_point':Q.get('weak_point'),'uc_istasyon':Q.get('uc_istasyon',{}),'internal_choch':aj.get('internal_choch','YOK'),'fl_dp_meta':Q.get('fl_dp_meta',{}),'qm_meta':aj.get('qm_meta',Q.get('qm_meta',{})),'v6_meta':aj.get('v6_meta',Q.get('v6_meta',{})),'v7_meta':Q.get('v7_meta',aj.get('v7_meta',{})),'v8_meta':Q.get('v8_meta',{}),'v9_meta':aj.get('v9_meta',Q.get('v9_meta',{})),'v10_meta':aj.get('v10_meta',Q.get('v10_meta',{})),'v11_meta':aj.get('v11_meta',Q.get('v11_meta',{})),'v12_meta':aj.get('v12_meta',Q.get('v12_meta',{})),'v13_meta':aj.get('v13_meta',Q.get('v13_meta',{})),'konum_meta':kFlt,'kysy_4h':aP.get('kysy_meta',{}),'kysy_1h':Q.get('kysy_meta',{}),'kysy_ltf':aj.get('kysy_meta',{}),'_ts_mem':time.time()};O=anahtar_yap(J,jR);analiz_hafizasi[O]=o6
 df_tutulan=[k_m for k_m,v_m in analiz_hafizasi.items()if I(v_m,dict)and'df_15m'in v_m and not I(acik_islemler.get(k_m),dict)]
 if L(df_tutulan)>24:
  df_tutulan.sort(key=lambda k_m:F(analiz_hafizasi[k_m].get('_ts_mem',0.0)))
  for eski_k in df_tutulan[:-18]:
   eski_d=analiz_hafizasi.get(eski_k)
   if I(eski_d,dict):
    for df_k_sil in('df_4h_full','df_1h_full','df_15m_full','df_4h','df_1h','df_15m'):eski_d.pop(df_k_sil,None)
 return o6
def tek_tf_canli_pa_analizi(J,bN,D='future',B=None,limit=300):
 lV=veri_cek(J,bN,limit,D);k8=market_yapisi_ve_fibo_analizi(lV,n=SWING_PENCERE);iy=B if B in('BULLISH','BEARISH')else k8['yon']if k8['yon']in('BULLISH','BEARISH')else'BULLISH';dP,ob,K,az,mD=poi_ve_bolge_analizi(lV,k8,bN.upper(),iy);_,_,_,dh=likidite_ve_sfp_analizi(lV,lV,k8,dP,iy);k8['v8_meta']=dh;return{'df_full':lV,'yapi':k8,'kutular':az,'poi_list':dP,'kurallar':K,'bolge_10p_skor':mD,'hedef_yon':iy}
def puana_gore_risk_hesapla(mN=0):
 return R(M(0.1,F(ISLEM_BASI_RISK_USDT)),2)
def dinamik_miktar_hesapla(J,P,al,D=None,mN=0):
 jR=D if D else'spot'if PIYASA_MODU=='spot'else'future';cv=veri_ist(jR);nP=M(A(P-al),P*1e-05)
 o7=KALDIRAC if jR=='future'else 1;aktif_risk=puana_gore_risk_hesapla(mN);lW=aktif_risk/nP;dZ=lW*P;fk=dZ/M(o7,1)
 if MAKS_MARJIN_USDT>0 and fk>MAKS_MARJIN_USDT:
  fk=F(MAKS_MARJIN_USDT);dZ=fk*M(o7,1);lW=dZ/M(P,1e-09)
 if dZ<5.5:
  dZ=5.5;fk=dZ/M(o7,1);lW=dZ/M(P,1e-09)
 raw_s=str(J).split(':')[0].replace('/','').upper()
 if jR=='future':
  q_s,_=_fapi_hassasiyet_formatla(raw_s,lW,None)
  try:Y=F(q_s)
  except X:Y=R(lW,6)
 else:
  try:Y=F(cv.amount_to_precision(J,lW))
  except X:Y=R(lW,6)
 if Y<=0 and lW>0:Y=M(R(lW,6),1e-06)
 fk=(Y*P)/M(o7,1)
 do=R(A(P-al)*Y,2);return(Y,fk,do)
def _parite_mtf_periyotlarini_bul(O_key=None,J=None,D='future',H_mevcut=None):
 dR=acik_islemler.get(O_key)if O_key else None
 if not I(dR,dict)and J:
  dR=acik_islemler.get(anahtar_yap(J,D))or acik_islemler.get(f"FUT:{J}")or acik_islemler.get(f"SPOT:{J}")
 if I(dR,dict):
  hp=str(dR.get('htf_periyot')or(H_mevcut.get('htf_periyot')if I(H_mevcut,dict)else None)or HTF_PERIYOT)
  mp=str(dR.get('mtf_periyot')or(H_mevcut.get('mtf_periyot')if I(H_mevcut,dict)else None)or MTF_PERIYOT)
  lp=str(dR.get('ltf_periyot')or(H_mevcut.get('ltf_periyot')if I(H_mevcut,dict)else None)or LTF_PERIYOT)
  sb=str(dR.get('mtf_sablonu')or f"{hp} / {mp} / {lp}")
  return(hp,mp,lp,sb)
 hp=str((H_mevcut.get('htf_periyot')if I(H_mevcut,dict)else None)or HTF_PERIYOT)
 mp=str((H_mevcut.get('mtf_periyot')if I(H_mevcut,dict)else None)or MTF_PERIYOT)
 lp=str((H_mevcut.get('ltf_periyot')if I(H_mevcut,dict)else None)or LTF_PERIYOT)
 sb=str((H_mevcut.get('mtf_sablonu')if I(H_mevcut,dict)else None)or AKTIF_MTF_SABLONU)
 return(hp,mp,lp,sb)
def pine_icin_4h_1h_5m_veri_hazirla(J,D='future',H_mevcut=None,O_key=None):
 htf_p,mtf_p,ltf_p,mtf_sb=_parite_mtf_periyotlarini_bul(O_key,J,D,H_mevcut)
 b4h=H_mevcut.get('df_4h_full')if H_mevcut and H_mevcut.get('htf_periyot')==htf_p and'df_4h_full'in H_mevcut else None
 b1h=H_mevcut.get('df_1h_full')if H_mevcut and H_mevcut.get('mtf_periyot')==mtf_p and'df_1h_full'in H_mevcut else None
 b5m=H_mevcut.get('df_15m_full')if H_mevcut and H_mevcut.get('ltf_periyot')==ltf_p and'df_15m_full'in H_mevcut else None
 try:
  if b4h is None:b4h=veri_cek(J,htf_p,300,D)
 except X:b4h=H_mevcut.get('df_4h_full')if H_mevcut else None
 try:
  if b1h is None:b1h=veri_cek(J,mtf_p,300,D)
 except X:b1h=H_mevcut.get('df_1h_full')if H_mevcut else None
 try:
  if b5m is None:b5m=veri_cek(J,ltf_p,300,D)
 except X:b5m=H_mevcut.get('df_15m_full')if H_mevcut else None
 if b4h is None or b1h is None or b5m is None:return H_mevcut or{}
 y4=market_yapisi_ve_fibo_analizi(b4h);y1=market_yapisi_ve_fibo_analizi(b1h);y5=market_yapisi_ve_fibo_analizi(b5m,n=2)
 if y4.get('yon')=='BEARISH'and D=='future':
  dQ=tek_yon_4_atli_hesapla(J,b4h,b1h,b5m,y4,y1,y5,'BEARISH')
 elif y4.get('yon')=='BULLISH':
  dQ=tek_yon_4_atli_hesapla(J,b4h,b1h,b5m,y4,y1,y5,'BULLISH')
 else:
  dQ=tek_yon_4_atli_hesapla(J,b4h,b1h,b5m,y4,y1,y5,'BULLISH'if D!='future'else'BEARISH')
  dQ['skor']=min(dQ.get('skor',0),45)
 iy=dQ['hedef_yon'];p1,p2,p3,p4=dQ['atli_puanlar'];nO=dQ['skor'];kFlt=dQ.get('konum_meta',{'konum_onay':False,'htf_zorunlu_bolge_onay':False,'saglanan_giris_sart_sayisi':0});kysy_ok=bool(y4.get('kysy_onay',True))
 htf_bolge_kesin_ok=bool(kFlt.get('htf_zorunlu_bolge_onay',False)and kFlt.get('ltf_herhangi_tetik',False)and kFlt.get('saglanan_giris_sart_sayisi',0)>=1)
 aU='LONG'if(htf_bolge_kesin_ok and kysy_ok and nO>=MIN_CONFLUENCE_SKORU and iy=='BULLISH'and y4['yon']=='BULLISH')else'SHORT'if(D=='future'and htf_bolge_kesin_ok and kysy_ok and nO>=MIN_CONFLUENCE_SKORU and iy=='BEARISH'and y4['yon']=='BEARISH')else'BEKLE'
 return{'sembol':J,'piyasa':D,'htf_periyot':htf_p,'mtf_periyot':mtf_p,'ltf_periyot':ltf_p,'mtf_sablonu':mtf_sb,'yon_4h':y4['yon'],'yon_1h':y1['yon'],'yon_5m':y5['yon'],'ana_yon':iy,'skor':nO,'bolge_10p_skor':dQ['bolge_10p_skor'],'giris_modeli':dQ['giris_modeli'],'atli_puanlar':dQ['atli_puanlar'],'sinyal':aU,'giris':dQ['giris']or _f(b5m,'close',-1),'sl':dQ['sl'],'df_4h_full':b4h,'df_1h_full':b1h,'df_15m_full':b5m,'df_4h':b4h,'df_1h':b1h,'df_5m':b5m,'df_15m':b5m,'yapi_4h':y4,'yapi_1h':y1,'yapi_5m':y5,'yapi_15m':y5,'kutular_4h':dQ.get('kutular_4h',[]),'kutular_1h':dQ.get('kutular_1h',[]),'kutular_5m':dQ.get('kutular_15m',[]),'cizim_kutulari_4h':dQ.get('kutular_4h',[]),'cizim_kutulari_1h':dQ.get('kutular_1h',[]),'cizim_kutulari_15m':dQ.get('kutular_15m',[]),'konum_meta':kFlt,'detayli_kurallar':dQ.get('detayli_kurallar',[])}
def pine_script_uret_4h_1h_5m(O,tf_secim='4h',H_ozel=None):
 H=H_ozel or analiz_hafizasi.get(O)or analiz_hafizasi.get(str(O).split(':',1)[-1])or{}
 J=H.get('sembol',str(O).split(':',1)[-1]);D=H.get('piyasa','spot'if str(O).startswith('SPOT:')else'future');tv_sym=J.split(':')[0].replace('/','')+('.P'if D=='future'else'')
 htf_p,mtf_p,ltf_p,_=_parite_mtf_periyotlarini_bul(O,J,D,H)
 if tf_secim in('4h',htf_p):
  tf_secim='4h';gercek_tf=htf_p;df=H.get('df_4h',H.get('df_4h_full'));yp=H.get('yapi_4h',{});kt=H.get('kutular_4h',H.get('cizim_kutulari_4h',[]));tf_lbl=f'{htf_p.upper()} (HTF Ana Yapı & Major Arz/Talep POI)';tv_tf=htf_p
 elif tf_secim in('1h',mtf_p):
  tf_secim='1h';gercek_tf=mtf_p;df=H.get('df_1h',H.get('df_1h_full'));yp=H.get('yapi_1h',{});kt=H.get('kutular_1h',H.get('cizim_kutulari_1h',[]));tf_lbl=f'{mtf_p.upper()} (MTF Konum Filtresi & İstasyonlar)';tv_tf=mtf_p
 else:
  tf_secim='5m';gercek_tf=ltf_p;df=H.get('df_5m',H.get('df_15m_full'));yp=H.get('yapi_5m',H.get('yapi_15m',{}));kt=H.get('kutular_5m',H.get('cizim_kutulari_15m',[]));tf_lbl=f'{ltf_p} (LTF İcra, Reversal Onay & Giriş/SL/TP)';tv_tf=ltf_p
 sp=F(yp.get('strong_point')or H.get('strong_point')or 0.0);wp=F(yp.get('weak_point')or H.get('weak_point')or 0.0)
 ist=yp.get('uc_istasyon',H.get('uc_istasyon',{}));fl_m=yp.get('fl_dp_meta',H.get('fl_dp_meta',{}));qm_m=yp.get('qm_meta',H.get('qm_meta',{}))
 magic=F(fl_m.get('magic_line')or ist.get('FL')or 0.0);itz=F(ist.get('ITZ')or 0.0);qml=F(yp.get('qml_seviyesi')or qm_m.get('qml_seviyesi')or 0.0)
 smax=F(yp.get('swing_max')or 0.0);smin=F(yp.get('swing_min')or 0.0)
 dR=acik_islemler.get(O)
 aktif_sinyal_p=bool(I(dR,dict)or H.get('sinyal')in('LONG','SHORT'))
 giris=F(dR['giris']if I(dR,dict)else(H.get('giris')if aktif_sinyal_p else 0.0))
 sl=F(dR['sl']if I(dR,dict)else(H.get('sl')if aktif_sinyal_p else 0.0))
 rk=A(giris-sl)if giris>0 and sl>0 else 0.0
 yon_s=dR['yon']if I(dR,dict)else(H.get('sinyal')if H.get('sinyal')in('LONG','SHORT')else(H.get('ana_yon','LONG')))
 mO=-1.0 if yon_s in('SHORT','BEARISH')else 1.0
 etkin_rr_p=F((H.get('konum_meta',{})if I(H,dict)else{}).get('etkin_rr_orani')or RISK_ODUL_ORANI)
 tp1=F(dR['tp']if I(dR,dict)else(giris+mO*rk*etkin_rr_p if(aktif_sinyal_p and rk>0)else 0.0))
 tp2=F(dR.get('tp_nihai',tp1)if I(dR,dict)else(giris+mO*rk*M(NIHAI_TP_RR,RISK_ODUL_ORANI+1.0)if(aktif_sinyal_p and rk>0)else 0.0))
 chk_txt=_karne_checklist_olustur(H,html_mi=False,yorum_on_eki='//')
 return(
  f"//@version=6\n"
  f"// ALFA TRADE CLUB [{BOT_VERSIYONU}] — {O} ({tv_sym}) | {tf_lbl}\n"
  f"// Aktif Mod: {GIRIS_STRATEJI_MODU} | Maks Açık İşlem: {a4}\n"
  f"{chk_txt}"
  f"indicator(\"Alfa PA {BOT_VERSIYONU} - {O} [{gercek_tf.upper()}]\", overlay=true, max_boxes_count=50, max_lines_count=50)\n"
  f"var float bot_sp = {sp:.6f}\n"
  f"var float bot_wp = {wp:.6f}\n"
  f"var float bot_magic = {magic:.6f}\n"
  f"var float bot_itz = {itz:.6f}\n"
  f"var float bot_qml = {qml:.6f}\n"
  f"var float bot_smax = {smax:.6f}\n"
  f"var float bot_smin = {smin:.6f}\n"
  f"var float bot_giris = {giris:.6f}\n"
  f"var float bot_sl = {sl:.6f}\n"
  f"var float bot_tp1 = {tp1:.6f}\n"
  f"var float bot_tp2 = {tp2:.6f}\n"
  f"plot(bot_giris > 0 ? bot_giris : na, \"Giriş\", color=color.aqua, linewidth=2)\n"
  f"plot(bot_sl > 0 ? bot_sl : na, \"Stop-Loss (1R)\", color=color.red, linewidth=2)\n"
  f"plot(bot_tp1 > 0 ? bot_tp1 : na, \"TP1 ({RISK_ODUL_ORANI}R)\", color=color.green, linewidth=2)\n"
  f"plot(bot_tp2 > 0 ? bot_tp2 : na, \"TP2 ({NIHAI_TP_RR}R)\", color=color.lime, linewidth=1)\n"
  f"plot(bot_qml > 0 ? bot_qml : na, \"QML\", color=color.purple, linewidth=2)\n"
 )
def _df_to_tv_json(df,yp,kt,tf_kodu='4h',htf_aktif_bolge=None):
 mum_list=[];zz_list=[];elenen_list=[];bos_list=[];kutu_list=[];arz_talep_list=[];ob_list=[];imbalance_list=[];liq_list=[];sfp_list=[]
 if df is None or L(df)<5:return{'mumlar':mum_list,'zigzag':zz_list,'elenen':elenen_list,'bos':bos_list,'kutular':kutu_list,'arz_talep':arz_talep_list,'ob_bolgeleri':ob_list,'imbalance':imbalance_list,'likidite':liq_list,'sfp':sfp_list}
 oc=M(0,L(df)-300)
 df_c=df.iloc[oc:].reset_index(drop=True)
 ct=L(df_c)
 ts_arr=[]
 son_t=0
 for idx,r in df_c.iterrows():
  ts_s=int(F(r['timestamp'])/1000)if'timestamp'in df_c.columns and F(r['timestamp'])>0 else(1700000000+int(idx)*300)
  if ts_s<=son_t:ts_s=son_t+60
  son_t=ts_s;ts_arr.append(ts_s)
  mum_list.append({'time':ts_s,'idx':int(idx),'open':F(r['open']),'high':F(r['high']),'low':F(r['low']),'close':F(r['close'])})
 E=M(_f(df_c,'atr',-2)if'atr'in df_c.columns else _f(df_c,'close',-1)*0.003,_f(df_c,'close',-1)*0.001)
 try:
  n_sw=2 if tf_kodu=='5m'else SWING_PENCERE
  uH,uL,kysy_m=kirilim_yoksa_swing_yoktur_analizi(df_c,n_sw)
  zz_raw=sorted([(i,v,'H')for i,v in uH]+[(i,v,'L')for i,v in uL],key=lambda x:x[0])
  prev_h=None;prev_l=None
  for idx_z,(i,v,tip)in enumerate(zz_raw):
   if 0<=i<L(ts_arr):
    if tip=='H':lbl='HH'if prev_h is None or v>=prev_h else'LH';prev_h=v
    else:
     if prev_l is None:lbl='LL'if(idx_z>0 and zz_raw[idx_z-1][2]=='H')else'HL'
     else:lbl='HL'if v>=prev_l else'LL'
     prev_l=v
    zz_list.append({'time':ts_arr[i],'idx':int(i),'value':F(v),'tip':tip,'lbl':lbl})
  for b_i,lvl,o_i,o_v,yon_b,ktip in kysy_m.get('bos_list',[]):
   if 0<=b_i<L(ts_arr):
    s_i=M(0,N(L(ts_arr)-1,int(o_i)))
    bos_list.append({'t1':ts_arr[s_i],'t2':ts_arr[b_i],'idx1':int(s_i),'idx2':int(b_i),'price':F(lvl),'yon':yon_b,'tip':ktip,'orig_idx':int(s_i),'orig_val':F(o_v)})
 except X:pass
 try:
  arz_talep_list,imbalance_list=_arz_talep_ve_imbalance_sablon_hesapla(df_c,ts_arr,bos_list,E,kysy_m.get('qml_seviyesi')if'kysy_m'in locals()else None)
 except X:pass
 if I(htf_aktif_bolge,dict)and F(htf_aktif_bolge.get('hi',0))>F(htf_aktif_bolge.get('lo',0))>0:
  h_lo,h_hi=(F(htf_aktif_bolge['lo']),F(htf_aktif_bolge['hi']))
  h_tur=str(htf_aktif_bolge.get('tur','TALEP'))
  var_mi=any(z.get('tur')==h_tur and M(F(z['lo']),h_lo)<=N(F(z['hi']),h_hi)+E*0.10 for z in arz_talep_list)
  if not var_mi:
   h_idx=M(0,N(ct-5,int(htf_aktif_bolge.get('idx1',ct-45))))
   h_et=str(htf_aktif_bolge.get('etiket',f"HTF {h_tur.title()} [Taze]"))
   if tf_kodu!='4h'and'HTF'not in h_et:h_et=f"[HTF] {h_et}"
   arz_talep_list.append({'tur':h_tur,'alt_tur':htf_aktif_bolge.get('alt_tur','VALID_DEMAND'if h_tur=='TALEP'else'VALID_SUPPLY'),'mod':htf_aktif_bolge.get('mod','DBR'if h_tur=='TALEP'else'RBD'),'idx1':h_idx,'t1':ts_arr[h_idx],'lo':h_lo,'hi':h_hi,'eq':(h_lo+h_hi)/2.0,'taze':True,'guclu_fresh':True,'ob_mi':bool(htf_aktif_bolge.get('ob_mi',False)),'guc_10p':F(htf_aktif_bolge.get('guc_10p',8.5)),'etiket':h_et})
 for z_ob in arz_talep_list:
  if z_ob.get('ob_mi',False)or z_ob.get('alt_tur')=='REVERSAL_OB':
   yon_ob='BULL'if z_ob.get('tur')=='TALEP'else'BEAR'
   ob_et=str(z_ob.get('ob_etiket')or f"{'Bull'if yon_ob=='BULL'else'Bear'} OB ({z_ob.get('mod','OB')}) [{z_ob.get('guc_10p',8.0)}/10]")
   ob_list.append({'yon':yon_ob,'idx1':int(z_ob.get('idx1',0)),'t1':z_ob.get('t1'),'lo':F(z_ob['lo']),'hi':F(z_ob['hi']),'eq':F(z_ob.get('eq',(z_ob['lo']+z_ob['hi'])/2.0)),'taze':bool(z_ob.get('taze',True)),'etiket':ob_et})
 for ktip,b_idx,lo,hi in(kt or[])[:6]:
  ns=M(0,N(ct-4,int(b_idx)-oc))if I(b_idx,(int,np.integer))else M(0,ct-35)
  kutu_list.append({'tip':str(ktip),'idx1':int(ns),'t1':ts_arr[ns],'lo':F(lo),'hi':F(hi)})
  if'OB'in str(ktip).upper()or'BB'in str(ktip).upper():
   lo_f,hi_f=(F(lo),F(hi))
   if hi_f>lo_f>0 and not any(M(F(o['lo']),lo_f)<=N(F(o['hi']),hi_f)+E*0.12 for o in ob_list):
    yon_k='BEAR'if'BEAR'in str(ktip).upper()else'BULL'
    ob_list.append({'yon':yon_k,'idx1':int(ns),'t1':ts_arr[ns],'lo':lo_f,'hi':hi_f,'eq':(lo_f+hi_f)/2.0,'taze':True,'etiket':f"{'Bull'if yon_k=='BULL'else'Bear'} Order Block (OB)"})
 try:
  liq_list,sfp_list,_=_likidite_ve_sfp_yapilarini_bul(df_c,uH if'uH'in locals()else None,uL if'uL'in locals()else None,ts_arr)
 except X:pass
 q_idx_tv=kysy_m.get('qml_idx')if'kysy_m'in locals()else None
 q_t1_tv=ts_arr[int(q_idx_tv)]if q_idx_tv is not None and 0<=int(q_idx_tv)<L(ts_arr)else None
 q_val_tv=F(kysy_m.get('qml_seviyesi')or 0.0)if'kysy_m'in locals()else 0.0
 return{'mumlar':mum_list,'zigzag':zz_list,'elenen':elenen_list,'bos':bos_list,'kutular':kutu_list,'arz_talep':arz_talep_list,'ob_bolgeleri':ob_list,'imbalance':imbalance_list,'likidite':liq_list,'sfp':sfp_list,'qml':q_val_tv,'qml_t1':q_t1_tv,'qml_idx':int(q_idx_tv)if q_idx_tv is not None else None}
def tradingview_kopyala_yapistirsiz_html_ac(O,tf_secim='5m',H_ozel=None):
 from pathlib import Path
 H=H_ozel or analiz_hafizasi.get(O)or analiz_hafizasi.get(str(O).split(':',1)[-1])or{}
 J=H.get('sembol',str(O).split(':',1)[-1]);D=H.get('piyasa','spot'if str(O).startswith('SPOT:')else'future')
 htf_p,mtf_p,ltf_p,mtf_sb=_parite_mtf_periyotlarini_bul(O,J,D,H)
 if not H or H.get('df_4h')is None or(H.get('df_5m')is None and H.get('df_15m')is None)or H.get('htf_periyot')!=htf_p or H.get('mtf_periyot')!=mtf_p or H.get('ltf_periyot')!=ltf_p:
  try:H=pine_icin_4h_1h_5m_veri_hazirla(J,D,H,O)
  except X:pass
 if tf_secim==htf_p:tf_secim='4h'
 elif tf_secim==mtf_p:tf_secim='1h'
 elif tf_secim not in('4h','1h','5m'):tf_secim='5m'
 raw_sym=J.split(':')[0].replace('/','').upper()
 tv_sym=raw_sym+('.P'if D=='future'else'')
 dR_kutu=acik_islemler.get(O)
 htf_aktif_kutu=(dR_kutu.get('htf_aktif_bolge')if I(dR_kutu,dict)else None)or(H.get('konum_meta',{}).get('aktif_htf_at_kutu')if I(H.get('konum_meta'),dict)else None)
 tf_data={}
 for t_k,df_k,yp_k,kt_k in[('4h','df_4h','yapi_4h','kutular_4h'),('1h','df_1h','yapi_1h','kutular_1h'),('5m','df_5m','yapi_5m','kutular_5m')]:
  df_t=H.get(df_k,H.get('df_4h_full'if t_k=='4h'else'df_1h_full'if t_k=='1h'else'df_15m_full'))
  yp_t=H.get(yp_k,H.get('yapi_15m'if t_k=='5m'else yp_k,{}))
  kt_t=H.get(kt_k,H.get('cizim_kutulari_4h'if t_k=='4h'else'cizim_kutulari_1h'if t_k=='1h'else'cizim_kutulari_15m',[]))
  tf_data[t_k]=_df_to_tv_json(df_t,yp_t,kt_t,t_k,htf_aktif_kutu)
  tf_data[t_k]['pine']=pine_script_uret_4h_1h_5m(O,t_k,H)
  tf_data[t_k]['yon']=yp_t.get('yon','-')
  tf_data[t_k]['kirilim_tipi']=yp_t.get('kirilim_tipi','-')
  tf_data[t_k]['fibo_oran']=F(yp_t.get('fibo_oran',0.5)or 0.5)
  tf_data[t_k]['wyckoff']=yp_t.get('wyckoff_fazi','TREND')
  tf_data[t_k]['sp']=F(yp_t.get('strong_point')or H.get('strong_point')or 0.0)
  tf_data[t_k]['wp']=F(yp_t.get('weak_point')or H.get('weak_point')or 0.0)
  ist_t=yp_t.get('uc_istasyon',H.get('uc_istasyon',{}));fl_t=yp_t.get('fl_dp_meta',H.get('fl_dp_meta',{}));qm_t=yp_t.get('qm_meta',H.get('qm_meta',{}))
  tf_data[t_k]['magic']=F(fl_t.get('magic_line')or ist_t.get('FL')or 0.0)
  tf_data[t_k]['fl_turu']=str(fl_t.get('fl_turu','FL'))
  tf_data[t_k]['dp_turu']=str(fl_t.get('dp_turu','DP'))
  tf_data[t_k]['itz']=F(ist_t.get('ITZ')or 0.0)
  tf_data[t_k]['qml']=F(tf_data[t_k].get('qml')or yp_t.get('qml_seviyesi')or qm_t.get('qml_seviyesi')or 0.0)
  tf_data[t_k]['qm_tipi']=str(qm_t.get('qm_tipi','QML'))
  tf_data[t_k]['smax']=F(yp_t.get('swing_max')or 0.0)
  tf_data[t_k]['smin']=F(yp_t.get('swing_min')or 0.0)
  kysy_t=yp_t.get('kysy_meta',{})
  tf_data[t_k]['kysy_onay']=bool(kysy_t.get('kysy_onay',True))
  tf_data[t_k]['elenen_sayi']=int(kysy_t.get('elenen_sayi',0))
 dR=acik_islemler.get(O)
 aktif_sinyal_var=bool(I(dR,dict)or H.get('sinyal')in('LONG','SHORT'))
 giris=F(dR['giris']if I(dR,dict)else(H.get('giris')if aktif_sinyal_var else 0.0))
 sl=F(dR['sl']if I(dR,dict)else(H.get('sl')if aktif_sinyal_var else 0.0))
 yon_islem=dR['yon']if I(dR,dict)else(H.get('sinyal')if H.get('sinyal')in('LONG','SHORT')else'BEKLE (Bölge Dışı)')
 rk=A(giris-sl)if giris>0 and sl>0 else 0.0;mO=-1.0 if yon_islem=='SHORT'else 1.0
 etkin_rr_h=F((H.get('konum_meta',{})if I(H,dict)else{}).get('etkin_rr_orani')or RISK_ODUL_ORANI)
 tp1=F(dR['tp']if I(dR,dict)else(giris+mO*rk*etkin_rr_h if rk>0 else 0.0))
 tp2=F(dR.get('tp_nihai',tp1)if I(dR,dict)else(giris+mO*rk*M(NIHAI_TP_RR,RISK_ODUL_ORANI+1.0)if rk>0 else 0.0))
 pnl_u,pnl_y=(0.0,0.0)
 if I(dR,dict):pnl_u,pnl_y,_,_,_,_,_=islem_kar_zarar_hesapla(O,dR)
 pnl_html=f"{_fmt_pnl(pnl_u)} (%{pnl_y:+.2f})"if I(dR,dict)else"Açık İşlem Yok (Analiz Modu)"
 pnl_renk="#4ade80"if pnl_u>=0 else"#f87171"
 kFlt=H.get('konum_meta',{'konum_onay':True,'konum_durumu':'ONAY','karar_senaryosu':'STANDART'})
 p1,p2,p3,p4=H.get('atli_puanlar',(0,0,0,0));skor=H.get('skor',0);sinyal=H.get('sinyal','BEKLE')
 pine_kodu=tf_data.get(tf_secim,tf_data['5m'])['pine']
 checklist_html=_karne_checklist_olustur(H,html_mi=True)
 rontgen_js_str=json.dumps(islem_rontgeni_olustur(O,H).get('tam_rapor_metni','')if'islem_rontgeni_olustur'in globals()else'',ensure_ascii=False)
 html_icerik=f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>TradingView Canlı PA & Pine v6 Çizim Şablonları — {O} [{tf_secim.upper()}]</title>
<script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js" onerror="var s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js';document.head.appendChild(s);"></script>
<script src="https://s3.tradingview.com/tv.js" async></script>
<style>
body {{ margin:0; padding:0; background:#0f172a; color:#f8fafc; font-family:'Segoe UI',sans-serif; display:flex; flex-direction:column; height:100vh; overflow:hidden; }}
.topbar {{ background:#1e293b; padding:6px 12px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #334155; flex-wrap:wrap; gap:6px; z-index:40; }}
.badge {{ padding:3px 8px; border-radius:6px; font-weight:bold; font-size:11.5px; margin-right:3px; display:inline-block; }}
.btn {{ background:#10b981; color:#fff; border:none; padding:5px 10px; border-radius:6px; font-weight:bold; cursor:pointer; text-decoration:none; font-size:11.5px; margin-left:3px; transition:0.15s; }}
.btn:hover {{ opacity:0.92; }}
.btn.active {{ outline:2px solid #fde047; }}
.layerbar {{ background:#131722; padding:5px 12px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #2a2e39; flex-wrap:wrap; gap:8px; font-size:11.5px; z-index:35; }}
.chk-group {{ display:flex; align-items:center; flex-wrap:wrap; gap:8px; }}
.chk-lbl {{ cursor:pointer; user-select:none; display:inline-flex; align-items:center; gap:4px; background:#1e222d; border:1px solid #334155; padding:3px 8px; border-radius:5px; color:#e2e8f0; font-weight:600; }}
.chk-lbl:hover {{ border-color:#38bdf8; }}
.chk-lbl input {{ accent-color:#10b981; width:14px; height:14px; cursor:pointer; margin:0; }}
.main {{ display:flex; flex:1; overflow:hidden; position:relative; }}
.tv-left-bar {{ width:38px; background:#131722; border-right:1px solid #2a2e39; display:flex; flex-direction:column; align-items:center; padding-top:8px; gap:8px; z-index:30; user-select:none; }}
.tv-tool-icon {{ width:28px; height:28px; border-radius:5px; display:flex; align-items:center; justify-content:center; color:#cbd5e1; font-size:13px; cursor:pointer; background:#1e222d; border:1px solid #2a2e39; }}
.tv-tool-icon:hover, .tv-tool-icon.active {{ color:#38bdf8; border-color:#38bdf8; background:#1e293b; }}
.chart-area {{ flex:7; height:100%; display:flex; flex-direction:column; position:relative; background:#131722; overflow:hidden; }}
.chart-stage {{ flex:1; position:relative; width:100%; min-height:420px; overflow:hidden; background:#131722; }}
#tv_chart {{ width:100%; height:100%; position:absolute; top:0; left:0; z-index:2; }}
#pine_canvas {{ width:100%; height:100%; position:absolute; top:0; left:0; z-index:6; pointer-events:none; }}
#rsi_pane {{ height:110px; width:100%; border-top:1px solid #2a2e39; background:#131722; position:relative; display:none; z-index:5; }}
#rsi_pane.show {{ display:block; }}
.side {{ flex:3; min-width:320px; max-width:400px; background:#11111b; border-left:1px solid #334155; padding:9px; display:flex; flex-direction:column; overflow-y:auto; z-index:30; transition:all 0.18s ease; }}
.side.gizli {{ display:none !important; width:0 !important; min-width:0 !important; max-width:0 !important; padding:0 !important; border:none !important; }}
.bilgi-ac-fab {{ position:absolute; top:10px; right:82px; z-index:25; background:#f59e0b; color:#11111b; border:1px solid #fde047; border-radius:6px; padding:5px 10px; font-size:11.5px; font-weight:bold; cursor:pointer; display:none; box-shadow:0 2px 10px rgba(0,0,0,0.45); }}
.bilgi-ac-fab.goster {{ display:inline-flex; align-items:center; gap:4px; }}
.card {{ background:#181825; border:1px solid #313244; border-radius:8px; padding:8px; margin-bottom:7px; font-size:11.5px; line-height:1.48; }}
textarea {{ width:100%; flex:1; min-height:175px; background:#090d16; color:#38bdf8; border:1px solid #334155; border-radius:6px; padding:7px; font-family:Consolas,monospace; font-size:10.5px; resize:none; box-sizing:border-box; }}
</style>
</head>
<body>
<div class="topbar">
  <div>
    <span class="badge" style="background:#2563eb;">🌲 ALFA PA {BOT_VERSIYONU} — CANLI TRADINGVIEW</span>
    <span class="badge" style="background:#0d9488;" id="lbl_parite">{O} ({tv_sym}) | {tf_secim.upper()}</span>
    <span class="badge" style="background:#059669;" id="lbl_anlik_fiyat">⚡ Anlık: Yükleniyor...</span>
    <span class="badge" style="background:{'#10b981' if sinyal=='LONG' else '#ef4444' if sinyal=='SHORT' else '#f59e0b'};">{sinyal} ({skor}/100)</span>
    <span class="badge" style="background:#1e1e2e;border:1px solid {pnl_renk};color:{pnl_renk};">💰 K/Z: {pnl_html}</span>
  </div>
  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
    <span style="font-size:11.5px;font-weight:bold;color:#a78bfa;">⏱️ MTF Şablon:</span>
    <select id="sel_mtf_sablon" onchange="mtfSablonDegistirJS(this.value)" style="background:#4c1d95;color:#fff;border:1px solid #7c3aed;border-radius:6px;padding:4px 7px;font-size:11.5px;font-weight:bold;cursor:pointer;">
      <option value="1h,15m,5m" {'selected' if (htf_p,mtf_p,ltf_p)==('1h','15m','5m') else ''}>1h / 15m / 5m (Intraday)</option>
      <option value="4h,1h,15m" {'selected' if (htf_p,mtf_p,ltf_p)==('4h','1h','15m') else ''}>4h / 1h / 15m (Swing)</option>
      <option value="4h,1h,5m" {'selected' if (htf_p,mtf_p,ltf_p)==('4h','1h','5m') else ''}>4h / 1h / 5m (Alfa Pine MTF)</option>
      <option value="4h,30m,3m" {'selected' if (htf_p,mtf_p,ltf_p)==('4h','30m','3m') else ''}>4h / 30m / 3m (Sniper)</option>
      <option value="1d,2h,15m" {'selected' if (htf_p,mtf_p,ltf_p)==('1d','2h','15m') else ''}>1d / 2h / 15m (Pozisyon)</option>
      <option value="1d,1h,5m" {'selected' if (htf_p,mtf_p,ltf_p)==('1d','1h','5m') else ''}>1d / 1h / 5m (Günlük MTF)</option>
      <option value="1M,2h,15m" {'selected' if (htf_p,mtf_p,ltf_p)==('1M','2h','15m') else ''}>1M / 2h / 15m (Aylık Macro)</option>
      <option value="1d,4h,1h" {'selected' if (htf_p,mtf_p,ltf_p)==('1d','4h','1h') else ''}>1d / 4h / 1h (Pozisyon)</option>
      <option value="2h,30m,5m" {'selected' if (htf_p,mtf_p,ltf_p)==('2h','30m','5m') else ''}>2h / 30m / 5m (Gün İçi)</option>
      <option value="15m,5m,1m" {'selected' if (htf_p,mtf_p,ltf_p)==('15m','5m','1m') else ''}>15m / 5m / 1m (Scalp)</option>
    </select>
    <button class="btn" id="btn_4h" style="background:#2563eb;" onclick="periyotDegistir('4h')">🏛️ HTF ({htf_p.upper()})</button>
    <button class="btn" id="btn_1h" style="background:#7c3aed;" onclick="periyotDegistir('1h')">🧭 MTF ({mtf_p.upper()})</button>
    <button class="btn" id="btn_5m" style="background:#0d9488;" onclick="periyotDegistir('5m')">🎯 LTF ({ltf_p})</button>
    <button class="btn" id="btn_mod" style="background:#8b5cf6;" onclick="gorunumDegistir()">🌐 Canlı TV Widget Göster</button>
    <button class="btn" style="background:#0284c7;" onclick="anlikGrafigeOdaklan()">🎯 Anlık Muma Git</button>
    <button class="btn" style="background:#eab308;color:#111;" onclick="kopyalaPine()">📋 Kopyala</button>
    <button class="btn" id="btn_bilgi_toggle" style="background:#f59e0b;color:#11111b;" onclick="bilgiPaneliToggle()">📊 Bilgi Ekranı: Açık ◀▶</button>
  </div>
</div>
<div class="layerbar">
  <div class="chk-group">
    <span style="color:#38bdf8;font-weight:bold;">🎨 Çizim Şablonları (İsteğe Göre Ekle):</span>
    <label class="chk-lbl"><input type="checkbox" id="chk_zz" onchange="katmanlariSimdiGuncelle()">Swing / BOS & QML</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_arz" onchange="katmanlariSimdiGuncelle()">🔴 Arz Bölgeleri</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_talep" onchange="katmanlariSimdiGuncelle()">🟢 Talep Bölgeleri</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_ob" onchange="katmanlariSimdiGuncelle()">🧱 OB Bölgeleri</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_kutu" onchange="katmanlariSimdiGuncelle()">Imbalance & FVG</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_ist" onchange="katmanlariSimdiGuncelle()">İstasyonlar / Magic Line</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_fibo" onchange="katmanlariSimdiGuncelle()">Sihirli Fibo / OTE</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_liq" onchange="katmanlariSimdiGuncelle()">Likidite / SFP</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_rr" onchange="katmanlariSimdiGuncelle()">İşlem & R:R</label>
    <label class="chk-lbl"><input type="checkbox" id="chk_rsi" onchange="rsiPanelToggle()">RSI(14)</label>
  </div>
  <div style="font-size:11px;color:#94a3b8;" id="durum_cubugu">🟢 Canlı Binance Akışı Aktif</div>
</div>
<div class="main">
  <div class="tv-left-bar" id="tv_left_bar">
    <div class="tv-tool-icon active" title="Artı İşareti (Crosshair)">✜</div>
    <div class="tv-tool-icon" id="ico_zz" title="Swing / BOS & QML" onclick="katmanToggle('zz')">📐</div>
    <div class="tv-tool-icon" id="ico_arz" title="Arz Bölgeleri (RBD / DBD / Flip Arz)" onclick="katmanToggle('arz')">🟥</div>
    <div class="tv-tool-icon" id="ico_talep" title="Talep Bölgeleri (DBR / RBR / Flip Talep)" onclick="katmanToggle('talep')">🟩</div>
    <div class="tv-tool-icon" id="ico_ob" title="Order Block (OB) Bölgeleri" onclick="katmanToggle('ob')">🧱</div>
    <div class="tv-tool-icon" id="ico_kutu" title="Imbalance & FVG (BISI / SIBI / IFVG / VIB)" onclick="katmanToggle('kutu')">▭</div>
    <div class="tv-tool-icon" id="ico_ist" title="İstasyonlar / Magic Line" onclick="katmanToggle('ist')">🏛</div>
    <div class="tv-tool-icon" id="ico_fibo" title="Sihirli Fibo / OTE" onclick="katmanToggle('fibo')">☰</div>
    <div class="tv-tool-icon" id="ico_liq" title="Likidite / SFP" onclick="katmanToggle('liq')">💧</div>
    <div class="tv-tool-icon" id="ico_rr" title="İşlem & R:R" onclick="katmanToggle('rr')">🎯</div>
  </div>
  <div class="chart-area">
    <button class="bilgi-ac-fab" id="btn_bilgi_fab" onclick="bilgiPaneliToggle()">📊 Bilgilendirme Ekranını Aç ◀</button>
    <div class="chart-stage" id="chart_stage" style="min-height:420px;">
      <div id="tv_chart"></div>
      <canvas id="pine_canvas"></canvas>
      <div id="tv_native_widget" style="width:100%;height:100%;position:absolute;top:0;left:0;z-index:12;display:none;background:#131722;"></div>
    </div>
    <div id="rsi_pane"></div>
  </div>
  <div class="side" id="side_panel">
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;gap:6px;">
        <div style="color:#38bdf8;font-weight:bold;font-size:13px;cursor:pointer;" id="karne_baslik" onclick="karneIcerikToggle()" title="Daraltmak/Genişletmek için tıklayın">📊 {O} [{tf_secim.upper()}] — Strateji & Seviye Karnesi ▾</div>
        <button class="btn" style="background:#334155;color:#f8fafc;padding:2px 7px;font-size:10.5px;margin:0;" onclick="bilgiPaneliToggle()" title="Bilgilendirme Ekranını Gizle">✖ Gizle</button>
      </div>
      <div id="karne_icerik_kapsayici">
      <div style="background:#11111b;padding:5px 8px;border-radius:6px;margin-bottom:5px;border-left:3px solid {pnl_renk};">
        <b>💰 Anlık İşlem Kâr/Zarar:</b> <span style="color:{pnl_renk};font-weight:bold;font-size:12.5px;">{pnl_html}</span>
      </div>
      {checklist_html}
      <div id="kysy_satir">• <b>Kırılım Yoksa Swing Yoktur:</b> ONAYLI</div>
      <div>• <b>Aktif Giriş Modu:</b> {GIRIS_STRATEJI_MODU}</div>
      <div>• <b>HTF Safe Bölge Durumu:</b> {kFlt.get('konum_durumu','ONAY')}</div>
      <div>• <b>Safe Derecesi & Senaryo:</b> {kFlt.get('karar_senaryosu','STANDART')}</div>
      <div id="yon_satir">• <b>{htf_p.upper()} / {mtf_p.upper()} / {ltf_p} Yapı Yönü:</b> {H.get('yon_4h','-')} / {H.get('yon_1h','-')} / {H.get('yon_5m',H.get('yapi_15m',{}).get('yon','-'))}</div>
      <div>• <b>4 Atlı Puanları:</b> {p1}/25 | {p2}/25 | {p3}/25 | {p4}/25 (Toplam: {skor}/100)</div>
      <hr style="border-color:#313244;margin:5px 0;">
      <div>• <b style="color:#38bdf8;">Giriş Fiyatı ({yon_islem}):</b> {_fmt_f(giris)}</div>
      <div>• <b style="color:#f87171;">Stop-Loss (1R):</b> {_fmt_f(sl)}</div>
      <div>• <b style="color:#4ade80;">TP1 ({RISK_ODUL_ORANI}R %50+BE):</b> {_fmt_f(tp1)}</div>
      <div>• <b style="color:#a3e635;">Nihai TP ({NIHAI_TP_RR}R):</b> {_fmt_f(tp2)}</div>
      <div id="sp_wp_satir">• <b style="color:#eab308;">Strong Origin / Weak Target:</b> -</div>
      <div id="ist_satir">• <b style="color:#f472b6;">Magic Line (FL) / ITZ / QML:</b> -</div>
      </div>
    </div>
    <div class="card" style="border-color:#8b5cf6;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
        <span style="color:#c084fc;font-weight:bold;font-size:12.5px;">🤖 Gemini AI İşlem Röntgeni & Canlı Soru-Cevap</span>
        <span class="badge" style="background:#4c1d95;color:#e9d5ff;font-size:10px;margin:0;">{BOT_VERSIYONU}</span>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
        <button class="btn" style="background:#2563eb;padding:3px 7px;font-size:10.5px;margin:0;" onclick="geminiHizliSor('Bu işlemi neye göre açtın? Giriş yerini nasıl belirledin?')">❓ Neye Göre Açtın?</button>
        <button class="btn" style="background:#0d9488;padding:3px 7px;font-size:10.5px;margin:0;" onclick="geminiHizliSor('Stop-Loss ve TP1/TP2 seviyelerini nasıl hesapladın?')">🛡️ Stop & TP Hesabı</button>
        <button class="btn" style="background:#d97706;padding:3px 7px;font-size:10.5px;margin:0;" onclick="geminiKatmanGoster()">📊 Tüm Giriş & Likiditeyi Çiz</button>
        <button class="btn" style="background:#dc2626;padding:3px 7px;font-size:10.5px;margin:0;" onclick="geminiHizliSor('Bu işlemde veya likidite/stop seçiminde herhangi bir hata veya risk var mı?')">🔍 Hata Denetimi</button>
      </div>
      <div id="gemini_tv_cevap" style="background:#090d16;border:1px solid #334155;border-radius:6px;padding:7px;font-size:11px;color:#e2e8f0;max-height:165px;overflow-y:auto;white-space:pre-wrap;margin-bottom:6px;">💡 Yukarıdaki butonlara tıklayarak veya aşağıya sorunuzu yazarak işlemin tüm röntgenini, giriş/stop hesabını ve hata denetimini anında görebilirsiniz.</div>
      <div style="display:flex;gap:4px;">
        <input id="gemini_tv_soru" type="text" placeholder="İşlemle ilgili her şeyi sorun..." style="flex:1;background:#090d16;color:#fff;border:1px solid #475569;border-radius:5px;padding:5px 7px;font-size:11px;" onkeydown="if(event.key==='Enter')geminiSorJS()">
        <button class="btn" style="background:#8b5cf6;padding:5px 9px;font-size:11px;margin:0;" onclick="geminiSorJS()">Gönder</button>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <span style="font-weight:bold;color:#fde047;font-size:11.5px;" id="pine_baslik">📜 Aktif Pine Script v6 Kodu ({tf_secim.upper()}):</span>
      <button class="btn" style="background:#0d9488;padding:3px 7px;font-size:10.5px;" onclick="pineKodunuSimdiUygula()">🔄 Kodu Uygula</button>
    </div>
    <textarea id="pine_box" oninput="pineKodunuSimdiUygula()">{pine_kodu}</textarea>
  </div>
</div>
<script>
const TUM_VERI = {json.dumps(tf_data)};
const RAW_SYM = "{raw_sym}";
const IS_FUT = {'true' if D=='future' else 'false'};
const TV_SYM = "{tv_sym}";
const PARITE_ETIKET = "{O}";
let GIRIS = {giris:.8f};
let SL = {sl:.8f};
let TP1 = {tp1:.8f};
let TP2 = {tp2:.8f};
const YON_ISLEM = "{yon_islem}";
let aktifTf = "{tf_secim}";
const TF_GERCEK_HARITA = {{ '4h': "{htf_p}", '1h': "{mtf_p}", '5m': "{ltf_p}" }};
let widgetModu = false;
let aktifMumlar = [];
let parseEdilenPine = {{ kutular: [], sp: 0, wp: 0, magic: 0, itz: 0, qml: 0, smax: 0, smin: 0, giris: GIRIS, sl: SL, tp1: TP1, tp2: TP2 }};
let wsBaglanti = null;
let fiyatTimer = null;

const stageEl = document.getElementById('chart_stage');
const container = document.getElementById('tv_chart');
const pineCanvas = document.getElementById('pine_canvas');
const rsiContainer = document.getElementById('rsi_pane');

const ilkGenislik = Math.max(480, stageEl.clientWidth || (window.innerWidth - 380));
const ilkYukseklik = Math.max(360, stageEl.clientHeight || (window.innerHeight - 95));
const chart = LightweightCharts.createChart(container, {{
  width: ilkGenislik,
  height: ilkYukseklik,
  layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
  grid: {{ vertLines: {{ color: 'rgba(30,34,45,0.85)' }}, horzLines: {{ color: 'rgba(30,34,45,0.85)' }} }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
  rightPriceScale: {{ borderColor: '#2a2e39', autoScale: true, scaleMargins: {{ top: 0.08, bottom: 0.10 }} }},
  timeScale: {{ borderColor: '#2a2e39', timeVisible: true, secondsVisible: false, rightOffset: 10, barSpacing: 5.5 }}
}});

const rsiChart = LightweightCharts.createChart(rsiContainer, {{
  layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#94a3b8' }},
  grid: {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
  rightPriceScale: {{ borderColor: '#2a2e39' }},
  timeScale: {{ borderColor: '#2a2e39', timeVisible: true, visible: false }}
}});
const rsiSeries = rsiChart.addLineSeries({{ color: '#a78bfa', lineWidth: 2, title: 'RSI(14)' }});
rsiSeries.createPriceLine({{ price: 70, color: '#f87171', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false, title: '' }});
rsiSeries.createPriceLine({{ price: 50, color: '#64748b', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: false, title: '' }});
rsiSeries.createPriceLine({{ price: 30, color: '#4ade80', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false, title: '' }});

let candleSeries = null;
let zzSeries = null;
let bosSerileri = [];
let aktifPriceLines = [];

function fiyatFormatla(v) {{
  const n = Number(v || 0);
  const a = Math.abs(n);
  if (a > 0 && a < 1) return n.toFixed(6);
  if (a < 100) return n.toFixed(4);
  return n.toFixed(2);
}}

function pineKodunuParseEt(pineText, fallbackVeri) {{
  const sonuc = {{
    kutular: [],
    sp: fallbackVeri.sp || 0,
    wp: fallbackVeri.wp || 0,
    magic: fallbackVeri.magic || 0,
    itz: fallbackVeri.itz || 0,
    qml: fallbackVeri.qml || 0,
    smax: fallbackVeri.smax || 0,
    smin: fallbackVeri.smin || 0,
    giris: GIRIS,
    sl: SL,
    tp1: TP1,
    tp2: TP2
  }};
  if (fallbackVeri.kutular && fallbackVeri.kutular.length > 0) {{
    fallbackVeri.kutular.forEach(k => {{
      sonuc.kutular.push({{
        tip: k.tip,
        idx1: typeof k.idx1 === 'number' ? k.idx1 : null,
        t1: k.t1 || null,
        solOffset: 32,
        sagOffset: 8,
        hi: k.hi,
        lo: k.lo
      }});
    }});
  }}
  if (!pineText) return sonuc;
  const flt = (rx, defVal) => {{
    const m = pineText.match(rx);
    return m ? parseFloat(m[1]) : defVal;
  }};
  sonuc.sp = flt(/var\s+float\s+bot_sp\s*=\s*([0-9.]+)/, sonuc.sp);
  sonuc.wp = flt(/var\s+float\s+bot_wp\s*=\s*([0-9.]+)/, sonuc.wp);
  sonuc.magic = flt(/var\s+float\s+bot_magic\s*=\s*([0-9.]+)/, sonuc.magic);
  sonuc.itz = flt(/var\s+float\s+bot_itz\s*=\s*([0-9.]+)/, sonuc.itz);
  sonuc.qml = flt(/var\s+float\s+bot_qml\s*=\s*([0-9.]+)/, sonuc.qml);
  sonuc.smax = flt(/var\s+float\s+bot_smax\s*=\s*([0-9.]+)/, sonuc.smax);
  sonuc.smin = flt(/var\s+float\s+bot_smin\s*=\s*([0-9.]+)/, sonuc.smin);
  sonuc.giris = flt(/var\s+float\s+bot_giris\s*=\s*([0-9.]+)/, sonuc.giris);
  sonuc.sl = flt(/var\s+float\s+bot_sl\s*=\s*([0-9.]+)/, sonuc.sl);
  sonuc.tp1 = flt(/var\s+float\s+bot_tp1\s*=\s*([0-9.]+)/, sonuc.tp1);
  sonuc.tp2 = flt(/var\s+float\s+bot_tp2\s*=\s*([0-9.]+)/, sonuc.tp2);
  return sonuc;
}}

function arzTalepStilCoz(z) {{
  const tur = String(z.tur || 'TALEP');
  const alt = String(z.alt_tur || '');
  if (tur === 'TALEP') {{
    if (alt.includes('FLIP')) return ['rgba(20,184,166,0.16)', '#14b8a6', z.etiket || 'Flip Talep'];
    if (z.taze) return ['rgba(16,185,129,0.18)', '#10b981', z.etiket || 'Talep OB (Taze)'];
    return ['rgba(59,130,246,0.15)', '#3b82f6', z.etiket || 'Talep Bölgesi'];
  }} else {{
    if (alt.includes('FLIP')) return ['rgba(244,63,94,0.16)', '#f43f5e', z.etiket || 'Flip Arz'];
    if (z.taze) return ['rgba(239,68,68,0.18)', '#ef4444', z.etiket || 'Arz OB (Taze)'];
    return ['rgba(249,115,22,0.15)', '#f97316', z.etiket || 'Arz Bölgesi'];
  }}
}}

function imbalanceStilCoz(im) {{
  const t = String(im.tip || 'FVG');
  if (t.includes('BISI')) return ['rgba(245,158,11,0.17)', '#f59e0b', im.etiket || 'BISI FVG'];
  if (t.includes('SIBI')) return ['rgba(168,85,247,0.17)', '#a855f7', im.etiket || 'SIBI FVG'];
  if (t.includes('IFVG')) return ['rgba(20,184,166,0.17)', '#14b8a6', im.etiket || 'IFVG Flip'];
  if (t.includes('VIB')) return ['rgba(250,204,21,0.18)', '#eab308', im.etiket || 'VIB/Gap'];
  return ['rgba(6,182,212,0.15)', '#06b6d4', im.etiket || 'Imbalance'];
}}

function fiyatCizgileriniTemizle() {{
  if (!candleSeries) return;
  aktifPriceLines.forEach(pl => {{
    try {{ candleSeries.removePriceLine(pl); }} catch (e) {{}}
  }});
  aktifPriceLines = [];
}}

function seriKatmanlariniGuncelle() {{
  if (!candleSeries) return;
  const veri = TUM_VERI[aktifTf] || TUM_VERI['5m'];
  const gosterZz  = document.getElementById('chk_zz').checked;
  const gosterIst = document.getElementById('chk_ist').checked;
  const gosterFibo = document.getElementById('chk_fibo').checked;
  const gosterRr  = document.getElementById('chk_rr').checked;
  const gosterLiq = document.getElementById('chk_liq').checked;

  ['zz','arz','talep','ob','kutu','ist','fibo','liq','rr'].forEach(k => {{
    const ic = document.getElementById('ico_' + k);
    const ch = document.getElementById('chk_' + k);
    if (ic && ch) ic.classList.toggle('active', ch.checked);
  }});

  if (zzSeries) {{ try {{ chart.removeSeries(zzSeries); }} catch(e){{}} zzSeries = null; }}
  bosSerileri.forEach(s => {{ try {{ chart.removeSeries(s); }} catch(e){{}} }});
  bosSerileri = [];

  const markers = [];
  if (gosterZz && veri.zigzag && veri.zigzag.length > 1) {{
    zzSeries = chart.addLineSeries({{ color: '#cbd5e1', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }});
    zzSeries.setData(veri.zigzag.map(z => ({{ time: z.time, value: z.value }})));
    veri.zigzag.forEach(z => {{
      const renkM = z.lbl === 'HH' ? '#4ade80' : z.lbl === 'LH' ? '#fb7185' : z.lbl === 'HL' ? '#38bdf8' : '#f97316';
      markers.push({{
        time: z.time,
        position: z.tip === 'H' ? 'aboveBar' : 'belowBar',
        color: renkM,
        shape: z.tip === 'H' ? 'arrowDown' : 'arrowUp',
        text: z.lbl
      }});
    }});
  }}
  if (gosterLiq && veri.sfp && veri.sfp.length > 0) {{
    veri.sfp.forEach(sf => {{
      markers.push({{
        time: sf.time,
        position: sf.yon === 'BULL' ? 'belowBar' : 'aboveBar',
        color: sf.yon === 'BULL' ? '#10b981' : '#f43f5e',
        shape: sf.yon === 'BULL' ? 'arrowUp' : 'arrowDown',
        text: sf.yon === 'BULL' ? 'SFP▲' : 'SFP▼'
      }});
    }});
  }}
  markers.sort((a, b) => a.time - b.time);
  candleSeries.setMarkers(markers);

  if (gosterZz && veri.bos && veri.bos.length > 0) {{
    veri.bos.forEach(b => {{
      if (b.t1 < b.t2) {{
        const bs = chart.addLineSeries({{
          color: b.yon === 'BULLISH' ? '#22c55e' : '#f43f5e',
          lineWidth: 1.5,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false
        }});
        bs.setData([{{ time: b.t1, value: b.price }}, {{ time: b.t2, value: b.price }}]);
        bosSerileri.push(bs);
      }}
    }});
  }}

  fiyatCizgileriniTemizle();
  function seviyeEkle(fiyat, baslik, renk, stil, kalinlik=1) {{
    if (fiyat && fiyat > 0) {{
      const pl = candleSeries.createPriceLine({{ price: fiyat, color: renk, lineWidth: kalinlik, lineStyle: stil, axisLabelVisible: true, title: baslik }});
      aktifPriceLines.push(pl);
    }}
  }}
  if (gosterRr) {{
    seviyeEkle(parseEdilenPine.giris, 'Giriş', '#38bdf8', LightweightCharts.LineStyle.Dashed, 2);
    seviyeEkle(parseEdilenPine.sl, 'SL(1R)', '#ef4444', LightweightCharts.LineStyle.Solid, 2);
    seviyeEkle(parseEdilenPine.tp1, 'TP1(3R)', '#10b981', LightweightCharts.LineStyle.Solid, 2);
    seviyeEkle(parseEdilenPine.tp2, 'TP2(4R)', '#a3e635', LightweightCharts.LineStyle.Dotted, 1);
  }}
  if (gosterIst) {{
    seviyeEkle(parseEdilenPine.sp, 'Origin', '#eab308', LightweightCharts.LineStyle.Dashed, 1);
    seviyeEkle(parseEdilenPine.wp, 'Weak', '#94a3b8', LightweightCharts.LineStyle.Dotted, 1);
    seviyeEkle(parseEdilenPine.magic, 'Magic/FL', '#ec4899', LightweightCharts.LineStyle.Dashed, 1);
    seviyeEkle(parseEdilenPine.itz, 'ITZ', '#06b6d4', LightweightCharts.LineStyle.Dotted, 1);
  }}
  if (gosterZz || gosterIst) {{
    const qmlPl = (veri.qml && veri.qml > 0) ? veri.qml : (parseEdilenPine.qml || 0);
    seviyeEkle(qmlPl, 'QML', '#c084fc', LightweightCharts.LineStyle.Dashed, 1);
  }}
  if (gosterFibo && parseEdilenPine.smax > parseEdilenPine.smin && parseEdilenPine.smin > 0) {{
    const eq = (parseEdilenPine.smax + parseEdilenPine.smin) / 2.0;
    seviyeEkle(eq, '0.50 EQ', '#64748b', LightweightCharts.LineStyle.Dashed, 1);
  }}
}}

function cizPineGostergeKatmani() {{
  if (!pineCanvas || !candleSeries || aktifMumlar.length < 3) return;
  const rect = stageEl.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  pineCanvas.width = Math.floor(rect.width * dpr);
  pineCanvas.height = Math.floor(rect.height * dpr);
  const ctx = pineCanvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);

  const isHTF = (aktifTf === '4h');
  const gosterArz   = document.getElementById('chk_arz') ? document.getElementById('chk_arz').checked : false;
  const gosterTalep = document.getElementById('chk_talep') ? document.getElementById('chk_talep').checked : false;
  const gosterOb    = document.getElementById('chk_ob') ? document.getElementById('chk_ob').checked : false;
  const gosterKutu  = document.getElementById('chk_kutu').checked;
  const gosterFibo  = document.getElementById('chk_fibo').checked;
  const gosterIst   = document.getElementById('chk_ist').checked;
  const gosterRr    = document.getElementById('chk_rr').checked;
  const gosterZz    = document.getElementById('chk_zz').checked;
  const gosterLiq   = document.getElementById('chk_liq').checked;

  const sonIdx = aktifMumlar.length - 1;
  const tSon = chart.timeScale().timeToCoordinate(aktifMumlar[sonIdx].time);
  const tOnceki = chart.timeScale().timeToCoordinate(aktifMumlar[Math.max(0, sonIdx - 10)].time);
  const barGenislik = (tSon !== null && tOnceki !== null && sonIdx >= 10) ? Math.max(3.5, (tSon - tOnceki) / 10.0) : 6.5;

  const doluEtiketAlanlari = [];
  function temizEtiketCiz(metin, xHedef, yHedef, metinRenk='#ffffff', hiza='right', fontStr='bold 9.5px Segoe UI, sans-serif') {{
    if (!metin) return;
    ctx.save();
    ctx.font = fontStr;
    const mGen = Math.ceil(ctx.measureText(metin).width);
    const padX = 5, padY = 2, kutuH = 14, kutuW = mGen + padX * 2;
    const adayYList = [0, 15, -15, 30, -30, 45, -45];
    const adayXList = [0, -(kutuW + 10), (kutuW + 10)];
    let secX1 = 0, secY1 = 0, bulundu = false;
    for (let dx of adayXList) {{
      for (let dy of adayYList) {{
        let cx = xHedef + dx;
        let cy = yHedef + dy;
        let bx1 = (hiza === 'right') ? (cx - kutuW) : (hiza === 'center' ? (cx - kutuW / 2) : cx);
        let by1 = cy - kutuH + 3;
        bx1 = Math.max(6, Math.min(rect.width - 74 - kutuW, bx1));
        by1 = Math.max(4, Math.min(rect.height - kutuH - 4, by1));
        const bx2 = bx1 + kutuW, by2 = by1 + kutuH;
        const cakisiyor = doluEtiketAlanlari.some(r => !(bx2 + 3 < r.x1 || bx1 - 3 > r.x2 || by2 + 2 < r.y1 || by1 - 2 > r.y2));
        if (!cakisiyor) {{
          secX1 = bx1; secY1 = by1; bulundu = true; break;
        }}
      }}
      if (bulundu) break;
    }}
    if (!bulundu) {{
      secX1 = Math.max(6, Math.min(rect.width - 74 - kutuW, (hiza === 'right') ? (xHedef - kutuW) : xHedef));
      secY1 = Math.max(4, Math.min(rect.height - kutuH - 4, yHedef - kutuH + 3));
    }}
    doluEtiketAlanlari.push({{ x1: secX1, y1: secY1, x2: secX1 + kutuW, y2: secY1 + kutuH }});
    ctx.fillStyle = 'rgba(15, 23, 42, 0.84)';
    ctx.fillRect(secX1, secY1, kutuW, kutuH);
    ctx.strokeStyle = metinRenk;
    ctx.lineWidth = 0.85;
    ctx.strokeRect(secX1, secY1, kutuW, kutuH);
    ctx.fillStyle = metinRenk;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(metin, secX1 + padX, secY1 + kutuH / 2 + 0.5);
    ctx.restore();
  }}

  function timeOrIdxToX(tVal, idxVal) {{
    if (tVal) {{
      const xt = chart.timeScale().timeToCoordinate(tVal);
      if (xt !== null) return xt;
    }}
    if (typeof idxVal === 'number' && idxVal >= 0 && idxVal <= sonIdx) {{
      const xi = chart.timeScale().timeToCoordinate(aktifMumlar[idxVal].time);
      if (xi !== null) return xi;
    }}
    const rel = (typeof idxVal === 'number') ? (idxVal - sonIdx) : -25;
    if (tSon !== null) return tSon + rel * barGenislik;
    return rect.width - 110 + rel * barGenislik;
  }}

  function barIndexToX(relOffset) {{
    return timeOrIdxToX(null, sonIdx + relOffset);
  }}

  function gelismisKutuCiz(x1, x2, fUst, fAlt, bgRenk, kenarRenk, kisaEtiket, metinRenk='#ffffff', solDikCizgi=true, ortaCizgiFiyat=null, kesikliKenar=false, etiketHiza='right') {{
    if (!fUst || !fAlt || fUst <= 0 || fAlt <= 0) return;
    const y1 = candleSeries.priceToCoordinate(Math.max(fUst, fAlt));
    const y2 = candleSeries.priceToCoordinate(Math.min(fUst, fAlt));
    if (y1 === null || y2 === null) return;
    const left = Math.max(4, Math.min(x1, x2));
    const right = Math.min(rect.width - 70, Math.max(x1, x2));
    if (right <= left + 4) return;
    const top = Math.min(y1, y2);
    const h = Math.max(4, Math.abs(y2 - y1));
    ctx.save();
    ctx.fillStyle = bgRenk;
    ctx.fillRect(left, top, right - left, h);
    ctx.strokeStyle = kenarRenk;
    ctx.lineWidth = 1.15;
    if (kesikliKenar) ctx.setLineDash([4, 3]);
    ctx.strokeRect(left, top, right - left, h);
    ctx.setLineDash([]);
    if (solDikCizgi) {{
      ctx.beginPath();
      ctx.moveTo(left, top);
      ctx.lineTo(left, top + h);
      ctx.lineWidth = 3.0;
      ctx.strokeStyle = kenarRenk;
      ctx.stroke();
    }}
    if (ortaCizgiFiyat && ortaCizgiFiyat > 0 && h >= 10) {{
      const yOrta = candleSeries.priceToCoordinate(ortaCizgiFiyat);
      if (yOrta !== null && yOrta > top + 2 && yOrta < top + h - 2) {{
        ctx.beginPath();
        ctx.setLineDash([3, 3]);
        ctx.moveTo(left + 2, yOrta);
        ctx.lineTo(right - 2, yOrta);
        ctx.lineWidth = 0.9;
        ctx.strokeStyle = kenarRenk;
        ctx.stroke();
        ctx.setLineDash([]);
      }}
    }}
    ctx.restore();
    if (kisaEtiket) {{
      const xEt = (etiketHiza === 'left') ? (left + 6) : (right - 5);
      const yEt = top + Math.min(13, Math.max(11, h - 2));
      temizEtiketCiz(kisaEtiket, xEt, yEt, metinRenk, etiketHiza);
    }}
  }}

  const veri = TUM_VERI[aktifTf] || TUM_VERI['5m'];

  if (gosterFibo && parseEdilenPine.smax > parseEdilenPine.smin && parseEdilenPine.smin > 0) {{
    const i4 = parseEdilenPine.smax;
    const i5 = parseEdilenPine.smin;
    const dK = i4 - i5;
    const lA = (veri.yon || 'BULLISH') !== 'BEARISH';
    const xFiboBas = veri.fibo_t1 ? timeOrIdxToX(veri.fibo_t1, null) : barIndexToX(-140);
    const xFiboBit = barIndexToX(8);
    const fibSeviyeler = [
      {{ r: -0.236, c: '#cbd5e1', lbl: '-0.236' }},
      {{ r: 0.0,    c: '#22c55e', lbl: '0' }},
      {{ r: 0.236,  c: '#ef4444', lbl: '0.236' }},
      {{ r: 0.382,  c: '#3b82f6', lbl: '0.382' }},
      {{ r: 0.5,    c: '#06b6d4', lbl: '0.5' }},
      {{ r: 0.618,  c: '#10b981', lbl: '0.618' }},
      {{ r: 0.705,  c: '#4ade80', lbl: '0.705' }},
      {{ r: 0.786,  c: '#60a5fa', lbl: '0.786' }},
      {{ r: 1.0,    c: '#f43f5e', lbl: '1' }}
    ];
    fibSeviyeler.forEach(fb => {{
      const fVal = lA ? (i4 - dK * fb.r) : (i5 + dK * fb.r);
      const yF = candleSeries.priceToCoordinate(fVal);
      if (yF !== null && yF > 4 && yF < rect.height - 4) {{
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(Math.max(4, xFiboBas), yF);
        ctx.lineTo(Math.min(rect.width - 72, xFiboBit), yF);
        ctx.strokeStyle = fb.c;
        ctx.lineWidth = (fb.r === 0 || fb.r === 1) ? 1.5 : 1.05;
        ctx.stroke();
        ctx.restore();
        temizEtiketCiz(`${{fb.lbl}} (${{fiyatFormatla(fVal)}})`, Math.max(8, xFiboBas + 6), yF - 2, fb.c, 'left');
      }}
    }});
    const ote1 = lA ? i4 - dK * 0.618 : i5 + dK * 0.618;
    const ote705 = lA ? i4 - dK * 0.705 : i5 + dK * 0.705;
    const ote2 = lA ? i4 - dK * 0.786 : i5 + dK * 0.786;
    const oteBg = lA ? 'rgba(244,63,94,0.16)' : 'rgba(59,130,246,0.16)';
    const oteBrd = lA ? '#fb7185' : '#60a5fa';
    const oteLbl = lA ? 'Bullish OTE (0.618-0.786)' : 'Bearish OTE (0.618-0.786)';
    gelismisKutuCiz(Math.max(xFiboBas + 30, barIndexToX(-95)), xFiboBit, ote1, ote2, oteBg, oteBrd, oteLbl, '#3b82f6', false, ote705, false, 'left');
  }}
  const aktifQmlFiyat = (veri.qml && veri.qml > 0) ? veri.qml : (parseEdilenPine.qml || 0);
  if (isHTF && (gosterZz || gosterIst || gosterFibo) && aktifQmlFiyat > 0) {{
    const yQml = candleSeries.priceToCoordinate(aktifQmlFiyat);
    const xQmlBas = (veri.qml_t1 || typeof veri.qml_idx === 'number') ? timeOrIdxToX(veri.qml_t1, veri.qml_idx) : barIndexToX(-160);
    const xQmlBit = barIndexToX(8);
    if (yQml !== null && yQml >= 2 && yQml <= rect.height - 2) {{
      const x1Q = Math.max(6, Math.min(rect.width - 120, xQmlBas));
      const x2Q = Math.min(rect.width - 70, Math.max(x1Q + 30, xQmlBit));
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x1Q, yQml);
      ctx.lineTo(x2Q, yQml);
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2.2;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x1Q, yQml, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = '#fde047';
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#ef4444';
      ctx.stroke();
      ctx.restore();
      temizEtiketCiz(`QML (${{fiyatFormatla(aktifQmlFiyat)}})`, x1Q + 8, Math.max(14, yQml - 4), '#fde047', 'left');
    }}
  }}

  if (gosterArz && veri.arz_talep && veri.arz_talep.length > 0) {{
    veri.arz_talep.filter(z => String(z.tur || '') === 'ARZ').forEach(z => {{
      const [bg, brd, et] = arzTalepStilCoz(z);
      const xStart = timeOrIdxToX(z.t1, z.idx1);
      const xEnd = barIndexToX(7);
      const eqFiyat = z.eq || ((z.lo + z.hi) / 2.0);
      gelismisKutuCiz(xStart, xEnd, z.hi, z.lo, bg, brd, et, brd, true, eqFiyat, !z.taze, 'right');
    }});
  }}

  if (gosterTalep && veri.arz_talep && veri.arz_talep.length > 0) {{
    veri.arz_talep.filter(z => String(z.tur || '') === 'TALEP').forEach(z => {{
      const [bg, brd, et] = arzTalepStilCoz(z);
      const xStart = timeOrIdxToX(z.t1, z.idx1);
      const xEnd = barIndexToX(7);
      const eqFiyat = z.eq || ((z.lo + z.hi) / 2.0);
      gelismisKutuCiz(xStart, xEnd, z.hi, z.lo, bg, brd, et, brd, true, eqFiyat, !z.taze, 'right');
    }});
  }}

  if (gosterOb && veri.ob_bolgeleri && veri.ob_bolgeleri.length > 0) {{
    veri.ob_bolgeleri.forEach(ob => {{
      const isBull = String(ob.yon || 'BULL') === 'BULL';
      const bg = isBull ? 'rgba(59,130,246,0.18)' : 'rgba(245,158,11,0.18)';
      const brd = isBull ? '#38bdf8' : '#fbbf24';
      const et = ob.etiket || (isBull ? 'Bullish OB' : 'Bearish OB');
      const xStart = timeOrIdxToX(ob.t1, ob.idx1);
      const xEnd = barIndexToX(7);
      const eqFiyat = ob.eq || ((ob.lo + ob.hi) / 2.0);
      gelismisKutuCiz(xStart, xEnd, ob.hi, ob.lo, bg, brd, et, brd, true, eqFiyat, !ob.taze, 'left');
    }});
  }}

  if (gosterKutu && veri.imbalance && veri.imbalance.length > 0) {{
    veri.imbalance.forEach(im => {{
      const [bg, brd, et] = imbalanceStilCoz(im);
      const xStart = timeOrIdxToX(im.t1, im.idx1);
      const xEnd = barIndexToX(6);
      const ceFiyat = im.ce || ((im.lo + im.hi) / 2.0);
      gelismisKutuCiz(xStart, xEnd, im.hi, im.lo, bg, brd, et, brd, true, ceFiyat, im.tip === 'IFVG' || !im.taze, 'right');
    }});
  }}

  if (gosterLiq && veri.likidite && veri.likidite.length > 0) {{
    veri.likidite.forEach(lq => {{
      const x1 = timeOrIdxToX(lq.t1, lq.idx1);
      const x2 = lq.aktif ? Math.min(rect.width - 72, Math.max(timeOrIdxToX(lq.t2, lq.idx2), barIndexToX(4))) : timeOrIdxToX(lq.t2, lq.idx2);
      const y1 = candleSeries.priceToCoordinate(lq.p1);
      const y2 = candleSeries.priceToCoordinate(lq.p2);
      if (x1 !== null && x2 !== null && y1 !== null && y2 !== null && Math.abs(x2 - x1) >= 4) {{
        ctx.save();
        ctx.beginPath();
        if (String(lq.tip || '').includes('Sweep')) ctx.setLineDash([2, 3]);
        else if (String(lq.tip || '').includes('Trendline')) ctx.setLineDash([6, 3]);
        else if (String(lq.tip || '').includes('IDM')) ctx.setLineDash([3, 2]);
        else ctx.setLineDash([4, 3]);
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = lq.renk || '#fbbf24';
        ctx.lineWidth = lq.aktif ? 1.55 : 1.25;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x1, y1, 3.0, 0, Math.PI * 2);
        ctx.fillStyle = lq.renk || '#fbbf24';
        ctx.fill();
        ctx.restore();
        const lblTxt = `${{lq.tip}} (${{fiyatFormatla(lq.p2)}})`;
        temizEtiketCiz(lblTxt, Math.min(rect.width - 74, Math.max(x1 + 55, x2 - 4)), (y1 + y2) / 2 - 4, lq.renk || '#fbbf24', 'right');
      }}
    }});
  }}

  const rrGiris = GIRIS > 0 ? GIRIS : (parseEdilenPine.giris || 0);
  const rrSl    = SL > 0 ? SL : (parseEdilenPine.sl || 0);
  const rrTp1   = TP1 > 0 ? TP1 : (parseEdilenPine.tp1 || 0);
  if (gosterRr && rrGiris > 0 && rrSl > 0) {{
    const yG = candleSeries.priceToCoordinate(rrGiris);
    const yS = candleSeries.priceToCoordinate(rrSl);
    const yT = rrTp1 > 0 ? candleSeries.priceToCoordinate(rrTp1) : null;
    const xL = Math.max(8, barIndexToX(-10));
    const xR = Math.min(rect.width - 70, Math.max(xL + 36, barIndexToX(6)));
    if (yG !== null && yS !== null && xR > xL + 4) {{
      ctx.save();
      const topR = Math.min(yG, yS), hR = Math.max(2, Math.abs(yS - yG));
      ctx.fillStyle = 'rgba(239,68,68,0.15)';
      ctx.fillRect(xL, topR, xR - xL, hR);
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.2;
      ctx.strokeRect(xL, topR, xR - xL, hR);
      if (yT !== null) {{
        const topT = Math.min(yG, yT), hT = Math.max(2, Math.abs(yT - yG));
        ctx.fillStyle = 'rgba(16,185,129,0.14)';
        ctx.fillRect(xL, topT, xR - xL, hT);
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 1.2;
        ctx.strokeRect(xL, topT, xR - xL, hT);
      }}
      ctx.beginPath();
      ctx.moveTo(xL, yG);
      ctx.lineTo(xR, yG);
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.0;
      ctx.stroke();
      ctx.restore();
    }}
  }}
}}

function katmanlariSimdiGuncelle() {{
  seriKatmanlariniGuncelle();
  requestAnimationFrame(() => cizPineGostergeKatmani());
}}

function katmanToggle(tip) {{
  const map = {{ arz: 'chk_arz', talep: 'chk_talep', ob: 'chk_ob', kutu: 'chk_kutu', zz: 'chk_zz', ist: 'chk_ist', fibo: 'chk_fibo', liq: 'chk_liq', rr: 'chk_rr' }};
  const el = document.getElementById(map[tip]);
  if (el) {{
    el.checked = !el.checked;
    katmanlariSimdiGuncelle();
  }}
}}

function rsiHesapla(mumlar, periyot=14) {{
  const out = [];
  if (!mumlar || mumlar.length < periyot + 1) return out;
  let kazanc = 0, kayip = 0;
  for (let i = 1; i <= periyot; i++) {{
    const f = mumlar[i].close - mumlar[i - 1].close;
    if (f >= 0) kazanc += f; else kayip -= f;
  }}
  let ortKazanc = kazanc / periyot;
  let ortKayip = kayip / periyot;
  for (let i = periyot; i < mumlar.length; i++) {{
    if (i > periyot) {{
      const f = mumlar[i].close - mumlar[i - 1].close;
      ortKazanc = (ortKazanc * (periyot - 1) + (f > 0 ? f : 0)) / periyot;
      ortKayip = (ortKayip * (periyot - 1) + (f < 0 ? -f : 0)) / periyot;
    }}
    const rs = ortKayip === 0 ? 100 : ortKazanc / ortKayip;
    const rsi = 100 - (100 / (1 + rs));
    out.push({{ time: mumlar[i].time, value: rsi }});
  }}
  return out;
}}

async function binanceMumCek(tf) {{
  const gercekTf = (typeof TF_GERCEK_HARITA !== 'undefined' && TF_GERCEK_HARITA[tf]) ? TF_GERCEK_HARITA[tf] : tf;
  const urls = IS_FUT
    ? [`https://fapi.binance.com/fapi/v1/klines?symbol=${{RAW_SYM}}&interval=${{gercekTf}}&limit=350`, `https://api.binance.com/api/v3/klines?symbol=${{RAW_SYM}}&interval=${{gercekTf}}&limit=350`]
    : [`https://api.binance.com/api/v3/klines?symbol=${{RAW_SYM}}&interval=${{gercekTf}}&limit=350`, `https://fapi.binance.com/fapi/v1/klines?symbol=${{RAW_SYM}}&interval=${{gercekTf}}&limit=350`];
  for (const url of urls) {{
    try {{
      const r = await fetch(url);
      const d = await r.json();
      if (Array.isArray(d) && d.length > 5) {{
        return d.map((k, idx) => ({{
          time: Math.floor(Number(k[0]) / 1000),
          idx: idx,
          open: parseFloat(k[1]),
          high: parseFloat(k[2]),
          low: parseFloat(k[3]),
          close: parseFloat(k[4]),
          volume: parseFloat(k[5] || 0)
        }}));
      }}
    }} catch (e) {{}}
  }}
  return [];
}}

async function anlikFiyatPolling() {{
  const urls = IS_FUT
    ? [`https://fapi.binance.com/fapi/v1/ticker/price?symbol=${{RAW_SYM}}`, `https://api.binance.com/api/v3/ticker/price?symbol=${{RAW_SYM}}`]
    : [`https://api.binance.com/api/v3/ticker/price?symbol=${{RAW_SYM}}`, `https://fapi.binance.com/fapi/v1/ticker/price?symbol=${{RAW_SYM}}`];
  for (const u of urls) {{
    try {{
      const r = await fetch(u);
      const j = await r.json();
      const p = parseFloat(j.price || 0);
      if (p > 0 && candleSeries && aktifMumlar.length > 0) {{
        const son = Object.assign({{}}, aktifMumlar[aktifMumlar.length - 1]);
        son.close = p;
        if (p > son.high) son.high = p;
        if (p < son.low) son.low = p;
        aktifMumlar[aktifMumlar.length - 1] = son;
        candleSeries.update(son);
        const lbl = document.getElementById('lbl_anlik_fiyat');
        if (lbl) lbl.innerText = `⚡ Anlık: ${{fiyatFormatla(p)}}`;
        requestAnimationFrame(() => cizPineGostergeKatmani());
        break;
      }}
    }} catch (e) {{}}
  }}
}}

function canliWebSocketBaslat(tf) {{
  if (wsBaglanti) {{
    try {{ wsBaglanti.close(); }} catch (e) {{}}
    wsBaglanti = null;
  }}
  if (fiyatTimer) clearInterval(fiyatTimer);
  fiyatTimer = setInterval(anlikFiyatPolling, 1500);
  try {{
    const gercekWsTf = (typeof TF_GERCEK_HARITA !== 'undefined' && TF_GERCEK_HARITA[tf]) ? TF_GERCEK_HARITA[tf] : tf;
    const wsUrl = IS_FUT
      ? `wss://fstream.binance.com/ws/${{RAW_SYM.toLowerCase()}}@kline_${{gercekWsTf}}`
      : `wss://stream.binance.com:9443/ws/${{RAW_SYM.toLowerCase()}}@kline_${{gercekWsTf}}`;
    wsBaglanti = new WebSocket(wsUrl);
    wsBaglanti.onmessage = (ev) => {{
      try {{
        const msg = JSON.parse(ev.data);
        if (msg && msg.k && candleSeries) {{
          const k = msg.k;
          const yeniMum = {{
            time: Math.floor(Number(k.t) / 1000),
            idx: Math.max(0, aktifMumlar.length - 1),
            open: parseFloat(k.o),
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: parseFloat(k.c)
          }};
          candleSeries.update(yeniMum);
          if (aktifMumlar.length > 0 && aktifMumlar[aktifMumlar.length - 1].time === yeniMum.time) {{
            aktifMumlar[aktifMumlar.length - 1] = yeniMum;
          }} else if (aktifMumlar.length === 0 || yeniMum.time > aktifMumlar[aktifMumlar.length - 1].time) {{
            yeniMum.idx = aktifMumlar.length;
            aktifMumlar.push(yeniMum);
          }}
          const lbl = document.getElementById('lbl_anlik_fiyat');
          if (lbl) lbl.innerText = `⚡ Anlık: ${{fiyatFormatla(yeniMum.close)}}`;
          requestAnimationFrame(() => cizPineGostergeKatmani());
        }}
      }} catch (err) {{}}
    }};
  }} catch (e) {{}}
}}

function anlikGrafigeOdaklan() {{
  chart.timeScale().scrollToRealTime();
  requestAnimationFrame(() => cizPineGostergeKatmani());
}}

function pineKodunuSimdiUygula() {{
  const veri = TUM_VERI[aktifTf] || TUM_VERI['5m'];
  const pineText = document.getElementById('pine_box').value;
  parseEdilenPine = pineKodunuParseEt(pineText, veri);
  katmanlariSimdiGuncelle();
}}

async function periyotDegistir(tf) {{
  aktifTf = tf;
  ['4h','1h','5m'].forEach(k => {{
    const b = document.getElementById('btn_' + k);
    if (b) b.classList.toggle('active', k === tf);
  }});
  const veri = TUM_VERI[tf] || TUM_VERI['5m'];
  const gTfAd = ((typeof TF_GERCEK_HARITA !== 'undefined' && TF_GERCEK_HARITA[tf]) ? TF_GERCEK_HARITA[tf] : tf).toUpperCase();
  const aktSblStr = `${{(TF_GERCEK_HARITA['4h'] || '4h').toUpperCase()}}/${{(TF_GERCEK_HARITA['1h'] || '1h').toUpperCase()}}/${{TF_GERCEK_HARITA['5m'] || '5m'}}`;
  document.getElementById('lbl_parite').innerText = `{O} (${{TV_SYM}}) | ${{gTfAd}} (Şablon: ${{aktSblStr}})`;
  document.getElementById('karne_baslik').innerText = `📊 {O} [${{gTfAd}}] — Strateji & Seviye Karnesi`;
  document.getElementById('pine_baslik').innerText = `📜 Aktif Pine Script v6 Kodu (${{gTfAd}}):`;
  document.getElementById('pine_box').value = veri.pine || '';
  document.getElementById('kysy_satir').innerHTML = `• <b>Kırılım Yoksa Swing Yoktur:</b> ${{veri.kysy_onay ? '<span style="color:#4ade80">ONAYLI</span>' : '<span style="color:#f59e0b">KIRILIM YOK</span>'}} (Elenen Gürültü: ${{veri.elenen_sayi}})`;
  document.getElementById('sp_wp_satir').innerHTML = `• <b style="color:#eab308;">Strong Origin / Weak Target:</b> ${{veri.sp ? veri.sp.toFixed(4) : '-'}} / ${{veri.wp ? veri.wp.toFixed(4) : '-'}}`;
  document.getElementById('ist_satir').innerHTML = `• <b style="color:#f472b6;">Magic Line (FL) / ITZ / QML:</b> ${{veri.magic ? veri.magic.toFixed(4) : '-'}} / ${{veri.itz ? veri.itz.toFixed(4) : '-'}} / ${{veri.qml ? veri.qml.toFixed(4) : '-'}}`;

  parseEdilenPine = pineKodunuParseEt(veri.pine || '', veri);

  if (candleSeries) {{ try {{ chart.removeSeries(candleSeries); }} catch(e){{}} }}
  const refFiyat = (veri.mumlar && veri.mumlar.length > 0) ? Math.abs(Number(veri.mumlar[veri.mumlar.length - 1].close || 1)) : 1;
  const pPrec = (refFiyat > 0 && refFiyat < 0.01) ? 6 : (refFiyat < 1 ? 5 : (refFiyat < 100 ? 4 : 2));
  const pMinMove = Number((1 / Math.pow(10, pPrec)).toFixed(pPrec));
  candleSeries = chart.addCandlestickSeries({{
    upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#4ade80', wickDownColor: '#f87171',
    priceFormat: {{ type: 'price', precision: pPrec, minMove: pMinMove }}
  }});

  if (veri.mumlar && veri.mumlar.length > 0) {{
    aktifMumlar = veri.mumlar.slice();
    candleSeries.setData(aktifMumlar);
    rsiSeries.setData(rsiHesapla(aktifMumlar, 14));
    const sonF = aktifMumlar[aktifMumlar.length - 1].close;
    document.getElementById('lbl_anlik_fiyat').innerText = `⚡ Anlık: ${{fiyatFormatla(sonF)}}`;
  }}

  seriKatmanlariniGuncelle();
  chart.timeScale().fitContent();
  chart.timeScale().scrollToRealTime();
  setTimeout(boyutlariEsitle, 40);

  const canliMumlar = await binanceMumCek(tf);
  if (canliMumlar && canliMumlar.length > 5 && aktifTf === tf) {{
    const birlesikMap = new Map();
    (veri.mumlar || []).forEach(m => birlesikMap.set(m.time, m));
    canliMumlar.forEach(m => birlesikMap.set(m.time, m));
    const sirali = Array.from(birlesikMap.values()).sort((a, b) => a.time - b.time).slice(-350);
    sirali.forEach((m, i) => {{ m.idx = i; }});
    aktifMumlar = sirali;
    candleSeries.setData(aktifMumlar);
    rsiSeries.setData(rsiHesapla(aktifMumlar, 14));
    const sonCanli = aktifMumlar[aktifMumlar.length - 1].close;
    document.getElementById('lbl_anlik_fiyat').innerText = `⚡ Anlık: ${{fiyatFormatla(sonCanli)}}`;
    seriKatmanlariniGuncelle();
    chart.timeScale().setVisibleLogicalRange({{ from: Math.max(0, aktifMumlar.length - 180), to: aktifMumlar.length + 8 }});
    requestAnimationFrame(() => cizPineGostergeKatmani());
    setTimeout(() => cizPineGostergeKatmani(), 60);
  }}
  canliWebSocketBaslat(tf);
  anlikFiyatPolling();
}}

function mtfSablonDegistirJS(deger) {{
  if (!deger) return;
  const parcalar = String(deger).split(',');
  if (parcalar.length === 3) {{
    TF_GERCEK_HARITA['4h'] = parcalar[0].trim();
    TF_GERCEK_HARITA['1h'] = parcalar[1].trim();
    TF_GERCEK_HARITA['5m'] = parcalar[2].trim();
    const b4 = document.getElementById('btn_4h');
    const b1 = document.getElementById('btn_1h');
    const b5 = document.getElementById('btn_5m');
    if (b4) b4.innerText = `🏛️ HTF (${{TF_GERCEK_HARITA['4h'].toUpperCase()}})`;
    if (b1) b1.innerText = `🧭 MTF (${{TF_GERCEK_HARITA['1h'].toUpperCase()}})`;
    if (b5) b5.innerText = `🎯 LTF (${{TF_GERCEK_HARITA['5m']}})`;
    periyotDegistir(aktifTf);
  }}
}}

function bilgiPaneliToggle() {{
  const sp = document.getElementById('side_panel');
  const btn = document.getElementById('btn_bilgi_toggle');
  const fab = document.getElementById('btn_bilgi_fab');
  if (!sp) return;
  const gizlendiMi = sp.classList.toggle('gizli');
  if (btn) {{
    btn.innerText = gizlendiMi ? '📊 Bilgi Ekranı: Kapalı (Aç ◀)' : '📊 Bilgi Ekranı: Açık ◀▶';
    btn.style.background = gizlendiMi ? '#475569' : '#f59e0b';
    btn.style.color = gizlendiMi ? '#f8fafc' : '#11111b';
  }}
  if (fab) fab.classList.toggle('goster', gizlendiMi);
  requestAnimationFrame(boyutlariEsitle);
  setTimeout(boyutlariEsitle, 35);
}}

function karneIcerikToggle() {{
  const ic = document.getElementById('karne_icerik_kapsayici');
  const bs = document.getElementById('karne_baslik');
  if (!ic) return;
  const kapali = ic.style.display === 'none';
  ic.style.display = kapali ? 'block' : 'none';
  if (bs) bs.innerText = bs.innerText.replace(/[▾▸]/g, '').trim() + (kapali ? ' ▾' : ' ▸');
}}

function rsiPanelToggle() {{
  const rp = document.getElementById('rsi_pane');
  const ch = document.getElementById('chk_rsi');
  if (ch) rp.classList.toggle('show', ch.checked);
  else rp.classList.toggle('show');
  setTimeout(boyutlariEsitle, 30);
}}

function boyutlariEsitle() {{
  const r = stageEl.getBoundingClientRect();
  if (r.width > 0 && r.height > 0) {{
    chart.applyOptions({{ width: r.width, height: r.height }});
  }}
  const rp = document.getElementById('rsi_pane');
  if (rp && rp.classList.contains('show')) {{
    const rr = rp.getBoundingClientRect();
    if (rr.width > 0 && rr.height > 0) {{
      rsiChart.applyOptions({{ width: rr.width, height: rr.height }});
    }}
  }}
  requestAnimationFrame(() => cizPineGostergeKatmani());
}}

function gorunumDegistir() {{
  widgetModu = !widgetModu;
  const btn = document.getElementById('btn_mod');
  const wDiv = document.getElementById('tv_native_widget');
  if (widgetModu) {{
    btn.innerText = '🌲 Alfa PA Çizimli Grafik Göster';
    btn.classList.add('active');
    if (wDiv) {{
      wDiv.style.display = 'block';
      const gTf = (typeof TF_GERCEK_HARITA !== 'undefined' && TF_GERCEK_HARITA[aktifTf]) ? TF_GERCEK_HARITA[aktifTf] : aktifTf;
      const tvIntervalMap = {{ '1m':'1', '3m':'3', '5m':'5', '15m':'15', '30m':'30', '1h':'60', '2h':'120', '4h':'240', '1d':'D', '1w':'W', '1M':'M' }};
      const tvInt = tvIntervalMap[gTf] || '15';
      const tvFullSym = 'BINANCE:' + RAW_SYM + (IS_FUT ? '.P' : '');
      wDiv.innerHTML = '<div id="tv_widget_inner" style="width:100%;height:100%;"></div>';
      if (typeof TradingView !== 'undefined' && TradingView.widget) {{
        new TradingView.widget({{
          autosize: true,
          symbol: tvFullSym,
          interval: tvInt,
          timezone: 'Europe/Istanbul',
          theme: 'dark',
          style: '1',
          locale: 'tr',
          toolbar_bg: '#131722',
          enable_publishing: false,
          hide_side_toolbar: false,
          allow_symbol_change: true,
          container_id: 'tv_widget_inner'
        }});
      }} else {{
        wDiv.innerHTML = `<iframe src="https://s.tradingview.com/widgetembed/?symbol=${{encodeURIComponent(tvFullSym)}}&interval=${{tvInt}}&theme=dark&style=1&timezone=Europe%2FIstanbul&locale=tr" style="width:100%;height:100%;border:0;" allowfullscreen></iframe>`;
      }}
    }}
  }} else {{
    btn.innerText = '🌐 Canlı TV Widget Göster';
    btn.classList.remove('active');
    if (wDiv) {{
      wDiv.style.display = 'none';
      wDiv.innerHTML = '';
    }}
    boyutlariEsitle();
    anlikGrafigeOdaklan();
  }}
}}

const GEMINI_API_KEY_JS = "{GEMINI_API_KEY}";
const GEMINI_MODEL_JS = "{GEMINI_MODEL}";
const ISLEM_RONTGEN_METNI_JS = {rontgen_js_str};

function geminiKatmanGoster() {{
  ['chk_zz','chk_arz','chk_talep','chk_ob','chk_kutu','chk_ist','chk_fibo','chk_liq','chk_rr'].forEach(id => {{
    const el = document.getElementById(id);
    if (el) el.checked = true;
  }});
  if (widgetModu) gorunumDegistir();
  katmanlariSimdiGuncelle();
  anlikGrafigeOdaklan();
  const kutu = document.getElementById('gemini_tv_cevap');
  if (kutu) kutu.innerText = "✅ Grafik üzerinde Giriş, SL/TP, KYSY Swing/QML, Gerçek OB (%50 MT), FVG (%50 CE), 3 İstasyon ve Likidite katmanlarının tamamı çizildi!\\n\\n" + (ISLEM_RONTGEN_METNI_JS || "");
}}

function geminiHizliSor(s) {{
  const inp = document.getElementById('gemini_tv_soru');
  if (inp) inp.value = s;
  geminiSorJS();
}}

async function geminiSorJS() {{
  const inp = document.getElementById('gemini_tv_soru');
  const kutu = document.getElementById('gemini_tv_cevap');
  if (!inp || !kutu) return;
  const soru = (inp.value || '').trim() || 'Bu işlemi neye göre açtın?';
  if (soru.toLowerCase().includes('çiz') || soru.toLowerCase().includes('göster')) {{
    geminiKatmanGoster();
  }}
  if (!GEMINI_API_KEY_JS) {{
    kutu.innerText = "🤖 AI Özeti:\\n" + (ISLEM_RONTGEN_METNI_JS || "İşlem verisi hazır.");
    return;
  }}
  kutu.innerText = "⏳ Gemini AI (" + GEMINI_MODEL_JS + ") işlemi ve grafiği inceliyor...";
  try {{
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${{GEMINI_MODEL_JS}}:generateContent?key=${{GEMINI_API_KEY_JS}}`;
    const prompt = `Sen Alfa Trade Club Bot {BOT_VERSIYONU} içindeki kurumsal Price Action & ICT uzmanısın. Aşağıdaki işlem röntgenine göre kullanıcının sorusunu net, maddeli ve Türkçe yanıtla:\\n\\n${{ISLEM_RONTGEN_METNI_JS}}\\n\\nKullanıcı Sorusu: ${{soru}}`;
    const r = await fetch(url, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ contents: [{{ parts: [{{ text: prompt }}] }}] }})
    }});
    const j = await r.json();
    const cvp = j?.candidates?.[0]?.content?.parts?.[0]?.text;
    kutu.innerText = cvp ? `🤖 Gemini AI (${{GEMINI_MODEL_JS}}):\\n` + cvp : ("🤖 [Dahili Röntgen]:\\n" + ISLEM_RONTGEN_METNI_JS);
  }} catch (e) {{
    kutu.innerText = "🤖 [Dahili Röntgen]:\\n" + ISLEM_RONTGEN_METNI_JS;
  }}
}}

function kopyalaPine() {{
  const el = document.getElementById('pine_box');
  el.select();
  document.execCommand('copy');
}}

chart.timeScale().subscribeVisibleLogicalRangeChange(() => {{
  requestAnimationFrame(() => cizPineGostergeKatmani());
  const lr = chart.timeScale().getVisibleLogicalRange();
  if (lr) rsiChart.timeScale().setVisibleLogicalRange(lr);
}});
chart.subscribeCrosshairMove(() => requestAnimationFrame(() => cizPineGostergeKatmani()));
window.addEventListener('resize', boyutlariEsitle);
if (typeof ResizeObserver !== 'undefined') {{
  new ResizeObserver(() => boyutlariEsitle()).observe(stageEl);
}}
window.addEventListener('load', () => {{
  boyutlariEsitle();
  setTimeout(boyutlariEsitle, 150);
}});
periyotDegistir(aktifTf);
</script>
</body>
</html>"""
 dosya_adi=f"tv_canli_{O.replace(':','_').replace('/','_')}_{tf_secim}.html"
 hedef_dizin=_yazilabilir_calisma_dizini()
 dosya_yolu=os.path.join(hedef_dizin,dosya_adi)
 try:
  with open(dosya_yolu,'w',encoding='utf-8')as f:f.write(html_icerik)
 except X:
  dosya_yolu=os.path.join(tempfile.gettempdir(),dosya_adi)
  with open(dosya_yolu,'w',encoding='utf-8')as f:f.write(html_icerik)
 try:
  if os.name=='nt':os.startfile(dosya_yolu)
  else:webbrowser.open(Path(dosya_yolu).as_uri())
 except X:
  try:webbrowser.open(Path(dosya_yolu).as_uri())
  except X:webbrowser.open('file://'+dosya_yolu)
 return(dosya_yolu,pine_kodu)
# ==============================================================================
# BULUT SENKRONİZASYON (PC <-> ANDROID EŞLEŞTİRME) VE TEK TUŞLA OTA GÜNCELLEME
# ==============================================================================
GITHUB_REPO_ADRESI = "emrhozbr/bot"
GITHUB_TOKEN = ""
BULUT_SENK_AKTIF = True
_SON_BULUT_OKUMA_TS = 0.0
_SON_BULUT_YAZMA_HASH = ""
_BULUT_DOSYA_ADI = "senkron_durum.json"
_OTA_YEREL_CEKIRDEK = os.path.join(ANDROID_VERI_DIZINI if 'ANDROID_VERI_DIZINI' in globals() else '.', 'ota_cekirdek_motor.py')

def _temiz_etiket_grafik(txt):
 return re.sub(r'[^\x00-\x7FğüşıöçĞÜŞİÖÇâîûÂÎÛ$€£%±×÷≤≥≠≈•–—…✓✔✕✖▲▼◀▶★☆]+','',str(txt)).strip()

def _google_hesap_token_bul():
 global GEMINI_API_KEY
 if GEMINI_API_KEY and L(str(GEMINI_API_KEY).strip())>10:
  return('api_key',str(GEMINI_API_KEY).strip())
 for env_k in('GEMINI_API_KEY','GOOGLE_API_KEY','GENAI_API_KEY'):
  val=os.environ.get(env_k,'').strip()
  if L(val)>10:
   GEMINI_API_KEY=val
   return('api_key',val)
 try:
  r=_subp.run(['gcloud','auth','application-default','print-access-token'],capture_output=True,text=True,timeout=2.0)
  if r.returncode==0 and L(r.stdout.strip())>20:
   return('oauth_token',r.stdout.strip())
 except Exception:
  pass
 return(None,'')

def gemini_hesap_durumu_getir():
 tip,deger=_google_hesap_token_bul()
 if tip=='api_key':
  maskeli=(deger[:6]+'...'+deger[-4:])if L(deger)>12 else'Aktif'
  return(True,f"🟢 Gemini API Bağlı ({maskeli} | {GEMINI_MODEL})")
 if tip=='oauth_token':
  return(True,f"🟢 Google Hesabı OAuth Bağlı ({GEMINI_MODEL})")
 return(True,'🟢 Özgür Bulut AI + Ajan Modu Aktif (Kendi Gemini API Anahtarınızı da Bağlayabilirsiniz)')

def islem_rontgeni_olustur(O,H_analiz=None,islem_kaydi=None):
 O_str=str(O or'FUT:BTC/USDT')
 dR=islem_kaydi if I(islem_kaydi,dict)else(acik_islemler.get(O_str)if I(acik_islemler.get(O_str),dict)else None)
 if dR is None and':'in O_str:
  for g_item in ah:
   if I(g_item,dict)and g_item.get('sembol')==O_str:
    if I(g_item.get('rontgen'),dict):
     return g_item['rontgen']
    dR=g_item
    break
 H=H_analiz if(I(H_analiz,dict)and H_analiz)else(analiz_hafizasi.get(O_str)or analiz_hafizasi.get(O_str.split(':',1)[-1])or{})
 J=(dR.get('sembol')if I(dR,dict)and'/'in str(dR.get('sembol',''))else None)or H.get('sembol')or O_str.split(':',1)[-1]
 D=(dR.get('piyasa')if I(dR,dict)and dR.get('piyasa')else None)or H.get('piyasa')or('spot'if O_str.startswith('SPOT:')else'future')
 htf_p,mtf_p,ltf_p,mtf_sb=_parite_mtf_periyotlarini_bul(O_str,J,D,H)
 yon=(dR.get('yon')if I(dR,dict)else None)or H.get('sinyal')or H.get('ana_yon')or'BEKLE'
 giris=F((dR.get('giris')if I(dR,dict)else None)or H.get('giris')or(_f(H.get('df_15m'),'close',-1)if I(H.get('df_15m'),pd.DataFrame)else 0.0))
 anlik_f=F((dR.get('anlik')if I(dR,dict)and dR.get('anlik')else None)or(_f(H.get('df_15m'),'close',-1)if I(H.get('df_15m'),pd.DataFrame)else giris))
 sl=F((dR.get('sl')if I(dR,dict)else None)or H.get('sl')or 0.0)
 ilk_sl=F((dR.get('ilk_sl')if I(dR,dict)else None)or sl)
 rk=A(giris-ilk_sl)if giris>0 and ilk_sl>0 else 0.0
 mO=-1.0 if yon=='SHORT'else 1.0
 tp1=F((dR.get('tp')if I(dR,dict)else None)or(giris+mO*rk*RISK_ODUL_ORANI if rk>0 else 0.0))
 tp2=F((dR.get('tp_nihai')if I(dR,dict)else None)or(giris+mO*rk*M(NIHAI_TP_RR,RISK_ODUL_ORANI+1.0)if rk>0 else 0.0))
 miktar=F((dR.get('miktar')if I(dR,dict)else None)or 0.0)
 marjin_u=F((dR.get('marjin_usdt')if I(dR,dict)else None)or 0.0)
 risk_u=F((dR.get('risk_usdt')if I(dR,dict)else None)or ISLEM_BASI_RISK_USDT)
 if miktar<=0 and giris>0 and sl>0:
  try:miktar,marjin_u,risk_u=dinamik_miktar_hesapla(J,giris,sl,D,H.get('skor',70))
  except Exception:pass
 kFlt=H.get('konum_meta',{})if I(H.get('konum_meta'),dict)else{}
 chk=kFlt.get('checklist',{})if I(kFlt.get('checklist'),dict)else{}
 p1,p2,p3,p4=H.get('atli_puanlar',(0,0,0,0))
 skor=int(H.get('skor',0)or(dR.get('skor',0)if I(dR,dict)else 0))
 bolge_10p=F(H.get('bolge_10p_skor',0.0))
 aktif_htf_bolgeler=kFlt.get('aktif_htf_bolgeler',[])
 aktif_birincil_bolgeler=kFlt.get('aktif_birincil_bolgeler',[])
 birincil_olcek_skoru=int(kFlt.get('birincil_olcek_skoru',0))
 birincil_olcek_carpani=F(kFlt.get('birincil_olcek_carpani_etkin',0.35))
 oncelik_etiket=kFlt.get('en_yuksek_oncelik_etiket','1.Mod:Fresh Arz/Talep,OB,OTE,QML')
 bolge_kademesi=int(kFlt.get('bolge_kademesi',1)or 1)
 safe_sayisi=int(kFlt.get('htf_bolge_sayisi',dR.get('uygun_kural_sayisi',1)if I(dR,dict)else 0))
 safe_puan=int(kFlt.get('htf_safe_puan',dR.get('uygun_alt_kural_sayisi',80)if I(dR,dict)else 0))
 safe_derece=kFlt.get('htf_safe_derecesi','🛡️ SAFE')
 ltf_kirilimlar=kFlt.get('ltf_kirilim_listesi',[])
 ltf_mumlar=kFlt.get('ltf_mum_listesi',[])
 stop_kaynak=kFlt.get('stop_kaynak_bilgi',STOP_BELIRLEME_MODU)
 yapi_4h=H.get('yapi_4h',{})if I(H.get('yapi_4h'),dict)else{}
 yapi_1h=H.get('yapi_1h',{})if I(H.get('yapi_1h'),dict)else{}
 v6=H.get('v6_meta',{})if I(H.get('v6_meta'),dict)else{}
 v8=H.get('v8_meta',{})if I(H.get('v8_meta'),dict)else{}
 v12=H.get('v12_meta',{})if I(H.get('v12_meta'),dict)else{}
 giris_kurallari=(dR.get('giris_kurallari')if I(dR,dict)and dR.get('giris_kurallari')else None)or H.get('detayli_kurallar',[])
 ozet_str=(dR.get('ozet')if I(dR,dict)and dR.get('ozet')else None)or H.get('ozet','-')
 denetim_notlari=[]
 if kFlt.get('htf_oncelikli_bolge_onay'):
  denetim_notlari.append(f"1.Mod Ana Bölge GEÇTİ: Fiyat {kFlt.get('htf_oncelikli_bolge_sayisi',1)}/4 ana bölgede ({'+'.join(aktif_birincil_bolgeler)}).")
 elif safe_sayisi>=1:
  denetim_notlari.append(f"2.Mod Öğrenilen Giriş Bölgesi: ({', '.join(aktif_htf_bolgeler)}).")
 else:
  denetim_notlari.append("HTF Bölge Dışı: Fiyat şu an belirlenen giriş bölgelerinde değil.")
 fibo_oran_4h=F(yapi_4h.get('fibo_oran',0.5)or 0.5)*100.0
 tam_metin=(
  f"Parite: {O_str} ({D.upper()}) | Mod: {GIRIS_STRATEJI_MODU} | Yön: {yon} | Anlık: {_fmt_f(anlik_f)} | Skor: {skor}/100 (1.Atlı:{p1}, 2.Atlı:{p2}, 3.Atlı:{p3}, 4.Atlı:{p4})\n"
  f"MTF: {htf_p.upper()}/{mtf_p.upper()}/{ltf_p} | HTF Yön: {H.get('yon_4h',yapi_4h.get('yon','-'))} (Fibo:%{fibo_oran_4h:.1f}) | MTF Yön: {H.get('yon_1h',yapi_1h.get('yon','-'))}\n"
  f"HTF Bölge ({safe_sayisi}/8 - {safe_derece} - {oncelik_etiket}): {', '.join(aktif_htf_bolgeler) if aktif_htf_bolgeler else 'Bölge Dışı'} | QML:{chk.get('qml_fiyat','-')} | OB:{chk.get('ob_aralik','-')} | Fresh:{chk.get('fresh_aralik','-')} | OTE:{chk.get('ote_aralik','-')}\n"
  f"LTF Tetikleyiciler: Kırılım(3a)={', '.join(ltf_kirilimlar)or'Yok'} | Mum(3b)={', '.join(ltf_mumlar)or'Yok'}\n"
  f"Giriş/SL/TP: Giriş={_fmt_f(giris)} | SL={_fmt_f(sl)} ({stop_kaynak}) | TP1({RISK_ODUL_ORANI}R)={_fmt_f(tp1)} | TP2({NIHAI_TP_RR}R)={_fmt_f(tp2)} | Miktar={miktar} (Marjin:{marjin_u:.2f}$, 1R Risk:-{risk_u:.2f}$)\n"
  f"Denetim: {' | '.join(denetim_notlari)}"
 )
 return{'parite':O_str,'sembol':J,'piyasa':D,'yon':yon,'anlik':anlik_f,'skor':skor,'giris':giris,'sl':sl,'ilk_sl':ilk_sl,'tp1':tp1,'tp2':tp2,'miktar':miktar,'marjin_usdt':marjin_u,'risk_usdt':risk_u,'htf_periyot':htf_p,'mtf_periyot':mtf_p,'ltf_periyot':ltf_p,'safe_sayisi':safe_sayisi,'safe_puan':safe_puan,'safe_derece':safe_derece,'oncelik_etiket':oncelik_etiket,'bolge_kademesi':bolge_kademesi,'birincil_olcek_skoru':birincil_olcek_skoru,'birincil_olcek_carpani':birincil_olcek_carpani,'aktif_htf_bolgeler':aktif_htf_bolgeler,'aktif_birincil_bolgeler':aktif_birincil_bolgeler,'chk':chk,'ltf_kirilimlar':ltf_kirilimlar,'ltf_mumlar':ltf_mumlar,'stop_kaynak':stop_kaynak,'atli_puanlar':(p1,p2,p3,p4),'likidite_turu':v8.get('likidite_turu','-'),'sfp_durumu':v8.get('sfp_durumu','-'),'imbalance_tipi':v6.get('imbalance_tipi','-'),'bolge_10p':bolge_10p,'denetim_notlari':denetim_notlari,'onerilen_duzeltmeler':[],'giris_kurallari':giris_kurallari,'ozet':ozet_str,'tam_rapor_metni':tam_metin}

def aninda_islem_grafigi_uret(O,mod='temiz_mum',H_ozel=None,kaydet_png=True,ozel_tf=None,bar_sayisi=85,katmanlar=None):
 O_str=str(O or'FUT:BTC/USDT')
 if':'not in O_str:
  O_str=f"FUT:{O_str}"if'/'in O_str else f"FUT:{O_str}/USDT"
 H=H_ozel if(I(H_ozel,dict)and H_ozel)else(analiz_hafizasi.get(O_str)or analiz_hafizasi.get(O_str.split(':',1)[-1])or{})
 dR=acik_islemler.get(O_str)if I(acik_islemler.get(O_str),dict)else None
 J=(dR.get('sembol')if I(dR,dict)else None)or H.get('sembol')or O_str.split(':',1)[-1]
 D=(dR.get('piyasa')if I(dR,dict)else None)or H.get('piyasa')or('spot'if O_str.startswith('SPOT:')else'future')
 htf_p,mtf_p,ltf_p,_=_parite_mtf_periyotlarini_bul(O_str,J,D,H)
 if not H or'df_15m'not in H:
  try:
   H=pine_icin_4h_1h_5m_veri_hazirla(J,D,H,O_str)
   analiz_hafizasi[O_str]=H
  except Exception:pass
 rontgen=islem_rontgeni_olustur(O_str,H,dR)
 return(None,'','',rontgen)

def gemini_api_sor(soru_metni,secili_o=None,H_ozel=None,gorsel_b64=None,gecmis_mesajlar=None,gui_ref=None):
 global KALDIRAC,ISLEM_BASI_RISK_USDT,MAKS_MARJIN_USDT,RISK_ODUL_ORANI,MIN_CONFLUENCE_SKORU,STOP_BELIRLEME_MODU,a4,MAKS_ACIK_ISLEM
 hedef_o=str(secili_o or'FUT:BTC/USDT')
 rg=islem_rontgeni_olustur(hedef_o,H_ozel)
 s_low=str(soru_metni or'').lower()
 cizim_istegi=None
 if'1. mod'in s_low or'sadece birincil'in s_low or'sadece 1. kademe'in s_low:
  giris_modu_uygula('1. Mod')
  if gui_ref and hasattr(gui_ref,'cmb_giris_modu'):gui_ref.cmb_giris_modu.set(GIRIS_STRATEJI_MODU)
  _api_kaydet_tam()
  return(f"✅ Giriş modu **{GIRIS_STRATEJI_MODU}** olarak güncellendi. Artık sadece Fresh Arz/Talep, OB, OTE ve QML noktalarından işleme girilecek.",None)
 if'2. mod'in s_low or'ikinci mod'in s_low or'tüm giriş'in s_low:
  giris_modu_uygula('2. Mod')
  if gui_ref and hasattr(gui_ref,'cmb_giris_modu'):gui_ref.cmb_giris_modu.set(GIRIS_STRATEJI_MODU)
  _api_kaydet_tam()
  return(f"✅ Giriş modu **{GIRIS_STRATEJI_MODU}** olarak güncellendi. Öğrenilen tüm giriş yerleri taranıp işleme girilecek.",None)
 m_maks=re.search(r'(?:maks|maksimum)\s*(?:işlem|islem)\s*(?:adedi|sayısı|sayisi)?\s*(\d+)',s_low)
 if m_maks:
  a4=M(1,N(100,int(m_maks.group(1))));MAKS_ACIK_ISLEM=a4
  if gui_ref and hasattr(gui_ref,'ent_maks_islem'):
   gui_ref.ent_maks_islem.delete(0,'end');gui_ref.ent_maks_islem.insert(0,str(a4))
  _api_kaydet_tam()
  if gui_ref:gui_ref.arayuzu_guncelle()
  return(f"✅ Maksimum açık işlem adedi **{a4}** olarak güncellendi.",None)
 if any(k in s_low for k in('çiz','göster','grafik')):
  cizim_istegi={'parite':hedef_o,'mod':'temiz_mum','tf':None,'bar':85,'ayri_pencere':'ayrı'in s_low}
 return(f"📌 **{rg['parite']} ({rg['yon']} | Skor: {rg['skor']}/100 | Mod: {GIRIS_STRATEJI_MODU} | Maks İşlem: {a4})**\n\n{rg['tam_rapor_metni']}",cizim_istegi)

def masaustu_kodunu_mobil_cekirdege_ayikla(kaynak_kod=None):
 if not kaynak_kod:
  mevcut_dosya=os.path.abspath(__file__)if'__file__'in globals()and os.path.exists(__file__)else BOT_DOSYA_ADI
  with open(mevcut_dosya,'r',encoding='utf-8')as f:kaynak_kod=f.read()
 satirlar=kaynak_kod.splitlines();cikti=[]
 for s in satirlar:
  st=s.strip()
  if st.startswith("ctk.set_appearance_mode")or st.startswith("class TradingBotGUI"):
   break
  if any(yasak in s for yasak in("import customtkinter","from tkinter","matplotlib","NavigationToolbar2Tk","FigureCanvasTkAgg")):
   continue
  if"bd='binance_api_config.json'"in s:
   continue
  if"_api_yukle();_ig_yukle();_ak_yukle();"in s:
   continue
  cikti.append(s)
 return"\n".join(cikti)

def ota_strateji_guncelle(repo_adresi=None,token=None,yerel_dosya_yolu=None):
 return(True,f"✅ OTA Güncelleme Hazır ({BOT_VERSIYONU})")

def bulut_durum_gonder(zorla=False):
 return False

def bulut_durum_cek(zorla=False):
 return False

def masaustunden_yerel_main_py_uret(log_fn=None):
 try:
  mevcut_dosya=os.path.abspath(__file__)if'__file__'in globals()and os.path.exists(__file__)else BOT_DOSYA_ADI
  with open(mevcut_dosya,'r',encoding='utf-8')as f:pc_kaynak=f.read()
  cekirdek=masaustu_kodunu_mobil_cekirdege_ayikla(pc_kaynak)
  with open(os.path.join(_yazilabilir_calisma_dizini(),'ota_cekirdek_motor.py'),'w',encoding='utf-8')as f:f.write(cekirdek)
  return True
 except Exception:return False

def pc_kodunu_githuba_ve_mobile_aktar(log_fn=None):
 return masaustunden_yerel_main_py_uret(log_fn)



# ==============================================================================
# FLET MOBIL ARAYUZ VE ARKA PLAN BOT YONETICISI (ANDROID APK)
# ==============================================================================
class AlfaMobileBotController:
    def __init__(self, page: ft.Page):
        self.page = page
        self._kapaniyor = False
        self._senk_calisiyor = False
        self._bot_baslangic_ts = None
        self._bot_baslangic_w = F(W)
        self._log_satirlari = []
        self._durum_metni = "Beklemede ⏸"
        self._durum_renk = "#f59e0b"
        self._arama_filtre = ""
        self._ui_build()
        threading.Thread(target=self._baslangic_yukle, daemon=True).start()
        threading.Thread(target=self._canli_pozisyon_senk_dongusu, daemon=True).start()

    def log_yaz(self, fs):
        satir = f"[{datetime.now().strftime('%H:%M:%S')}] {fs}"
        self._log_satirlari.append(satir)
        if len(self._log_satirlari) > 160:
            self._log_satirlari = self._log_satirlari[-140:]
        try:
            if hasattr(self, "txt_loglar"):
                self.txt_loglar.value = "\n".join(self._log_satirlari)
                self.page.update()
        except X:
            pass

    def durum_guncelle(self, mM, f8="#4ade80"):
        self._durum_metni = str(mM)
        self._durum_renk = str(f8)
        try:
            if hasattr(self, "lbl_durum"):
                self.lbl_durum.value = self._durum_metni
                self.lbl_durum.color = self._durum_renk
                self.page.update()
        except X:
            pass

    def _baslangic_yukle(self):
        global V, T
        try:
            _ak_yukle()
            V, T = bakiye_getir()
            self.log_yaz(f"✅ Mobil Motor Hazır ({BOT_VERSIYONU}) | Mod: {GIRIS_STRATEJI_MODU.split(':')[0]}")
            self.arayuzu_guncelle()
        except X as e:
            self.log_yaz(f"⚠️ Başlangıç yükleme uyarısı: {e}")

    def _canli_pozisyon_senk_dongusu(self):
        while not self._kapaniyor:
            try:
                if not self._senk_calisiyor:
                    self._senk_calisiyor = True
                    try:
                        self.pozisyonlari_senkronize_et()
                    finally:
                        self._senk_calisiyor = False
            except X:
                pass
            time.sleep(2.5)

    def _emir_kapat(self, J, D, bt, Y, e5):
        if e5:
            return (True, {})
        if D == 'future' and not TESTNET_AKTIF and API_KEY and API_SECRET:
            return _fapi_gercek_vadeli_emir_kapat(J, bt, Y)
        a9 = emir_ist(D)
        J_em = _emir_sembolu(a9, J, D)
        try:
            a9.cancel_all_orders(J_em)
        except X:
            pass
        try:
            if D == 'future':
                if bt == 'LONG':
                    a9.create_market_sell_order(J_em, Y, {'reduceOnly': True})
                else:
                    a9.create_market_buy_order(J_em, Y, {'reduceOnly': True})
            else:
                a9.create_market_sell_order(J_em, Y)
            return (True, {})
        except X:
            return (False, {})

    def _poz_kapat(self, O, dl='MANUEL KAPATMA', pJ=True):
        global W, S
        try:
            bq = acik_islemler.get(O)
            if not bq:
                return
            J, b0, ig = (bq.get('sembol', O.split(':', 1)[-1]), bq.get('piyasa', 'future'), bq.get('simule', False))
            Y, bZ, bt = (bq['miktar'], bq['giris'], bq.get('yon', 'LONG'))
            try:
                bM = anlik_fiyat_getir(J, b0)
            except X:
                bM = F(bq.get('anlik') or bZ)
            self.log_yaz(f'⏳ {O} ({bt}) pozisyonu kapatılıyor...')
            kapat_ok, ord_j = self._emir_kapat(J, b0, bt, Y, ig)
            if not ig and b0 == 'future' and not TESTNET_AKTIF:
                if not kapat_ok:
                    self.log_yaz(f'⚠️ {O} Binance üzerinde henüz kapanmadı.')
                    return
                time.sleep(0.25)
                raw_k = str(J).split(':')[0].replace('/', '').upper()
                kv = _fapi_gercek_kapanis_verisi_al(raw_k, bq)
                if kv.get('bulundu'):
                    bZ, bM, Y, kz, nf = (kv['giris'], kv['cikis'], kv['miktar'], kv['pnl_usdt'], kv['pnl_yuzde'])
                    _ig_kaydet(J, b0, bt, bZ, bM, Y, kz, nf, dl, bq.get('ozet', ''), tarih_str=kv.get('tarih'), binance_tran_id=kv.get('tran_id'), binance_onayli=True)
                else:
                    avg_p = F((ord_j or {}).get('avgPrice') or 0.0)
                    if avg_p > 0:
                        bM = avg_p
                    kz = (bZ - bM if bt == 'SHORT' else bM - bZ) * Y
                    marj_k = M(F(bq.get('borsa_marjin_usdt') or bq.get('marjin_usdt') or ((Y * bZ) / M(bq.get('kaldirac', 1), 1))), 1e-09)
                    nf = (kz / marj_k) * 100.0
                    _ig_kaydet(J, b0, bt, bZ, bM, Y, kz, nf, dl, bq.get('ozet', ''))
            else:
                kz = (bZ - bM if bt == 'SHORT' else bM - bZ) * Y
                nf = (bZ - bM if bt == 'SHORT' else bM - bZ) / M(bZ, 1e-9) * 100 * bq.get('kaldirac', 1)
                _ig_kaydet(J, b0, bt, bZ, bM, Y, kz, nf, dl, bq.get('ozet', ''))
            W += kz
            if ig and b0 == 'future':
                S += kz
            acik_islemler.pop(O, None)
            _ak_kaydet()
            self.log_yaz(f'✅ {O} ({bt}) [{dl}] kapatıldı! Net Sonuç: {kz:+.2f} USDT')
            tg_bildir(f'🖐 <b>{dl} ({O} - {bt})</b>\nSonuç: {kz:+.2f} USDT')
            if pJ:
                self.pozisyonlari_senkronize_et()
        except X as e:
            self.log_yaz(f'⚠️ {O} kapatılırken hata: {e}')

    def pozisyonlari_senkronize_et(self):
        global acik_islemler, V, T, W, S
        try:
            if not TESTNET_AKTIF:
                demo_k = [k_d for k_d, v_d in list(acik_islemler.items()) if I(v_d, dict) and v_d.get('simule', False)]
                if demo_k:
                    for k_d in demo_k:
                        acik_islemler.pop(k_d, None)
                    _ak_kaydet()
                canli_d = _fapi_canli_hesap_durumu_cek()
                if canli_d.get('bakiye_ok') and canli_d['wallet_balance'] > 0:
                    T = canli_d['wallet_balance']
                    V = canli_d['available_balance']
                if canli_d.get('pozisyon_ok'):
                    borsa_pozlar = canli_d.get('pozisyonlar', {})
                    acik_emir_set = canli_d.get('acik_emir_sembolleri', set())
                    for O_m, bq_m in list(acik_islemler.items()):
                        if not I(bq_m, dict) or bq_m.get('piyasa', 'future') != 'future':
                            continue
                        if O_m in borsa_pozlar:
                            bq_m['_kapali_onay_sayaci'] = 0
                        else:
                            acilis_z = F(bq_m.get('_acilis_ts', 0.0))
                            if acilis_z > 0 and (time.time() - acilis_z) < 10.0:
                                continue
                            bq_m['_kapali_onay_sayaci'] = int(bq_m.get('_kapali_onay_sayaci', 0)) + 1
                            if bq_m['_kapali_onay_sayaci'] < 2:
                                continue
                            J_m = bq_m.get('sembol', O_m.split(':', 1)[-1])
                            raw_m = str(J_m).split(':')[0].replace('/', '').upper()
                            if not _fapi_pozisyon_gercekten_kapali_mi(raw_m, bq_m.get('yon')):
                                bq_m['_kapali_onay_sayaci'] = 0
                                continue
                            kv_m = _fapi_gercek_kapanis_verisi_al(raw_m, bq_m)
                            if kv_m.get('bulundu'):
                                gercek_kapanis_pnl = kv_m['pnl_usdt']
                                W += gercek_kapanis_pnl
                                _ig_kaydet(J_m, 'future', kv_m['yon'], kv_m['giris'], kv_m['cikis'], kv_m['miktar'], gercek_kapanis_pnl, kv_m['pnl_yuzde'], 'BORSADA KAPANDI (SL/TP/MANUEL)', bq_m.get('ozet', ''), tarih_str=kv_m.get('tarih'), binance_tran_id=kv_m.get('tran_id'), binance_onayli=True)
                                self.log_yaz(f'🔄 [BORSA SENKRONİZASYONU] {O_m} kapandı (Net K/Z: {gercek_kapanis_pnl:+.2f} USDT)')
                            try:
                                _fapi_imzali_istek('DELETE', '/fapi/v1/allOpenOrders', {'symbol': raw_m})
                                _fapi_imzali_istek('DELETE', '/fapi/v1/algoOpenOrders', {'symbol': raw_m})
                            except X:
                                pass
                            acik_islemler.pop(O_m, None)
                    for O_b, bp in borsa_pozlar.items():
                        mev_b = acik_islemler.get(O_b)
                        if I(mev_b, dict):
                            mev_b['_kapali_onay_sayaci'] = 0
                            mev_b['giris'] = bp['giris']
                            mev_b['anlik'] = bp['anlik']
                            mev_b['borsa_mark_fiyat'] = bp['anlik']
                            mev_b['miktar'] = bp['miktar']
                            mev_b['yon'] = bp['yon']
                            mev_b['kaldirac'] = bp['kaldirac']
                            mev_b['borsa_pnl_usdt'] = bp['pnl_usdt']
                            mev_b['borsa_marjin_usdt'] = bp['marjin_usdt']
                            mev_b['marjin_usdt'] = bp['marjin_usdt']
                            mev_b['simule'] = False
                        else:
                            ep_b, yon_b = (bp['giris'], bp['yon'])
                            eski_meta = _son_acilan_islem_meta_hafizasi.get(O_b, {})
                            vars_sl = F(eski_meta.get('sl') or 0.0) if F(eski_meta.get('sl') or 0.0) > 0 else R(ep_b * (0.985 if yon_b == 'LONG' else 1.015), 6)
                            vars_tp = F(eski_meta.get('tp') or 0.0) if F(eski_meta.get('tp') or 0.0) > 0 else R(ep_b * (1.030 if yon_b == 'LONG' else 0.970), 6)
                            vars_tp_nihai = F(eski_meta.get('tp_nihai') or vars_tp)
                            acik_islemler[O_b] = {'sembol': bp['sembol'], 'yon': yon_b, 'piyasa': 'future', 'simule': False, 'kaldirac': bp['kaldirac'], 'giris': ep_b, 'anlik': bp['anlik'], 'borsa_mark_fiyat': bp['anlik'], 'sl': vars_sl, 'ilk_sl': vars_sl, 'tp': vars_tp, 'tp_nihai': vars_tp_nihai, 'miktar': bp['miktar'], 'marjin_usdt': bp['marjin_usdt'], 'borsa_marjin_usdt': bp['marjin_usdt'], 'borsa_pnl_usdt': bp['pnl_usdt'], 'risk_usdt': R(A(ep_b - vars_sl) * bp['miktar'], 2), 'skor': 80, 'kismi_tp_alindi': False, 'ozet': str(eski_meta.get('ozet') or '[Binance Hesabından Senkronize Edildi]'), 'giris_kurallari': [], 'htf_periyot': HTF_PERIYOT, 'mtf_periyot': MTF_PERIYOT, 'ltf_periyot': LTF_PERIYOT, 'mtf_sablonu': AKTIF_MTF_SABLONU, 'giris_modu': GIRIS_STRATEJI_MODU, '_acilis_ts': F(eski_meta.get('_acilis_ts') or time.time())}
                    _fapi_gecmis_tam_senkronize_et(borsa_pozlar=borsa_pozlar, zorla=False, log_fn=self.log_yaz)
                elif not canli_d.get('bakiye_ok'):
                    V, T = bakiye_getir()
            else:
                V, T = bakiye_getir()
            for O, bq in list(acik_islemler.items()):
                if not I(bq, dict):
                    continue
                J, b0, ig = (bq.get('sembol', O.split(':', 1)[-1]), bq.get('piyasa', 'future'), bq.get('simule', False))
                if not ig and b0 == 'future' and F(bq.get('borsa_mark_fiyat') or 0.0) > 0:
                    bM = F(bq['borsa_mark_fiyat'])
                else:
                    try:
                        bM = anlik_fiyat_getir(J, b0)
                    except X:
                        bM = F(bq.get('anlik') or bq.get('giris') or 0.0)
                if bM <= 0:
                    continue
                if O in a1:
                    a1[O]['fiyat'] = bM
                bq['anlik'] = bM
                bt, bZ, sl, tp = (bq.get('yon', 'LONG'), F(bq['giris']), F(bq['sl']), F(bq['tp']))
                oN, Y, gX = (F(bq.get('tp_nihai', tp)), F(bq['miktar']), bq.get('kismi_tp_alindi', False))
                nt = bt == 'SHORT'
                nu = (bZ - bM if nt else bM - bZ) / M(bZ, 1e-09) * 100 * F(bq.get('kaldirac', 1))
                nv = (sl > 0 and (bM >= sl if nt else bM <= sl))
                kV = (tp > 0 and (bM <= tp if nt else bM >= tp))
                gM = (oN > 0 and (bM <= (oN if gX else tp) if nt else bM >= (oN if gX else tp)))
                if nv:
                    self.log_yaz(f'🛑 [STOP-LOSS] {O} ({bt}) stop ({_fmt_f(sl)}) tetiklendi!')
                    kapat_ok_sl, ord_j_sl = self._emir_kapat(J, b0, bt, Y, ig)
                    if not ig and b0 == 'future' and not TESTNET_AKTIF:
                        if not kapat_ok_sl:
                            continue
                        time.sleep(0.25)
                        raw_sl = str(J).split(':')[0].replace('/', '').upper()
                        kv_sl = _fapi_gercek_kapanis_verisi_al(raw_sl, bq)
                        if kv_sl.get('bulundu'):
                            eB = kv_sl['pnl_usdt']
                            _ig_kaydet(J, b0, bt, kv_sl['giris'], kv_sl['cikis'], kv_sl['miktar'], eB, kv_sl['pnl_yuzde'], 'STOP-LOSS / BE' if gX else 'STOP-LOSS', bq.get('ozet', ''), tarih_str=kv_sl.get('tarih'), binance_tran_id=kv_sl.get('tran_id'), binance_onayli=True)
                        else:
                            avg_sl = F((ord_j_sl or {}).get('avgPrice') or 0.0)
                            if avg_sl > 0:
                                bM = avg_sl
                            eB = (bZ - bM if nt else bM - bZ) * Y
                            _ig_kaydet(J, b0, bt, bZ, bM, Y, eB, nu, 'STOP-LOSS / BE' if gX else 'STOP-LOSS', bq.get('ozet', ''))
                    else:
                        eB = (bZ - bM if nt else bM - bZ) * Y
                        _ig_kaydet(J, b0, bt, bZ, bM, Y, eB, nu, 'STOP-LOSS / BE' if gX else 'STOP-LOSS', bq.get('ozet', ''))
                    W += eB
                    if ig and b0 == 'future':
                        S += eB
                    acik_islemler.pop(O, None)
                    _ak_kaydet()
                    continue
                if KISMI_KAR_AL_AKTIF and (not gX) and kV:
                    raw_s_k = str(J).split(':')[0].replace('/', '').upper()
                    fe_s, _ = _fapi_hassasiyet_formatla(raw_s_k, Y * 0.5, None) if b0 == 'future' else (str(R(Y * 0.5, 6)), None)
                    fe = F(fe_s or 0.0)
                    jA = R(Y - fe, 6)
                    if fe > 0 and jA > 0:
                        kapat_ok_p, _ = self._emir_kapat(J, b0, bt, fe, ig)
                        if not ig and b0 == 'future' and not TESTNET_AKTIF and not kapat_ok_p:
                            continue
                        _, rU_s = _fapi_hassasiyet_formatla(raw_s_k, None, bZ) if b0 == 'future' else (None, str(R(bZ, 6)))
                        rU = F(rU_s or bZ)
                        ip = A(bM - bZ) * fe
                        _ig_kaydet(J, b0, bt, bZ, bM, fe, ip, nu, '3R %50 KISMİ KÂR AL', bq.get('ozet', ''))
                        W += ip
                        if ig and b0 == 'future':
                            S += ip
                        bq.update({'miktar': jA, 'sl': rU, 'tp': oN, 'risk_usdt': 0.0, 'kismi_tp_alindi': True})
                        _ak_kaydet()
                        continue
                if gM:
                    kapat_ok_tp, ord_j_tp = self._emir_kapat(J, b0, bt, Y, ig)
                    if not ig and b0 == 'future' and not TESTNET_AKTIF and not kapat_ok_tp:
                        continue
                    ip = A(bM - bZ) * Y
                    _ig_kaydet(J, b0, bt, bZ, bM, Y, ip, nu, 'NİHAİ TAKE-PROFIT', bq.get('ozet', ''))
                    W += ip
                    if ig and b0 == 'future':
                        S += ip
                    acik_islemler.pop(O, None)
                    _ak_kaydet()
            _ak_kaydet()
            self.arayuzu_guncelle()
        except X as e:
            self.log_yaz(f'⚠️ Senkronizasyon hatası: {e}')

    def isleme_gir(self, J, aU, P, al, mN=0, bG='', K=None, D=None):
        global acik_islemler, V, T, a4, MAKS_ACIK_ISLEM
        hd = D if D else 'spot' if PIYASA_MODU == 'spot' else 'future'
        ja, jb = (veri_ist(hd), emir_ist(hd))
        O = anahtar_yap(J, hd)
        if acik_islemler.get(O) is not None or aU not in ('LONG', 'SHORT') or (hd == 'spot' and aU == 'SHORT'):
            return
        mevcut_acik_sayisi = sum((1 for v in acik_islemler.values() if I(v, dict)))
        if mevcut_acik_sayisi >= a4:
            return
        H_kontrol = analiz_hafizasi.get(O) or analiz_hafizasi.get(J) or {}
        kFlt_kontrol = H_kontrol.get('konum_meta', {})
        mod1_sadece_birincil = ('1. Mod' in str(GIRIS_STRATEJI_MODU) or not IKINCIL_BOLGE_GIRIS_AKTIF)
        if not kFlt_kontrol.get('ltf_yon_uyumlu', True):
            return
        if not kFlt_kontrol.get('ltf_herhangi_tetik', False) or kFlt_kontrol.get('ltf_giris_emare_sayisi', 0) < 1:
            return
        if mod1_sadece_birincil:
            if not kFlt_kontrol.get('mod1_zorunlu_sart1', False) or not kFlt_kontrol.get('htf_arz_talep_bolgesinde', False):
                return
            if kFlt_kontrol.get('ltf_kirilim_aninda_erken_mi', False) or not kFlt_kontrol.get('onemli_giris_noktasinda_mi', True):
                return
        else:
            if not kFlt_kontrol.get('htf_zorunlu_bolge_onay', False) or kFlt_kontrol.get('saglanan_giris_sart_sayisi', 0) < 1:
                return
        try:
            eO = anlik_fiyat_getir(J, hd)
            P = eO if eO else P
        except X:
            pass
        if (aU == 'LONG' and al >= P) or (aU == 'SHORT' and al <= P):
            return
        Y, fk, kF = dinamik_miktar_hesapla(J, P, al, hd, mN)
        if not Y or Y <= 0:
            return
        mO = -1.0 if aU == 'SHORT' else 1.0
        raw_sym_ig = str(J).split(':')[0].replace('/', '').upper()
        if hd == 'future':
            _, f2_s = _fapi_hassasiyet_formatla(raw_sym_ig, None, al)
            f2 = F(f2_s) if f2_s and F(f2_s) > 0 else R(al, 6)
        else:
            try:
                f2 = F(ja.price_to_precision(J, al))
            except X:
                f2 = R(al, 6)
        iU_gercek = M(A(P - f2), P * aW)
        Y, fk, kF = dinamik_miktar_hesapla(J, P, f2, hd, mN)
        if not Y or Y <= 0:
            return
        agresif_mi_ig = bool(kFlt_kontrol.get('agresif_giris_mi', False))
        etkin_rr_ig = F(kFlt_kontrol.get('etkin_rr_orani') or (M(1.15, N(1.50, RISK_ODUL_ORANI * 0.58)) if agresif_mi_ig else RISK_ODUL_ORANI))
        pK = M(etkin_rr_ig + 0.6, NIHAI_TP_RR if not agresif_mi_ig else etkin_rr_ig + 0.8)
        ham_eo = M(1e-06, P + mO * iU_gercek * etkin_rr_ig)
        ham_gb = M(1e-06, P + mO * iU_gercek * pK)
        if hd == 'future':
            _, eo_s = _fapi_hassasiyet_formatla(raw_sym_ig, None, ham_eo)
            _, gb_s = _fapi_hassasiyet_formatla(raw_sym_ig, None, ham_gb)
            eo = F(eo_s) if eo_s and F(eo_s) > 0 else R(ham_eo, 6)
            gb = F(gb_s) if gb_s and F(gb_s) > 0 else R(ham_gb, 6)
        else:
            eo = R(ham_eo, 6)
            gb = R(ham_gb, 6)
        mP = False
        try:
            if hd == 'future':
                if TESTNET_AKTIF:
                    mP = True
                else:
                    ord_res = _fapi_gercek_vadeli_emir_ac(J, aU, Y, f2, eo, KALDIRAC, MARJIN_TIPI, self.log_yaz)
                    if I(ord_res, dict):
                        gercek_avg = F(ord_res.get('avgPrice') or 0.0)
                        gercek_qty = F(ord_res.get('executedQty') or ord_res.get('origQty') or 0.0)
                        if gercek_avg > 0:
                            P = gercek_avg
                        if gercek_qty > 0:
                            Y = gercek_qty
                            fk = (Y * P) / M(KALDIRAC, 1)
                            kF = R(A(P - f2) * Y, 2)
            else:
                if TESTNET_AKTIF:
                    mP = True
                else:
                    J_sp = _emir_sembolu(jb, J, 'spot')
                    jb.create_market_buy_order(J_sp, Y)
            acik_islemler[O] = {'sembol': J, 'yon': aU, 'piyasa': hd, 'simule': mP, 'kaldirac': KALDIRAC if hd == 'future' else 1, 'giris': P, 'anlik': P, 'sl': f2, 'ilk_sl': f2, 'tp': eo, 'tp_nihai': gb, 'miktar': Y, 'marjin_usdt': R(fk, 2), 'risk_usdt': kF, 'skor': mN, 'kismi_tp_alindi': False, 'ozet': bG, 'giris_kurallari': K or [], 'htf_periyot': HTF_PERIYOT, 'mtf_periyot': MTF_PERIYOT, 'ltf_periyot': LTF_PERIYOT, 'mtf_sablonu': AKTIF_MTF_SABLONU, 'giris_modu': GIRIS_STRATEJI_MODU, 'htf_aktif_bolge': kFlt_kontrol.get('aktif_htf_at_kutu'), '_acilis_ts': time.time(), '_sl_tp_senk_denendi': True}
            acik_islemler[O]['rontgen'] = islem_rontgeni_olustur(O, H_kontrol, acik_islemler[O])
            _ak_kaydet()
            V, T = bakiye_getir()
            self.arayuzu_guncelle()
            ng = '🟢' if aU == 'LONG' else '🔴'
            self.log_yaz(f'{ng} YENİ İŞLEM: {O} {aU} | Skor: {mN}/100 | Giriş: {_fmt_f(P)} | SL: {_fmt_f(f2)} | TP: {_fmt_f(eo)}')
            tg_bildir(f'{ng} <b>İŞLEM AÇILDI ({O} - {aU})</b>\n📌 Skor: {mN}/100 | Giriş: {P} | Stop: {f2} | TP1: {eo}')
        except X as e:
            self.log_yaz(f'⚠️ {O} Emir Hatası: {e}')

    def bot_ana_dongu(self):
        global aQ, V, T, bE, bot_calisiyor
        try:
            pariteleri_yukle(self.log_yaz)
            V, T = bakiye_getir()
            if aQ == 0:
                aQ = T
            self.log_yaz(f'✅ Tarama Başladı | Bakiye: {T:.2f} USDT | Parite: {L(ab)}')
        except X as e:
            self.log_yaz(f'⚠️ Borsa bağlantı hatası: {e}')
        while bot_calisiyor and not self._kapaniyor:
            try:
                self.pozisyonlari_senkronize_et()
                jr = 'spot' if PIYASA_MODU == 'spot' else 'future'
                for js in ('BTC/USDT', 'ETH/USDT'):
                    if not bot_calisiyor:
                        break
                    try:
                        veri_cek(js, MTF_PERIYOT, 70, jr)
                        veri_cek(js, LTF_PERIYOT, 70, jr)
                    except X:
                        pass
                qu = sorted(list(ab), key=lambda it: F(parite_hacim_map.get(anahtar_yap(it[0], it[1])) or parite_hacim_map.get(it[0]) or 0.0), reverse=True)
                mod1_sadece_birincil = ('1. Mod' in str(GIRIS_STRATEJI_MODU) or not IKINCIL_BOLGE_GIRIS_AKTIF)
                for bu, (J, b0) in enumerate(qu, start=1):
                    if not bot_calisiyor:
                        break
                    try:
                        bE = bu
                        O = anahtar_yap(J, b0)
                        bS = veri_cek(J, HTF_PERIYOT, 250, b0)
                        bw = veri_cek(J, MTF_PERIYOT, 250, b0)
                        aY = veri_cek(J, LTF_PERIYOT, 250, b0)
                        jB = _f(aY, 'close', -1)
                        H = mahserin_4_atlisi_confluence_analizi(J, bS, bw, aY, b0)
                        km_tarama = H.get('konum_meta', {})
                        sart1_t = bool(km_tarama.get('mod1_zorunlu_sart1', False))
                        ek_say_t = int(km_tarama.get('mod1_ek_sart_sayisi', 0))
                        olcek_sk_t = int(km_tarama.get('birincil_olcek_skoru', 0))
                        if H['sinyal'] in ('LONG', 'SHORT') and acik_islemler.get(O) is None and sum((1 for v in acik_islemler.values() if I(v, dict))) < a4:
                            if (mod1_sadece_birincil and sart1_t) or (not mod1_sadece_birincil and km_tarama.get('htf_zorunlu_bolge_onay', False)):
                                if km_tarama.get('ltf_herhangi_tetik', False):
                                    self.isleme_gir(J, H['sinyal'], H['giris'], H['sl'], H['skor'], H['ozet'], H['detayli_kurallar'], b0)
                        a1[O] = {'fiyat': jB, '4h': H['yon_4h'], '1h': H['yon_1h'], 'ana_yon': H['ana_yon'], 'skor': f"{H['skor']}/100", 'ltf': f"AÇIK ({acik_islemler[O]['yon']})" if I(acik_islemler.get(O), dict) else H['sinyal'], 'setup_detay': H['ozet'], 'oncelikli_bolge': (1 + ek_say_t) if sart1_t else 0, 'birincil_olcek_skoru': olcek_sk_t}
                        if I(acik_islemler.get(O), dict):
                            acik_islemler[O]['anlik'] = jB
                        if bu % 5 == 0:
                            self.durum_guncelle(f"Taranıyor: {bu}/{L(qu)} | Açık: {sum(1 for v in acik_islemler.values() if I(v,dict))}/{a4} 🟢", "#4ade80")
                            self.arayuzu_guncelle()
                        if bu % 25 == 0:
                            gc.collect()
                        time.sleep(0.05)
                    except X:
                        time.sleep(0.1)
                self.log_yaz(f'🔄 Tarama tamamlandı ({L(qu)} parite). 5sn sonra devam edecek...')
                for _ in range(5):
                    if not bot_calisiyor:
                        break
                    time.sleep(1)
            except BaseException as e:
                if not bot_calisiyor or self._kapaniyor:
                    break
                self.log_yaz(f'🛡️ Döngü hatası izole edildi: {e}')
                time.sleep(3)

    def botu_baslat_click(self, e=None):
        global bot_calisiyor
        if not bot_calisiyor:
            self._bot_baslangic_ts = time.time()
            self._bot_baslangic_w = F(W)
            bot_calisiyor = True
            self.btn_baslat.disabled = True
            self.btn_durdur.disabled = False
            self.durum_guncelle(f"Çalışıyor ({GIRIS_STRATEJI_MODU.split(':')[0]}) 🟢", "#4ade80")
            self.log_yaz(f"🚀 Bot Başlatıldı | {GIRIS_STRATEJI_MODU} | {HTF_PERIYOT}/{MTF_PERIYOT}/{LTF_PERIYOT}")
            threading.Thread(target=self.bot_ana_dongu, daemon=True).start()

    def botu_durdur_click(self, e=None):
        global bot_calisiyor
        bot_calisiyor = False
        self.btn_baslat.disabled = False
        self.btn_durdur.disabled = True
        self.durum_guncelle("Durduruldu 🔴", "#f87171")
        self.log_yaz("⏹ Bot durduruldu.")

    def tumunu_kapat_click(self, e=None):
        acik_list = [O_k for O_k, bq_k in list(acik_islemler.items()) if I(bq_k, dict)]
        if not acik_list:
            self.log_yaz("ℹ️ Açık işlem yok.")
            return
        def _run():
            for O_k in acik_list:
                self._poz_kapat(O_k, dl='ACİL TÜMÜNÜ KAPATMA', pJ=False)
            self.pozisyonlari_senkronize_et()
        threading.Thread(target=_run, daemon=True).start()

    def kz_sifirla_click(self, e=None):
        global W, _kz_sifirlama_ts
        W = 0.0
        _kz_sifirlama_ts = time.time()
        _ak_kaydet()
        self.arayuzu_guncelle()
        self.log_yaz("🔄 Toplam Net K/Z sıfırlandı.")

    def rontgen_goster(self, O_key):
        rg = islem_rontgeni_olustur(O_key)
        dlg = ft.AlertDialog(
            title=ft.Text(f"🔍 {O_key} — İşlem Röntgeni", size=16, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=360,
                height=380,
                content=ft.Column([ft.Text(rg.get("tam_rapor_metni", "-"), size=12, selectable=True)], scroll=ft.ScrollMode.AUTO),
            ),
            actions=[ft.TextButton("Kapat", on_click=lambda _: self._kapat_dlg(dlg))],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _kapat_dlg(self, dlg):
        dlg.open = False
        self.page.update()

    def ayarlari_kaydet_click(self, e=None):
        global PIYASA_MODU, TESTNET_AKTIF, MARJIN_TIPI, a4, MAKS_ACIK_ISLEM, MAKS_MARJIN_USDT, KALDIRAC, ISLEM_BASI_RISK_USDT, RISK_ODUL_ORANI, MIN_CONFLUENCE_SKORU, ae, STOP_BELIRLEME_MODU, API_KEY, API_SECRET, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY
        try:
            p_val = self.dd_piyasa.value
            yeni_p = 'her_ikisi' if 'HER İKİSİ' in p_val else ('future' if 'VADELİ' in p_val else 'spot')
            yeni_t = 'TESTNET' in str(self.dd_ag.value)
            giris_modu_uygula(self.dd_giris_modu.value)
            mtf_sablonu_uygula(self.dd_mtf.value)
            MARJIN_TIPI = self.dd_marjin.value
            STOP_BELIRLEME_MODU = self.dd_stop.value
            a4 = M(1, N(100, int(F(self.in_maks.value or a4)))); MAKS_ACIK_ISLEM = a4
            MAKS_MARJIN_USDT = M(0.5, F(self.in_marjin.value or MAKS_MARJIN_USDT))
            KALDIRAC = M(1, N(125, int(F(self.in_kaldirac.value or KALDIRAC))))
            ISLEM_BASI_RISK_USDT = M(0.1, F(self.in_risk.value or ISLEM_BASI_RISK_USDT))
            RISK_ODUL_ORANI = M(0.5, F(self.in_rr.value or RISK_ODUL_ORANI))
            MIN_CONFLUENCE_SKORU = M(10, N(100, int(F(self.in_skor.value or MIN_CONFLUENCE_SKORU))))
            ae = M(0, int(F(self.in_limit.value or 0)))
            API_KEY = self.in_api_key.value.strip()
            API_SECRET = self.in_api_sec.value.strip()
            TELEGRAM_TOKEN = self.in_tg_tok.value.strip()
            TELEGRAM_CHAT_ID = self.in_tg_id.value.strip()
            GEMINI_API_KEY = self.in_gem_key.value.strip()
            _api_kaydet_tam()
            borsa_kur(yeni_p, yeni_t)
            threading.Thread(target=lambda: pariteleri_yukle(self.log_yaz), daemon=True).start()
            self.log_yaz("💾 Tüm ayarlar ve API bilgileri kaydedildi!")
            self.arayuzu_guncelle()
        except X as ex:
            self.log_yaz(f"⚠️ Ayar kayıt hatası: {ex}")

    def arayuzu_guncelle(self):
        try:
            kU, rI, jq = (0.0, 0.0, 0)
            acik_kartlar = []
            for O, bq in list(acik_islemler.items()):
                if not I(bq, dict):
                    continue
                jq += 1
                gW, nD, bZ, bM, fk, k1, k0 = islem_kar_zarar_hesapla(O, bq)
                bt = bq.get('yon', 'LONG')
                sl, tp = (bq.get('sl', 0.0), bq.get('tp', 0.0))
                kU += gW
                rI += fk
                renk_pnl = "#4ade80" if gW >= 0 else "#f87171"
                acik_kartlar.append(
                    ft.Container(
                        bgcolor="#181825",
                        border_radius=10,
                        padding=10,
                        border=ft.border.all(1, "#313244"),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{O} ({bt} {k1}x)", weight=ft.FontWeight.BOLD, size=14, color="#38bdf8"),
                                ft.Text(f"{gW:+.2f} $ (%{nD:+.1f})", weight=ft.FontWeight.BOLD, size=14, color=renk_pnl),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Giriş: {_fmt_f(bZ)} | Anlık: {_fmt_f(bM)} | Marjin: {fk:.1f}$", size=12, color="#cbd5e1"),
                            ft.Text(f"SL: {_fmt_f(sl)} | TP: {_fmt_f(tp)} | Risk: -{k0:.2f}$", size=12, color="#94a3b8"),
                            ft.Row([
                                ft.ElevatedButton("🔍 Röntgen", bgcolor="#2563eb", color="#ffffff", height=32, on_click=lambda _, o=O: self.rontgen_goster(o)),
                                ft.ElevatedButton("🚨 Kapat", bgcolor="#ef4444", color="#ffffff", height=32, on_click=lambda _, o=O: threading.Thread(target=self._poz_kapat, args=(o,), daemon=True).start()),
                            ], spacing=8),
                        ], spacing=4),
                    )
                )
            qo = (T + kU) if T > 0 else (V + rI + kU)
            self.lbl_portfoy.value = f"{qo:.2f} USDT"
            self.lbl_serbest.value = f"{V:.2f} USDT"
            self.lbl_acik_pnl.value = f"{kU:+.2f} USDT"
            self.lbl_acik_pnl.color = "#4ade80" if kU >= 0 else "#f87171"
            self.lbl_net_pnl.value = f"{W:+.2f} USDT"
            self.lbl_net_pnl.color = "#4ade80" if W >= 0 else "#f87171"
            self.lbl_acik_sayi.value = f"{jq} / {a4}"
            self.col_acik.controls = acik_kartlar if acik_kartlar else [ft.Text("Şu an açık işlem bulunmuyor.", color="#94a3b8", size=13)]

            # Tarama listesi (ilk 50)
            kG = sorted(a1.items(), key=lambda x: (int(x[1].get('oncelikli_bolge', 0)), int(x[1].get('birincil_olcek_skoru', 0))), reverse=True)
            flt = self._arama_filtre.upper()
            tarama_kartlar = []
            for O, b in kG:
                if flt and flt not in O.upper():
                    continue
                if len(tarama_kartlar) >= 50:
                    break
                r_y = "#4ade80" if b.get('ana_yon') == 'BULLISH' else ("#f87171" if b.get('ana_yon') == 'BEARISH' else "#94a3b8")
                tarama_kartlar.append(
                    ft.Container(
                        bgcolor="#181825",
                        border_radius=8,
                        padding=8,
                        border=ft.border.all(1, "#2a2e39"),
                        on_click=lambda _, o=O: self.rontgen_goster(o),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{O} | {_fmt_f(b['fiyat'])}", weight=ft.FontWeight.BOLD, size=13, color="#f8fafc"),
                                ft.Text(f"{b['skor']} ({b['ltf']})", weight=ft.FontWeight.BOLD, size=12, color=r_y),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"HTF:{b['4h']} | MTF:{b['1h']} — {str(b.get('setup_detay', ''))[:95]}", size=11, color="#94a3b8"),
                        ], spacing=2),
                    )
                )
            self.col_tarama.controls = tarama_kartlar if tarama_kartlar else [ft.Text("Tarama verisi bekleniyor... Botu başlatın.", color="#94a3b8", size=13)]

            # Gecmis listesi
            top_g = L(ah)
            kaz_g = sum(1 for x in ah if F(x.get('pnl_usdt', 0)) > 0)
            wr_g = (kaz_g / top_g * 100.0) if top_g > 0 else 0.0
            net_g = sum(F(x.get('pnl_usdt', 0)) for x in ah)
            self.lbl_gecmis_ozet.value = f"Winrate: %{wr_g:.1f} ({kaz_g}/{top_g}) | Net K/Z: {net_g:+.2f} USDT"
            gecmis_kartlar = []
            for x in ah[:60]:
                pu = F(x.get('pnl_usdt', 0))
                rc = "#4ade80" if pu >= 0 else "#f87171"
                gecmis_kartlar.append(
                    ft.Container(
                        bgcolor="#181825",
                        border_radius=8,
                        padding=8,
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{x.get('sembol','-')} ({x.get('yon','-')})", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(f"{pu:+.2f} $ (%{F(x.get('pnl_yuzde',0)):+.1f})", weight=ft.FontWeight.BOLD, size=13, color=rc),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"{x.get('tarih','-')} | Giriş:{x.get('giris',0)} -> Çıkış:{x.get('cikis',0)} | {x.get('neden','-')}", size=11, color="#94a3b8"),
                        ], spacing=2),
                    )
                )
            self.col_gecmis.controls = gecmis_kartlar if gecmis_kartlar else [ft.Text("Henüz işlem geçmişi yok.", color="#94a3b8")]
            self.page.update()
        except X:
            pass

    def _ui_build(self):
        self.page.title = f"Alfa Trade Club [{BOT_VERSIYONU}]"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f172a"
        self.page.padding = 8

        self.lbl_durum = ft.Text(self._durum_metni, size=12, weight=ft.FontWeight.BOLD, color=self._durum_renk)
        self.lbl_portfoy = ft.Text("0.00 USDT", size=16, weight=ft.FontWeight.BOLD, color="#38bdf8")
        self.lbl_serbest = ft.Text("0.00 USDT", size=14, weight=ft.FontWeight.BOLD, color="#cbd5e1")
        self.lbl_acik_pnl = ft.Text("+0.00 USDT", size=16, weight=ft.FontWeight.BOLD, color="#4ade80")
        self.lbl_net_pnl = ft.Text("+0.00 USDT", size=14, weight=ft.FontWeight.BOLD, color="#f59e0b")
        self.lbl_acik_sayi = ft.Text(f"0 / {a4}", size=14, weight=ft.FontWeight.BOLD, color="#a78bfa")

        self.btn_baslat = ft.ElevatedButton("▶ Başlat", bgcolor="#10b981", color="#ffffff", on_click=self.botu_baslat_click)
        self.btn_durdur = ft.ElevatedButton("⏹ Durdur", bgcolor="#ef4444", color="#ffffff", disabled=True, on_click=self.botu_durdur_click)
        self.btn_tum_kapat = ft.ElevatedButton("🛑 Tümünü Kapat", bgcolor="#dc2626", color="#ffffff", on_click=self.tumunu_kapat_click)
        self.btn_kz_sifir = ft.ElevatedButton("🔄 K/Z Sıfırla", bgcolor="#475569", color="#ffffff", on_click=self.kz_sifirla_click)

        self.col_acik = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        tab_ozet = ft.Column([
            ft.Container(
                bgcolor="#1e293b",
                border_radius=10,
                padding=10,
                content=ft.Column([
                    ft.Row([ft.Text("🚀 Alfa Trade Club", size=15, weight=ft.FontWeight.BOLD, color="#f8fafc"), self.lbl_durum], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Column([ft.Text("Portföy", size=11, color="#94a3b8"), self.lbl_portfoy]),
                        ft.Column([ft.Text("Açık PnL", size=11, color="#94a3b8"), self.lbl_acik_pnl]),
                        ft.Column([ft.Text("Açık", size=11, color="#94a3b8"), self.lbl_acik_sayi]),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Column([ft.Text("Kullanılabilir", size=11, color="#94a3b8"), self.lbl_serbest]),
                        ft.Column([ft.Text("Net K/Z", size=11, color="#94a3b8"), self.lbl_net_pnl]),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([self.btn_baslat, self.btn_durdur, self.btn_tum_kapat, self.btn_kz_sifir], wrap=True, spacing=6),
                ], spacing=6),
            ),
            ft.Text("📌 Açık İşlemler", size=14, weight=ft.FontWeight.BOLD, color="#38bdf8"),
            self.col_acik,
        ], expand=True, spacing=8)

        self.col_tarama = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        def _ara_degisti(e):
            self._arama_filtre = e.control.value or ""
            self.arayuzu_guncelle()
        tab_tarama = ft.Column([
            ft.TextField(label="Parite Ara (Örn: BTC, SOL)", dense=True, on_change=_ara_degisti),
            self.col_tarama,
        ], expand=True, spacing=8)

        # Ayarlar sekmesi
        self.dd_piyasa = ft.Dropdown(label="Piyasa", value="HER İKİSİ (SPOT+VADELİ)" if PIYASA_MODU == 'her_ikisi' else ("VADELİ (FUTURES)" if PIYASA_MODU == 'future' else "SPOT"), options=[ft.dropdown.Option("HER İKİSİ (SPOT+VADELİ)"), ft.dropdown.Option("VADELİ (FUTURES)"), ft.dropdown.Option("SPOT")])
        self.dd_ag = ft.Dropdown(label="Ağ", value="TESTNET / DEMO" if TESTNET_AKTIF else "GERÇEK (MAINNET)", options=[ft.dropdown.Option("TESTNET / DEMO"), ft.dropdown.Option("GERÇEK (MAINNET)")])
        self.dd_giris_modu = ft.Dropdown(label="Giriş Modu", value=GIRIS_STRATEJI_MODU, options=[ft.dropdown.Option(x) for x in GIRIS_MODU_SECENEKLERI])
        self.dd_mtf = ft.Dropdown(label="MTF Şablonu", value=AKTIF_MTF_SABLONU, options=[ft.dropdown.Option(k) for k in MTF_SABLONLARI.keys()])
        self.dd_marjin = ft.Dropdown(label="Marjin Tipi", value=MARJIN_TIPI, options=[ft.dropdown.Option("ISOLATED"), ft.dropdown.Option("CROSSED")])
        self.dd_stop = ft.Dropdown(label="Stop Modu", value=STOP_BELIRLEME_MODU, options=[ft.dropdown.Option(x) for x in STOP_BELIRLEME_SECENEKLERI])
        self.in_maks = ft.TextField(label="Maks Açık İşlem", value=str(a4), dense=True)
        self.in_marjin = ft.TextField(label="Marjin (USDT)", value=str(MAKS_MARJIN_USDT), dense=True)
        self.in_kaldirac = ft.TextField(label="Kaldıraç (x)", value=str(KALDIRAC), dense=True)
        self.in_risk = ft.TextField(label="İşlem Başı Risk ($)", value=str(ISLEM_BASI_RISK_USDT), dense=True)
        self.in_rr = ft.TextField(label="Risk/Ödül (RR)", value=str(RISK_ODUL_ORANI), dense=True)
        self.in_skor = ft.TextField(label="Min Skor", value=str(MIN_CONFLUENCE_SKORU), dense=True)
        self.in_limit = ft.TextField(label="Parite Limiti (0=Tümü)", value=str(ae), dense=True)
        self.in_api_key = ft.TextField(label="Binance API Key", value=API_KEY, dense=True)
        self.in_api_sec = ft.TextField(label="Binance Secret Key", value=API_SECRET, password=True, can_reveal_password=True, dense=True)
        self.in_tg_tok = ft.TextField(label="Telegram Bot Token", value=TELEGRAM_TOKEN, dense=True)
        self.in_tg_id = ft.TextField(label="Telegram Chat ID", value=TELEGRAM_CHAT_ID, dense=True)
        self.in_gem_key = ft.TextField(label="Gemini API Key", value=GEMINI_API_KEY, password=True, can_reveal_password=True, dense=True)

        tab_ayarlar = ft.Column([
            self.dd_piyasa, self.dd_ag, self.dd_giris_modu, self.dd_mtf, self.dd_marjin, self.dd_stop,
            ft.Row([ft.Container(self.in_maks, expand=True), ft.Container(self.in_marjin, expand=True)]),
            ft.Row([ft.Container(self.in_kaldirac, expand=True), ft.Container(self.in_risk, expand=True)]),
            ft.Row([ft.Container(self.in_rr, expand=True), ft.Container(self.in_skor, expand=True)]),
            self.in_limit,
            ft.Divider(),
            self.in_api_key, self.in_api_sec, self.in_tg_tok, self.in_tg_id, self.in_gem_key,
            ft.ElevatedButton("💾 Tüm Ayarları ve API Bilgilerini Kaydet", bgcolor="#2563eb", color="#ffffff", on_click=self.ayarlari_kaydet_click),
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)

        # Gecmis sekmesi
        self.lbl_gecmis_ozet = ft.Text("Yükleniyor...", size=13, weight=ft.FontWeight.BOLD, color="#4ade80")
        self.col_gecmis = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        tab_gecmis = ft.Column([self.lbl_gecmis_ozet, self.col_gecmis], expand=True, spacing=8)

        # Loglar sekmesi
        self.txt_loglar = ft.Text("", size=11, font_family="monospace", color="#cbd5e1", selectable=True)
        tab_loglar = ft.Column([self.txt_loglar], scroll=ft.ScrollMode.AUTO, expand=True)

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            expand=True,
            tabs=[
                ft.Tab(text="Özet", content=ft.Container(tab_ozet, padding=6)),
                ft.Tab(text="Tarama", content=ft.Container(tab_tarama, padding=6)),
                ft.Tab(text="Ayarlar", content=ft.Container(tab_ayarlar, padding=6)),
                ft.Tab(text="Geçmiş", content=ft.Container(tab_gecmis, padding=6)),
                ft.Tab(text="Loglar", content=ft.Container(tab_loglar, padding=6)),
            ],
        )
        self.page.add(tabs)

def main(page: ft.Page):
    AlfaMobileBotController(page)

if __name__ == "__main__":
    ft.app(target=main)
