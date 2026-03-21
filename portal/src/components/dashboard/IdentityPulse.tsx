"use client"

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

type IdentityStats = {
  hits?: number
}

export function IdentityPulse({ stats }: { stats?: IdentityStats }) {
  const data = [
    { name: "Email", value: stats?.hits || 0, color: "#18181b" },
    { name: "Cluster", value: Math.round((stats?.hits || 0) * 0.7), color: "#52525b" },
    { name: "Sybil", value: Math.round((stats?.hits || 0) * 0.3), color: "#a1a1aa" },
  ]

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#f4f4f5" />
          <XAxis 
            dataKey="name" 
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
            cursor={{ fill: '#f4f4f5' }}
            contentStyle={{ 
              backgroundColor: '#ffffff',
              borderRadius: '8px', 
              border: '1px solid #e4e4e7',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)',
              padding: '10px 14px'
            }}
            itemStyle={{ fontSize: '13px', fontWeight: 600, color: '#18181b' }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={28}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
