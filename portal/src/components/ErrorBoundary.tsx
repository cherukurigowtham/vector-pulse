"use client"

import React from "react"
import { ShieldAlert, RefreshCw } from "lucide-react"

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  errorMessage: string
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, errorMessage: "" }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // In production, this would call Sentry.captureException(error, { extra: info })
    console.error("[ErrorBoundary] Caught error:", error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-red-100 shadow-xl shadow-red-50/50 p-8 text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50">
              <ShieldAlert className="h-8 w-8 text-red-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-slate-600 mb-1">
              An unexpected error was caught. Our team has been notified automatically.
            </p>
            {process.env.NODE_ENV === "development" && (
              <p className="mt-3 text-xs font-mono text-red-600 bg-red-50 rounded-lg px-3 py-2 text-left break-all">
                {this.state.errorMessage}
              </p>
            )}
            <button
              onClick={() => {
                this.setState({ hasError: false, errorMessage: "" })
                window.location.reload()
              }}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Reload application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
