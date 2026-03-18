"use client"

import { useState, useRef, useEffect } from "react"
import { 
  BrainCircuit, 
  Send, 
  User, 
  Bot, 
  Scale, 
  ShieldCheck, 
  ExternalLink,
  ChevronRight,
  Sparkles
} from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export default function ForensicAnalyst() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello! I am your AI Forensic Analyst. You can ask me to analyze a specific Transaction ID or query my reasoning on recent blocks.", time: "10:30 AM" }
  ])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isTyping])

  const handleSend = async () => {
    if (!input.trim()) return
    
    const userMsg = { role: "user", content: input, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    // Simulate AI reasoning (Free-of-cost local logic or Gemini Free Tier)
    setTimeout(() => {
      let response = "I've analyzed the request. Based on the Identity Pillar and Velocity spikes in the Maharashtra region, the block is justified with 92% confidence."
      
      if (input.toLowerCase().includes("r-9201")) {
        response = "Audit R-9201 originated from a known VPN IP range (DigitalOcean Proxy). The user attempted 4 checkouts in 30 seconds, triggering a High Velocity block. Reputation score is low (12/100)."
      }

      const botMsg = { role: "assistant", content: response, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      setMessages(prev => [...prev, botMsg])
      setIsTyping(false)
    }, 1500)
  }

  return (
    <div className="flex h-[calc(100vh-160px)] flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <BrainCircuit className="h-6 w-6 text-indigo-500" />
          AI Forensic Analyst
        </h1>
        <p className="text-slate-500">Conversational risk intelligence powered by Gemini.</p>
      </div>

      <div className="flex flex-1 gap-6 overflow-hidden">
        {/* Chat Interface */}
        <div className="flex flex-1 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
            {messages.map((msg, idx) => (
              <div key={idx} className={cn(
                "flex gap-4 max-w-[85%]",
                msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
              )}>
                <div className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-sm font-bold",
                  msg.role === "user" ? "bg-slate-50 border-slate-200 text-slate-600" : "bg-indigo-50 border-indigo-100 text-indigo-600"
                )}>
                  {msg.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className="space-y-1">
                  <div className={cn(
                    "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                    msg.role === "user" 
                      ? "bg-slate-900 text-white" 
                      : "bg-slate-50 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border border-slate-100 dark:border-slate-700 shadow-sm"
                  )}>
                    {msg.content}
                  </div>
                  <p className="text-[10px] text-slate-400 font-medium px-1">{msg.time}</p>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-4 mr-auto">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="bg-slate-50 dark:bg-slate-800 rounded-2xl px-4 py-2.5 flex items-center gap-1.5 shadow-sm border border-slate-100 dark:border-slate-700">
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
          </div>

          <div className="border-t p-4 flex gap-3 bg-slate-50/30 dark:bg-slate-950/30">
            <input 
              type="text" 
              placeholder="Ask about a Transaction ID (e.g., R-9201)..." 
              className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-800 dark:bg-slate-900 shadow-sm"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button 
              onClick={handleSend}
              className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg transition-transform hover:scale-105 active:scale-95 disabled:opacity-50"
              disabled={!input.trim()}
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Sidebar Context */}
        <div className="w-80 space-y-6 overflow-y-auto">
           <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                 <Sparkles className="h-4 w-4 text-amber-500" />
                 Suggested Inquiries
              </h3>
              <div className="space-y-2">
                 {[
                   "Why was R-9201 blocked?",
                   "Show identity clusters today",
                   "Summarize velocity alerts",
                   "Draft a whitelist rule"
                 ].map(q => (
                   <button 
                    key={q} 
                    onClick={() => setInput(q)}
                    className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/50 p-2.5 text-left text-xs font-medium text-slate-600 hover:border-indigo-200 hover:bg-white hover:text-indigo-600 transition-all dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400 dark:hover:text-indigo-400 group"
                   >
                     {q}
                     <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                   </button>
                 ))}
              </div>
           </div>

           <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-5 dark:border-emerald-900/30 dark:bg-emerald-900/10">
              <h3 className="text-xs font-bold text-emerald-800 dark:text-emerald-400 uppercase tracking-widest flex items-center gap-1.5 mb-3">
                 <ShieldCheck className="h-3.5 w-3.5" />
                 Confidence Score
              </h3>
              <div className="text-3xl font-black text-emerald-600 dark:text-emerald-500">92.4%</div>
              <p className="mt-2 text-[11px] text-emerald-700/70 dark:text-emerald-500/50 leading-relaxed font-medium">
                Analysis based on unified consortium intelligence and cognitive behavioral DNA.
              </p>
           </div>
        </div>
      </div>
    </div>
  )
}
