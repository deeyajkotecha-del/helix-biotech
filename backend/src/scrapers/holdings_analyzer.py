"""
Holdings Analyzer

Analyzes 13F holdings data to identify:
- Quarter-over-quarter changes
- New positions
- Closed positions
- Consensus positions across specialist funds
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from collections import defaultdict
from typing import Optional
import csv


@dataclass
class HoldingChange:
    """Represents a change in a fund's position"""
    ticker: str
    company_name: str
    cusip: str
    fund_name: str
    
    # Current quarter
    current_shares: int
    current_value_k: int  # in thousands
    current_pct_of_portfolio: float
    
    # Previous quarter
    prev_shares: Optional[int]
    prev_value_k: Optional[int]
    prev_pct_of_portfolio: Optional[float]
    
    # Changes
    shares_change: int
    shares_change_pct: Optional[float]
    value_change_k: int
    
    # Flags
    is_new_position: bool
    is_closed_position: bool
    is_increased: bool
    is_decreased: bool
    
    current_quarter: str  # e.g., "Q3 2024"
    previous_quarter: Optional[str]


# Common biotech company CUSIP to ticker mapping
# In production, you'd use a full mapping service (OpenFIGI, etc.)
# This is a starter list of commonly held biotech names
CUSIP_TO_TICKER = {
    # Large/Mid Cap Biotech
    "00287Y109": "ABBV",   # AbbVie
    "009290103": "AMGN",   # Amgen
    "09062X103": "BIIB",   # Biogen
    "12504L109": "CELG",   # Celgene (now BMS)
    "25470M109": "GILD",   # Gilead
    "45168D104": "ILMN",   # Illumina
    "45781M101": "INCY",   # Incyte
    "46120E602": "IONS",   # Ionis
    "58933Y105": "MRNA",   # Moderna
    "63935N107": "NVAX",   # Novavax
    "75886F107": "REGN",   # Regeneron
    "78409V104": "SRPT",   # Sarepta
    "88025U109": "VRTX",   # Vertex
    
    # Clinical Stage / Emerging
    "00289Y107": "ABVX",   # Abivax
    "00847B102": "AKRO",   # Akero
    "02043Q107": "ALNY",   # Alnylam
    "03674X106": "ANNX",   # Annexon
    "04016X101": "ARQT",   # Arcus Bio
    "05379J107": "AVXL",   # Anavex
    "09857F108": "BMRN",   # BioMarin
    "10889B100": "BPMC",   # Blueprint
    "12573L106": "CGEN",   # Compugen
    "14149Y108": "CRSP",   # CRISPR
    "17275R102": "CPRX",   # Catalyst Pharma
    "22160N109": "CORT",   # Corcept
    "26817C107": "DXCM",   # Dexcom
    "29261A100": "ENTA",   # Enanta
    "30225T102": "EXEL",   # Exelixis
    "35908M106": "FRPT",   # Freshpet
    "38268T103": "GOSS",   # Gossamer
    "40416E103": "HALO",   # Halozyme
    "45337C102": "IMVT",   # Immunovant
    "45778K101": "INSM",   # Insmed
    "46266C105": "IONS",   # Ionis
    "49714P108": "KRTX",   # Karuna (now BMS)
    "54465A100": "LOVE",   # Lovesac
    "55261F104": "MDGL",   # Madrigal
    "58463J304": "MRK",    # Merck
    "58933Y105": "MRNA",   # Moderna
    "606822104": "MIST",   # Milestone
    "62886E108": "NBIX",   # Neurocrine
    "67066G104": "NVTA",   # Invitae
    "67103H107": "OPK",    # Opko
    "70614W100": "PCRX",   # Pacira
    "71944F106": "PCVX",   # Vaxcyte
    "73939C105": "PTGX",   # Protagonist
    "74587V107": "PRTA",   # Prothena
    "74967X103": "RXRX",   # Recursion
    "75943R102": "RGEN",   # Repligen
    "78440X101": "SGEN",   # Seagen (now Pfizer)
    "81721M109": "SNDX",   # Syndax
    "82489T104": "SHPG",   # Shire (now Takeda)
    "84680Y108": "SUPN",   # Supernus
    "87901J105": "TGTX",   # TG Therapeutics
    "88025T103": "VIR",    # Vir Bio
    "88632Q103": "TVTX",   # Travere
    "89236T109": "TRVN",   # Trevena
    "91324P102": "UNH",    # UnitedHealth
    "91913Y100": "RARE",   # Ultragenyx
    "92345Y106": "VRTX",   # Vertex
    "92532W103": "VRNA",   # Verona
    "92553P201": "VCEL",   # Vericel
    "95790P107": "WERN",   # Werner
    "98422D105": "XNCR",   # Xencor
    "98978V103": "ZNTL",   # Zentalis
}


