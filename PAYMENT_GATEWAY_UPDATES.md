# Payment Gateway Services Rewrite - Implementation Guide

This document describes the updates made to Click and Payme merchant services based on their official documentation.

## Changes Overview

### 1. Click Service Updates

**File**: `services/payment/click_service_new.py`

#### Key Improvements:

- **Error Codes**: Added official Click error codes (-1 to -9)
- **Signature Verification**: Fixed signature algorithm for Complete action
    - Prepare (action=0):
      `MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)`
    - Complete (action=1):
      `MD5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)`
    - **NOTE**: The current implementation was missing `merchant_prepare_id` in Complete signature!

- **Response Builders**: Added helper methods for consistent responses
    - `prepare_response()`: For Prepare action responses
    - `complete_response()`: For Complete action responses
    - `error_response()`: For error responses
    - `build_response()`: Generic response builder

- **Authentication**: Added `get_auth_header()` for Merchant API requests
    - Format: `merchant_user_id:digest:timestamp`
    - Digest: `SHA1(timestamp + secret_key)`

- **URLs**: Added `api_url` for Merchant API endpoints

#### Breaking Changes:

- `create_payment_link()` signature changed: removed `user_id` parameter (not needed)
- Removed async from methods (not needed for sync operations)

---

### 2. Payme Service Updates

**File**: `services/payment/payme_service_new.py`

#### Key Improvements:

- **Error Codes**: Added all official Payme error codes
    - General errors: -32xxx (RPC errors)
    - Transaction errors: -31xxx (business logic errors)

- **Transaction States**: Added official state constants
    - `CREATED = 1`: Transaction created/reserved
    - `COMPLETED = 2`: Transaction performed
    - `CANCELLED = -1`: Cancelled before completion
    - `CANCELLED_AFTER_COMPLETE = -2`: Refunded after completion

- **Cancellation Reasons**: Added reason codes (1-10)

- **Response Builders**: Added helpers for all Merchant API methods
    - `check_perform_transaction_response()`
    - `create_transaction_response()`
    - `perform_transaction_response()`
    - `cancel_transaction_response()`
    - `check_transaction_response()`
    - `get_statement_response()`

- **Helper Methods**:
    - `timestamp_ms()`: Get current timestamp in milliseconds
    - `amount_to_tiyin()`: Convert UZS to tiyin (1 UZS = 100 tiyin)
    - `tiyin_to_amount()`: Convert tiyin to UZS

#### Breaking Changes:

- `create_payment_link()` signature changed: removed `user_id` parameter
- Removed async from methods

---

### 3. Webhook Handler Updates

**File**: `django_admin/apps/transactions/views_webhooks_updated.py`

#### Click Webhook Improvements:

1. **Fixed signature verification** for Complete action (now includes `merchant_prepare_id`)
2. **Added error handling** for Click-reported errors
3. **Improved idempotency** - properly handles duplicate requests
4. **Better logging** with more detailed messages
5. **Transaction state validation** - checks cancelled status
6. **Uses service response builders** for consistent formatting

#### Payme Webhook Improvements:

1. **Complete JSON-RPC 2.0 implementation** for all 6 methods:
    - CheckPerformTransaction
    - CreateTransaction
    - PerformTransaction
    - CancelTransaction
    - CheckTransaction
    - GetStatement

2. **Proper error handling** with correct error codes
3. **Idempotency support** for all methods
4. **Refund support** via CancelTransaction
5. **Amount validation** (tiyin to UZS conversion)
6. **GetStatement** implementation for reconciliation
7. **Better state management** with proper state transitions

---

## Installation Steps

### Step 1: Backup Current Files

```bash
cd C:\Users\Predator\PycharmProjects\TranscriptionBot
cp services/payment/click_service.py services/payment/click_service_old.py
cp services/payment/payme_service.py services/payment/payme_service_old.py
cp django_admin/apps/transactions/views.py django_admin/apps/transactions/views_old.py
```

### Step 2: Replace Service Files

```bash
# Replace Click service
mv services/payment/click_service_new.py services/payment/click_service.py

# Replace Payme service
mv services/payment/payme_service_new.py services/payment/payme_service.py
```

### Step 3: Update Webhook Handlers

Open `django_admin/apps/transactions/views.py` and replace the webhook functions:

- Replace `click_webhook()` function (lines 139-266)
- Replace `payme_webhook()` function (lines 269-531)

With the updated implementations from `views_webhooks_updated.py`

### Step 4: Update Django Settings

Ensure your `django_admin/config/settings/base.py` has these settings:

```python
# Click Payment Gateway
CLICK_MERCHANT_ID = env.str('CLICK_MERCHANT_ID')
CLICK_SERVICE_ID = env.str('CLICK_SERVICE_ID')
CLICK_SECRET_KEY = env.str('CLICK_SECRET_KEY')
CLICK_MERCHANT_USER_ID = env.str('CLICK_MERCHANT_USER_ID', default=None)

# Payme Payment Gateway
PAYME_MERCHANT_ID = env.str('PAYME_MERCHANT_ID')
PAYME_SECRET_KEY = env.str('PAYME_SECRET_KEY')
```

### Step 5: Update Environment Variables

Add to your `.env` file:

```env
# Click credentials
CLICK_MERCHANT_ID=your_merchant_id
CLICK_SERVICE_ID=your_service_id
CLICK_SECRET_KEY=your_secret_key
CLICK_MERCHANT_USER_ID=your_merchant_user_id  # Optional, for Merchant API

# Payme credentials
PAYME_MERCHANT_ID=your_merchant_id
PAYME_SECRET_KEY=your_secret_key
```

### Step 6: Update Bot Handler

