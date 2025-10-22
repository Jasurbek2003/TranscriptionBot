# Payme Configuration & Verification Guide

## Issue: telegram_id vs order_id

If you're seeing `telegram_id` in Payme instead of `order_id`, here's how to fix it:

---

## ✅ Current Implementation (CORRECT)

The code is **already correct**. Payment links use `order_id`:

```python
# services/payment/payme_service.py (Line 112)
params = {
    "m": self.merchant_id,
    "a": str(amount_tiyin),
    "ac.order_id": order_id,  # ✅ CORRECT - uses order_id
}
```

### Generated Payment URL Format:

```
https://checkout.paycom.uz?m=MERCHANT_ID&a=1000000&ac.order_id=TRANSACTION_UUID
```

Example:

```
https://checkout.paycom.uz?m=123456&a=1000000&ac.order_id=550e8400-e29b-41d4-a716-446655440000
```

---

## 🔍 Where You Might See telegram_id

### 1. In Payme Merchant Dashboard

When setting up your Payme merchant account, you configure **account fields**:

#### ❌ WRONG Configuration:

```
Account Field: telegram_id
```

#### ✅ CORRECT Configuration:

```
Account Field: order_id
Account Type: String/Text
Required: Yes
```

**How to Fix:**

1. Go to Payme Merchant Dashboard
2. Navigate to Settings → Integration → Account Parameters
3. Change account field name from `telegram_id` to `order_id`
4. Save changes

---

### 2. In Webhook Logs

When Payme sends webhook requests, check the `account` parameter:

#### What Payme Sends:

```json
{
  "method": "CheckPerformTransaction",
  "params": {
    "amount": 1000000,
    "account": {
      "order_id": "550e8400-e29b-41d4-a716-446655440000"  // ✅ Should be order_id
    }
  }
}
```

#### What Our Webhook Expects:

```python
# django_admin/apps/transactions/views.py
account = params.get("account", {})
order_id = account.get("order_id")  # ✅ Looking for order_id

try:
    trans = Transaction.objects.get(reference_id=order_id)
except Transaction.DoesNotExist:
    return error_response("Transaction not found")
```

---

## 🛠️ Verification Steps

### Step 1: Check Payment Link Generation

Run this test:

```python
from services.payment.payme_service import PaymeService

payme = PaymeService(
    merchant_id="your_merchant_id",
    secret_key="your_secret_key",
    test_mode=True
)

url = payme.create_payment_link(
    amount=10000,
    order_id="test-123"
)

print(url)
# Expected: https://test.paycom.uz?m=...&a=1000000&ac.order_id=test-123
```

### Step 2: Check Transaction Creation

```python
from bot.django_setup import Transaction, Wallet
import uuid

# Create test transaction
transaction = Transaction.objects.create(
    user=user,
    wallet=wallet,
    type="credit",
    amount=10000,
    reference_id=str(uuid.uuid4()),  # ✅ This is the order_id
    payment_method="payme",
    status="pending"
)

print(f"Transaction reference_id: {transaction.reference_id}")
# This should match the order_id in payment link
```

### Step 3: Test Webhook

```bash
curl -X POST http://localhost:8000/api/transactions/webhooks/payme/ \
  -H "Authorization: Basic $(echo -n 'Paycom:YOUR_SECRET_KEY' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "CheckPerformTransaction",
    "params": {
      "amount": 1000000,
      "account": {
        "order_id": "PASTE_YOUR_TRANSACTION_REFERENCE_ID_HERE"
      }
    },
    "id": 1
  }'
```

Expected response:

```json
{
  "result": {
    "allow": true
  },
  "id": 1
}
```

---

## 🔧 If You Need to Change Account Field

### Option 1: Update Payme Merchant Dashboard

1. Login to https://merchant.payme.uz
2. Go to Settings → Integration
3. Update account parameter from `telegram_id` to `order_id`
4. **Important**: Existing payment links may break if you change this!

### Option 2: Support Both Fields (Not Recommended)

If you must support both temporarily:

```python
# In webhook handler (NOT RECOMMENDED - just for migration)
account = params.get("account", {})
order_id = account.get("order_id") or account.get("telegram_id")  # Fallback

if not order_id:
    return error_response("order_id or telegram_id required")
```

---

## 📋 Transaction Flow Verification

### 1. User Initiates Payment

```
User sends /topup
→ Selects Payme
→ Enters 10000 UZS
→ Bot creates Transaction with reference_id="550e8400-..."
→ Bot generates payment link with ac.order_id="550e8400-..."
→ User clicks link
```

### 2. User Pays on Payme

```
User completes payment on Payme website
→ Payme stores account.order_id="550e8400-..."
```