def load_filings_from_json(data_dir: str = "data/13f") -> list[dict]:
    """Load all saved 13F filings from JSON files"""
    data_path = Path(data_dir)
    filings = []
    
    for json_file in data_path.glob("*.json"):
        with open(json_file) as f:
            filings.append(json.load(f))
    
    return filings


def get_ticker_from_cusip(cusip: str) -> Optional[str]:
    """
    Convert CUSIP to ticker.
    
    In production, use OpenFIGI API or a proper mapping service.
    This is a simplified version with common biotechs.
    """
    return CUSIP_TO_TICKER.get(cusip)


def calculate_qoq_changes(
    current_filing: dict,
    previous_filing: Optional[dict]
) -> list[HoldingChange]:
    """
    Calculate quarter-over-quarter changes between two filings.
    
    Returns list of HoldingChange objects for each position.
    """
    changes = []
    
    # Build lookup for previous holdings
    prev_holdings = {}
    if previous_filing:
        for h in previous_filing.get("holdings", []):
            prev_holdings[h["cusip"]] = h
    
    # Calculate total portfolio value for percentage calculations
    current_total = current_filing.get("total_value", 0) or 1
    prev_total = previous_filing.get("total_value", 0) if previous_filing else 1
    
    # Process current holdings
    current_cusips = set()
    for h in current_filing.get("holdings", []):
        cusip = h["cusip"]
        current_cusips.add(cusip)
        
        ticker = get_ticker_from_cusip(cusip)
        
        current_shares = h.get("shares", 0)
        current_value = h.get("value", 0)
        current_pct = (current_value / current_total * 100) if current_total else 0
        
        prev = prev_holdings.get(cusip)
        
        if prev:
            prev_shares = prev.get("shares", 0)
            prev_value = prev.get("value", 0)
            prev_pct = (prev_value / prev_total * 100) if prev_total else 0
            
            shares_change = current_shares - prev_shares
            shares_change_pct = (shares_change / prev_shares * 100) if prev_shares else None
            value_change = current_value - prev_value
            
            is_new = False
            is_increased = shares_change > 0
            is_decreased = shares_change < 0
        else:
            prev_shares = None
            prev_value = None
            prev_pct = None
            shares_change = current_shares
            shares_change_pct = None
            value_change = current_value
            is_new = True
            is_increased = False
            is_decreased = False
        
        change = HoldingChange(
            ticker=ticker or f"CUSIP:{cusip[:6]}",
            company_name=h.get("company_name", ""),
            cusip=cusip,
            fund_name=current_filing.get("fund_name", "Unknown"),
            current_shares=current_shares,
            current_value_k=current_value,
            current_pct_of_portfolio=round(current_pct, 2),
            prev_shares=prev_shares,
            prev_value_k=prev_value,
            prev_pct_of_portfolio=round(prev_pct, 2) if prev_pct else None,
            shares_change=shares_change,
            shares_change_pct=round(shares_change_pct, 1) if shares_change_pct else None,
            value_change_k=value_change,
            is_new_position=is_new,
            is_closed_position=False,
            is_increased=is_increased,
            is_decreased=is_decreased,
            current_quarter=current_filing.get("report_date", ""),
            previous_quarter=previous_filing.get("report_date") if previous_filing else None,
        )
        
        changes.append(change)
    
    # Find closed positions (in previous but not current)
    if previous_filing:
        for cusip, prev in prev_holdings.items():
            if cusip not in current_cusips:
                ticker = get_ticker_from_cusip(cusip)
                prev_value = prev.get("value", 0)
                prev_pct = (prev_value / prev_total * 100) if prev_total else 0
                
                change = HoldingChange(
                    ticker=ticker or f"CUSIP:{cusip[:6]}",
                    company_name=prev.get("company_name", ""),
                    cusip=cusip,
                    fund_name=current_filing.get("fund_name", "Unknown"),
                    current_shares=0,
                    current_value_k=0,
                    current_pct_of_portfolio=0,
                    prev_shares=prev.get("shares", 0),
                    prev_value_k=prev_value,
                    prev_pct_of_portfolio=round(prev_pct, 2),
                    shares_change=-prev.get("shares", 0),
                    shares_change_pct=-100.0,
                    value_change_k=-prev_value,
                    is_new_position=False,
                    is_closed_position=True,
                    is_increased=False,
                    is_decreased=False,
                    current_quarter=current_filing.get("report_date", ""),
                    previous_quarter=previous_filing.get("report_date"),
                )
                
                changes.append(change)
    
    return changes


