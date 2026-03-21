"use client"

import { useState } from "react"
import { Bot, Send, Sparkles, Terminal } from "lucide-react"
import { cn } from "@/lib/cn"

export default function ForensicAnalyst() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Forensics assistant is online. Ask about an anomaly and I will summarize likely causes." },
  ])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  const handleSend = () => {
    if (!input.trim()) return
    setMessages((prev) => [...prev, { role: "user", content: input }])
    setInput("")
    setIsTyping(true)

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I found an elevated velocity pattern in the Maharashtra segment over the last 6 hours. Recommend stricter rules for first-time users and closer device clustering checks.",
        },
      ])
      setIsTyping(false)
    }, 1000)
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">AI Forensics</h1>
            <p className="text-sm text-slate-600">Investigate suspicious behavior quickly.</p>
          </div>
        </div>

        <button className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400">
          <Terminal className="h-4 w-4" />
          View logs
        </button>
      </div>

      <div className="app-card flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {messages.map((message, index) => (
            <div key={index} className={cn("max-w-[85%]", message.role === "user" ? "ml-auto" : "mr-auto")}>
              <div
                className={cn(
                  "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  message.role === "user" ? "bg-blue-600 text-white" : "border border-slate-200 bg-slate-50 text-slate-700",
                )}
              >
                {message.content}
              </div>
            </div>
          ))}

          {isTyping ? (
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500">
              <Sparkles className="h-4 w-4" />
              Analyzing latest events...
            </div>
          ) : null}
        </div>

        <div className="border-t border-slate-200 p-4">
          <div className="relative">
            <input
              type="text"
              className="app-input pr-12"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about suspicious behavior"
            />
            <button
              onClick={handleSend}
              className="absolute right-1.5 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg bg-[var(--primary)] text-white hover:bg-blue-700"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
