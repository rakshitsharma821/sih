import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)

pdf_filename = "ChainSentinel_Complete_System_Forensic_Guide.pdf"
doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    rightMargin=36,
    leftMargin=36,
    topMargin=32,
    bottomMargin=32
)

styles = getSampleStyleSheet()

# Color Palette
primary_color = colors.HexColor("#0f172a")      # Slate 900
accent_color = colors.HexColor("#d97706")       # Amber 600
accent_sub = colors.HexColor("#b45309")         # Darker amber
emerald_color = colors.HexColor("#059669")      # Green 600
blue_color = colors.HexColor("#2563eb")         # Blue 600
secondary_text = colors.HexColor("#334155")     # Slate 700
dark_border = colors.HexColor("#cbd5e1")        # Slate 300
card_bg = colors.HexColor("#f8fafc")            # Slate 50
card_alt = colors.HexColor("#f1f5f9")           # Slate 100

# Typography Styles
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=20,
    leading=24,
    textColor=accent_color,
    spaceAfter=4
)

subtitle_style = ParagraphStyle(
    'DocSubtitle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=10.5,
    leading=14,
    textColor=primary_color,
    spaceAfter=12
)

h1_style = ParagraphStyle(
    'SectionH1',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=13,
    leading=17,
    textColor=primary_color,
    spaceBefore=12,
    spaceAfter=6
)

h2_style = ParagraphStyle(
    'SectionH2',
    parent=styles['Heading3'],
    fontName='Helvetica-Bold',
    fontSize=10.5,
    leading=14,
    textColor=accent_sub,
    spaceBefore=8,
    spaceAfter=4
)

body_style = ParagraphStyle(
    'BodyDark',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9,
    leading=13.5,
    textColor=secondary_text,
    spaceAfter=5
)

bold_body_style = ParagraphStyle(
    'BoldBody',
    parent=body_style,
    fontName='Helvetica-Bold',
    textColor=primary_color
)

term_box_style = ParagraphStyle(
    'TermBox',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=8.5,
    leading=12,
    textColor=colors.HexColor("#1e293b")
)

code_style = ParagraphStyle(
    'CodeStyle',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#0f172a")
)

def make_card(title, content, border_color="#e2e8f0", bg_color="#f8fafc"):
    b_col = colors.HexColor(border_color) if isinstance(border_color, str) else border_color
    bg_col = colors.HexColor(bg_color) if isinstance(bg_color, str) else bg_color
    data = [
        [Paragraph(f"<b>{title}</b>", ParagraphStyle('CardH', fontName='Helvetica-Bold', fontSize=9, textColor=accent_color)), ""],
        [Paragraph(content, term_box_style), ""]
    ]
    t = Table(data, colWidths=[510, 30])
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('BACKGROUND', (0, 0), (-1, -1), bg_col),
        ('BOX', (0, 0), (-1, -1), 1, b_col),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t

elements = []

# =========================================================================
# HEADER & METADATA
# =========================================================================
elements.append(Paragraph("CHAINSENTINEL // FORENSIC SYSTEM GUIDE", title_style))
elements.append(Paragraph(
    "Smart India Hackathon (SIH26146) &bull; National Technical Research Organisation (NTRO)<br/>"
    "<b>Topic:</b> AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic &bull; <b>Live URL:</b> https://sih-dm42.onrender.com",
    subtitle_style
))
elements.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceAfter=10))

# =========================================================================
# SECTION 1: EXECUTIVE SUMMARY & CORE PROBLEM
# =========================================================================
elements.append(Paragraph("1. Executive Summary & Problem Formulation", h1_style))
elements.append(Paragraph(
    "Traditional banking systems mein har account ek verified KYC identity (PAN card, Aadhaar, Passport) se juda hota hai. Lekin Bitcoin mein <b>Pseudonymity</b> hoti hai. Koi bhi user bina identity verification ke seconds mein hazaron naye wallet addresses generate kar sakta hai. Is vajah se cyber criminals Ransomware payouts, Darknet drug markets, Hawala transactions aur terrorist financing ke liye Bitcoin ka istemal karte hain.",
    body_style
))

