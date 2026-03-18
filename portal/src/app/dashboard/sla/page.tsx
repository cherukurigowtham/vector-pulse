'use client';

import React, { useState, useEffect } from 'react';

export default function SLAMonitor() {
  const [stats, setStats] = useState({
    avg_latency: 0,
    uptime: 99.99,
    accuracy: 94.2,
    total_scans: 0
  });

  useEffect(() => {
    // Simulated real-time pulse from Phase 28/29 Telemetry
    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        avg_latency: 25 + Math.random() * 10,
        total_scans: prev.total_scans + Math.floor(Math.random() * 5)
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-white p-8 font-sans">
      <header className="mb-12 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tighter bg-gradient-to-r from-teal-400 to-blue-500 bg-clip-text text-transparent">
            VANTIX SLA MONITOR
          </h1>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-bold">Platform 2.0 Neural Pulse</p>
        </div>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-teal-500/10 border border-teal-500/20 text-teal-400 rounded-full text-xs font-bold animate-pulse">
            ● SYSTEM LIVE
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        <StatCard label="Avg Neural Latency" value={`${stats.avg_latency.toFixed(2)}ms`} trend="-4.2%" color="text-teal-400" />
        <StatCard label="AI Execution Uptime" value={`${stats.uptime}%`} trend="Optimal" color="text-blue-400" />
        <StatCard label="Adjudication Accuracy" value={`${stats.accuracy}%`} trend="+0.8%" color="text-purple-400" />
        <StatCard label="Total Edge Scans" value={stats.total_scans.toLocaleString()} trend="Live" color="text-white" />
      </div>

      <div className="bg-[#0f0f0f] border border-white/5 rounded-3xl p-8 relative overflow-hidden">
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-teal-500 rounded-full"></span>
            Dynamic Governance Log
        </h2>
        <div className="space-y-4 opacity-80">
          <LogItem time="10:45:22" event="Weight Autotuning for block_rule_7" status="Success" />
          <LogItem time="10:48:05" event="Vault Access: Merchant Key Rotation" status="Audited" />
          <LogItem time="10:50:11" event="SLA Threshold Check: Latency Nominal" status="Nominal" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, trend, color }: any) {
  return (
    <div className="bg-[#0f0f0f] border border-white/5 p-6 rounded-3xl hover:border-teal-500/30 transition-all cursor-default">
      <p className="text-xs font-bold text-gray-500 uppercase tracking-tight mb-4">{label}</p>
      <h3 className={`text-4xl font-black ${color} tracking-tighter`}>{value}</h3>
      <p className="text-[10px] mt-2 font-mono text-gray-400">{trend}</p>
    </div>
  );
}

function LogItem({ time, event, status }: any) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-white/5 last:border-0 text-sm">
      <div className="flex gap-4">
        <span className="text-gray-600 font-mono">{time}</span>
        <span className="font-semibold">{event}</span>
      </div>
      <span className="text-xs font-bold px-2 py-0.5 bg-gray-500/10 rounded uppercase text-gray-400">{status}</span>
    </div>
  );
}
