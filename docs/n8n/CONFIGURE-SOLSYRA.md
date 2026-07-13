# Solyra WhatsApp — your exact configuration

Configured for **automation.solyra.ma** on 2026-07-13.

## Your IDs

| Item | Value |
|------|-------|
| n8n | https://automation.solyra.ma |
| Order webhook URL | `https://automation.solyra.ma/webhook/solyra-order-whatsapp` |
| Inbound webhook URL | `https://automation.solyra.ma/webhook/solyra-whatsapp-inbound` |
| Phone Number ID | `1192283630638261` |
| WhatsApp Business Account ID | `1569571918147458` |
| Solyra API | `https://api.solyra.ma` |
| Meta verify token | `solyra_whatsapp_verify_2026` |

## EasyPanel — already set via MCP

### `solyra` → `backend`
- `ENABLE_N8N_WHATSAPP=true`
- `N8N_ORDER_WEBHOOK_URL=https://automation.solyra.ma/webhook/solyra-order-whatsapp`

**Action required:** Redeploy **backend** on EasyPanel (latest code `778ec42`).

### `solyra` → `n8n`
- `META_PHONE_NUMBER_ID=1192283630638261` ✓
- `META_WABA_ID=1569571918147458` ✓
- `SOLYRA_API_URL=https://api.solyra.ma` ✓
- `SOLYRA_API_URL=https://api.solyra.ma`
- `ORDER_WEBHOOK_SECRET` (same as backend)
- `META_TEMPLATE_NAME=hello_world` (testing until Darija template approved)
- `META_TEMPLATE_LANG=en_US`
- `META_VERIFY_TOKEN=solyra_whatsapp_verify_2026`

**Action required:** Add manually in EasyPanel → n8n → Environment:

```
META_ACCESS_TOKEN=<paste token from Meta API Setup — NO angle brackets>
```

⚠️ Paste the raw token only (starts with `EAA…`). Do **not** include `<` or `>`.

Use the token from **Generate access token** on the WhatsApp API Setup page (expires ~24h). For production, create a **System User** permanent token with `whatsapp_business_messaging`.

Redeploy **n8n** after adding the token.

## Meta Developer — webhook (Configuration tab)

| Field | Value |
|-------|-------|
| Callback URL | `https://automation.solyra.ma/webhook/solyra-whatsapp-inbound` |
| Verify token | `solyra_whatsapp_verify_2026` |
| Subscribe | `messages` |

## n8n — import workflows

1. Open https://automation.solyra.ma/home/workflows
2. **Import** → `solyra-order-to-whatsapp.json`
3. **Import** → `solyra-whatsapp-inbound.json`
4. **Activate** both workflows (inbound is often left inactive — turn it on)
5. Re-import `solyra-order-to-whatsapp.json` if you still have the old 2-node version (new version has **Build Meta Payload** for `hello_world` + Darija)

## Google Sheet — Status dropdown

Add these 4 values:

- `CONFIRMED BY WhatsApp`
- `UPSELL PACK ON WHATSAPP`
- `CANCELED BY WhatsApp`
- `MODIFY BY WhatsApp`

## Testing order

1. Redeploy backend + n8n
2. Generate Meta access token → paste in n8n env → redeploy n8n
3. Register Meta webhook → verify succeeds
4. Activate n8n workflows
5. Place test order on solyra.ma
6. You should receive `hello_world` WhatsApp (pipe test)
7. Submit Darija template `solyra_tlimat_darija_v1` → change n8n `META_TEMPLATE_NAME` + `META_TEMPLATE_LANG=ar`

## Darija template (submit in WhatsApp Manager)

See [whatsapp-setup.md](./whatsapp-setup.md) for full Darija copy and buttons.