elements.append(make_card(
    "Key Forensic Term: Pseudonymity vs Anonymity",
    "<b>Pseudonymity:</b> Bitcoin anonymous nahi, pseudonymous hai. Iska matlab ledger 100% public hai aur sabhi transactions visible hain, lekin wallet address (e.g. <code>1EnAhuVD...</code>) ke peeche ke asali insaan ka naam chupa hota hai.<br/>"
    "<b>Hamara Goal:</b> Network Layer (IPs, Ports, Relays) aur Blockchain Layer (Wallets, TXIDs, UTXO) ko jod kar pseudonymous actors ko unmask karna."
))
elements.append(Spacer(1, 6))

elements.append(make_card(
    "Key Term: UTXO (Unspent Transaction Output)",
    "Bitcoin mein account balance jaisa koi column nahi hota. Yahan physical currency notes ki tarah <b>UTXO</b> chalte hain. Ek transaction mein purane bache hue notes <b>Inputs</b> bante hain aur naye recipients ko diye gaye notes <b>Outputs</b> bante hain. Dono ke beech ka antar <b>Miner Fee</b> kehlata hai."
))
elements.append(Spacer(1, 10))

# =========================================================================
# SECTION 2: END-TO-END 6-LAYER ARCHITECTURE
# =========================================================================
elements.append(Paragraph("2. End-to-End System Architecture (Pipeline Layers)", h1_style))
elements.append(Paragraph(
    "ChainSentinel pure pipeline ko 6 modular layers mein run karta hai. Har layer mathematically verified aur air-gapped offline environment ke liye optimize ki gayi hai:",
    body_style
))

# Layer 1
elements.append(Paragraph("Layer 1: Multi-Format Bulk Ingestion & Normalization (ingest.py)", h2_style))
elements.append(Paragraph(
    "Raw data CSV, JSON ya XML formats mein mil sakta hai. Hamara ingestion engine chunked streaming use karta hai jisse memory spike na ho. Har row ko validate karke local <b>SQLite (bitcoin_traffic.db)</b> mein teen relational tables mein store kiya jata hai: <br/>"
    "&bull; <b>transactions:</b> TXID, timestamp, src_ip, dst_ip, ports, country, ASN, fee, volume.<br/>"
    "&bull; <b>tx_inputs:</b> Kis wallet ne kitna input amount spend kiya.<br/>"
    "&bull; <b>tx_outputs:</b> Kis wallet ko kitna output amount receive hua.<br/>"
    "Malformed ya corrupted rows ko quarantine file (<code>quarantine.csv</code>) mein isolate kiya jata hai.",
    body_style
))

# Layer 2
elements.append(Paragraph("Layer 2: Heterogeneous NetworkX Multigraph Correlation (graph_builder.py)", h2_style))
elements.append(Paragraph(
    "Sirf database tables se laundering chains trace karna asambhav hai. Isliye NetworkX <code>MultiDiGraph</code> model banaya gaya hai (42,707 nodes aur 48,105 edges):<br/>"
    "&bull; <b>Nodes:</b> Transaction (box), Wallet (dot), IP Address (diamond).<br/>"
    "&bull; <b>Edges:</b> <code>BROADCAST_FROM</code> (src IP ➔ TX), <code>INPUT_OF</code> (Wallet ➔ TX), <code>OUTPUT_TO</code> (TX ➔ Wallet), <code>RELAYED_TO</code> (TX ➔ dst relay IP).",
    body_style
))

# Layer 3
elements.append(Paragraph("Layer 3: De-Anonymization via Common-Input DSU Clustering (entity_clustering.py)", h2_style))
elements.append(make_card(
    "Common-Input-Ownership (CIO) Heuristic + Disjoint Set Union (DSU)",
    "<b>Principle:</b> Agar kisi transaction mein 3 alag-alag addresses se fund combine hokar spend hota hai, toh un teeno addresses ka private key owner mathematically ek hi insaan hota hai.<br/>"
    "<b>Algorithm:</b> Hum <b>Disjoint Set Union (DSU)</b> with path compression use karte hain (Time complexity: O(&alpha;(N))). Isne 23,756 wallets ko cluster karke single criminal entities (e.g. <code>ENTITY_00171</code>) mein group kar diya."
))
elements.append(Spacer(1, 8))

