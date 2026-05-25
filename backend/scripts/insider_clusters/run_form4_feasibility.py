"""run_form4_feasibility.py — Stage 0 SEC Form 4 feasibility (R&D Cycle v2 / Cycle 1).

Validates 2019-06-01 → 2025-11-30 historical retrieval for insider cluster backtest.

Pipeline :
  1. Fetch SEC company_tickers.json → CIK→ticker map snapshot daté
  2. For each SP500 CIK : fetch submissions JSON (modern + paginated old) → Form 4 acc_no list in date range
  3. Parse each Form 4 XML : transaction code P, senior officer filter, value computation
  4. Detect clusters : ≥3 distinct senior insiders / 30d rolling / same CIK / cumul > $25k
  5. Match clusters to SP500 prices parquet (T to T+90 availability)
  6. Output feasibility_report.md + decision GO/escalade/STOP

Honors :
  - SEC rate limit ≤10 req/s + proper User-Agent
  - Disk cache (replay free)
  - Acceptance/filing date (no lookahead)
  - reportingOwnerCik (insider ID)
  - isDirector/isOfficer/officerTitle/isTenPercentOwner filter
  - Loss counters (parsing_error / non_sp500 / cik_unmatched / price_missing / t_plus_90_unavailable)

Usage :
  .venv/bin/python backend/scripts/insider_clusters/run_form4_feasibility.py \
    --start 2019-06-01 --end 2025-11-30 \
    --output backend/data/insider_clusters/feasibility_report.md
  .venv/bin/python backend/scripts/insider_clusters/run_form4_feasibility.py \
    --max-ciks 50 --quick-mode  # first-pass sampling
"""
from __future__ import annotations

import argparse
import json
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ============================================================================
# Constants
# ============================================================================

SEC_USER_AGENT = "Dexterio Research insider-clusters-feasibility blanchardalexayrtongood@gmail.com"
SEC_RATE_LIMIT_S = 0.11  # ~9 req/s safe under 10/s SEC limit
SEC_BASE_DATA = "https://data.sec.gov"
SEC_BASE_ARCHIVES = "https://www.sec.gov/Archives"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SP500_CONSTITUENTS_PATH = REPO_ROOT / "backend/data/universe/sp500_constituents.txt"
SP500_PRICES_PATH = REPO_ROOT / "backend/data/equities/sp500_prices_6.5y.parquet"
DATA_DIR = REPO_ROOT / "backend/data/insider_clusters"
CACHE_DIR = DATA_DIR / "cache"

CLUSTER_MIN_INSIDERS = 3        # ≥3 distinct senior insiders
CLUSTER_WINDOW_DAYS = 30        # rolling 30-day window
CLUSTER_MIN_VALUE_USD = 25_000  # cumulated transaction value > $25k
HOLDING_DAYS = 90               # T to T+90 availability requirement


# ============================================================================
# SEC EDGAR client (rate-limited + cached)
# ============================================================================

class SECEdgarClient:
    """Rate-limited SEC EDGAR HTTP client with disk cache."""

    def __init__(self, cache_dir: Path):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip,deflate",
        })
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_req = 0.0
        self.fetched = 0
        self.cached = 0
        self.errors = 0

    def get(self, url: str, cache_key: Optional[str] = None,
              force: bool = False) -> Optional[str]:
        """GET with rate limit + cache. Returns text or None on error."""
        cache_path = self.cache_dir / f"{cache_key}.cache" if cache_key else None
        if cache_path is not None and cache_path.exists() and not force:
            self.cached += 1
            return cache_path.read_text(encoding="utf-8")
        # rate limit
        delta = time.time() - self._last_req
        if delta < SEC_RATE_LIMIT_S:
            time.sleep(SEC_RATE_LIMIT_S - delta)
        try:
            resp = self.session.get(url, timeout=30)
            self._last_req = time.time()
            if resp.status_code == 404:
                # 404 = legitimate "not found" → cache empty marker
                if cache_path is not None:
                    cache_path.write_text("", encoding="utf-8")
                return ""
            resp.raise_for_status()
            text = resp.text
            self.fetched += 1
            if cache_path is not None:
                cache_path.write_text(text, encoding="utf-8")
            return text
        except Exception as e:
            self.errors += 1
            print(f"   [ERROR] {url}: {e}", flush=True)
            return None


# ============================================================================
# Phase 1 : CIK → ticker map snapshot
# ============================================================================

