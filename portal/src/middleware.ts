import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { jwtVerify } from 'jose'

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || 'vantix-dev-secret-change-in-production'
)

async function getVerifiedPayload(token: string) {
  try {
    const { payload } = await jwtVerify(token, JWT_SECRET, {
      algorithms: ['HS256'],
    })
    return payload
  } catch {
    return null
  }
}

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname

  // Read JWT from HttpOnly cookie (XSS-safe, set by FastAPI backend)
  const token = request.cookies.get('vp_token')?.value

  // --- Unauthenticated: Redirect to Landing ---
  if (!token) {
    if (path.startsWith('/dashboard')) {
      const url = request.nextUrl.clone()
      url.pathname = '/'
      return NextResponse.redirect(url)
    }
    return NextResponse.next()
  }

  // --- Verify JWT signature ---
  const payload = await getVerifiedPayload(token)

  if (!payload) {
    // Token is forged or expired — nuke cookies and redirect
    const url = request.nextUrl.clone()
    url.pathname = '/'
    const response = NextResponse.redirect(url)
    response.cookies.delete('vp_token')
    response.cookies.delete('vp_session')
    response.cookies.delete('vp_csrf')
    return response
  }

  // --- Role-Based Route Guard ---
  const role = payload.role as string | undefined

  if (path.startsWith('/dashboard/admin')) {
    if (role !== 'ADMIN') {
      const url = request.nextUrl.clone()
      url.pathname = '/dashboard'
      return NextResponse.redirect(url)
    }
  }

  // Inject verified user context into request headers for Server Components
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-user-email', String(payload.sub ?? ''))
  requestHeaders.set('x-user-role', String(role ?? 'VIEWER'))
  requestHeaders.set('x-team-id', String(payload.team_id ?? ''))

  return NextResponse.next({
    request: { headers: requestHeaders },
  })
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
