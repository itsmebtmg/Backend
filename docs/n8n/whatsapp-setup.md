# Solyra WhatsApp Order Confirmation (n8n + Meta Cloud API)

**Your instance:** https://automation.solyra.ma  
**Quick config:** [CONFIGURE-SOLSYRA.md](./CONFIGURE-SOLSYRA.md)

Darija-only WhatsApp flow:

1. Customer orders on solyra.ma → backend POSTs to n8n
2. n8n sends **Message 1** (approved Meta template) with 3 buttons
3. Customer taps **Iyyeh, n2ekked** → status `whatsapp_confirmed`, sheet `CONFIRMED BY WhatsApp`
4. If **Lumea+ only 239 d.م** → n8n sends **Message 2** upsell (session message, no template)
5. Customer accepts upsell → sheet `UPSELL PACK ON WHATSAPP`, total **349 d.م**
6. Agent calls → sets **Confirmé** in Google Sheet → real `confirmed` (counts for Confirmation rate KPI)

## Prerequisites

| Item | Where |
|------|-------|
| n8n on EasyPanel | Public URL, e.g. `https://n8n.yourdomain.ma` |
| Meta WhatsApp Cloud API | Phone Number ID, permanent access token |
| Approved utility template | WhatsApp Manager → Message templates |
| `ORDER_WEBHOOK_SECRET` | Same on backend + n8n (for API calls to Solyra) |
| Google Sheet dropdown | Add 4 status values (see below) |

## Backend env (EasyPanel `solyra_backend`)

```bash
ENABLE_N8N_WHATSAPP=true
N8N_ORDER_WEBHOOK_URL=https://n8n.yourdomain.ma/webhook/solyra-order-whatsapp
ORDER_WEBHOOK_SECRET=your-secret-here
```

Redeploy backend after setting these.

## Google Sheet — Status dropdown

Add to your **Status** column data validation:

- `CONFIRMED BY WhatsApp`
- `UPSELL PACK ON WHATSAPP`
- `CANCELED BY WhatsApp`
- `MODIFY BY WhatsApp`

## n8n environment variables

In n8n → Settings → Variables:

| Variable | Example |
|----------|---------|
| `META_PHONE_NUMBER_ID` | `123456789012345` |
| `META_ACCESS_TOKEN` | Permanent system user token |
| `META_TEMPLATE_NAME` | `solyra_tlimat_darija_v1` |
| `META_TEMPLATE_LANG` | `ar` |
| `SOLYRA_API_URL` | `https://api.solyra.ma` |
| `ORDER_WEBHOOK_SECRET` | Same as backend |
| `META_VERIFY_TOKEN` | Any string you choose for webhook verify |

## Import workflows

1. n8n → Workflows → Import from file
2. Import [`solyra-order-to-whatsapp.json`](./solyra-order-to-whatsapp.json)
3. Import [`solyra-whatsapp-inbound.json`](./solyra-whatsapp-inbound.json)
4. Activate both workflows
5. Copy **Production URL** from Workflow A webhook node → set as `N8N_ORDER_WEBHOOK_URL` on backend

## Meta Developer — webhook

1. Meta Developer → Your App → WhatsApp → Configuration
2. Callback URL: `https://n8n.yourdomain.ma/webhook/solyra-whatsapp-inbound`
3. Verify token: same as `META_VERIFY_TOKEN` in n8n
4. Subscribe to: `messages`

## Meta template to submit (Darija)

**Name:** `solyra_tlimat_darija_v1`  
**Category:** Utility  
**Language:** Arabic (`ar`)

**Body:**

```
Aslema {{1}} 👋

Chokran 3la tlimatik f Solyra 🛍️

Numero d'tlimat: #{{2}}
Prodwit: {{3}}
Total: {{4}} d.م
Livraison: 24-48h · Khllas 3nd l'istilam

Wakha t2ekked l'commande dyalek?
```

**Quick reply buttons:**

1. `Iyyeh, n2ekked` → payload `wa_confirm`
2. `La, annuli` → payload `wa_cancel`
3. `Beddel` → payload `wa_modify`

Sample values for review: `Fatima`, `Solyra-20260713-4821`, `Lumea+ x1`, `239`

## Message 2 — Upsell (session only, Darija)

Sent by n8n after `wa_confirm` when API returns `whatsapp_upsell_eligible: true`:

```
Mezian {{name}}! 🎉

3endna 3rd exclusive lik:
➕ Solyra Pure (Gel) b +110 d.م
🎁 Sun Protect+ (Ecran) balash

Total jdid: 349 d.م (bdl 239 d.م)

Bghiti tzidhom?
```

Buttons: `Iyyeh, zidhom` (`wa_upsell_yes`) / `La chokran` (`wa_upsell_no`)

## Message 3 — Follow-up (Darija)

```
Chokran! Wa7ed l'agent dyal Solyra ghadi ytssel bik daba bach y2ekked l'adresse. 📞

Ma khllas walou daba — COD 3nd l'istilam.
```

If upsell accepted, append: `Zedna Gel + Ecran l'tlimatik. Total: 349 d.م`

## Solyra API endpoints (called by n8n)

### POST `/v1/orders/whatsapp-lookup`

Resolve order from customer phone (template buttons use static payloads):

```json
{
  "phone": "212612345678",
  "secret": "ORDER_WEBHOOK_SECRET"
}
```

### POST `/v1/orders/whatsapp-status`

```json
{
  "order_id": "Solyra-20260713-4821",
  "action": "confirm",
  "secret": "ORDER_WEBHOOK_SECRET"
}
```

`action`: `confirm` | `cancel` | `modify`

Response includes `whatsapp_upsell_eligible` (boolean).

### POST `/v1/orders/whatsapp-upsell`

```json
{
  "order_id": "Solyra-20260713-4821",
  "accepted": true,
  "secret": "ORDER_WEBHOOK_SECRET"
}
```

## Test checklist

1. Set all env vars, redeploy backend, activate n8n workflows
2. Place Lumea+ test order (239 d.م, decline site upsell)
3. Receive Darija WhatsApp msg 1 within 1–2 min
4. Tap **Iyyeh, n2ekked** → sheet `CONFIRMED BY WhatsApp`, admin `whatsapp_confirmed`
5. Receive upsell msg 2 → tap **Iyyeh, zidhom** → sheet `UPSELL PACK ON WHATSAPP`, total 349
6. Agent sets **Confirmé** → admin `confirmed`, confirmation rate increases
7. Test **La, annuli** and **Beddel**

## KPI meaning (admin dashboard)

| KPI | Counts |
|-----|--------|
| **WhatsApp pre-confirm** | `whatsapp_confirmed` status (said yes on WhatsApp) |
| **Confirmation rate** | Agent **Confirmé** only (`confirmed`, `delivered`, `returned`) |
