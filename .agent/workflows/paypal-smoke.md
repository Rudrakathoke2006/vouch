# PayPal Smoke Test Workflow

Executes a complete end-to-end sandbox lifecycle test:
1. Obtain OAuth2 access token from PayPal Sandbox.
2. Create an order for a synthetic donation ($10.00).
3. Capture the order.
4. Issue a test payout to a verified sandbox recipient.
5. Issue a partial or full refund on the capture.
6. Verify and output all generated transaction IDs.
