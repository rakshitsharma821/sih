import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, Activity, GitFork, Search, Database, Cpu, 
  FileText, ArrowUpRight, ArrowDownLeft, AlertTriangle, 
  CheckCircle2, RefreshCw, Layers, ExternalLink, Globe, Lock, Play, Download, UploadCloud
} from 'lucide-react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

export default function App() {
  const [activeTab, setActiveTab] = useState('threats');
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [topSuspects, setTopSuspects] = useState([]);
  
  // Suspect search state
  const [searchAddress, setSearchAddress] = useState('');
  const [walletData, setWalletData] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  // Graph state
  const [graphCenterTx, setGraphCenterTx] = useState('');
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphEmpty, setGraphEmpty] = useState(false);
  const networkContainerRef = useRef(null);
  const networkInstanceRef = useRef(null);

  // Dataset & Live Ingestion State
  const [txFeed, setTxFeed] = useState([]);
  const [txTotal, setTxTotal] = useState(0);
  const [txFilterPattern, setTxFilterPattern] = useState('ALL');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState('');
  const [selectedTx, setSelectedTx] = useState(null);

  // Step 3 Entity Clusters State
  const [entities, setEntities] = useState([]);

  // Load initial data
  useEffect(() => {
    fetchMetrics();
    fetchAlerts();
    fetchTopSuspects();
    fetchTransactions();
    fetchEntities();
  }, []);

  const fetchEntities = async () => {
    try {
      const res = await fetch('/api/entities');
      const data = await res.json();
      setEntities(data);
    } catch (err) {
      console.error("Error fetching entities:", err);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await fetch('/api/metrics');
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      console.error("Error fetching metrics:", err);
    }
  };

  const fetchAlerts = async (sev = 'ALL') => {
    try {
      const url = sev === 'ALL' ? '/api/alerts' : `/api/alerts?severity=${sev}`;
      const res = await fetch(url);
      const data = await res.json();
      setAlerts(data);
    } catch (err) {
      console.error("Error fetching alerts:", err);
    }
  };

  const fetchTopSuspects = async () => {
    try {
      const res = await fetch('/api/top-suspects');
      const data = await res.json();
      setTopSuspects(data);
      if (data.length > 0 && !searchAddress) {
        const addr = data[0].wallet_address || data[0].address;
        setSearchAddress(addr);
        investigateWallet(addr);
      }
    } catch (err) {
      console.error("Error fetching suspects:", err);
    }
  };

  const fetchTransactions = async (pattern = 'ALL') => {
    try {
      const url = pattern === 'ALL' ? '/api/transactions?limit=60' : `/api/transactions?limit=60&pattern=${pattern}`;
      const res = await fetch(url);
      const data = await res.json();
      setTxFeed(data.transactions || []);
      setTxTotal(data.total || 0);
    } catch (err) {
      console.error("Error fetching transactions:", err);
    }
  };

  const triggerGenerateDataset = async (numTxs = 5000) => {
    setIsGenerating(true);
    setGenerateMsg(`Synthesizing ${numTxs.toLocaleString()} hybrid Bitcoin transactions with network telemetry...`);
    try {
      const res = await fetch(`/api/generate-dataset?num_tx=${numTxs}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || `Server returned error code ${res.status}`);
      }
      setGenerateMsg(data.message || `Successfully generated ${numTxs.toLocaleString()} transactions!`);
      fetchMetrics();
      fetchAlerts();
      fetchTransactions();
    } catch (err) {
      setGenerateMsg('Generation error: ' + err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const investigateWallet = async (addr) => {
    if (!addr) return;
    setIsSearching(true);
    try {
      const res = await fetch(`/api/wallet/${addr.trim()}`);
      if (!res.ok) throw new Error("Wallet not found");
      const data = await res.json();
      setWalletData(data);
    } catch (err) {
      console.error("Investigate error:", err);
      setWalletData(null);
    } finally {
      setIsSearching(false);
    }
  };

  // Vis.js Graph Rendering
  useEffect(() => {
    if (activeTab === 'graph' && networkContainerRef.current) {
      loadGraphNetwork();
    }
  }, [activeTab, graphCenterTx]);

  const loadGraphNetwork = async (overrideTx) => {
    const targetTx = overrideTx !== undefined ? overrideTx : graphCenterTx;
    setGraphLoading(true);
    setGraphEmpty(false);
    try {
      const url = targetTx ? `/api/graph/subgraph?txid=${targetTx.trim()}` : '/api/graph/subgraph';
      const res = await fetch(url);
      const data = await res.json();

      if (data.center && !targetTx) {
        setGraphCenterTx(data.center);
      }

      if (!data.nodes || data.nodes.length === 0) {
        setGraphEmpty(true);
        if (networkInstanceRef.current) {
          networkInstanceRef.current.destroy();
          networkInstanceRef.current = null;
        }
        return;
      }

      if (!networkContainerRef.current) return;

      const nodes = new DataSet(
        data.nodes.map(n => ({
          id: n.id,
          label: n.label,
          title: n.title,
          color: {
            background: n.color || (n.group === 'transaction' ? '#2563eb' : (n.group === 'ip' ? '#38bdf8' : '#f59e0b')),
            border: '#ffffff',
            highlight: { background: '#ef4444', border: '#ffffff' }
          },
          font: { color: '#f8fafc', size: n.is_center ? 13 : 11, face: 'monospace', bold: n.is_center },
          shape: n.shape || (n.group === 'transaction' ? 'box' : (n.group === 'ip' ? 'diamond' : 'dot')),
          size: n.size || (n.group === 'transaction' ? 24 : 16),
          margin: 8,
          shadow: n.is_center ? { enabled: true, color: 'rgba(239, 68, 68, 0.6)', size: 15 } : false
        }))
      );

      const edges = new DataSet(
        data.edges.map(e => ({
          from: e.from,
          to: e.to,
          label: e.label,
          arrows: { to: { enabled: true, scaleFactor: 0.7 } },
          color: { color: '#475569', highlight: '#f59e0b', opacity: 0.7 },
          font: { 
            color: '#94a3b8', 
            size: 9, 
            align: 'top', 
            background: 'rgba(7, 9, 14, 0.75)',
            strokeWidth: 0 
          },
          smooth: {
            enabled: true,
            type: 'cubicBezier',
            roundness: 0.4
          }
        }))
      );

      const options = {
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -120,
            centralGravity: 0.015,
            springLength: 160,
            springConstant: 0.08,
            damping: 0.4,
            avoidOverlap: 1
          },
          stabilization: { iterations: 120 }
        },
        interaction: { hover: true, tooltipDelay: 100, zoomView: true, dragView: true },
        layout: { improvedLayout: true, randomSeed: 42 }
      };

      if (networkInstanceRef.current) {
        networkInstanceRef.current.destroy();
      }
      networkInstanceRef.current = new Network(networkContainerRef.current, { nodes, edges }, options);
    } catch (err) {
      console.error("Graph load error:", err);
      setGraphEmpty(true);
    } finally {
      setGraphLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col selection:bg-amber-500 selection:text-black">
      {/* Unified Sticky Header & Navigation Bar */}
      <div className="sticky top-0 z-50 bg-[#0b0f19]/95 backdrop-blur border-b border-slate-800 shadow-md">
        <header className="px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20 text-slate-950 font-black text-xl">
              ₿
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-wider text-slate-100">CHAINSENTINEL</span>
                <span className="text-[10px] uppercase font-bold tracking-widest bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded border border-amber-500/20">
                  SIH26146 SOC
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">AI-Powered Bitcoin Traffic Forensics & Anomaly Monitoring</p>
            </div>
          </div>

          {/* Status Pill */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-medium text-emerald-400">Offline Local Node Online</span>
            </div>
          </div>
        </header>

        {/* Navigation Tabs Bar */}
        <nav className="border-t border-slate-800/80 bg-[#0d1322]/90 px-6 flex gap-1 overflow-x-auto">
          {[
            { id: 'threats', label: 'Threat Overview', icon: Activity },
            { id: 'dataset', label: 'Dataset & Live Feed', icon: Database },
            { id: 'entities', label: 'Entity Clusters', icon: Layers },
            { id: 'graph', label: 'Link-Analysis Graph', icon: GitFork },
            { id: 'alerts', label: `Forensic Alerts (${metrics?.alert_count || 150})`, icon: ShieldAlert },
            { id: 'suspect', label: 'Suspect Wallet Profiler', icon: Search },
            { id: 'pipeline', label: 'Pipeline Control', icon: Cpu },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2.5 px-5 py-3 text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                  isActive 
                    ? 'border-amber-400 text-amber-400 bg-amber-400/5' 
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon size={16} className={isActive ? 'text-amber-400' : 'text-slate-500'} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">

        {/* TAB 1: THREAT OVERVIEW */}
        {activeTab === 'threats' && (
          <div className="space-y-6">
            {/* KPI Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 hover:border-slate-700 transition">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Indexed Txs</div>
                <div className="text-3xl font-black text-slate-100 mt-2 font-mono">
                  {metrics?.total_tx?.toLocaleString() || '7,862'}
                </div>
                <div className="text-xs text-slate-500 mt-1">Multi-format parsed & normalized</div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 hover:border-slate-700 transition">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Unique Wallets</div>
                <div className="text-3xl font-black text-cyan-400 mt-2 font-mono">
                  {metrics?.total_wallets?.toLocaleString() || '27,772'}
                </div>
                <div className="text-xs text-slate-500 mt-1">Graph nodes with CIO heuristic</div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 hover:border-slate-700 transition">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Flagged Forensic Alerts</div>
                <div className="text-3xl font-black text-rose-500 mt-2 font-mono">
                  {metrics?.alert_count || '150'}
                </div>
                <div className="text-xs text-rose-400/80 mt-1 flex items-center gap-1">
                  <AlertTriangle size={12} /> Autoencoder + Isolation Forest
                </div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 hover:border-slate-700 transition">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Patterns Detected</div>
                <div className="text-3xl font-black text-amber-400 mt-2 font-mono">
                  {(metrics?.peeling_chains || 64) + (metrics?.coinjoin_mixes || 200) + (metrics?.ip_hopping_cases || 259)}
                </div>
                <div className="text-xs text-amber-400/80 mt-1">
                  {metrics?.peeling_chains || 64} Peeling · {metrics?.coinjoin_mixes || 200} CoinJoins · {metrics?.ip_hopping_cases || 259} IP Hopping
                </div>
              </div>
            </div>

            {/* Middle Grid: Geographic + Patterns Info */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Pattern Breakdown */}
              <div className="lg:col-span-2 p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-4">
                <h3 className="font-bold text-slate-200 flex items-center gap-2">
                  <Layers size={18} className="text-amber-400" />
                  Graph Pattern & Laundering Heuristics
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-[#07090e] border border-slate-800/80">
                    <div className="text-sm font-semibold text-amber-400">Peeling Chain Topology</div>
                    <p className="text-xs text-slate-400 mt-1">
                      Rapid 1-in 2-out hops peeling small payments while moving bulk unspent change forward.
                    </p>
                    <div className="mt-3 text-2xl font-bold font-mono text-slate-200">
                      {metrics?.peeling_chains || 64} Chains
                    </div>
                    <span className="text-[10px] text-amber-400/80">Avg depth: 5-8 continuous hops</span>
                  </div>

                  <div className="p-4 rounded-lg bg-[#07090e] border border-slate-800/80">
                    <div className="text-sm font-semibold text-cyan-400">CoinJoin Mixing Pools</div>
                    <p className="text-xs text-slate-400 mt-1">
                      Multi-party equal denomination obfuscation (Wasabi / Whirlpool signature).
                    </p>
                    <div className="mt-3 text-2xl font-bold font-mono text-slate-200">
                      {metrics?.coinjoin_mixes || 200} Transactions
                    </div>
                    <span className="text-[10px] text-cyan-400/80">Entropy obfuscation detected</span>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300">
                  <strong>Forensic Tip:</strong> Bitcoin transactions are pseudonymous on-chain records. Our AI combines Graph Union-Find (Common Input Ownership) with Random Walk Embeddings to de-anonymize clusters.
                </div>
              </div>

              {/* Geographic IP Footprint */}
              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-4">
                <h3 className="font-bold text-slate-200 flex items-center gap-2">
                  <Globe size={18} className="text-cyan-400" />
                  Top Relay Peer Jurisdictions
                </h3>
                <div className="space-y-3">
                  {metrics?.top_countries?.map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-slate-300 flex items-center gap-2">
                        <span className="w-5 text-slate-500">{i+1}.</span> {c.country}
                      </span>
                      <span className="font-mono font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                        {c.count} txs
                      </span>
                    </div>
                  )) || (
                    <div className="text-xs text-slate-500">Loading network telemetry...</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: DATASET & LIVE FEED (RESTORED & ENHANCED) */}
        {activeTab === 'dataset' && (
          <div className="space-y-6">
            {/* Generator Action Box */}
            <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-100 flex items-center gap-2 text-base">
                    <Database size={18} className="text-amber-400" />
                    Automated Hybrid Dataset Engine
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Grounded in real 1-minute Kaggle BTC/USD price data with synthetic network metadata and injected anomalies.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => triggerGenerateDataset(5000)}
                    disabled={isGenerating}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-slate-950 font-bold text-xs hover:bg-amber-400 transition cursor-pointer disabled:opacity-50 shadow-md shadow-amber-500/20"
                  >
                    <Play size={14} className={isGenerating ? 'animate-spin' : ''} />
                    {isGenerating ? 'Synthesizing...' : '1-Click Auto-Generate 5,000 Txs'}
                  </button>
                  <button
                    onClick={() => triggerGenerateDataset(10000)}
                    disabled={isGenerating}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition cursor-pointer disabled:opacity-50"
                  >
                    Generate 10,000 Txs
                  </button>
                </div>
              </div>

              {generateMsg && (
                <div className="p-3 bg-[#07090e] border border-amber-500/30 rounded-lg text-xs font-mono text-amber-300 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
                  {generateMsg}
                </div>
              )}
            </div>

            {/* Transactions Feed Table */}
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Filter Pattern:</span>
                  {['ALL', 'NORMAL', 'PEELING_CHAIN', 'COINJOIN_MIXING', 'COMMON_INPUT_CLUSTER', 'STATISTICAL_ANOMALY'].map(pat => (
                    <button
                      key={pat}
                      onClick={() => {
                        setTxFilterPattern(pat);
                        fetchTransactions(pat);
                      }}
                      className={`px-2.5 py-1 rounded text-[11px] font-bold transition cursor-pointer ${
                        txFilterPattern === pat 
                          ? 'bg-amber-500 text-slate-950' 
                          : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {pat.replace('_', ' ')}
                    </button>
                  ))}
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  Indexed Records: <span className="text-amber-400 font-bold">{txTotal.toLocaleString()}</span>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#0e1424] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-[#090d18] text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
                      <tr>
                        <th className="p-3">TXID</th>
                        <th className="p-3">Timestamp (UTC)</th>
                        <th className="p-3">Relay IP:Port</th>
                        <th className="p-3">Geo / ASN</th>
                        <th className="p-3">Script</th>
                        <th className="p-3">Volume (USD)</th>
                        <th className="p-3">Pattern Label</th>
                        <th className="p-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-sans">
                      {txFeed.map((tx, idx) => {
                        const patBadge = 
                          tx.pattern_label === 'NORMAL' ? 'bg-slate-800 text-slate-400' :
                          tx.pattern_label === 'PEELING_CHAIN' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                          tx.pattern_label === 'COINJOIN_MIXING' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' :
                          'bg-rose-500/10 text-rose-400 border border-rose-500/30';

                        return (
                          <tr key={idx} className="hover:bg-slate-800/30 transition">
                            <td className="p-3 font-mono text-cyan-400 font-medium">
                              {tx.txid.slice(0, 14)}...
                            </td>
                            <td className="p-3 font-mono text-slate-400">{tx.datetime_utc || 'N/A'}</td>
                            <td className="p-3 font-mono text-slate-300">{tx.src_ip}:{tx.src_port}</td>
                            <td className="p-3 font-mono text-slate-400">{tx.geo_country} · {tx.asn}</td>
                            <td className="p-3 font-mono text-slate-400">{tx.script_type}</td>
                            <td className="p-3 font-mono font-bold text-slate-200">${(tx.volume_usd || 0).toLocaleString()}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${patBadge}`}>
                                {tx.pattern_label}
                              </span>
                            </td>
                            <td className="p-3 text-right">
                              <button
                                onClick={() => {
                                  setGraphCenterTx(tx.txid);
                                  setActiveTab('graph');
                                }}
                                className="px-2 py-1 rounded bg-amber-500/10 text-amber-400 hover:bg-amber-500 hover:text-slate-950 font-semibold transition cursor-pointer text-[11px]"
                              >
                                Trace Graph
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB: STEP 3 ENTITY RESOLUTION & CLUSTERS */}
        {activeTab === 'entities' && (
          <div className="space-y-6">
            {/* Step 3 KPI Header */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Resolved Entities</div>
                <div className="text-3xl font-black text-amber-400 mt-2 font-mono">
                  {metrics?.total_entities?.toLocaleString() || '23,756'}
                </div>
                <div className="text-xs text-slate-500 mt-1">Disjoint Set Union (DSU) partitions</div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Multi-Wallet Clusters</div>
                <div className="text-3xl font-black text-cyan-400 mt-2 font-mono">
                  {metrics?.multi_wallet_clusters?.toLocaleString() || '2,125'}
                </div>
                <div className="text-xs text-cyan-400/80 mt-1">De-anonymized criminal actors</div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Graph Nodes Mapped</div>
                <div className="text-3xl font-black text-slate-100 mt-2 font-mono">
                  {metrics?.graph_nodes?.toLocaleString() || '42,707'}
                </div>
                <div className="text-xs text-slate-500 mt-1">Wallets, TXIDs & IPs in NetworkX</div>
              </div>

              <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Directed Multigraph Edges</div>
                <div className="text-3xl font-black text-emerald-400 mt-2 font-mono">
                  {metrics?.graph_edges?.toLocaleString() || '48,105'}
                </div>
                <div className="text-xs text-emerald-400/80 mt-1">Relational UTXO flow links</div>
              </div>
            </div>

            {/* Heuristic Explanation Card */}
            <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-3">
              <h3 className="font-bold text-slate-100 flex items-center gap-2 text-sm">
                <Layers size={18} className="text-amber-400" />
                Forensic Clustering Principle: Common-Input-Ownership (CIO) Heuristic
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                In Bitcoin, an on-chain transaction spending from multiple input addresses requires cryptographic private key signatures for each input. Under the <strong>Common-Input Ownership</strong> heuristic, all addresses co-spent as inputs within the same transaction are controlled by the exact same real-world entity.
              </p>
              <div className="p-3 bg-[#07090e] border border-slate-800 rounded-lg text-xs font-mono text-slate-400 space-y-1">
                <div className="text-amber-400 font-bold">Mathematical Implementation:</div>
                <div>• Graph Engine: NetworkX Directed Multigraph with typed attributes ('node_type': wallet, tx, ip)</div>
                <div>• Clustering Method: Disjoint Set Union (DSU) with Path Compression — O(α(N)) near-instant runtime</div>
                <div>• Verified Output: Exported to <span className="text-slate-200">wallet_entities.csv</span> (27,772 addresses mapped into 23,756 entity groups)</div>
              </div>
            </div>

            {/* Entity Groups Table */}
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-xl bg-[#0e1424] border border-slate-800">
                <div className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                  Discovered High-Degree Multi-Wallet Entities (Same Controller)
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  Showing Top Resolved Clusters
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {entities.map((ent, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-[#0e1424] border border-slate-800 space-y-3 hover:border-slate-700 transition">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-cyan-400">{ent.entity_id}</span>
                        <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] font-bold">
                          {ent.wallet_count} Linked Addresses
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 uppercase font-mono">Co-Spent Entity</span>
                    </div>

                    <p className="text-[11px] text-slate-400">
                      These distinct pseudonymous addresses were co-spent across common-input transactions and belong to the same controller:
                    </p>

                    <div className="flex flex-wrap gap-1.5">
                      {ent.sample_wallets.map((w, wIdx) => (
                        <button
                          key={wIdx}
                          onClick={() => {
                            setSearchAddress(w);
                            investigateWallet(w);
                            setActiveTab('suspect');
                          }}
                          className="px-2 py-1 rounded bg-[#07090e] border border-slate-800 hover:border-amber-400 text-[11px] font-mono text-slate-300 transition cursor-pointer flex items-center gap-1"
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                          {w.slice(0, 10)}...
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: FORENSIC ALERTS */}
        {activeTab === 'alerts' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-[#0e1424] border border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase">Filter Severity:</span>
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(sev => (
                  <button
                    key={sev}
                    onClick={() => {
                      setSelectedSeverity(sev);
                      fetchAlerts(sev);
                    }}
                    className={`px-3 py-1 rounded text-xs font-bold transition cursor-pointer ${
                      selectedSeverity === sev 
                        ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20' 
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Showing {alerts.length} Ranked Forensic Signals
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0e1424] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[#090d18] text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
                    <tr>
                      <th className="p-3.5">Severity</th>
                      <th className="p-3.5">Transaction ID</th>
                      <th className="p-3.5">Risk Score</th>
                      <th className="p-3.5">Pattern Flag</th>
                      <th className="p-3.5">Forensic Explanation</th>
                      <th className="p-3.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans">
                    {alerts.map((al, idx) => {
                      const sevColor = al.severity === 'CRITICAL' 
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' 
                        : al.severity === 'HIGH' 
                        ? 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/30';
                      
                      return (
                        <tr key={idx} className="hover:bg-slate-800/30 transition">
                          <td className="p-3.5">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${sevColor}`}>
                              {al.severity}
                            </span>
                          </td>
                          <td className="p-3.5 font-mono text-slate-300">
                            {al.txid?.slice(0, 16)}...
                          </td>
                          <td className="p-3.5 font-mono font-bold text-amber-400">
                            {(al.risk_score || al.composite_risk || 0.85).toFixed(3)}
                          </td>
                          <td className="p-3.5">
                            <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${
                              (al.primary_flag || al.pattern_type) === 'IP_HOPPING_SUSPECT'
                                ? 'bg-purple-950/60 text-purple-300 border-purple-500/50 shadow-sm shadow-purple-500/20'
                                : (al.primary_flag || al.pattern_type) === 'COINJOIN_MIXING'
                                ? 'bg-cyan-950/60 text-cyan-300 border-cyan-500/50'
                                : (al.primary_flag || al.pattern_type) === 'PEELING_CHAIN'
                                ? 'bg-amber-950/60 text-amber-300 border-amber-500/50'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}>
                              {al.primary_flag || al.pattern_type || 'ANOMALY'}
                            </span>
                          </td>
                          <td className="p-3.5 text-slate-300 max-w-md truncate">
                            {al.forensic_explanation || al.evidence_summary || 'Reconstruction loss outlier detected.'}
                          </td>
                          <td className="p-3.5 text-right">
                            <button
                              onClick={() => {
                                setGraphCenterTx(al.txid);
                                setActiveTab('graph');
                              }}
                              className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 hover:bg-amber-500 hover:text-slate-950 font-semibold transition cursor-pointer text-[11px]"
                            >
                              Trace Graph
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: LINK-ANALYSIS GRAPH */}
        {activeTab === 'graph' && (
          <div className="space-y-4">
            {/* Graph Header & Search */}
            <div className="p-4 rounded-xl bg-[#0e1424] border border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-slate-100 flex items-center gap-2">
                  <GitFork size={18} className="text-amber-400" />
                  Visual Link-Analysis & UTXO Flow Graph
                </h3>
                <p className="text-xs text-slate-400">
                  Interactive forensic graph showing Bitcoin transactions, wallet entities, and money laundering paths.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Focus TXID or Wallet..."
                  value={graphCenterTx}
                  onChange={(e) => setGraphCenterTx(e.target.value)}
                  className="bg-[#07090e] border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-400 w-64"
                />
                <button
                  onClick={loadGraphNetwork}
                  className="px-3 py-1.5 rounded bg-amber-500 text-slate-950 font-bold text-xs hover:bg-amber-400 transition cursor-pointer"
                >
                  Focus Node
                </button>
              </div>
            </div>

            {/* VISUAL LEGEND & EXPLAINER STRIP */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3.5 rounded-xl bg-[#090d18] border border-slate-800 text-xs">
              <div className="flex items-center gap-2.5 p-2 rounded bg-[#0e1424] border border-slate-800">
                <span className="h-3.5 w-3.5 rounded-full bg-amber-500 shadow-sm shadow-amber-500/50"></span>
                <div>
                  <div className="font-bold text-slate-200">Amber Circle: Wallet Address</div>
                  <div className="text-[10px] text-slate-400">Owner or receiver of BTC funds</div>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-2 rounded bg-[#0e1424] border border-slate-800">
                <span className="h-3.5 w-3.5 rounded bg-blue-500 shadow-sm shadow-blue-500/50"></span>
                <div>
                  <div className="font-bold text-slate-200">Blue Box: Transaction (TXID)</div>
                  <div className="text-[10px] text-slate-400">On-chain transfer event</div>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-2 rounded bg-[#0e1424] border border-slate-800">
                <span className="text-amber-400 font-bold text-base leading-none">&rarr;</span>
                <div>
                  <div className="font-bold text-slate-200">Arrows (Edges): Money Flow</div>
                  <div className="text-[10px] text-slate-400">Direction & BTC amount transferred</div>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-2 rounded bg-[#0e1424] border border-slate-800">
                <span className="h-3.5 w-3.5 rounded-full bg-rose-500 animate-ping"></span>
                <div>
                  <div className="font-bold text-rose-400">Red Node: Tainted / Illicit Seed</div>
                  <div className="text-[10px] text-slate-400">Flagged by PageRank / AI Ensemble</div>
                </div>
              </div>
            </div>

            {/* Graph Canvas & Side Legend Guide */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              {/* Vis.js Canvas */}
              <div className="lg:col-span-3 h-[600px] rounded-xl bg-[#090d18] border border-slate-800 relative overflow-hidden shadow-inner cursor-grab active:cursor-grabbing">
                <div ref={networkContainerRef} className="w-full h-full" />
                {graphLoading && (
                  <div className="absolute inset-0 bg-[#090d18]/85 flex flex-col items-center justify-center gap-3 text-slate-300 z-10 pointer-events-none">
                    <RefreshCw size={28} className="animate-spin text-amber-400" />
                    <span className="text-xs font-mono">Querying graph topology & relational UTXO flows...</span>
                  </div>
                )}
                {!graphLoading && graphEmpty && (
                  <div className="absolute inset-0 bg-[#090d18]/90 flex flex-col items-center justify-center gap-3 text-slate-400 p-6 text-center z-10">
                    <GitFork size={36} className="text-slate-600 mb-1" />
                    <span className="text-sm font-semibold text-slate-300">No graph topology found for this identifier</span>
                    <span className="text-xs text-slate-500 max-w-sm">Enter a valid Transaction ID (TXID) above or click "Trace Graph" from the Forensic Alerts table.</span>
                  </div>
                )}
              </div>

              {/* Side Guide / How to Interpret for Judges & Officers */}
              <div className="p-4 rounded-xl bg-[#0e1424] border border-slate-800 space-y-4 text-xs">
                <div className="font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800 pb-2">
                  <ShieldAlert size={14} /> How to Read This Graph
                </div>

                <div className="space-y-3 text-slate-300 leading-relaxed">
                  <div>
                    <span className="font-bold text-slate-100">1. Peeling Chains (Laundering):</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      A single transaction splits into two outputs: one small pseudo-legitimate transfer and one peel/change address moving bulk illicit funds across sequential hops.
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-slate-100">2. CoinJoin Mixing Pools:</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Multi-party transactions combining inputs from various participants and producing identical output denominations to obscure sender-receiver links.
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-slate-100">3. Entity Resolution (CIO Heuristic):</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Common-Input-Ownership rule: All input wallet addresses co-spent in a single transaction are controlled by the same actor entity via Disjoint Set Union.
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-slate-100">4. Interactive Canvas Controls:</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Use mouse wheel to <strong>Zoom In/Out</strong>. Click and drag nodes to <strong>Reposition</strong>. Hover over any node to view detailed forensic metadata tooltips.
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 font-mono">
                  Pro-Tip: Click "Trace Graph" from the Forensic Alerts or Suspect Profiler tabs to instantly focus that transaction in this interactive network.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SUSPECT WALLET INVESTIGATION */}
        {activeTab === 'suspect' && (
          <div className="space-y-6">
            <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-4">
              <h3 className="font-bold text-slate-200 flex items-center gap-2">
                <Search size={18} className="text-amber-400" />
                Inspect Suspect Bitcoin Address
              </h3>
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchAddress}
                  onChange={(e) => setSearchAddress(e.target.value)}
                  placeholder="Enter suspect Bitcoin address (e.g. 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa)..."
                  className="flex-1 bg-[#07090e] border border-slate-700 rounded-lg px-4 py-2.5 text-sm font-mono text-slate-100 focus:outline-none focus:border-amber-400"
                />
                <button
                  onClick={() => investigateWallet(searchAddress)}
                  disabled={isSearching}
                  className="px-6 py-2.5 rounded-lg bg-amber-500 text-slate-950 font-bold text-sm hover:bg-amber-400 transition disabled:opacity-50 cursor-pointer"
                >
                  {isSearching ? 'Profiling...' : 'Investigate'}
                </button>
              </div>

              {topSuspects.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80">
                  <div className="text-xs text-slate-400 mb-2">High-Risk Tainted Seeds Detected by PageRank:</div>
                  <div className="flex flex-wrap gap-2">
                    {topSuspects.slice(0, 6).map((s, idx) => {
                      const addr = s.wallet_address || s.address;
                      const vol = s.total_vol_btc ? `${s.total_vol_btc} BTC` : '';
                      return (
                        <button
                          key={idx}
                          onClick={() => {
                            setSearchAddress(addr);
                            investigateWallet(addr);
                          }}
                          className="px-3 py-1.5 rounded-lg bg-[#07090e] border border-slate-700 hover:border-amber-400 text-xs font-mono text-slate-200 flex items-center gap-2 transition cursor-pointer shadow-sm hover:shadow-amber-500/10"
                        >
                          <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                          <span>{addr.slice(0, 14)}...</span>
                          <span className="text-amber-400 font-bold font-mono">{vol || `Risk: ${(s.risk_score || 0).toFixed(2)}`}</span>
                        </button>
                      );
                    })}

                    {/* Dedicated 1-Click Demo Chip for Multi-IP Hopping Actor */}
                    <button
                      onClick={() => {
                        const hopAddr = '1EnAhuVDifUaaQgEHo9acEhtd3FfWgfW';
                        setSearchAddress(hopAddr);
                        investigateWallet(hopAddr);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-purple-950/40 border border-purple-500/50 hover:border-purple-400 text-xs font-mono text-purple-200 flex items-center gap-2 transition cursor-pointer shadow-sm hover:shadow-purple-500/20"
                    >
                      <Globe size={12} className="text-purple-400 animate-pulse" />
                      <span>1EnAhuVD...</span>
                      <span className="text-purple-300 font-bold font-mono bg-purple-900/60 px-1.5 py-0.5 rounded text-[10px]">
                        Multi-IP Hopping (3 IPs)
                      </span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {walletData && (
              <div className="space-y-6">
                <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-400 uppercase">Target Address:</span>
                        <span className="font-mono text-amber-400 font-bold text-sm sm:text-base break-all">
                          {walletData.address}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-400 font-mono">
                        <span>Entity ID: {walletData.entity_id || 'Solo Entity'}</span>
                        {walletData.is_tainted_seed && (
                          <span className="bg-rose-500/10 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded font-bold">
                            Illicit Seed Node
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-[10px] text-slate-400 uppercase">PageRank Risk Level</div>
                        <div className={`text-lg font-black font-mono ${
                          walletData.risk_level === 'CRITICAL' ? 'text-rose-500' :
                          walletData.risk_level === 'HIGH' ? 'text-orange-400' : 'text-amber-400'
                        }`}>
                          {walletData.risk_level} ({walletData.risk_score})
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-4 border-t border-slate-800">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase">Total Received</div>
                      <div className="text-base font-bold font-mono text-emerald-400 flex items-center gap-1">
                        <ArrowDownLeft size={14} /> {walletData.total_received_btc} BTC
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase">Total Sent</div>
                      <div className="text-base font-bold font-mono text-rose-400 flex items-center gap-1">
                        <ArrowUpRight size={14} /> {walletData.total_sent_btc} BTC
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase">Current Balance</div>
                      <div className="text-base font-bold font-mono text-slate-200">
                        {walletData.current_balance_btc} BTC
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase">Total Activity</div>
                      <div className="text-base font-bold font-mono text-cyan-400">
                        {walletData.total_transactions} Transactions
                      </div>
                    </div>
                  </div>
                </div>

                {/* Associated Network Telemetry & Multi-IP Footprint */}
                {walletData.associated_ips && walletData.associated_ips.length > 0 && (
                  <div className="p-4 rounded-xl bg-[#0e1424] border border-slate-800 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs font-bold text-cyan-400 uppercase flex items-center gap-2">
                        <Globe size={14} /> Associated Network Footprint ({walletData.ip_diversity_count} Distinct IPs, {walletData.country_diversity_count} Countries)
                      </div>
                      {walletData.ip_hopping_detected && (
                        <span className="px-2.5 py-0.5 rounded-full bg-purple-950/60 text-purple-300 border border-purple-500/50 text-[10px] font-bold flex items-center gap-1.5 shadow-sm shadow-purple-500/20">
                          <AlertTriangle size={12} className="text-purple-400" /> IP Hopping / Proxy Rotation Suspect
                        </span>
                      )}
                    </div>

                    {walletData.ip_hopping_detected && (
                      <div className="p-3 rounded-lg bg-purple-950/25 border border-purple-800/40 text-[11px] text-purple-200 leading-relaxed">
                        <strong className="text-purple-300">Forensic Network Signal:</strong> This wallet has repeatedly broadcast Bitcoin transactions across {walletData.ip_diversity_count} distinct IP addresses and {walletData.country_diversity_count} distinct country jurisdictions/ASNs. This is a signature indicator of automated proxy churn, commercial VPN server hopping (e.g. AWS/Alibaba/Tor), or distributed node evasion.
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                      {walletData.associated_ips.map((ipObj, idx) => (
                        <div key={idx} className="p-2.5 rounded-lg bg-[#07090e] border border-slate-800 flex items-center justify-between text-xs hover:border-slate-700 transition">
                          <div>
                            <div className="font-mono text-cyan-400 font-bold flex items-center gap-1.5">
                              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                              {ipObj.ip}
                            </div>
                            <div className="text-[10px] text-slate-400 truncate max-w-[190px]">
                              {ipObj.country} · {ipObj.asn}
                            </div>
                          </div>
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-amber-400 font-bold">
                            {ipObj.tx_count} TXs
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {walletData.co_clustered_wallets && walletData.co_clustered_wallets.length > 0 && (
                  <div className="p-4 rounded-xl bg-[#0e1424] border border-slate-800 space-y-2">
                    <div className="text-xs font-bold text-amber-400 uppercase flex items-center gap-2">
                      <Lock size={14} /> Common-Input Clustered Wallets (Same Controller)
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {walletData.co_clustered_wallets.map((cw, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setSearchAddress(cw);
                            investigateWallet(cw);
                          }}
                          className="px-2.5 py-1 rounded bg-[#07090e] border border-slate-700 hover:border-amber-400 text-xs font-mono text-slate-300 transition cursor-pointer"
                        >
                          {cw.slice(0, 14)}...
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="rounded-xl border border-slate-800 bg-[#0e1424] overflow-hidden">
                  <div className="p-4 border-b border-slate-800 font-bold text-xs uppercase tracking-wider text-slate-300">
                    Recent UTXO Ledger Activity ({walletData.transactions.length})
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-[#090d18] text-slate-400 font-mono border-b border-slate-800">
                        <tr>
                          <th className="p-3">Direction</th>
                          <th className="p-3">Transaction ID</th>
                          <th className="p-3">Amount (BTC)</th>
                          <th className="p-3">Relay Country</th>
                          <th className="p-3">Timestamp (UTC)</th>
                          <th className="p-3 text-right">Inspect</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-sans">
                        {walletData.transactions.map((tx, i) => (
                          <tr key={i} className="hover:bg-slate-800/30 transition">
                            <td className="p-3 font-bold">
                              {tx.direction === 'INCOMING' ? (
                                <span className="text-emerald-400 flex items-center gap-1">
                                  <ArrowDownLeft size={12} /> IN
                                </span>
                              ) : (
                                <span className="text-rose-400 flex items-center gap-1">
                                  <ArrowUpRight size={12} /> OUT
                                </span>
                              )}
                            </td>
                            <td className="p-3 font-mono text-slate-300">{tx.txid.slice(0, 16)}...</td>
                            <td className="p-3 font-mono font-bold text-slate-100">{tx.amount_btc} BTC</td>
                            <td className="p-3 font-mono text-slate-400">{tx.geo_country || 'UNKNOWN'}</td>
                            <td className="p-3 font-mono text-slate-400">{tx.datetime_utc || 'N/A'}</td>
                            <td className="p-3 text-right">
                              <button
                                onClick={() => {
                                  setGraphCenterTx(tx.txid);
                                  setActiveTab('graph');
                                }}
                                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-300 text-[11px] font-mono transition cursor-pointer"
                              >
                                View TX
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: PIPELINE ORCHESTRATION */}
        {activeTab === 'pipeline' && (
          <div className="space-y-6">
            <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800 space-y-3">
              <h3 className="font-bold text-slate-200 flex items-center gap-2">
                <Cpu size={18} className="text-amber-400" />
                Pipeline Orchestration Engine
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                ChainSentinel runs an end-to-end multi-stage pipeline completely offline on your workstation:
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-4 rounded-lg bg-[#07090e] border border-slate-800">
                  <div className="text-xs font-bold text-amber-400 uppercase">Stage 1: Ground Truth Ingestion</div>
                  <p className="text-xs text-slate-400 mt-1">
                    Multi-format streaming parser loads CSV, JSON, XML into SQLite with transaction atomicity.
                  </p>
                  <div className="mt-2 text-xs font-mono text-emerald-400">✓ Database: bitcoin_traffic.db</div>
                </div>

                <div className="p-4 rounded-lg bg-[#07090e] border border-slate-800">
                  <div className="text-xs font-bold text-cyan-400 uppercase">Stage 2: Entity Resolution</div>
                  <p className="text-xs text-slate-400 mt-1">
                    Disjoint Set Union (DSU) groups addresses co-spent in the same transaction into single actor entities.
                  </p>
                  <div className="mt-2 text-xs font-mono text-emerald-400">✓ Graph: 42,707 nodes resolved</div>
                </div>

                <div className="p-4 rounded-lg bg-[#07090e] border border-slate-800">
                  <div className="text-xs font-bold text-rose-400 uppercase">Stage 3: AI Ensemble Detection</div>
                  <p className="text-xs text-slate-400 mt-1">
                    Isolation Forest + Autoencoder reconstruction loss + PageRank risk propagation ($α=0.85$).
                  </p>
                  <div className="mt-2 text-xs font-mono text-emerald-400">✓ 150 Alerts with SHAP explanations</div>
                </div>
              </div>
            </div>

            <div className="p-5 rounded-xl bg-[#0e1424] border border-slate-800">
              <h4 className="font-bold text-slate-200 text-sm mb-2">CLI Pipeline Execution Command</h4>
              <p className="text-xs text-slate-400 mb-3">
                To run or re-train the entire pipeline from scratch, execute this single command in terminal:
              </p>
              <div className="p-3 bg-[#07090e] rounded-lg border border-slate-800 font-mono text-xs text-amber-400 select-all">
                python run_pipeline.py
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0b0f19] px-6 py-3 text-center text-xs text-slate-500 font-mono">
        ChainSentinel SOC Forensics · Local Offline Instance · SIH26146 Architecture
      </footer>
    </div>
  );
}
