const axios = require('axios');
const crypto = require('crypto');

class VantixClient {
  /**
   * Official Vantix Node.js SDK.
   * @param {string} apiKey - Your Vantix API Key
   * @param {string} baseUrl - Optional custom API base URL
   */
  constructor(apiKey, baseUrl = 'https://api.vantix.ai') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      timeout: 5000
    });
  }

  /**
   * Verifies API key connectivity.
   * @returns {Promise<boolean>}
   */
  async testConnection() {
    try {
      const resp = await this.client.post('/v1/auth/test-connection');
      return resp.status === 200;
    } catch (e) {
      return false;
    }
  }

  /**
   * Analyzes order risk.
   * @param {Object} orderData - The order details (uid, amt, addr, pin, etc.)
   * @returns {Promise<Object>} The risk analysis result.
   */
  async analyzeOrder(orderData) {
    try {
      const resp = await this.client.post('/v1/risk/analyze', orderData);
      return resp.data;
    } catch (e) {
      console.error('Vantix API Error:', e.response ? e.response.data : e.message);
      throw e;
    }
  }

  /**
   * Internal helper to sign requests (Iron Shield).
   */
  _signRequest(nonce, timestamp, body) {
    const secret = this.apiKey; // Using API Key as secret for now
    const message = Buffer.concat([
      Buffer.from(nonce),
      Buffer.from(timestamp),
      Buffer.from(typeof body === 'string' ? body : JSON.stringify(body))
    ]);
    return crypto.createHmac('sha256', secret).update(message).digest('hex');
  }

  /**
   * Ingests behavioral telemetry data via secure tunnel.
   * @param {string} sessionId - The current user session ID
   * @param {Array} events - List of clickstream events
   */
  async ingestBehavioral(sessionId, events) {
    const nonce = crypto.randomBytes(16).toString('hex');
    const timestamp = (Date.now() / 1000).toString();
    const payload = {
      session_id: sessionId,
      events: events,
      client_metadata: { sdk: 'node-iron-shield' }
    };

    // Encrypted via Signal Tunnel (Simulated XOR for Phase 16)
    const tunnelKey = Buffer.from("VANTIX_IRON_SHIELD_2026");
    const jsonStr = Buffer.from(JSON.stringify(payload));
    const encrypted = Buffer.from(jsonStr.map((b, i) => b ^ tunnelKey[i % tunnelKey.length]));
    const b64Payload = encrypted.toString('base64');

    const body = { payload: b64Payload };
    const signature = this._signRequest(nonce, timestamp, body);

    try {
      const resp = await axios.post(`${this.baseUrl}/v1/behavioral/ingest`, body, {
        headers: {
          'X-API-Key': this.apiKey,
          'X-Vantix-Signature': signature,
          'X-Vantix-Nonce': nonce,
          'X-Vantix-Timestamp': timestamp,
          'Content-Type': 'application/json'
        }
      });
      return resp.data;
    } catch (e) {
      console.error('Vantix Signal Tunnel Error:', e.response ? e.response.data : e.message);
      throw e;
    }
  }
}

module.exports = VantixClient;