def analyze_consensus_positions(all_changes: list[HoldingChange]) -> dict:
    """
    Identify positions that multiple specialist funds are building/trimming.
    
    Returns dict of ticker -> consensus analysis
    """
    # Group changes by ticker
    by_ticker = defaultdict(list)
    for change in all_changes:
        if change.ticker and not change.ticker.startswith("CUSIP:"):
            by_ticker[change.ticker].append(change)
    
    consensus = {}
    
    for ticker, changes in by_ticker.items():
        funds_holding = len(changes)
        funds_increasing = sum(1 for c in changes if c.is_increased or c.is_new_position)
        funds_decreasing = sum(1 for c in changes if c.is_decreased or c.is_closed_position)
        
        total_value = sum(c.current_value_k for c in changes)
        avg_portfolio_weight = sum(c.current_pct_of_portfolio for c in changes) / len(changes)
        
        # Determine consensus direction
        if funds_increasing > funds_decreasing and funds_increasing >= 2:
            direction = "ACCUMULATING"
        elif funds_decreasing > funds_increasing and funds_decreasing >= 2:
            direction = "DISTRIBUTING"
        else:
            direction = "MIXED"
        
        consensus[ticker] = {
            "ticker": ticker,
            "company_name": changes[0].company_name,
            "specialist_fund_count": funds_holding,
            "funds_increasing": funds_increasing,
            "funds_decreasing": funds_decreasing,
            "consensus_direction": direction,
            "total_value_mm": round(total_value / 1000, 1),  # Convert to millions
            "avg_portfolio_weight_pct": round(avg_portfolio_weight, 2),
            "funds": [
                {
                    "name": c.fund_name,
                    "shares": c.current_shares,
                    "value_mm": round(c.current_value_k / 1000, 1),
                    "pct_of_portfolio": c.current_pct_of_portfolio,
                    "change": "NEW" if c.is_new_position else 
                             "CLOSED" if c.is_closed_position else
                             f"+{c.shares_change_pct}%" if c.is_increased else
                             f"{c.shares_change_pct}%" if c.is_decreased else
                             "UNCHANGED"
                }
                for c in changes
            ]
        }
    
    # Sort by fund count and value
    consensus = dict(sorted(
        consensus.items(),
        key=lambda x: (x[1]["specialist_fund_count"], x[1]["total_value_mm"]),
        reverse=True
    ))
    
    return consensus


def find_new_positions(all_changes: list[HoldingChange]) -> list[dict]:
    """Find all new positions opened this quarter"""
    new_positions = [c for c in all_changes if c.is_new_position]
    
    # Group by ticker
    by_ticker = defaultdict(list)
    for pos in new_positions:
        if pos.ticker and not pos.ticker.startswith("CUSIP:"):
            by_ticker[pos.ticker].append(pos)
    
    results = []
    for ticker, positions in by_ticker.items():
        results.append({
            "ticker": ticker,
            "company_name": positions[0].company_name,
            "funds_initiating": len(positions),
            "total_value_mm": round(sum(p.current_value_k for p in positions) / 1000, 1),
            "funds": [
                {
                    "name": p.fund_name,
                    "shares": p.current_shares,
                    "value_mm": round(p.current_value_k / 1000, 1),
                    "pct_of_portfolio": p.current_pct_of_portfolio,
                }
                for p in positions
            ]
        })
    
    # Sort by number of funds initiating
    results.sort(key=lambda x: x["funds_initiating"], reverse=True)
    
    return results


