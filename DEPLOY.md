# 🚀 Vector-Pulse: Zero-Cost Deployment Guide

Follow these steps in order. Total time: ~30 minutes. Total cost: ₹0.

---

## Step 1 — Redis (Upstash Free Tier)

1. Go to **[upstash.com](https://upstash.com)** → Create account (free, no card)
2. Click **Create Database** → Choose region closest to you (e.g., `ap-southeast-1` for India)
3. Copy these values from the dashboard:
   - `REDIS_HOST` (looks like `xxxx.upstash.io`)
   - `REDIS_PASSWORD`
   - Keep `REDIS_PORT` as `6379` and `REDIS_SSL` as `true`

---

## Step 2 — Push Code to GitHub

```bash
cd /Users/gowthamcherukuri/Desktop/vector_pulse
git init
git add .
git commit -m "feat: initial Vector-Pulse launch"
# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/vector-pulse.git
git push -u origin main
```

---

## Step 3 — Deploy API on Render (Free)

1. Go to **[render.com](https://render.com)** → Sign up with GitHub
2. Click **New** → **Web Service** → Connect your `vector-pulse` repo
3. Render auto-detects `render.yaml`. Confirm the settings.
4. Under **Environment Variables**, add:
   | Key | Value |
   |-----|-------|
   | `REDIS_HOST` | your Upstash host |
   | `REDIS_PASSWORD` | your Upstash password |
   | `REDIS_PORT` | `6379` |
   | `REDIS_SSL` | `true` |
   | `ADMIN_SECRET_KEY` | pick a strong secret (keep this private!) |
5. Click **Deploy**. Wait ~5 min for the Rust build.
6. Your API lives at: `https://vector-pulse-api.onrender.com`

---

## Step 4 — Deploy Landing Page on Vercel (Free)

1. Go to **[vercel.com](https://vercel.com)** → Sign up with GitHub
2. Click **Add New Project** → Import your `vector-pulse` repo
3. Vercel reads `vercel.json` automatically — no configuration needed
4. Click **Deploy**. Done in ~30 seconds.
5. **Update the landing page** — open `landing/index.html` and replace:
   - `https://your-api.onrender.com` → your real Render URL
   - `your@email.com` → your real email address
   - `https://rzp.io/l/vectorpulse-growth` → your Razorpay payment link (see Step 6)

---

## Step 5 — Issue Your First API Key

Once Render is live, run this once to create a test key:

```bash
curl -X POST https://vector-pulse-api.onrender.com/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","plan":"starter","admin_key":"YOUR_ADMIN_SECRET_KEY"}'
```

You'll get back an `api_key`. Test it:

```bash
curl -X POST https://vector-pulse-api.onrender.com/v1/risk-check \
  -H "X-API-Key: vp_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"uid":"user_1","amt":1200,"addr":"HSR Layout","pin":"560102"}'
```

---

## Step 6 — Set Up Razorpay Payment Links (Free)

1. Go to **[razorpay.com](https://razorpay.com)** → Create account (free, 2% fee per transaction)
2. Dashboard → **Payment Links** → **Create Link**
3. Set amount to ₹2,999, title "Vector-Pulse Growth Plan"
4. Copy the link and paste it into `landing/index.html` → `href` on the Growth plan button
5. Push to GitHub → Vercel auto-deploys in seconds

---

## Step 7 — Get Your First Customer

**LinkedIn message template:**
> "Hey [Name], I see you run [Store]. RTO returns are bleeding margins across D2C right now. I built a fraud detection API that flags fake COD orders in <5ms. Free tier, no infra needed. Mind if I set it up for you for free for 30 days? Happy to show the savings live."

**Tweet template:**
> "Built a real-time RTO fraud engine for Indian e-commerce with Rust + Python. Blocks fake COD orders in &lt;5ms using Z-Score + Sybil detection. Free API tier available. DM me if you run a D2C store 🧵 [screenshot of monitor dashboard]"

---

## Quick Reference

| Service | URL | Cost |
|---------|-----|------|
| API | `https://vector-pulse-api.onrender.com` | ₹0 |
| Landing Page | `https://vector-pulse.vercel.app` | ₹0 |
| Redis | Upstash free tier | ₹0 |
| Payments | Razorpay (2% per txn) | ₹0 upfront |