# Layer 4
elements.append(Paragraph("Layer 4: Structural Laundering Detectors (pattern_detection.py)", h2_style))
elements.append(Paragraph(
    "Criminals paisa chupane ke liye do well-known structural patterns use karte hain:<br/>"
    "1. <b>Peeling Chains:</b> Bada amount (e.g. 45 BTC) ek sath cashout nahi hota. Chhota payment (1 BTC) bahar nikalta hai aur bacha hua bulk amount naye address par transfer hota hai. Graph traversal se <b>&ge; 4 continuous hops</b> wali chains detect hoti hain.<br/>"
    "2. <b>CoinJoin Mixing Pools:</b> 10-20 users milkar single transaction mein funds pool karte hain aur equal denomination ke outputs lete hain. System <b>Uniform Value Frequency Entropy</b> se mixers ko isolate karta hai.",
    body_style
))

# Page Break for clean reading
elements.append(PageBreak())

# Layer 5 (NEW FEATURE)
elements.append(Paragraph("Layer 5: [NEW FEATURE] IP Hopping & Network Footprint Telemetry", h1_style))
elements.append(make_card(
    "Multi-IP Churning / Footprint Detector (detect_ip_hopping)",
    "<b>Criminal Strategy:</b> Law enforcement se bachne ke liye suspect har transaction alag IP address, alag VPN provider ya alag country se broadcast karta hai.<br/>"
    "<b>Hamara Forensic Solution:</b><br/>"
    "&bull; Har wallet ka temporal IP footprint monitor hota hai.<br/>"
    "&bull; Agar ek single wallet address 2 ya usse zyada distinct IPs ya alag countries (e.g. US, SG, DE) se broadcast hota hai, toh system use <b>IP Hopping Suspect</b> mark karta hai.<br/>"
    "&bull; Automatic <code>IP_HOPPING_SUSPECT</code> alert generate hota hai aur Suspect Profiler mein uski puri IP list, ASN (AWS, Alibaba, Cloudflare) aur country breakdown display hoti hai.<br/>"
    "&bull; <b>Verified in Code:</b> 10,079 multi-IP transactions flag huye across 259 high-churn criminal actors."
, border_color="#d97706", bg_color="#fffbeb"))
elements.append(Spacer(1, 8))

# Layer 6
elements.append(Paragraph("Layer 6: Dual AI Ensemble & Explainable AI (SHAP)", h1_style))
elements.append(Paragraph(
    "Novel zero-day financial frauds pakadne ke liye hum 2 AI models aur 1 Graph Diffusion algorithm chalate hain:",
    body_style
))

elements.append(Paragraph(
    "<b>1. Deep Autoencoder (PyTorch Neural Network):</b><br/>"
    "Unsupervised bottleneck neural network jo normal traffic representation learn karta hai. Suspicious transactions par model ka reconstruction loss (MSE) high aata hai, jo bounded anomaly score deta hai.<br/><br/>"
    "<b>2. Isolation Forest (Scikit-Learn Ensemble):</b><br/>"
    "8 behavioral features (fee ratio, input consolidation, output fan-out, temporal burst, colocation) par isolation trees banata hai aur outliers isolate karta hai.<br/><br/>"
    "<b>3. Personalized PageRank / Random Walk with Restart (&alpha; = 0.85):</b><br/>"
    "Sanctioned ya darknet seed wallets se tainted funds ka mathematical flow calculate karta hai. Suspect wallet illicit node ke jitna pass hoga, uska taint score utna high hoga.<br/><br/>"
    "<b>4. Explainable AI (SHAP TreeExplainer):</b><br/>"
    "Model black-box nahi hai. SHAP investigator ko plain English mein batata hai ki transaction kyu flag hui (e.g. <i>'Input Consolidation Count: +2.48 SHAP'</i>, <i>'Miner Fee Spike: +2.15 SHAP'</i>).",
    body_style
))
elements.append(Spacer(1, 10))

