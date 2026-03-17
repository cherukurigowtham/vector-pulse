const axios = require('axios');

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
}

module.exports = VantixClient;
