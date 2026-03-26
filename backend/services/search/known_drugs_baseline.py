"""
SatyaBio — Known Drugs Baseline
================================
A curated set of ~250 well-known drugs so the novelty detector can distinguish
"under the radar" assets from already-established therapies.

Categories:
  1. FDA-approved blockbusters (top 100 by revenue)
  2. Major late-stage pipeline drugs (Phase 3+)
  3. Well-known checkpoint inhibitors, ADCs, targeted therapies
  4. Common drugs that appear in trial comparator arms

This is used by the Regional News Miner's novelty detector to avoid
flagging pembrolizumab or semaglutide as "novel."
"""

# Each entry: canonical_name → set of aliases (lowercase)
# The novelty detector checks if a candidate matches ANY alias.

KNOWN_DRUGS = {
    # ── Checkpoint Inhibitors / Immuno-Oncology ──
    "pembrolizumab": {"pembrolizumab", "keytruda", "mk-3475", "lambrolizumab"},
    "nivolumab": {"nivolumab", "opdivo", "bms-936558", "ono-4538"},
    "atezolizumab": {"atezolizumab", "tecentriq", "mpdl3280a"},
    "durvalumab": {"durvalumab", "imfinzi", "medi4736"},
    "avelumab": {"avelumab", "bavencio", "msb0010718c"},
    "ipilimumab": {"ipilimumab", "yervoy", "mdx-010"},
    "cemiplimab": {"cemiplimab", "libtayo", "regn2810"},
    "tremelimumab": {"tremelimumab", "imjudo"},
    "dostarlimab": {"dostarlimab", "jemperli", "tsr-042"},
    "retifanlimab": {"retifanlimab", "zynyz"},
    "tislelizumab": {"tislelizumab", "tevimbra", "bgb-a317"},
    "sintilimab": {"sintilimab", "tyvyt", "ibi308"},
    "camrelizumab": {"camrelizumab", "shr-1210"},
    "toripalimab": {"toripalimab", "loqtorzi", "js001"},

    # ── ADCs (Antibody-Drug Conjugates) ──
    "trastuzumab deruxtecan": {"trastuzumab deruxtecan", "enhertu", "t-dxd", "ds-8201", "ds8201"},
    "sacituzumab govitecan": {"sacituzumab govitecan", "trodelvy", "immu-132"},
    "enfortumab vedotin": {"enfortumab vedotin", "padcev", "agS-22m6e", "ev"},
    "trastuzumab emtansine": {"trastuzumab emtansine", "kadcyla", "t-dm1", "ado-trastuzumab"},
    "brentuximab vedotin": {"brentuximab vedotin", "adcetris", "sgn-35"},
    "polatuzumab vedotin": {"polatuzumab vedotin", "polivy"},
    "loncastuximab tesirine": {"loncastuximab tesirine", "zynlonta", "adct-402"},
    "mirvetuximab soravtansine": {"mirvetuximab soravtansine", "elahere", "imgn853"},
    "disitamab vedotin": {"disitamab vedotin", "aidixi", "rc48"},
    "datopotamab deruxtecan": {"datopotamab deruxtecan", "dato-dxd", "ds-1062"},
    "patritumab deruxtecan": {"patritumab deruxtecan", "her3-dxd", "u3-1402"},
    "ifinatamab deruxtecan": {"ifinatamab deruxtecan", "i-dxd", "ds-7300"},

    # ── KRAS Inhibitors ──
    "sotorasib": {"sotorasib", "lumakras", "amg 510", "amg510"},
    "adagrasib": {"adagrasib", "krazati", "mrtx849", "mrtx-849"},
    "divarasib": {"divarasib", "gdc-6036", "gdc6036"},
    "garsorasib": {"garsorasib", "d-1553", "d1553"},
    "glecirasib": {"glecirasib", "jab-21822", "jab21822"},
    "fulzerasib": {"fulzerasib", "ibi351", "ibi-351"},

    # ── Targeted Oncology (non-KRAS) ──
    "osimertinib": {"osimertinib", "tagrisso", "azd9291"},
    "alectinib": {"alectinib", "alecensa"},
    "lorlatinib": {"lorlatinib", "lorbrena", "pf-06463922"},
    "selpercatinib": {"selpercatinib", "retevmo", "loxo-292"},
    "pralsetinib": {"pralsetinib", "gavreto", "blu-667"},
    "capmatinib": {"capmatinib", "tabrecta", "inc280"},
    "tepotinib": {"tepotinib", "tepmetko", "msc2156119j"},
    "entrectinib": {"entrectinib", "rozlytrek", "rxdx-101"},
    "larotrectinib": {"larotrectinib", "vitrakvi", "loxo-101"},
    "tucatinib": {"tucatinib", "tukysa", "ono-4538"},
    "olaparib": {"olaparib", "lynparza", "azd2281"},
    "rucaparib": {"rucaparib", "rubraca"},
    "niraparib": {"niraparib", "zejula", "mk-4827"},
    "talazoparib": {"talazoparib", "talzenna", "bmn-673"},
    "inavolisib": {"inavolisib", "itovebi", "gdc-0077"},
    "alpelisib": {"alpelisib", "piqray", "byl719"},
    "abemaciclib": {"abemaciclib", "verzenio", "ly2835219"},
    "palbociclib": {"palbociclib", "ibrance", "pd-0332991"},
    "ribociclib": {"ribociclib", "kisqali", "lee011"},
    "venetoclax": {"venetoclax", "venclexta", "abt-199"},
    "ibrutinib": {"ibrutinib", "imbruvica", "pci-32765"},
    "acalabrutinib": {"acalabrutinib", "calquence", "acp-196"},
    "zanubrutinib": {"zanubrutinib", "brukinsa", "bgb-3111"},
    "pirtobrutinib": {"pirtobrutinib", "jaypirca", "loxo-305"},
    "idelalisib": {"idelalisib", "zydelig"},
    "copanlisib": {"copanlisib", "aliqopa"},
    "umbralisib": {"umbralisib", "ukoniq"},
    "selinexor": {"selinexor", "xpovio", "kpt-330"},
    "lenvatinib": {"lenvatinib", "lenvima", "e7080"},
    "cabozantinib": {"cabozantinib", "cabometyx", "cometriq", "xl184"},
    "regorafenib": {"regorafenib", "stivarga", "bay 73-4506"},
    "sorafenib": {"sorafenib", "nexavar", "bay 43-9006"},
    "sunitinib": {"sunitinib", "sutent", "su11248"},
    "axitinib": {"axitinib", "inlyta", "ag-013736"},
    "pazopanib": {"pazopanib", "votrient", "gw786034"},
    "erlotinib": {"erlotinib", "tarceva"},
    "gefitinib": {"gefitinib", "iressa"},
    "afatinib": {"afatinib", "gilotrif"},
    "dacomitinib": {"dacomitinib", "vizimpro"},
    "imatinib": {"imatinib", "gleevec", "sti571"},
    "dasatinib": {"dasatinib", "sprycel"},
    "nilotinib": {"nilotinib", "tasigna"},
    "bosutinib": {"bosutinib", "bosulif"},
    "ponatinib": {"ponatinib", "iclusig"},
    "asciminib": {"asciminib", "scemblix"},

    # ── Bispecifics ──
    "epcoritamab": {"epcoritamab", "epkinly"},
    "glofitamab": {"glofitamab", "columvi"},
    "teclistamab": {"teclistamab", "tecvayli"},
    "mosunetuzumab": {"mosunetuzumab", "lunsumio"},
    "elranatamab": {"elranatamab", "elrexfio"},
    "talquetamab": {"talquetamab", "talvey"},
    "blinatumomab": {"blinatumomab", "blincyto"},
    "cadonilimab": {"cadonilimab", "ak104"},
    "ivonescimab": {"ivonescimab", "ak112"},
    "zanidatamab": {"zanidatamab", "zymeworks"},

    # ── CAR-T / Cell Therapy ──
    "axicabtagene ciloleucel": {"axicabtagene ciloleucel", "yescarta", "axi-cel"},
    "tisagenlecleucel": {"tisagenlecleucel", "kymriah"},
    "lisocabtagene maraleucel": {"lisocabtagene maraleucel", "breyanzi", "liso-cel"},
    "brexucabtagene autoleucel": {"brexucabtagene autoleucel", "tecartus"},
    "idecabtagene vicleucel": {"idecabtagene vicleucel", "abecma", "ide-cel"},
    "ciltacabtagene autoleucel": {"ciltacabtagene autoleucel", "carvykti", "cilta-cel"},
    "lifileucel": {"lifileucel", "amtagvi", "ln-144"},

    # ── GLP-1 / Metabolic ──
    "semaglutide": {"semaglutide", "ozempic", "wegovy", "rybelsus"},
    "tirzepatide": {"tirzepatide", "mounjaro", "zepbound", "ly3298176"},
    "liraglutide": {"liraglutide", "victoza", "saxenda"},
    "dulaglutide": {"dulaglutide", "trulicity", "ly2189265"},
    "exenatide": {"exenatide", "byetta", "bydureon"},
    "orforglipron": {"orforglipron", "ly3502970"},
    "survodutide": {"survodutide", "bi 456906"},
    "retatrutide": {"retatrutide", "ly3437943"},
    "resmetirom": {"resmetirom", "rezdiffra", "mgl-3196"},

    # ── Neuroscience / Alzheimer's ──
    "lecanemab": {"lecanemab", "leqembi", "ban2401"},
    "donanemab": {"donanemab", "kisunla", "ly3002813"},
    "aducanumab": {"aducanumab", "aduhelm", "biib037"},

    # ── Immunology / Autoimmune ──
    "dupilumab": {"dupilumab", "dupixent"},
    "secukinumab": {"secukinumab", "cosentyx"},
    "risankizumab": {"risankizumab", "skyrizi"},
    "guselkumab": {"guselkumab", "tremfya"},
    "upadacitinib": {"upadacitinib", "rinvoq"},
    "baricitinib": {"baricitinib", "olumiant"},
    "tofacitinib": {"tofacitinib", "xeljanz"},
    "ruxolitinib": {"ruxolitinib", "jakafi", "jakavi"},
    "deucravacitinib": {"deucravacitinib", "sotyktu"},
    "efgartigimod": {"efgartigimod", "vyvgart"},
    "anifrolumab": {"anifrolumab", "saphnelo"},
    "belimumab": {"belimumab", "benlysta"},

    # ── Anti-VEGF / Ophthalmology ──
    "bevacizumab": {"bevacizumab", "avastin"},
    "ramucirumab": {"ramucirumab", "cyramza"},
    "aflibercept": {"aflibercept", "eylea"},
    "ranibizumab": {"ranibizumab", "lucentis"},
    "faricimab": {"faricimab", "vabysmo"},

    # ── Cardiovascular ──
    "teplizumab": {"teplizumab", "tzield"},

    # ── Other Well-Known Drugs ──
    "rituximab": {"rituximab", "rituxan", "mabthera"},
    "trastuzumab": {"trastuzumab", "herceptin"},
    "cetuximab": {"cetuximab", "erbitux"},
    "panitumumab": {"panitumumab", "vectibix"},
    "pertuzumab": {"pertuzumab", "perjeta"},
    "daratumumab": {"daratumumab", "darzalex"},
    "elotuzumab": {"elotuzumab", "empliciti"},
    "obinutuzumab": {"obinutuzumab", "gazyva"},
    "mogamulizumab": {"mogamulizumab", "poteligeo"},
    "margetuximab": {"margetuximab", "margenza"},
    "zolbetuximab": {"zolbetuximab", "vyloy", "imab362"},

    # ── Chemotherapy / Standard of Care ──
    "docetaxel": {"docetaxel", "taxotere"},
    "paclitaxel": {"paclitaxel", "taxol", "abraxane"},
    "carboplatin": {"carboplatin", "paraplatin"},
    "cisplatin": {"cisplatin", "platinol"},
    "gemcitabine": {"gemcitabine", "gemzar"},
    "pemetrexed": {"pemetrexed", "alimta"},
    "capecitabine": {"capecitabine", "xeloda"},
    "fluorouracil": {"fluorouracil", "5-fu", "adrucil"},
    "irinotecan": {"irinotecan", "camptosar"},
    "topotecan": {"topotecan", "hycamtin"},
    "etoposide": {"etoposide", "vepesid"},
    "doxorubicin": {"doxorubicin", "adriamycin"},
    "cyclophosphamide": {"cyclophosphamide", "cytoxan"},
    "temozolomide": {"temozolomide", "temodar"},
    "anlotinib": {"anlotinib", "focus v"},

    # ── SHP2 / KRAS pathway ──
    "daraxonrasib": {"daraxonrasib", "rmc-6236", "rmc6236"},
    "opnurasib": {"opnurasib", "rmc-6291", "rmc6291"},

    # ── Revolution Medicines pipeline ──
    "rmc-9805": {"rmc-9805", "rmc9805"},

    # ── Other notable pipeline drugs ──
    "saruparib": {"saruparib", "azd5305", "azd-5305"},
    "capivasertib": {"capivasertib", "truqap", "azd5363"},
    "dato-dxd": {"dato-dxd", "datopotamab deruxtecan", "ds-1062"},
    "bnt327": {"bnt327", "biontech pd-l1/vegf"},
}