Update `bot/handlers/payment.py` to remove the `user_id` parameter from `create_payment_link()` calls:

```python
# Old:
payment_url = click_service.create_payment_link(
    amount=amount,
    order_id=transaction.reference_id,
    user_id=str(user.telegram_id),
    return_url=return_url
)

# New:
payment_url = click_service.create_payment_link(
    amount=amount,
    order_id=transaction.reference_id,
    return_url=return_url
)
```

### Step 7: Test the Integration

#### Test Click Webhook (Prepare):

```bash
curl -X POST http://localhost:8000/api/transactions/webhooks/click/ \
  -d "click_trans_id=123456" \
  -d "service_id=YOUR_SERVICE_ID" \
  -d "click_paydoc_id=123" \
  -d "merchant_trans_id=YOUR_TRANSACTION_REF_ID" \
  -d "amount=10000" \
  -d "action=0" \
  -d "error=0" \
  -d "error_note=Success" \
  -d "sign_time=1234567890" \
  -d "sign=CALCULATED_MD5_HASH"
```

#### Test Payme Webhook (CheckPerformTransaction):

```bash
curl -X POST http://localhost:8000/api/transactions/webhooks/payme/ \
  -H "Authorization: Basic $(echo -n 'Paycom:YOUR_SECRET_KEY' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "CheckPerformTransaction",
    "params": {
      "amount": 1000000,
      "account": {
        "order_id": "YOUR_TRANSACTION_REF_ID"
      }
    },
    "id": 1
  }'
```

---

## Key Differences from Old Implementation

### Click Service

| Feature            | Old                         | New                          |
|--------------------|-----------------------------|------------------------------|
| Error codes        | None                        | Official codes (-1 to -9)    |
| Complete signature | Missing merchant_prepare_id | Includes merchant_prepare_id |
| Response format    | Manual dict creation        | Helper methods               |
| Merchant API auth  | Not implemented             | SHA1 digest auth             |
| Async methods      | async                       | sync (not needed)            |

### Payme Service

| Feature              | Old                | New                        |
|----------------------|--------------------|----------------------------|
| Transaction states   | Hardcoded integers | Named constants            |
| Error codes          | Incomplete         | All official codes         |
| Cancellation reasons | Not documented     | All 10 reasons             |
| Response builders    | None               | 6 method-specific builders |
| GetStatement         | Basic              | Full implementation        |
| Amount conversion    | Manual             | Helper methods             |

### Webhook Handlers

| Feature          | Old                | New                      |
|------------------|--------------------|--------------------------|
| Click signature  | Wrong for Complete | Correct for both actions |
| Error handling   | Basic              | Comprehensive            |
| Idempotency      | Partial            | Full support             |
| Click errors     | Not checked        | Validated                |
| Payme refunds    | Not supported      | Fully supported          |
| Logging          | Minimal            | Detailed                 |
| State validation | Basic              | Complete                 |

---

## Testing Checklist

- [ ] Click Prepare request works
- [ ] Click Complete request works (with correct signature)
- [ ] Click signature verification rejects invalid signatures
- [ ] Click handles duplicate Complete requests (idempotency)
- [ ] Payme CheckPerformTransaction works
- [ ] Payme CreateTransaction works
- [ ] Payme PerformTransaction credits wallet
- [ ] Payme CancelTransaction before completion works
- [ ] Payme CancelTransaction after completion (refund) works
- [ ] Payme CheckTransaction returns correct state
- [ ] Payme GetStatement returns transactions
- [ ] Payme rejects requests without proper auth
- [ ] Payment links are generated correctly
- [ ] Amount validation works (Click and Payme)
- [ ] Transaction state transitions are correct

---

## Documentation References

- **Click Official Docs**: https://docs.click.uz/
- **Click Merchant API**: https://docs.click.uz/en/merchant-api-request/
- **Payme Official Docs**: https://developer.help.paycom.uz/
- **Payme Merchant API Protocol**: https://developer.help.paycom.uz/protokol-merchant-api
- **Payme Merchant API Methods**: https://developer.help.paycom.uz/metody-merchant-api

---

## Troubleshooting

### Click Signature Verification Fails

**Issue**: "Invalid signature" error for Complete action

**Solution**: The new implementation correctly includes `merchant_prepare_id` in the signature for Complete action. Make
sure you're using the updated service.

### Payme Authentication Fails

**Issue**: "Insufficient privileges" error

**Solution**: Verify your `PAYME_SECRET_KEY` is correct. The auth header should be:

```
Authorization: Basic base64(Paycom:YOUR_SECRET_KEY)
```

### Amount Mismatch Errors

**Issue**: "Amount mismatch" in Payme

**Solution**: Payme uses tiyin (1 UZS = 100 tiyin). The service now has helper methods:

- `amount_to_tiyin(100)` → 10000
- `tiyin_to_amount(10000)` → 100.0

### Transaction Not Found

**Issue**: Transaction lookup fails in webhooks

**Solution**: Ensure:

1. Transaction `reference_id` matches the ID passed to payment gateway
2. For Payme, also check `gateway="payme"` filter

---

## Migration Notes

This is a **non-breaking update** if you follow the installation steps. The API signatures are mostly compatible, with
these exceptions:

1. **`create_payment_link()`**: Remove `user_id` parameter from calls
2. **Async removal**: If you were using `await`, remove it

All other changes are backward compatible.

---

## Support

If you encounter issues:

1. Check Django logs: `django_admin/logs/django.log`
2. Check bot logs
3. Verify environment variables are set correctly
4. Test webhooks with curl commands provided above
5. Compare signatures manually for Click Complete action

---

**Generated**: 2025-10-21
**Based on**: Official Click and Payme documentation (2025)