def fetch_cik_ticker_map(client: SECEdgarClient) -> dict:
    """Fetch company_tickers.json + persist dated snapshot. Returns raw SEC data dict."""
    raw = client.get(SEC_TICKERS_URL, cache_key="cik_ticker_master")
    if not raw:
        raise RuntimeError("Failed to fetch SEC ticker map")
    data = json.loads(raw)
    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": SEC_TICKERS_URL,
        "n_entries": len(data),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "cik_ticker_map.json").write_text(json.dumps(snapshot, indent=2))
    return data


def load_sp500_universe() -> set[str]:
    if not SP500_CONSTITUENTS_PATH.exists():
        raise FileNotFoundError(f"SP500 universe missing: {SP500_CONSTITUENTS_PATH}")
    return {
        line.strip().upper()
        for line in SP500_CONSTITUENTS_PATH.read_text().splitlines()
        if line.strip()
    }


def build_ticker_to_cik(sec_data: dict,
                          sp500_tickers: set[str]) -> tuple[dict[str, str], list[str]]:
    """Build ticker → CIK for SP500 universe. SEC file has 1 CIK : N tickers,
    so iterate per-entry and keep first CIK match per SP500 ticker."""
    ticker_to_cik: dict[str, str] = {}
    # SEC uses dashes (BRK-B) for share classes ; SP500 file may use dashes or dots.
    # Normalize both sides to dashes.
    sp500_norm = {t.replace(".", "-").upper(): t for t in sp500_tickers}
    for entry in sec_data.values():
        ticker = entry["ticker"].upper()
        ticker_norm = ticker.replace(".", "-")
        if ticker_norm in sp500_norm and sp500_norm[ticker_norm] not in ticker_to_cik:
            cik = str(entry["cik_str"]).zfill(10)
            ticker_to_cik[sp500_norm[ticker_norm]] = cik
    unmatched = sorted(sp500_tickers - ticker_to_cik.keys())
    return ticker_to_cik, unmatched


# ============================================================================
# Phase 2 : Submissions JSON → Form 4 acc_no list per CIK in date range
# ============================================================================

@dataclass
class FilingRef:
    """Form 4 filing reference (pre-XML-parse)."""
    cik: str            # 10-digit padded
    ticker: str
    accession: str      # accession number (with dashes)
    filing_date: str    # YYYY-MM-DD
    acceptance_dt: str  # ISO datetime (filing/acceptance date for lookahead-safe entry)
    primary_doc: str


def fetch_form4_filings_for_cik(client: SECEdgarClient, cik: str, ticker: str,
                                  start_date: str, end_date: str) -> list[FilingRef]:
    """Fetch all Form 4 filings for a CIK in [start_date, end_date]. Includes paginated history."""
    url = f"{SEC_BASE_DATA}/submissions/CIK{cik}.json"
    raw = client.get(url, cache_key=f"submissions_{cik}")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    filings: list[FilingRef] = []
    # Process recent filings
    recent = data.get("filings", {}).get("recent", {})
    _extract_form4(recent, cik, ticker, start_date, end_date, filings)
    # Process older paginated files
    for f in data.get("filings", {}).get("files", []):
        # Skip if entirely outside our date range
        f_to = f.get("filingTo", "")
        f_from = f.get("filingFrom", "")
        if f_to and f_to < start_date:
            continue  # all older than our window
        if f_from and f_from > end_date:
            continue  # all newer than our window
        sub_url = f"{SEC_BASE_DATA}/submissions/{f['name']}"
        sub_raw = client.get(sub_url, cache_key=f"submissions_{f['name'].replace('.json','')}")
        if not sub_raw:
            continue
        try:
            sub_data = json.loads(sub_raw)
            _extract_form4(sub_data, cik, ticker, start_date, end_date, filings)
        except json.JSONDecodeError:
            continue
    return filings


def _extract_form4(filings_dict: dict, cik: str, ticker: str,
                    start_date: str, end_date: str,
                    out: list[FilingRef]) -> None:
    forms = filings_dict.get("form", [])
    accessions = filings_dict.get("accessionNumber", [])
    filing_dates = filings_dict.get("filingDate", [])
    acceptance = filings_dict.get("acceptanceDateTime", [])
    primary_docs = filings_dict.get("primaryDocument", [])
    for i, form in enumerate(forms):
        if form != "4":
            continue
        fd = filing_dates[i] if i < len(filing_dates) else ""
        if not (start_date <= fd <= end_date):
            continue
        out.append(FilingRef(
            cik=cik,
            ticker=ticker,
            accession=accessions[i] if i < len(accessions) else "",
            filing_date=fd,
            acceptance_dt=acceptance[i] if i < len(acceptance) else "",
            primary_doc=primary_docs[i] if i < len(primary_docs) else "",
        ))


# ============================================================================
# Phase 3 : Form 4 XML parsing → transaction records
# ============================================================================