def get_known_drug_set():
    """
    Returns a flat set of all known drug aliases (lowercase).
    Used by the novelty detector.
    """
    known = set()
    for canonical, aliases in KNOWN_DRUGS.items():
        known.add(canonical.lower())
        for alias in aliases:
            known.add(alias.lower())
    return known


def is_known_drug(name):
    """Check if a drug name is in the known drugs baseline."""
    known = get_known_drug_set()
    name_lower = name.lower().strip()
    # Exact match
    if name_lower in known:
        return True
    # Partial match (e.g., "enfortumab" matches "enfortumab vedotin")
    for alias in known:
        if name_lower in alias or alias in name_lower:
            return True
    return False


def get_canonical_name(name):
    """Look up the canonical name for a drug alias."""
    name_lower = name.lower().strip()
    for canonical, aliases in KNOWN_DRUGS.items():
        if name_lower == canonical.lower():
            return canonical
        for alias in aliases:
            if name_lower == alias.lower():
                return canonical
    return None


if __name__ == "__main__":
    known = get_known_drug_set()
    print(f"Known drugs baseline: {len(KNOWN_DRUGS)} canonical drugs, {len(known)} total aliases")

    # Test some lookups
    test_names = [
        "pembrolizumab", "Keytruda", "AZD5305", "saruparib",
        "enfortumab vedotin", "BG-68501", "garsorasib",
        "upadacitinib", "tofacitinib", "anlotinib",
        "LOXO-435", "AND017", "TB-500",  # These should be novel
    ]
    print("\nNovelty test:")
    for name in test_names:
        known_flag = is_known_drug(name)
        canonical = get_canonical_name(name) or "—"
        status = "KNOWN" if known_flag else "★ NOVEL"
        print(f"  {name:30s} → {status:10s} (canonical: {canonical})")
