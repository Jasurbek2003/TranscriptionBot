# How to Create a Payme Payment

This guide shows you how to create payments using the Payme payment gateway.

## Overview

The payment process has two parts:

1. **Frontend (Bot)**: Creates transaction and payment link
2. **Backend (Django)**: Handles webhook callbacks from Payme

---

## Method 1: Using the Bot (Recommended)

### Step 1: User Initiates Payment

User clicks "💳 Top Up" button or uses `/topup` command

### Step 2: Select Payment Method

User selects "Payme" from payment methods

### Step 3: Enter Amount

User enters amount (e.g., 10000 UZS)

### Step 4: Bot Creates Payment

The bot automatically:

1. Creates a pending transaction in database
2. Generates Payme payment link
3. Sends link to user

**Code** (already implemented in `bot/handlers/payment.py`):

```python
# This is already done for you!
payment_service = PaymeService(
    merchant_id=settings.payment.payme_merchant_id,
    secret_key=settings.payment.payme_secret_key,
    test_mode=settings.payment.payme_test_mode
)

payment_url = payment_service.create_payment_link(
    amount=10000,  # Amount in UZS
    order_id=transaction_id,  # Your transaction reference ID
    return_url=None  # Optional callback URL after payment
)

# Send payment link to user
await message.answer(
    f"Pay here: {payment_url}",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay Now", url=payment_url)]
    ])
)
```

### Step 5: User Pays

User clicks link and pays on Payme's website

### Step 6: Automatic Verification

Payme sends webhook to your server:

- URL: `https://yourdomain.com/api/transactions/webhooks/payme/`
- The webhook handler automatically verifies and completes the transaction

---

## Method 2: Programmatic Payment (Django/API)

### Step 1: Create Transaction in Database

```python
from django_admin.apps.transactions.models import Transaction
from django_admin.apps.wallet.models import Wallet
from decimal import Decimal
import uuid

# Get or create wallet for user
wallet = Wallet.objects.get_or_create(user=user)[0]

# Create pending transaction
transaction = Transaction.objects.create(
    user=user,
    wallet=wallet,
    type="credit",
    amount=Decimal("10000.00"),
    balance_before=wallet.balance,
    balance_after=wallet.balance,  # Will be updated by webhook
    payment_method="payme",
    status="pending",
    reference_id=str(uuid.uuid4()),
    description="Top up via Payme"
)
```

### Step 2: Generate Payment Link

```python
from services.payment.payme_service import PaymeService
from django.conf import settings

# Initialize Payme service
payme = PaymeService(
    merchant_id=settings.PAYME_MERCHANT_ID,
    secret_key=settings.PAYME_SECRET_KEY,
    test_mode=True  # Set to False for production
)

# Create payment link
payment_url = payme.create_payment_link(
    amount=10000,  # Amount in UZS (will be converted to tiyin internally)
    order_id=transaction.reference_id,
    return_url="https://yourdomain.com/payment-success"  # Optional
)

print(f"Payment URL: {payment_url}")
```

### Step 3: Send Link to User

Send the `payment_url` to your user via:

- Telegram message with inline button
- SMS
- Email
- QR code

### Step 4: Payment Flow

1. **User pays** on Payme website
2. **Payme calls your webhook** with `CheckPerformTransaction`
3. **Your server responds** if transaction is valid
4. **Payme calls webhook** with `CreateTransaction` (reserves payment)
5. **Payme calls webhook** with `PerformTransaction` (completes payment)
6. **Your server updates** wallet balance and transaction status
7. **User receives notification** (you implement this)

---

## Payment Link Format

The generated payment link looks like:

```
https://checkout.paycom.uz?m=MERCHANT_ID&a=1000000&ac.order_id=TRANSACTION_ID
```

Parameters:

- `m` - Merchant ID
- `a` - Amount in **tiyin** (1 UZS = 100 tiyin, so 10000 UZS = 1000000 tiyin)
- `ac.order_id` - Your transaction reference ID

---

## Webhook Flow (Automatic)

Your webhook handler at `/api/transactions/webhooks/payme/` handles these JSON-RPC methods:

### 1. CheckPerformTransaction

**Purpose**: Verify if transaction can be performed

**Request from Payme**:

```json
{
  "method": "CheckPerformTransaction",
  "params": {
    "amount": 1000000,
    "account": {
      "order_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  },
  "id": 1
}
```

**Your Response**:

```json
{
  "result": {
    "allow": true
  },
  "id": 1
}
```

### 2. CreateTransaction

**Purpose**: Create and reserve transaction

**Request from Payme**:

```json
{
  "method": "CreateTransaction",
  "params": {
    "id": "63107b1dd15f8d8d093b379b",
    "time": 1662006045123,
    "amount": 1000000,
    "account": {
      "order_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  },
  "id": 2
}
```

**Your Response**:

```json
{
  "result": {
    "create_time": 1662006045123,
    "transaction": "1234",
    "state": 1
  },
  "id": 2
}
```

### 3. PerformTransaction

**Purpose**: Complete the payment

**Request from Payme**:

```json
{
  "method": "PerformTransaction",
  "params": {
    "id": "63107b1dd15f8d8d093b379b"
  },
  "id": 3
}
```

**Your Response**:

```json
{
  "result": {
    "transaction": "1234",
    "perform_time": 1662006145456,
    "state": 2
  },
  "id": 3
}
```

