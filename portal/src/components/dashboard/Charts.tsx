"use client"

import { useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { WSMetricPayload } from "@/app/dashboard/page"

const threatData = [
  { name: "Velocity", value: 45, color: "#18181b" },
  { name: "Identity", value: 30, color: "#52525b" },
  { name: "Sybil", value: 15, color: "#a1a1aa" },
  { name: "Geo", value: 10, color: "#d4d4d8" },
]

export function RiskPulseChart({ wsMetrics }: { wsMetrics?: WSMetricPayload }) {
  const [activeData, setActiveData] = useState(() => {
    return Array.from({ length: 24 }).map((_, i) => ({
      time: new Date(Date.now() - (23 - i) * 2000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      scans: Math.floor(Math.random() * 500) + 200,
      blocks: Math.floor(Math.random() * 50) + 10,
    }))
  })

  useEffect(() => {
    if (!wsMetrics) return;
    
    Promise.resolve().then(() => {
      setActiveData((prev) => {
        const next = [...prev.slice(1)]
        const lastScans = next[next.length - 1].scans;
        const lastBlocks = next[next.length - 1].blocks;

        next.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          scans: lastScans + (Math.random() > 0.5 ? 2 : -1),
          blocks: wsMetrics.action === "BLOCKED" ? lastBlocks + 1 : lastBlocks,
        })
        return next
      })
    })
  }, [wsMetrics])

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={activeData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
          <defs>
            <linearGradient id="scanArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#18181b" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#18181b" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="blockArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#f4f4f5" />
          <XAxis 
            dataKey="time" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 500 }}
            dy={12}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 500 }}
          />
          <Tooltip 
            cursor={{ stroke: '#e4e4e7', strokeWidth: 1, strokeDasharray: '4 4' }}
            contentStyle={{ 
              backgroundColor: '#ffffff',
              borderRadius: '8px', 
              border: '1px solid #e4e4e7',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)',
              padding: '10px 14px'
            }}
            itemStyle={{ fontSize: '13px', fontWeight: 600, color: '#18181b' }}
            labelStyle={{ fontSize: '11px', color: '#71717a', fontWeight: 500, marginBottom: '4px' }}
          />
          <Area type="monotone" dataKey="scans" stroke="#18181b" strokeWidth={2} fill="url(#scanArea)" dot={false} activeDot={{ r: 4, strokeWidth: 0, fill: '#18181b' }} isAnimationActive={false} />
          <Area type="monotone" dataKey="blocks" stroke="#ef4444" strokeWidth={2} fill="url(#blockArea)" dot={false} activeDot={{ r: 4, strokeWidth: 0, fill: '#ef4444' }} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ThreatDistributionChart({ wsMetrics }: { wsMetrics?: WSMetricPayload }) {
  const [activeThreatData, setActiveThreatData] = useState(threatData)

  useEffect(() => {
    if (!wsMetrics) return;
    if (wsMetrics.action === "BLOCKED" && wsMetrics.vector) {
      Promise.resolve().then(() => {
        setActiveThreatData((prev) => {
          return prev.map(t => {
            if (t.name.toUpperCase().includes(wsMetrics.vector.split('_')[0])) {
              return { ...t, value: t.value + Math.floor(Math.random() * 5 + 1) };
            }
            return t;
          })
        })
      })
    }
  }, [wsMetrics])

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={activeThreatData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <XAxis type="number" hide />
          <YAxis 
            dataKey="name" 
            type="category" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#71717a", fontSize: 12, fontWeight: 500 }} 
          />
          <Tooltip 
            cursor={{ fill: '#f4f4f5' }} 
            contentStyle={{ 
              borderRadius: '8px', 
              border: '1px solid #e4e4e7',
              boxShadow: '0 2px 4px -1px rgb(0 0 0 / 0.05)',
              padding: '8px 12px'
            }}
            itemStyle={{ fontSize: '13px', fontWeight: 600, color: '#18181b' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={12} isAnimationActive={true} animationDuration={500}>
            {activeThreatData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
