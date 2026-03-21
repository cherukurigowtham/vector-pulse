
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE
  ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem("vp_token")
  
  const headers = {
    "Content-Type": "application/json",
    ...(token && { "Authorization": `Bearer ${token}` }),
    ...options.headers,
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`)
  }

  return response.json()
}