@dataclass
class TransactionRecord:
    """A single insider transaction (after XML parse + filtering)."""
    cik: str
    ticker: str
    accession: str
    filing_date: str
    acceptance_dt: str
    insider_cik: str          # rptOwnerCik (preferred ID)
    insider_name: str
    is_director: bool
    is_officer: bool
    is_ten_percent: bool
    officer_title: str
    transaction_code: str
    transaction_date: str
    shares: float
    price_per_share: float
    value_usd: float
    acquired: bool            # True if A, False if D


def fetch_form4_xml(client: SECEdgarClient, cik: str, accession: str,
                      primary_doc: str = "") -> Optional[str]:
    """Fetch the raw Form 4 XML for a given filing. Returns None if unavailable.

    Tries (in order) :
      1. primaryDocument hint (filename, with .htm→.xml swap if needed) — modern filings
      2. form4.xml at filing root — legacy convention
      3. index.json fallback to find any *.xml — last resort
    """
    cik_no_zeros = str(int(cik))
    acc_clean = accession.replace("-", "")
    base = f"{SEC_BASE_ARCHIVES}/edgar/data/{cik_no_zeros}/{acc_clean}"

    # Strategy 1 : derive XML filename from primaryDocument
    if primary_doc:
        fname = primary_doc.split("/")[-1]  # strip xslF345X0Y/ prefix if present
        if fname.endswith(".xml"):
            xml_fname = fname
        else:
            xml_fname = fname.rsplit(".", 1)[0] + ".xml"
        raw = client.get(f"{base}/{xml_fname}", cache_key=f"form4pd_{acc_clean}")
        if raw and raw.strip().startswith("<") and "ownershipDocument" in raw[:500]:
            return raw

    # Strategy 2 : form4.xml at root (legacy convention)
    raw = client.get(f"{base}/form4.xml", cache_key=f"form4_{acc_clean}")
    if raw and raw.strip().startswith("<") and "ownershipDocument" in raw[:500]:
        return raw

    # Strategy 3 : index.json fallback to find xml file in directory listing
    idx_raw = client.get(f"{base}/index.json", cache_key=f"form4idx_{acc_clean}")
    if not idx_raw:
        return None
    try:
        idx = json.loads(idx_raw)
    except json.JSONDecodeError:
        return None
    items = idx.get("directory", {}).get("item", [])
    for it in items:
        name = it.get("name", "")
        if name.endswith(".xml") and "form" in name.lower():
            return client.get(f"{base}/{name}", cache_key=f"form4alt_{acc_clean}")
    for it in items:
        name = it.get("name", "")
        if name.endswith(".xml"):
            return client.get(f"{base}/{name}", cache_key=f"form4anyxml_{acc_clean}")
    return None


def _xml_text(elem: Optional[ET.Element], path: str = "") -> str:
    if elem is None:
        return ""
    if path:
        sub = elem.find(path)
        if sub is None:
            return ""
        return (sub.text or "").strip()
    return (elem.text or "").strip()


def _xml_value(parent: Optional[ET.Element], child_path: str) -> str:
    """Form 4 wraps actual values in <value> sub-elements. Walk to it."""
    if parent is None:
        return ""
    sub = parent.find(child_path)
    if sub is None:
        return ""
    val = sub.find("value")
    if val is not None:
        return (val.text or "").strip()
    return (sub.text or "").strip()


def _xml_bool(elem: Optional[ET.Element], path: str) -> bool:
    txt = _xml_value(elem, path).lower()
    if not txt:
        # Try direct tag without <value>
        sub = elem.find(path) if elem is not None else None
        if sub is not None:
            txt = (sub.text or "").strip().lower()
    return txt in ("true", "1", "y", "yes")