At this point:

- ✅ Wallet balance is increased
- ✅ Transaction status changed to "completed"
- ✅ User is notified (you should implement this)

### 4. CancelTransaction

**Purpose**: Cancel or refund payment

**Request from Payme**:

```json
{
  "method": "CancelTransaction",
  "params": {
    "id": "63107b1dd15f8d8d093b379b",
    "reason": 5
  },
  "id": 4
}
```

**Your Response**:

```json
{
  "result": {
    "transaction": "1234",
    "cancel_time": 1662006200789,
    "state": -1
  },
  "id": 4
}
```

---

## Testing

### Test Environment

Set in `.env`:

```env
PAYME_MERCHANT_ID=your_test_merchant_id
PAYME_SECRET_KEY=your_test_secret_key
```

In Django settings:

```python
PAYME_MERCHANT_ID = env.str('PAYME_MERCHANT_ID')
PAYME_SECRET_KEY = env.str('PAYME_SECRET_KEY')
```

### Test Payment Link

```python
from services.payment.payme_service import PaymeService

payme = PaymeService(
    merchant_id="YOUR_TEST_MERCHANT_ID",
    secret_key="YOUR_TEST_SECRET_KEY",
    test_mode=True
)

url = payme.create_payment_link(
    amount=1000,  # 1000 UZS
    order_id="test-order-123"
)

print(url)
# Output: https://test.paycom.uz?m=...&a=100000&ac.order_id=test-order-123
```

### Test Webhook Locally

Use ngrok to expose your local server:

```bash
ngrok http 8000
```

Then configure your Payme merchant dashboard with:

```
https://your-ngrok-url.ngrok.io/api/transactions/webhooks/payme/
```

### Manual Webhook Test

```bash
curl -X POST http://localhost:8000/api/transactions/webhooks/payme/ \
  -H "Authorization: Basic $(echo -n 'Paycom:YOUR_SECRET_KEY' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "CheckPerformTransaction",
    "params": {
      "amount": 100000,
      "account": {
        "order_id": "your-transaction-ref-id"
      }
    },
    "id": 1
  }'
```

---

## Amount Conversion

Payme uses **tiyin** (1 UZS = 100 tiyin):

```python
# In PaymeService
amount_tiyin = payme_service.amount_to_tiyin(10000)  # 10000 UZS → 1000000 tiyin
amount_uzs = payme_service.tiyin_to_amount(1000000)  # 1000000 tiyin → 10000 UZS

# Automatic in create_payment_link
payment_url = payme.create_payment_link(
    amount=10000  # You pass UZS, service converts to tiyin automatically
)
```

---

## Error Handling

The webhook automatically handles errors:

```python
# Invalid amount
{
  "error": {
    "code": -31001,
    "message": "Amount mismatch"
  }
}

# Transaction not found
{
  "error": {
    "code": -31050,
    "message": "Transaction not found"
  }
}

# Cannot perform operation
{
  "error": {
    "code": -31008,
    "message": "Transaction already completed"
  }
}
```

---

## Production Checklist

- [ ] Set `test_mode=False` in PaymeService
- [ ] Use production Payme merchant credentials
- [ ] Configure webhook URL in Payme merchant dashboard
- [ ] Use HTTPS for webhook endpoint
- [ ] Implement user notifications when payment completes
- [ ] Add logging and monitoring
- [ ] Test refund scenario
- [ ] Set up payment timeout handling (12 hours)

---

## Complete Example

```python
# 1. Create transaction
transaction = Transaction.objects.create(
    user=user,
    wallet=wallet,
    type="credit",
    amount=Decimal("50000.00"),
    payment_method="payme",
    status="pending",
    reference_id=str(uuid.uuid4()),
    description="Balance top-up"
)

# 2. Generate payment link
payme = PaymeService(
    merchant_id=settings.PAYME_MERCHANT_ID,
    secret_key=settings.PAYME_SECRET_KEY,
    test_mode=False
)

payment_url = payme.create_payment_link(
    amount=50000,
    order_id=transaction.reference_id,
    return_url="https://t.me/your_bot"
)

# 3. Send to user
await bot.send_message(
    user.telegram_id,
    f"💳 Pay 50,000 UZS\n\n"
    f"Click the button to pay:",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay with Payme", url=payment_url)]
    ])
)

# 4. Webhook automatically handles the rest!
# - User pays
# - Payme calls webhooks
# - Balance updated
# - Transaction completed
```

---

## Troubleshooting

### Payment link doesn't work

- Check merchant ID and secret key
- Verify test_mode setting matches your credentials

### Webhook not receiving calls

- Check URL is accessible from internet (use ngrok for local testing)
- Verify webhook URL configured in Payme dashboard
- Check Basic Auth credentials are correct

### Transaction not completing

- Check webhook logs in Django
- Verify transaction exists with correct reference_id
- Check amount matches exactly

### Authentication failed

- Verify Authorization header format: `Basic base64(Paycom:SECRET_KEY)`
- Check secret key is correct

---

## Documentation Links

- **Payme Official Docs**: https://developer.help.paycom.uz/
- **Merchant API Methods**: https://developer.help.paycom.uz/metody-merchant-api
- **Error Codes**: https://developer.help.paycom.uz/metody-merchant-api/oshibki-errors

---

**That's it!** Your Payme integration is ready to use. The bot handler already implements all of this for you.