### 3. Payme Calls Webhook

```json
POST /api/transactions/webhooks/payme/
{
  "method": "CheckPerformTransaction",
  "params": {
    "account": {
      "order_id": "550e8400-..."  // ✅ Must match reference_id
    }
  }
}
```

### 4. Webhook Finds Transaction

```python
trans = Transaction.objects.get(reference_id="550e8400-...")  # ✅ Found!
```

---

## 🎯 Django Admin Verification

Now you can verify payments in Django Admin:

### Access Admin Panel

```
http://localhost:8000/admin/
```

### Transaction List View

You'll see:

- ✅ Reference ID (shortened)
- ✅ User link
- ✅ Type badge (Credit/Debit)
- ✅ Amount with color
- ✅ Payment method
- ✅ **Gateway badge** (Payme/Click) - NEW!
- ✅ Status badge
- ✅ Created date

### Transaction Detail View

Enhanced fields:

- ✅ Gateway (payme/click)
- ✅ Gateway Transaction ID (Payme's transaction ID)
- ✅ External ID (Payme's transaction ID from CreateTransaction)
- ✅ Reference ID (Your order_id/transaction UUID)

### Search Capabilities

You can now search by:

- ✅ Reference ID
- ✅ External ID (Payme transaction ID)
- ✅ Gateway Transaction ID
- ✅ User Telegram ID
- ✅ User Telegram Username

### Filter Options

Filter transactions by:

- ✅ Type (credit/debit)
- ✅ Status (pending/completed/failed)
- ✅ Payment Method
- ✅ **Gateway (payme/click)** - NEW!
- ✅ Created Date

---

## 🐛 Debugging Common Issues

### Issue 1: "Transaction not found" in webhook

**Cause**: order_id in webhook doesn't match reference_id in database

**Solution**:

```python
# Check what Payme sent
logger.info(f"Payme webhook params: {params}")
order_id = params.get("account", {}).get("order_id")
logger.info(f"Looking for transaction with reference_id={order_id}")

# Check if transaction exists
trans = Transaction.objects.filter(reference_id=order_id).first()
if not trans:
    logger.error(f"No transaction found with reference_id={order_id}")
    # Check all pending transactions
    pending = Transaction.objects.filter(status="pending", payment_method="payme")
    logger.info(f"Pending Payme transactions: {[t.reference_id for t in pending]}")
```

### Issue 2: Payment link works but webhook fails

**Cause**: Mismatch between payment link parameter and webhook lookup

**Solution**:

```python
# Verify payment link generation
payment_url = payme.create_payment_link(amount=10000, order_id=transaction.reference_id)
print(payment_url)
# Should contain: ac.order_id=<transaction.reference_id>

# Verify webhook lookup
order_id = params.get("account", {}).get("order_id")
# Should match: transaction.reference_id
```

### Issue 3: Seeing telegram_id instead of order_id

**Cause**: Payme merchant account configured with wrong field name

**Solution**:

1. Check Payme merchant dashboard settings
2. Verify account field is named `order_id` not `telegram_id`
3. If you change it, update all active payment links

---

## ✅ Complete Checklist

- [x] Transaction model has `reference_id` field (UUID)
- [x] Payment link uses `ac.order_id=<reference_id>`
- [x] Webhook looks up transaction by `reference_id`
- [x] Payme merchant dashboard configured with `order_id` field
- [x] Django admin shows gateway field
- [x] Can search by gateway transaction ID
- [x] Can filter by gateway (payme/click)

---

## 📊 Admin Panel Access

### Transaction Admin Features

1. **List View**:
    - Click and Payme badges with colors
    - Gateway field for filtering
    - Reference ID (shortened for readability)
    - Searchable by all IDs

2. **Detail View**:
    - All gateway-related fields
    - Payment method and gateway
    - Transaction IDs from payment gateways
    - Related user and wallet

3. **Actions**:
    - Mark as completed (bulk action)
    - Mark as failed (bulk action)
    - Export to CSV

### Wallet Admin Features

1. **List View**:
    - User info with link
    - Balance with color coding
    - Total credited/debited
    - Active/Inactive status

2. **Actions**:
    - Activate/Deactivate wallets
    - Add bonus (100 UZS)

---

## 🎉 Summary

**The code is already correct!** ✅

- Payment links use `order_id` ✅
- Webhooks expect `order_id` ✅
- Admin panel enhanced with gateway tracking ✅

If you're seeing `telegram_id` anywhere, it's likely in your Payme merchant dashboard configuration - update it to
`order_id`.

**Need help?** Check Django admin logs at:

```
django_admin/logs/django.log
```
