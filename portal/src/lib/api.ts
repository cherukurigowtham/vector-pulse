
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE
  ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1`
  : "http://localhost:8000/api/v1"

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
    // HttpOnly cookies (vp_token, vp_session) are sent automatically — no localStorage needed
    credentials: "include",
  })

  if (response.status === 401) {
    // Session expired — redirect to landing page cleanly
    if (typeof window !== "undefined") window.location.href = "/"
    throw new Error("Session expired. Redirecting to login.")
  }

  if (!response.ok) {
    const body = await response.text()
    throw new Error(`API Error ${response.status}: ${body || response.statusText}`)
  }

  return response.json()
}