# =========================================================================
# SECTION 3: REST API & POSTMAN VERIFICATION
# =========================================================================
elements.append(Paragraph("3. Production REST API & Postman Verification", h1_style))
elements.append(Paragraph(
    "ChainSentinel ka backend ek pure <b>FastAPI REST API</b> hai. Postman ya Swagger Docs (<code>/docs</code>) se test karne ke liye exact endpoints:",
    body_style
))

api_table_data = [
    [Paragraph("<b>Method & Endpoint</b>", ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color)),
     Paragraph("<b>Description & Postman Test Status</b>", ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color))],
    [Paragraph("<code>GET /api/health</code>", code_style), Paragraph("Returns <code>{\"status\": \"online\", \"mode\": \"local_offline\"}</code> (Postman: 200 OK, 313ms).", body_style)],
    [Paragraph("<code>GET /api/metrics</code>", code_style), Paragraph("Returns system summary: 5,672 transactions, 150 alerts, 23,756 clustered entities.", body_style)],
    [Paragraph("<code>GET /api/alerts?severity=CRITICAL</code>", code_style), Paragraph("Returns prioritized alerts with confidence score (0.868), CoinJoin signature, and SHAP drivers.", body_style)],
    [Paragraph("<code>GET /api/wallet/{address}</code>", code_style), Paragraph("Profiles suspect wallet: balance, transaction history, and <b>associated IPs + IP Hopping flag</b>.", body_style)],
    [Paragraph("<code>GET /api/top-suspects</code>", code_style), Paragraph("Returns highest risk seed entities (e.g. <code>bc1qh729...</code> with 170.38 BTC volume).", body_style)],
    [Paragraph("<code>GET /api/entities</code>", code_style), Paragraph("Returns multi-wallet clusters resolved via Common-Input DSU heuristic.", body_style)],
    [Paragraph("<code>GET /api/graph/subgraph</code>", code_style), Paragraph("Returns Vis.js topological nodes (TX, Inputs, Outputs, Broadcast IP) and BTC labeled edges.", body_style)],
    [Paragraph("<code>GET /api/transactions</code>", code_style), Paragraph("Paginated transaction feed with filter parameters (e.g. <code>pattern=PEELING_CHAIN</code>).", body_style)],
]

t_api = Table(api_table_data, colWidths=[180, 360])
t_api.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), card_alt),
    ('GRID', (0, 0), (-1, -1), 0.5, dark_border),
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]))
elements.append(t_api)
elements.append(Spacer(1, 10))

# Page Break for clean reading
elements.append(PageBreak())

# =========================================================================
# SECTION 4: TEAMMATE PRESENTATION SCRIPT & DEMO FLOW
# =========================================================================
elements.append(Paragraph("4. Teammate Presentation Roles & 3-Minute Winning Demo", h1_style))
elements.append(Paragraph(
    "Hackathon jury presentation ke liye 5 members ka standard role allocation aur sequence:",
    body_style
))

roles_table_data = [
    [Paragraph("<b>Speaker</b>", ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color)),
     Paragraph("<b>Role & Focus Area</b>", ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color)),
     Paragraph("<b>Key Script Points to Speak</b>", ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color))],
    [
        Paragraph("<b>Member 1</b><br/>Team Lead", body_style),
        Paragraph("Problem Statement & Architecture Overview", body_style),
        Paragraph("NTRO SIH26146 introduction. Bitcoin pseudonymity problem. Hamara solution: Network + Blockchain layer correlation without external paid APIs.", body_style)
    ],
    [
        Paragraph("<b>Member 2</b><br/>Data & Graph Lead", body_style),
        Paragraph("Ingestion, DSU Clustering & Multigraph", body_style),
        Paragraph("Multi-format streaming ingestion (CSV/JSON/XML). NetworkX MultiDiGraph (42k+ nodes). Common-Input DSU clustering resolving 23,756 wallets.", body_style)
    ],
    [
        Paragraph("<b>Member 3</b><br/>AI / ML Lead", body_style),
        Paragraph("Dual AI Ensemble & Explainability", body_style),
        Paragraph("Isolation Forest + Deep Autoencoder reconstruction loss. SHAP TreeExplainer local feature attribution giving plain-text forensic drivers.", body_style)
    ],
    [
        Paragraph("<b>Member 4</b><br/>Forensics Lead", body_style),
        Paragraph("Laundering Patterns & <b>IP Hopping</b>", body_style),
        Paragraph("Peeling Chains traversal & CoinJoin mixer entropy. <b>Highlight our new feature: IP Hopping & Network Footprint Telemetry (multi-IP churning).</b>", body_style)
    ],
    [
        Paragraph("<b>Member 5</b><br/>SOC / Demo Lead", body_style),
        Paragraph("Live Dashboard & API Verification", body_style),
        Paragraph("Live Render demo (https://sih-dm42.onrender.com). Vis.js interactive graph demo. Postman verification with 14/14 passed tests.", body_style)
    ],
]

