/**
 * Vector Pulse: Shopify Webhook Integration (Node.js)
 * 
 * Description:
 * This script demonstrates how to integrate Vector Pulse into a Shopify store using
 * a Node.js Express server to handle the 'orders/create' webhook.
 */

const express = require('express');
const crypto = require('crypto');
const axios = require('axios');

const app = express();
app.use(express.json());

const SHOPIFY_SECRET = process.env.SHOPIFY_API_SECRET;
const VECTOR_PULSE_KEY = process.env.VECTOR_PULSE_API_KEY;
const VECTOR_PULSE_URL = 'https://vector-pulse-b97i.onrender.com/v1/risk-check';

/**
 * Middleware to verify Shopify Webhook signature
 */
function verifyShopifySignature(req, res, next) {
    const hmac = req.get('X-Shopify-Hmac-Sha256');
    const hash = crypto
        .createHmac('sha256', SHOPIFY_SECRET)
        .update(JSON.stringify(req.body))
        .digest('base64');

    if (hash === hmac) {
        return next();
    }
    return res.status(401).send('Unauthorized');
}

app.post('/webhooks/orders-create', verifyShopifySignature, async (req, res) => {
    const order = req.body;

    // 1. Map Shopify order to Vector Pulse Model
    const riskPayload = {
        uid: order.id.toString(),
        amt: parseFloat(order.total_price),
        addr: `${order.shipping_address.address1}, ${order.shipping_address.city}`,
        pin: order.shipping_address.zip,
        name: `${order.shipping_address.first_name} ${order.shipping_address.last_name}`,
        email: order.email,
        phone: order.shipping_address.phone,
        ip: order.browser_ip,
        checkout_time_secs: 10, // Shopify doesn't provide this directly in webhook, 
                                 // would typically be captured by storefront JS
    };

    try {
        // 2. Query Vector Pulse
        const vpResponse = await axios.post(VECTOR_PULSE_URL, riskPayload, {
            headers: { 'X-API-Key': VECTOR_PULSE_KEY }
        });

        const decision = vpResponse.data.decision;

        // 3. Take Action
        if (decision === 'FORCE_PREPAID') {
            console.log(`Risk Detected for Order ${order.name}: ${vpResponse.data.risk_factors.join(', ')}`);
            
            // LOGIC: Tag the order in Shopify or use Shopify API to cancel it if it's COD
            // Example: axios.put(`https://${shop}/admin/api/2023-01/orders/${order.id}.json`, {
            //   order: { tags: "RISKY_ORDER_VECTOR_PULSE" }
            // });
        }

    } catch (error) {
        console.error('Vector Pulse API Error:', error.message);
    }

    res.status(200).send('Webhook Received');
});

app.listen(3000, () => console.log('Vector Pulse Webhook Listener active on port 3000'));