def parse_form4_xml(xml_text: str, ref: FilingRef
                      ) -> tuple[list[TransactionRecord], Optional[str]]:
    """Parse Form 4 XML into transaction records. Returns (records, error_msg)."""
    if not xml_text or not xml_text.strip():
        return [], "empty_xml"
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [], f"xml_parse_error: {e}"

    # Issuer
    issuer = root.find("issuer")
    if issuer is None:
        return [], "no_issuer"
    issuer_cik = _xml_text(issuer, "issuerCik")
    if issuer_cik:
        issuer_cik = issuer_cik.zfill(10)

    records: list[TransactionRecord] = []
    # Iterate reportingOwners (may be multiple — but typically 1 per Form 4)
    for owner in root.findall("reportingOwner"):
        owner_id = owner.find("reportingOwnerId")
        owner_cik = _xml_text(owner_id, "rptOwnerCik") if owner_id is not None else ""
        if owner_cik:
            owner_cik = owner_cik.zfill(10)
        owner_name = _xml_text(owner_id, "rptOwnerName") if owner_id is not None else ""
        rel = owner.find("reportingOwnerRelationship")
        is_director = _xml_bool(rel, "isDirector") if rel is not None else False
        is_officer = _xml_bool(rel, "isOfficer") if rel is not None else False
        is_ten_pct = _xml_bool(rel, "isTenPercentOwner") if rel is not None else False
        officer_title = _xml_text(rel, "officerTitle") if rel is not None else ""

        # Iterate non-derivative transactions
        for tx in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
            coding = tx.find("transactionCoding")
            tx_code = _xml_value(coding, "transactionCode") if coding is not None else ""
            tx_date = _xml_value(tx, "transactionDate")
            amounts = tx.find("transactionAmounts")
            shares_str = _xml_value(amounts, "transactionShares") if amounts is not None else ""
            price_str = _xml_value(amounts, "transactionPricePerShare") if amounts is not None else ""
            ad_code = _xml_value(amounts, "transactionAcquiredDisposedCode") if amounts is not None else ""
            try:
                shares = float(shares_str) if shares_str else 0.0
            except ValueError:
                shares = 0.0
            try:
                price = float(price_str) if price_str else 0.0
            except ValueError:
                price = 0.0
            value_usd = shares * price
            records.append(TransactionRecord(
                cik=issuer_cik or ref.cik,
                ticker=ref.ticker,
                accession=ref.accession,
                filing_date=ref.filing_date,
                acceptance_dt=ref.acceptance_dt,
                insider_cik=owner_cik,
                insider_name=owner_name,
                is_director=is_director,
                is_officer=is_officer,
                is_ten_percent=is_ten_pct,
                officer_title=officer_title,
                transaction_code=tx_code,
                transaction_date=tx_date,
                shares=shares,
                price_per_share=price,
                value_usd=value_usd,
                acquired=(ad_code == "A"),
            ))
    return records, None


# ============================================================================
# Phase 4 : Cluster detection
# ============================================================================

@dataclass
class ClusterEvent:
    """A confirmed cluster event (≥3 senior insiders, 30d window, cumul > $25k)."""
    cik: str
    ticker: str
    confirmation_date: str       # filing/acceptance date of 3rd insider's filing (entry signal time)
    transaction_dates: list[str]
    insider_ciks: list[str]
    cluster_size: int            # n distinct senior insiders
    cumul_value_usd: float
    accession_numbers: list[str]


def is_senior(rec: TransactionRecord) -> bool:
    """Senior officer filter per spec : isDirector | isOfficer | officerTitle keywords. Excludes 10% holders."""
    if rec.is_ten_percent:
        return False
    if rec.is_director or rec.is_officer:
        return True
    title = rec.officer_title.lower()
    if any(kw in title for kw in ["ceo", "cfo", "coo", "president", "chairman", "chief", "director"]):
        return True
    return False