def find_largest_increases(all_changes: list[HoldingChange], top_n: int = 20) -> list[dict]:
    """Find the largest position increases by dollar value"""
    increases = [
        c for c in all_changes 
        if c.is_increased and not c.is_new_position and c.value_change_k > 0
    ]
    
    # Sort by value change
    increases.sort(key=lambda x: x.value_change_k, reverse=True)
    
    results = []
    for c in increases[:top_n]:
        results.append({
            "ticker": c.ticker,
            "company_name": c.company_name,
            "fund_name": c.fund_name,
            "value_added_mm": round(c.value_change_k / 1000, 1),
            "shares_change_pct": c.shares_change_pct,
            "current_value_mm": round(c.current_value_k / 1000, 1),
            "pct_of_portfolio": c.current_pct_of_portfolio,
        })
    
    return results


def generate_summary_report(data_dir: str = "data/13f") -> dict:
    """
    Generate a comprehensive summary report of 13F activity.
    
    This is the "smart money" intelligence that WhaleWisdom doesn't provide.
    """
    filings = load_filings_from_json(data_dir)
    
    if not filings:
        return {"error": "No filings found"}
    
    # Group filings by fund
    by_fund = defaultdict(list)
    for f in filings:
        by_fund[f["fund_name"]].append(f)
    
    # Sort each fund's filings by date
    for fund_name in by_fund:
        by_fund[fund_name].sort(
            key=lambda x: x.get("report_date", ""),
            reverse=True
        )
    
    # Calculate QoQ changes for each fund
    all_changes = []
    for fund_name, fund_filings in by_fund.items():
        if len(fund_filings) >= 1:
            current = fund_filings[0]
            previous = fund_filings[1] if len(fund_filings) > 1 else None
            changes = calculate_qoq_changes(current, previous)
            all_changes.extend(changes)
    
    # Generate analyses
    report = {
        "generated_at": date.today().isoformat(),
        "funds_analyzed": list(by_fund.keys()),
        "consensus_positions": analyze_consensus_positions(all_changes),
        "new_positions": find_new_positions(all_changes),
        "largest_increases": find_largest_increases(all_changes),
        "total_holdings_analyzed": len(all_changes),
    }
    
    return report


def export_to_csv(report: dict, output_dir: str = "data/reports"):
    """Export report data to CSV files for easy analysis"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Export consensus positions
    if report.get("consensus_positions"):
        with open(output_path / "consensus_positions.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Ticker", "Company", "# Funds", "Accumulating", "Distributing",
                "Direction", "Total Value ($M)", "Avg Weight (%)"
            ])
            for ticker, data in report["consensus_positions"].items():
                writer.writerow([
                    ticker,
                    data["company_name"],
                    data["specialist_fund_count"],
                    data["funds_increasing"],
                    data["funds_decreasing"],
                    data["consensus_direction"],
                    data["total_value_mm"],
                    data["avg_portfolio_weight_pct"],
                ])
    
    # Export new positions
    if report.get("new_positions"):
        with open(output_path / "new_positions.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Ticker", "Company", "# Funds Initiating", "Total Value ($M)"
            ])
            for pos in report["new_positions"]:
                writer.writerow([
                    pos["ticker"],
                    pos["company_name"],
                    pos["funds_initiating"],
                    pos["total_value_mm"],
                ])
    
    print(f"Reports exported to {output_path}")


if __name__ == "__main__":
    print("Generating 13F analysis report...")
    report = generate_summary_report()
    
    if "error" not in report:
        print(f"\nFunds analyzed: {len(report['funds_analyzed'])}")
        print(f"Total holdings analyzed: {report['total_holdings_analyzed']}")
        
        print("\n" + "=" * 60)
        print("TOP CONSENSUS POSITIONS (held by 3+ specialist funds)")
        print("=" * 60)
        
        for ticker, data in list(report["consensus_positions"].items())[:10]:
            if data["specialist_fund_count"] >= 3:
                print(f"\n{ticker} - {data['company_name']}")
                print(f"  Funds: {data['specialist_fund_count']} | "
                      f"Direction: {data['consensus_direction']} | "
                      f"Value: ${data['total_value_mm']}M")
                for fund in data["funds"]:
                    print(f"    - {fund['name']}: ${fund['value_mm']}M ({fund['change']})")
        
        print("\n" + "=" * 60)
        print("NEW POSITIONS THIS QUARTER")
        print("=" * 60)
        
        for pos in report["new_positions"][:10]:
            print(f"\n{pos['ticker']} - {pos['company_name']}")
            print(f"  {pos['funds_initiating']} funds initiated | ${pos['total_value_mm']}M total")
        
        # Export to CSV
        export_to_csv(report)
    else:
        print(f"Error: {report['error']}")
