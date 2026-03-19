import Image from "next/image";
import Navigation from "../components/Navigation";

export default function Home() {
  return (
    <>
      <div className="ambient-glow">
        <div className="glow-1"></div>
        <div className="glow-2"></div>
      </div>
      
      <Navigation />

      <header className="hero">
        <div className="container">
          <div className="hero-grid">
            <div className="hero-content">
              <div className="eyebrow">
                <span style={{ width: '8px', height: '8px', background: 'var(--accent)', borderRadius: '50%' }}></span>
                Production Ready Fraud Engine
              </div>
              <h1>Order Risk. <span className="gradient-text">Sorted.</span></h1>
              <p>
                Stop RTO fraud before it hits your balance sheet. Our behavioral engine detects high-risk COD orders in real-time, allowing you to force prepaid shipments selectively.
              </p>
              <div className="hero-actions">
                <a href="#pricing" className="btn btn-primary">Try for Free</a>
                <a href="#how-it-works" className="btn btn-secondary">See Demo</a>
              </div>
            </div>
            <div className="hero-visual">
              <div className="hero-img-container">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/hero.png" alt="Vantix Intelligence" className="hero-img" />
              </div>
              <div className="decision-overlay">
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '12px', fontWeight: 700 }}>Live Decision</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, fontSize: '18px' }}>Force Prepaid</span>
                  <span style={{ color: '#ef4444', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>94/100</span>
                </div>
                <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--text-muted)' }}>
                  Signal: High Velocity Anomaly
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <section id="results">
        <div className="container">
          <div className="results-bar">
            {[ 
              { val: "98.2%", label: "Accuracy" },
              { val: "<30ms", label: "Latency" },
              { val: "14.2%", label: "RTO Reduction" },
              { val: "3.5M+", label: "Scans/mo" }
            ].map((stat, i) => (
              <div key={i} className="result-item visible" style={{ opacity: 1, transform: 'translateY(0)' }}>
                <span className="result-value">{stat.val}</span>
                <span className="result-label">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="product" className="surface">
        <div className="container">
          <div className="section-head visible" style={{ opacity: 1, transform: 'translateY(0)' }}>
            <h2>Engineered for High-Velocity Commerce.</h2>
            <p>A battle-tested logic layer that fits right into your checkout flow.</p>
          </div>
          <div className="feature-grid">
            {[ 
              { title: "Behavioral Biometrics", desc: "Analyze how users interact with your forms to detect bot behavior and checkout speed anomalies." },
              { title: "Global Consortium", desc: "Leverage cross-merchant signals to identify serial RTO offenders across the entire network." },
              { title: "Go Core Engine", desc: "Sub-millisecond processing for struct analysis, distributed locks, and database checks powered by Golang." }
            ].map((feat, i) => (
              <div key={i} className="feature-card visible" style={{ opacity: 1, transform: 'translateY(0)' }}>
                <h3>{feat.title}</h3>
                <p>{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing">
        <div className="container">
          <div className="section-head">
            <h2>Transparent Pricing.</h2>
            <p>Start small, scale as you save.</p>
          </div>
          <div className="pricing-grid">
            <div className="feature-card">
              <h3>Free</h3>
              <div style={{ fontSize: '38px', fontWeight: 800, margin: '15px 0' }}>₹0</div>
              <p>Perfect for testing and small pilots.</p>
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '15px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'left' }}>
                <li style={{ marginBottom: '8px' }}>✓ 1,000 scans per month</li>
                <li style={{ marginBottom: '8px' }}>✓ Basic Behavioral Analysis</li>
                <li style={{ marginBottom: '8px' }}>✓ Community Support</li>
              </ul>
            </div>
            <div className="feature-card" style={{ borderColor: 'var(--accent)', transform: 'scale(1.05)', zIndex: 1, boxShadow: '0 0 40px var(--accent-glow)' }}>
              <div className="eyebrow" style={{ marginBottom: '5px' }}>Best for D2C</div>
              <h3>Growth</h3>
              <div style={{ fontSize: '38px', fontWeight: 800, margin: '15px 0' }}>₹2,999</div>
              <p>Supercharge your store&#39;s security.</p>
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '15px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'left' }}>
                <li style={{ marginBottom: '8px', color: 'var(--accent)' }}>✓ 10k scans + Priority Logic</li>
                <li style={{ marginBottom: '8px' }}>✓ Full Consortium Signals</li>
                <li style={{ marginBottom: '8px' }}>✓ Real-time Analytics Hub</li>
                <li style={{ marginBottom: '8px' }}>✓ Instant Webhook Alerts</li>
              </ul>
            </div>
            <div className="feature-card">
              <h3>Scale</h3>
              <div style={{ fontSize: '38px', fontWeight: 800, margin: '15px 0' }}>₹9,999</div>
              <p>For high-volume high-growth brands.</p>
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '15px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'left' }}>
                <li style={{ marginBottom: '8px' }}>✓ 100k scans + Custom Tiers</li>
                <li style={{ marginBottom: '8px' }}>✓ Dedicated Success Manager</li>
                <li style={{ marginBottom: '8px' }}>✓ Advanced AI Training</li>
              </ul>
            </div>
            <div className="feature-card">
              <h3>Enterprise</h3>
              <div style={{ fontSize: '38px', fontWeight: 800, margin: '15px 0' }}>Custom</div>
              <p>Bespoke logic for enterprise scale.</p>
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '15px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'left' }}>
                <li style={{ marginBottom: '8px' }}>✓ Unlimited Scans</li>
                <li style={{ marginBottom: '8px' }}>✓ Custom Domain Integrations</li>
                <li style={{ marginBottom: '8px' }}>✓ On-Premise Deployment</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className="container">
          <div className="footer-grid">
            <div>
              <span className="footer-brand">Vantix</span>
              <p>Protecting the digital economy, one pulse at a time.</p>
            </div>
            <div>
              <h4 style={{ color: 'var(--text)', marginBottom: '12px' }}>Product</h4>
              <a href="#product" style={{ display: 'block', color: 'inherit', marginBottom: '8px', textDecoration: 'none' }}>Features</a>
              <a href="#pricing" style={{ display: 'block', color: 'inherit', marginBottom: '8px', textDecoration: 'none' }}>Pricing</a>
            </div>
            <div>
              <h4 style={{ color: 'var(--text)', marginBottom: '12px' }}>Company</h4>
              <a href="#" style={{ display: 'block', color: 'inherit', marginBottom: '8px', textDecoration: 'none' }}>About</a>
              <a href="#" style={{ display: 'block', color: 'inherit', textDecoration: 'none' }}>Privacy</a>
            </div>
          </div>
          <div style={{ marginTop: '40px', fontSize: '12px', textAlign: 'center', color: 'var(--text-dim)' }}>
            &copy; 2026 Vantix. All rights reserved.
          </div>
        </div>
      </footer>
    </>
  );
}