def detect_clusters(records: list[TransactionRecord]) -> list[ClusterEvent]:
    """Detect ≥3 distinct senior insiders / 30d rolling window / same CIK / cumul > $25k.

    Cluster confirmation date = filing/acceptance date of the 3rd insider's filing
    (anti-lookahead : we use filing date, not transaction date).

    Each filing × (insider_cik) is grouped. Multiple transactions same filing same insider
    aggregate into one "buy event" per insider.
    """
    # Filter to code "P" (open market purchase), acquired, senior, value > 0
    p_records = [
        r for r in records
        if r.transaction_code == "P"
        and r.acquired
        and is_senior(r)
        and r.value_usd > 0
        and r.insider_cik
    ]
    # Group by (cik, accession, insider_cik) → aggregate value (one filing per insider per company)
    by_filing: dict[tuple[str, str, str], dict] = {}
    for r in p_records:
        key = (r.cik, r.accession, r.insider_cik)
        if key not in by_filing:
            by_filing[key] = {
                "cik": r.cik,
                "ticker": r.ticker,
                "accession": r.accession,
                "filing_date": r.filing_date,
                "acceptance_dt": r.acceptance_dt,
                "insider_cik": r.insider_cik,
                "value_usd": 0.0,
            }
        by_filing[key]["value_usd"] += r.value_usd
    insider_filings = list(by_filing.values())
    # Sort by (cik, filing_date)
    insider_filings.sort(key=lambda x: (x["cik"], x["filing_date"]))

    # Group by issuer CIK then sweep with a 30-day rolling window
    clusters: list[ClusterEvent] = []
    by_cik: dict[str, list[dict]] = defaultdict(list)
    for f in insider_filings:
        by_cik[f["cik"]].append(f)

    for cik_id, filings in by_cik.items():
        if len(filings) < CLUSTER_MIN_INSIDERS:
            continue
        # Sliding window on filing_date
        n = len(filings)
        for i in range(n):
            window = [filings[i]]
            window_insiders = {filings[i]["insider_cik"]}
            anchor_date = datetime.strptime(filings[i]["filing_date"], "%Y-%m-%d")
            j = i + 1
            while j < n:
                fj_date = datetime.strptime(filings[j]["filing_date"], "%Y-%m-%d")
                if (fj_date - anchor_date).days > CLUSTER_WINDOW_DAYS:
                    break
                window.append(filings[j])
                window_insiders.add(filings[j]["insider_cik"])
                if len(window_insiders) >= CLUSTER_MIN_INSIDERS:
                    cumul = sum(f["value_usd"] for f in window)
                    if cumul > CLUSTER_MIN_VALUE_USD:
                        # Confirmation = filing date of the filing that brought us to ≥3 insiders
                        conf_filing = filings[j]
                        clusters.append(ClusterEvent(
                            cik=cik_id,
                            ticker=window[0]["ticker"],
                            confirmation_date=conf_filing["filing_date"],
                            transaction_dates=[w["filing_date"] for w in window],
                            insider_ciks=sorted(window_insiders),
                            cluster_size=len(window_insiders),
                            cumul_value_usd=cumul,
                            accession_numbers=[w["accession"] for w in window],
                        ))
                        # Skip ahead to avoid double-counting same anchor cluster
                        break
                j += 1

    # Deduplicate : keep first cluster per CIK per ~30d (avoid overlapping windows on same anchor)
    deduped: list[ClusterEvent] = []
    seen_keys: set[tuple[str, str]] = set()
    clusters.sort(key=lambda c: (c.cik, c.confirmation_date))
    last_cik: Optional[str] = None
    last_date: Optional[datetime] = None
    for c in clusters:
        c_dt = datetime.strptime(c.confirmation_date, "%Y-%m-%d")
        if last_cik == c.cik and last_date is not None and (c_dt - last_date).days < CLUSTER_WINDOW_DAYS:
            continue
        deduped.append(c)
        last_cik = c.cik
        last_date = c_dt
    return deduped


# ============================================================================
# Phase 5 : Match clusters to SP500 prices (T to T+90 availability)
# ============================================================================

def check_price_availability(clusters: list[ClusterEvent],
                              prices_df: pd.DataFrame
                              ) -> tuple[list[ClusterEvent], list[ClusterEvent], dict[str, int]]:
    """Return (exploitable, unexploitable, loss_counters)."""
    # Build lookup : ticker → set of dates
    if "date" in prices_df.columns:
        prices_df = prices_df.copy()
        prices_df["date"] = pd.to_datetime(prices_df["date"])
        ticker_dates: dict[str, pd.Series] = {
            sym: g["date"].dt.normalize()
            for sym, g in prices_df.groupby("symbol")
        }
    else:
        return [], clusters, {"price_missing": len(clusters)}

    exploitable: list[ClusterEvent] = []
    unexploitable: list[ClusterEvent] = []
    loss = {"price_missing": 0, "t_plus_90_unavailable": 0}
    for c in clusters:
        ds = ticker_dates.get(c.ticker)
        if ds is None or ds.empty:
            loss["price_missing"] += 1
            unexploitable.append(c)
            continue
        t = pd.to_datetime(c.confirmation_date).normalize()
        # Need next trading day at/after T (entry) AND a trading day at/after T+90 (exit)
        t_plus_90 = t + pd.Timedelta(days=HOLDING_DAYS)
        has_t_or_after = (ds >= t).any()
        has_exit = (ds >= t_plus_90).any()
        if not has_t_or_after:
            loss["price_missing"] += 1
            unexploitable.append(c)
            continue
        if not has_exit:
            loss["t_plus_90_unavailable"] += 1
            unexploitable.append(c)
            continue
        exploitable.append(c)
    return exploitable, unexploitable, loss


# ============================================================================
# Phase 6 : Report generation + decision
# ============================================================================