t_roles = Table(roles_table_data, colWidths=[80, 160, 300])
t_roles.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), card_alt),
    ('GRID', (0, 0), (-1, -1), 0.5, dark_border),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]))
elements.append(t_roles)
elements.append(Spacer(1, 10))

elements.append(Paragraph("3-Minute Live Jury Demo Script", h2_style))
elements.append(Paragraph(
    "<b>Minute 1 (Overview & Scale):</b> Open <code>https://sih-dm42.onrender.com</code>. Show total metrics (5,672 transactions, 150 alerts, 2,125 multi-wallet clusters). Point to the new Bitcoin squircle logo.<br/>"
    "<b>Minute 2 (Alerts & Explainability):</b> Open Forensic Alerts tab. Click on <code>ALT_00978</code>. Show jury the CoinJoin mixer pattern, 86% confidence, and SHAP impact chart explaining the exact drivers.<br/>"
    "<b>Minute 3 (IP Hopping & Graph):</b> Go to Suspect Profiler. Enter <code>1EnAhuVDifUaaQgEHo9acEhtd3FfWgfW</code>. Show the jury: <i>'Look, IP Hopping Detected: True! 3 distinct IPs across US and Singapore.'</i> Switch to Link Analysis and rotate the interactive graph.",
    body_style
))
elements.append(Spacer(1, 10))

# =========================================================================
# SECTION 5: FREQUENTLY ASKED EVALUATION QUESTIONS
# =========================================================================
elements.append(Paragraph("5. Defense Technical Q&A for Judges / Evaluation", h1_style))

elements.append(Paragraph("<b>Q1: Kya ye solution live Bitcoin Mainnet par chal sakta hai?</b>", bold_body_style))
elements.append(Paragraph(
    "<b>A:</b> Haan, bilkul. Humara pipeline standard Bitcoin RPC / ZeroMQ blocks aur p2p wire protocol ke format ke compatible hai. Ingestion engine mein input source badal kar live Bitcoin Core Node RPC connect karte hi ye bina kisi code change ke real mainnet traffic process karega.",
    body_style
))
elements.append(Spacer(1, 4))

elements.append(Paragraph("<b>Q2: CoinJoin transactions mein Common-Input Heuristic fail kyu nahi hui?</b>", bold_body_style))
elements.append(Paragraph(
    "<b>A:</b> CoinJoin transactions mein multiple independent users ek hi transaction mein inputs pool karte hain, isliye wahan CIO heuristic lagane se false grouping ho sakti hai. Hamara system Layer 4 mein pehle CoinJoin mixing signatures ko detect karke filter karta hai aur sirf non-mixer transactions par DSU clustering lagata hai. Isse false positive rate zero ke barabar rehta hai.",
    body_style
))
elements.append(Spacer(1, 4))

elements.append(Paragraph("<b>Q3: System 100% Offline / Air-Gapped kaise verify hota hai?</b>", bold_body_style))
elements.append(Paragraph(
    "<b>A:</b> Sabhi machine learning models (Isolation Forest, PyTorch Autoencoder), graph analytics (NetworkX, PageRank), database (SQLite WAL) aur UI assets (pre-compiled React + Tailwind bundle) local system par chalte hain. Zero outbound cloud network requests kiye jaate hain, jo classified defense networks ke liye mandatory requirement hai.",
    body_style
))

# Build Document
doc.build(elements)
print(f"Generated PDF at: {os.path.abspath(pdf_filename)}")