def render_report(*, args, ticker_to_cik: dict[str, str],
                    unmatched_tickers: list[str],
                    sp500_universe: set[str],
                    n_filings_total: int,
                    parsed_records: list[TransactionRecord],
                    parse_errors: int,
                    clusters_all: list[ClusterEvent],
                    exploitable: list[ClusterEvent],
                    unexploitable: list[ClusterEvent],
                    loss_counters: dict[str, int],
                    client: SECEdgarClient,
                    elapsed_s: float) -> str:
    """Render the feasibility markdown report."""
    n_events = len(exploitable)
    if n_events >= 100:
        decision = "GO Cycle 1 backtest baseline"
        decision_emoji = "✅ GO"
    elif n_events >= 30:
        decision = "Escalade user §0.3 point 5 (extension historique vs pivot Cycle 2)"
        decision_emoji = "⚠️ ESCALADE"
    else:
        decision = "STOP propre — non-testable sur scope actuel 6.5y. Pas d'extension auto."
        decision_emoji = "🛑 STOP"

    # Stats
    n_p = sum(1 for r in parsed_records if r.transaction_code == "P")
    n_p_senior = sum(1 for r in parsed_records if r.transaction_code == "P" and is_senior(r) and r.acquired)
    cluster_sizes = [c.cluster_size for c in exploitable]
    sizes_dist = {3: 0, 4: 0, 5: 0, 6: 0}
    for s in cluster_sizes:
        if s >= 6:
            sizes_dist[6] += 1
        else:
            sizes_dist[s] = sizes_dist.get(s, 0) + 1
    annual: dict[int, int] = defaultdict(int)
    for c in exploitable:
        y = int(c.confirmation_date[:4])
        annual[y] += 1
    annual_str = " | ".join(f"{y}: {annual[y]}" for y in sorted(annual.keys()))

    # Loss breakdown
    n_unmatched_cik = len(unmatched_tickers)
    cik_unmatched_count = n_unmatched_cik

    lines: list[str] = []
    lines.append(f"# Stage 0 — SEC Form 4 Feasibility Report")
    lines.append("")
    lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Window** : {args.start} → {args.end}")
    lines.append(f"**Mode** : {'QUICK (max-ciks=' + str(args.max_ciks) + ')' if args.max_ciks else 'FULL SP500'}")
    lines.append(f"**Elapsed** : {elapsed_s:.1f}s")
    lines.append("")
    lines.append(f"## Decision : {decision_emoji}")
    lines.append("")
    lines.append(f"**N events exploitables** : **{n_events}**")
    lines.append("")
    lines.append(f"**Threshold rules (frozen pré-spec)** :")
    lines.append(f"- ≥ 100 → GO Cycle 1 backtest")
    lines.append(f"- 30 ≤ n < 100 → Escalade user §0.3 point 5")
    lines.append(f"- < 30 → STOP propre, non-testable scope actuel")
    lines.append("")
    lines.append(f"**Verdict** : {decision}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Sources & coverage")
    lines.append("")
    lines.append(f"- **CIK→ticker map** : `{SEC_TICKERS_URL}` (snapshot dated, persisted in `cik_ticker_map.json`)")
    lines.append(f"- **Submissions API** : `{SEC_BASE_DATA}/submissions/CIK<CIK>.json`")
    lines.append(f"- **Form 4 XML** : `{SEC_BASE_ARCHIVES}/edgar/data/<CIK>/<acc_no>/form4.xml`")
    lines.append(f"- **Period demanded** : {args.start} → {args.end}")
    lines.append(f"- **SP500 universe** : {len(sp500_universe)} tickers (constituents 2026-current rétroprojeté ; survivorship bias documenté)")
    lines.append(f"- **Tickers matched to CIK** : {len(ticker_to_cik)}")
    lines.append(f"- **Tickers unmatched** : {n_unmatched_cik}{' (' + ', '.join(unmatched_tickers[:10]) + ('...' if len(unmatched_tickers) > 10 else '') + ')' if unmatched_tickers else ''}")
    lines.append("")
    lines.append("## SEC client stats")
    lines.append("")
    lines.append(f"- Fetched (network) : {client.fetched}")
    lines.append(f"- Cached (disk hit) : {client.cached}")
    lines.append(f"- Errors : {client.errors}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Filings funnel")
    lines.append("")
    lines.append(f"| Stage | Count |")
    lines.append(f"|---|---:|")
    lines.append(f"| Form 4 filings retrieved (raw, in window) | {n_filings_total} |")
    lines.append(f"| Form 4 XML parse errors | {parse_errors} |")
    lines.append(f"| Transactions parsed (any code) | {len(parsed_records)} |")
    lines.append(f"| Transactions code P (open market purchase) | {n_p} |")
    lines.append(f"| Transactions code P + senior + acquired | {n_p_senior} |")
    lines.append(f"| Clusters ≥3 senior insiders 30d cumul > $25k (raw) | {len(clusters_all)} |")
    lines.append(f"| Clusters with prices T to T+90 available (exploitable) | {n_events} |")
    lines.append("")
    lines.append("## Loss counters")
    lines.append("")
    lines.append(f"| Stage | Count |")
    lines.append(f"|---|---:|")
    lines.append(f"| `parsing_error` (XML invalid / schema issue) | {parse_errors} |")
    lines.append(f"| `cik_unmatched` (SP500 ticker → CIK absent du map) | {cik_unmatched_count} |")
    lines.append(f"| `non_sp500` (Form 4 hors SP500 universe) | 0 (filtered upstream) |")
    lines.append(f"| `price_missing` (cluster confirmé mais pas de prix à T) | {loss_counters.get('price_missing', 0)} |")
    lines.append(f"| `t_plus_90_unavailable` (prix à T mais pas à T+90) | {loss_counters.get('t_plus_90_unavailable', 0)} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Distributions (exploitable events only)")
    lines.append("")
    lines.append(f"### Annual distribution")
    lines.append("")
    lines.append(f"`{annual_str}`")
    lines.append("")
    lines.append(f"### Cluster size distribution")
    lines.append("")
    lines.append(f"| Cluster size | Count |")
    lines.append(f"|---|---:|")
    for size in sorted(sizes_dist.keys()):
        label = f"{size}+" if size == 6 else str(size)
        lines.append(f"| {label} | {sizes_dist[size]} |")
    lines.append("")
    if exploitable:
        lines.append(f"### Sample exploitable events (top 10 by cumul value)")
        lines.append("")
        lines.append(f"| ticker | confirm_date | n_insiders | cumul_$ |")
        lines.append(f"|---|---|---:|---:|")
        for c in sorted(exploitable, key=lambda x: -x.cumul_value_usd)[:10]:
            lines.append(f"| {c.ticker} | {c.confirmation_date} | {c.cluster_size} | {c.cumul_value_usd:,.0f} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Methodology notes")
    lines.append("")
    lines.append(f"- **Filing/acceptance date** used for cluster confirmation (anti-lookahead : `filingDate` from submissions JSON)")
    lines.append(f"- **Insider ID** via `reportingOwnerCik` (preferred over name to avoid homonym issues)")
    lines.append(f"- **Senior filter** : `isDirector` OR `isOfficer` OR title keywords (CEO/CFO/COO/President/Chairman/Director). Excludes `isTenPercentOwner=true`.")
    lines.append(f"- **Cluster definition** : ≥3 distinct senior insider CIKs / same issuer CIK / 30-day rolling window on filing_date / cumul transaction value > $25k")
    lines.append(f"- **Survivorship bias** : SP500 universe = 2026-current constituents file. Tickers délisted/M&A pre-2026 NOT included. Documented for Stage 2 correction (point-in-time SP500 historical reconstitution required before paper).")
    lines.append(f"- **Rate limit** : ≤9 req/s (under SEC 10/s cap). Cache aggressive disk-backed.")
    lines.append("")
    return "\n".join(lines)


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2019-06-01")
    parser.add_argument("--end", default="2025-11-30")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "feasibility_report.md")
    parser.add_argument("--max-ciks", type=int, default=0,
                          help="Cap CIKs processed (0 = full SP500). Useful for first-pass quick sampling.")
    parser.add_argument("--quick-mode", action="store_true",
                          help="Skip XML fetching for filings beyond first 100 per CIK (sample mode).")
    parser.add_argument("--persist-records", action="store_true",
                          help="Save parsed transactions to parquet for audit.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Stage 0] Form 4 feasibility {args.start} → {args.end}", flush=True)
    t0 = time.time()

    client = SECEdgarClient(CACHE_DIR)

    # Phase 1 : Maps
    print("[1/6] Fetching CIK→ticker map...", flush=True)
    sec_data = fetch_cik_ticker_map(client)
    sp500 = load_sp500_universe()
    ticker_to_cik, unmatched = build_ticker_to_cik(sec_data, sp500)
    print(f"      SP500 universe: {len(sp500)} tickers, matched to CIK: {len(ticker_to_cik)}, unmatched: {len(unmatched)}", flush=True)

    # Limit CIKs if requested
    cik_items = sorted(ticker_to_cik.items())
    if args.max_ciks and args.max_ciks > 0:
        cik_items = cik_items[:args.max_ciks]
        print(f"      LIMITED to first {len(cik_items)} CIKs (sample mode)", flush=True)

    # Phase 2 : Submissions → Form 4 filings list per CIK
    print(f"[2/6] Enumerating Form 4 filings for {len(cik_items)} CIKs...", flush=True)
    all_filings: list[FilingRef] = []
    for idx, (ticker, cik) in enumerate(cik_items):
        if idx % 50 == 0 or idx == len(cik_items) - 1:
            print(f"      [{idx+1}/{len(cik_items)}] {ticker} ({cik})... fetched={client.fetched} cached={client.cached}", flush=True)
        filings = fetch_form4_filings_for_cik(client, cik, ticker, args.start, args.end)
        all_filings.extend(filings)
    print(f"      Total Form 4 filings in window: {len(all_filings)}", flush=True)

    # Phase 3 : Parse XMLs
    print(f"[3/6] Fetching & parsing {len(all_filings)} Form 4 XMLs...", flush=True)
    parsed_records: list[TransactionRecord] = []
    parse_errors = 0
    n_filings = len(all_filings)
    # Optional sample limit per CIK in quick mode
    if args.quick_mode:
        # Stratified temporal sample : evenly distributed across the date range per CIK
        # to avoid bias toward recent filings (which would miss 2020 panic / 2022 bear)
        by_cik_filings: dict[str, list[FilingRef]] = defaultdict(list)
        for f in all_filings:
            by_cik_filings[f.cik].append(f)
        sampled: list[FilingRef] = []
        cap = 100
        for cik_id, fs in by_cik_filings.items():
            fs_sorted = sorted(fs, key=lambda x: x.filing_date)
            if len(fs_sorted) <= cap:
                sampled.extend(fs_sorted)
            else:
                # Evenly-spaced indices across full date range (not just first/last 100)
                step = len(fs_sorted) / cap
                indices = sorted(set(int(i * step) for i in range(cap)))
                sampled.extend(fs_sorted[i] for i in indices if i < len(fs_sorted))
        print(f"      QUICK MODE (stratified temporal): capped at {cap} filings per CIK → {len(sampled)} filings", flush=True)
        all_filings = sampled
        n_filings = len(all_filings)

    for i, ref in enumerate(all_filings):
        if i % 200 == 0 or i == n_filings - 1:
            print(f"      [{i+1}/{n_filings}] {ref.ticker} {ref.accession}... net={client.fetched} cache={client.cached} err={client.errors}", flush=True)
        xml = fetch_form4_xml(client, ref.cik, ref.accession, ref.primary_doc)
        if xml is None:
            parse_errors += 1
            continue
        recs, err = parse_form4_xml(xml, ref)
        if err is not None:
            parse_errors += 1
            continue
        parsed_records.extend(recs)
    print(f"      Parsed {len(parsed_records)} transactions, {parse_errors} parse errors", flush=True)

    # Persist parsed records (optional)
    if args.persist_records and parsed_records:
        rec_df = pd.DataFrame([r.__dict__ for r in parsed_records])
        rec_df.to_parquet(DATA_DIR / "parsed_form4.parquet", index=False)
        print(f"      Persisted parsed records → parsed_form4.parquet", flush=True)

    # Phase 4 : Cluster detection
    print(f"[4/6] Detecting clusters (≥{CLUSTER_MIN_INSIDERS} senior insiders / "
            f"{CLUSTER_WINDOW_DAYS}d / cumul > ${CLUSTER_MIN_VALUE_USD:,})...", flush=True)
    clusters_all = detect_clusters(parsed_records)
    print(f"      Raw clusters detected: {len(clusters_all)}", flush=True)

    # Phase 5 : Price match
    print(f"[5/6] Matching clusters to SP500 prices (T to T+{HOLDING_DAYS}d availability)...", flush=True)
    if not SP500_PRICES_PATH.exists():
        raise FileNotFoundError(f"SP500 prices missing: {SP500_PRICES_PATH}")
    prices_df = pd.read_parquet(SP500_PRICES_PATH)
    exploitable, unexploitable, loss = check_price_availability(clusters_all, prices_df)
    print(f"      Exploitable: {len(exploitable)} | Unexploitable: {len(unexploitable)} | "
            f"price_missing={loss['price_missing']} t+90_unavailable={loss['t_plus_90_unavailable']}",
            flush=True)

    # Phase 6 : Report
    elapsed = time.time() - t0
    print(f"[6/6] Generating report... (elapsed={elapsed:.1f}s)", flush=True)
    report = render_report(
        args=args,
        ticker_to_cik=ticker_to_cik,
        unmatched_tickers=unmatched,
        sp500_universe=sp500,
        n_filings_total=n_filings,
        parsed_records=parsed_records,
        parse_errors=parse_errors,
        clusters_all=clusters_all,
        exploitable=exploitable,
        unexploitable=unexploitable,
        loss_counters=loss,
        client=client,
        elapsed_s=elapsed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"\n=== Report → {args.output}", flush=True)
    print(f"=== Decision: n events = {len(exploitable)}", flush=True)
    if len(exploitable) >= 100:
        print("=== ✅ GO Cycle 1 backtest", flush=True)
    elif len(exploitable) >= 30:
        print("=== ⚠️  Escalade user", flush=True)
    else:
        print("=== 🛑 STOP propre", flush=True)


if __name__ == "__main__":
    main()
