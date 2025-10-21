# django_admin/webapp/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from apps.users.models import TelegramUser
from apps.wallet.models import Wallet
from apps.transcriptions.models import Transcription
from apps.pricing.utils import get_active_pricing, calculate_transcription_cost
from webapp.models import OneTimeToken
from webapp.telegram_auth import (
    validate_telegram_webapp_data,
    extract_user_from_init_data,
    create_telegram_auth_response
)
from services.transcription.gemini_service import GeminiTranscriptionService
from services.media_utils import get_media_duration
from bot.config import settings

logger = logging.getLogger(__name__)


def home(request):
    """Home page - landing or dashboard"""
    if request.user.is_authenticated:
        # Redirect to dashboard if logged in
        return redirect('webapp:dashboard')

    # Show landing page for anonymous users
    return render(request, 'landing.html', {
        'bot_username': settings.bot_username or 'Test_NJ_bot'
    })


def auth_with_token(request):
    """Authenticate user with one-time token"""
    token_value = request.GET.get('token')

    if not token_value:
        return render(request, 'error.html', {
            'error': 'No token provided',
            'message': 'Please request a new authentication link from the Telegram bot.'
        }, status=400)

    try:
        # Find the token
        print(token_value)
        print(OneTimeToken.objects.all().count(), "all tokens")
        token = OneTimeToken.objects.get(token=token_value)
        print(token, "found")
        # Check if valid
        if not token.is_valid():
            print("not valid")
            return render(request, 'error.html', {
                'error': 'Invalid or expired token',
                'message': 'This authentication link is invalid or has already been used. Please request a new link from the Telegram bot.'
            }, status=400)

        # Get user
        user = TelegramUser.objects.get(id=token.user_id)

        # Mark token as used
        token.is_used = True
        token.used_at = timezone.now()
        token.ip_address = request.META.get('REMOTE_ADDR')
        token.user_agent = request.META.get('HTTP_USER_AGENT', '')
        token.save()

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info(f"User {user.telegram_id} authenticated via one-time token")

        # Redirect to dashboard
        return redirect('webapp:dashboard')

    except OneTimeToken.DoesNotExist:
        return render(request, 'error.html', {
            'error': 'Invalid token',
            'message': 'This authentication link is not valid. Please request a new link from the Telegram bot.'
        }, status=400)
    except TelegramUser.DoesNotExist:
        return render(request, 'error.html', {
            'error': 'User not found',
            'message': 'Your user account was not found. Please contact support.'
        }, status=400)
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        return render(request, 'error.html', {
            'error': 'Authentication failed',
            'message': 'An error occurred during authentication. Please try again.'
        }, status=500)


@login_required
def dashboard(request):
    """Dashboard page"""
    try:
        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)

        # Get recent transcriptions
        recent_transcriptions = Transcription.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        # Get current pricing
        pricing = get_active_pricing()

        return render(request, 'dashboard.html', {
            'user': request.user,
            'wallet': wallet,
            'recent_transcriptions': recent_transcriptions,
            'settings': {
                'pricing': pricing,
                'ai': {
                    'max_file_size_mb': settings.ai.max_file_size_mb
                }
            }
        })
    except Wallet.DoesNotExist:
        logger.error(f"Wallet not found for user {request.user.id}")
        return render(request, 'error.html', {
            'error': 'Wallet not found',
            'message': 'Your wallet was not found. Please contact support.'
        }, status=500)


@login_required
def upload_page(request):
    """File upload page"""
    try:
        wallet = Wallet.objects.get(user=request.user)
        pricing = get_active_pricing()

        return render(request, 'upload.html', {
            'user': request.user,
            'wallet': wallet,
            'max_file_size_mb': settings.ai.max_file_size_mb,
            'max_audio_duration_min': settings.ai.max_audio_duration_seconds // 60,
            'max_video_duration_min': settings.ai.max_video_duration_seconds // 60,
            'settings': {
                'pricing': pricing,
                'ai': {
                    'max_file_size_mb': settings.ai.max_file_size_mb
                }
            }
        })
    except Wallet.DoesNotExist:
        return render(request, 'error.html', {
            'error': 'Wallet not found',
            'message': 'Your wallet was not found. Please contact support.'
        }, status=500)


@login_required
def transcriptions_page(request):
    """View user's transcription history"""
    try:
        # Get user's transcriptions
        transcriptions = Transcription.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]

        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)

        # Get current pricing
        pricing = get_active_pricing()

        return render(request, 'transcriptions.html', {
            'user': request.user,
            'wallet': wallet,
            'transcriptions': transcriptions,
            'settings': {
                'pricing': pricing
            }
        })
    except Wallet.DoesNotExist:
        return render(request, 'error.html', {
            'error': 'Wallet not found',
            'message': 'Your wallet was not found. Please contact support.'
        }, status=500)


@login_required
def payment_page(request):
    """Payment/top-up page"""
    try:
        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)

        return render(request, 'payment.html', {
            'user': request.user,
            'wallet': wallet
        })
    except Wallet.DoesNotExist:
        return render(request, 'error.html', {
            'error': 'Wallet not found',
            'message': 'Your wallet was not found. Please contact support.'
        }, status=500)


def user_logout(request):
    """Logout user"""
    logout(request)
    return redirect('webapp:home')


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webapp_auth(request):
    """
    Authenticate user via Telegram WebApp initData

    This endpoint receives initData from Telegram WebApp and validates it,
    then automatically logs in the user.
    """
    try:
        # Get initData from request
        data = json.loads(request.body)
        init_data = data.get('initData')

        if not init_data:
            return JsonResponse(
                create_telegram_auth_response(False, "No initData provided"),
                status=400
            )

        # Validate initData with bot token
        validated_data = validate_telegram_webapp_data(init_data, settings.bot_token)

        if not validated_data:
            return JsonResponse(
                create_telegram_auth_response(False, "Invalid or expired initData"),
                status=401
            )

        # Extract user data
        user_data = extract_user_from_init_data(validated_data)

        if not user_data or not user_data.get('telegram_id'):
            return JsonResponse(
                create_telegram_auth_response(False, "Could not extract user data"),
                status=400
            )

        # Find or create user
        try:
            user = TelegramUser.objects.get(telegram_id=user_data['telegram_id'])

            # Update user info from Telegram
            user.first_name = user_data.get('first_name', '')
            user.last_name = user_data.get('last_name', '')
            user.username = user_data.get('username', '')
            user.language_code = user_data.get('language_code', 'en')
            user.is_premium = user_data.get('is_premium', False)
            user.last_login = timezone.now()
            user.save()

            logger.info(f"Existing user authenticated via WebApp: {user.telegram_id}")

        except TelegramUser.DoesNotExist:
            # Create new user
            user = TelegramUser.objects.create(
                telegram_id=user_data['telegram_id'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                username=user_data.get('username', ''),
                language_code=user_data.get('language_code', 'en'),
                is_premium=user_data.get('is_premium', False),
                is_active=True,
                is_bot=False
            )

            # Create wallet for new user
            Wallet.objects.create(user=user)

            logger.info(f"New user created via WebApp: {user.telegram_id}")

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Return success response
        return JsonResponse(
            create_telegram_auth_response(
                True,
                "Authentication successful",
                {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'first_name': user.first_name,
                    'username': user.username
                }
            )
        )

    except json.JSONDecodeError:
        return JsonResponse(
            create_telegram_auth_response(False, "Invalid JSON data"),
            status=400
        )
    except Exception as e:
        logger.error(f"Telegram WebApp auth error: {e}", exc_info=True)
        return JsonResponse(
            create_telegram_auth_response(False, "Authentication failed"),
            status=500
        )


# API Endpoints

@login_required
@require_http_methods(["GET"])
def auth_status(request):
    """Check authentication status"""
    return JsonResponse({
        'authenticated': True,
        'user': {
            'id': request.user.id,
            'telegram_id': request.user.telegram_id,
            'first_name': request.user.first_name,
            'username': request.user.username
        }
    })


@login_required
@require_http_methods(["GET"])
def download_transcription(request, transcription_id):
    """Download transcription as text file"""
    try:
        # Get transcription
        transcription = Transcription.objects.get(
            id=transcription_id,
            user=request.user
        )

        # Create response with text file
        from django.http import HttpResponse
        response = HttpResponse(
            transcription.transcription_text,
            content_type='text/plain; charset=utf-8'
        )

        # Set filename
        filename = transcription.file_name or f"transcription_{transcription_id}"
        # Remove extension if exists
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        filename = f"{filename}.txt"

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f"User {request.user.telegram_id} downloaded transcription {transcription_id}")
        return response

    except Transcription.DoesNotExist:
        return JsonResponse({'error': 'Transcription not found'}, status=404)
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return JsonResponse({'error': 'Download failed'}, status=500)


@login_required
@require_http_methods(["POST"])
def upload_file(request):
    """Upload and transcribe file"""
    try:
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        file = request.FILES['file']
        file_content = file.read()
        file_size = len(file_content)
        max_file_size = settings.ai.max_file_size_mb * 1024 * 1024

        # Validate file size
        if file_size > max_file_size:
            return JsonResponse({
                'error': f'File too large. Maximum size: {settings.ai.max_file_size_mb} MB'
            }, status=400)

        # Determine media type from content type
        content_type = file.content_type or ""
        if "audio" in content_type:
            media_type = "audio"
            max_duration = settings.ai.max_audio_duration_seconds
        elif "video" in content_type:
            media_type = "video"
            max_duration = settings.ai.max_video_duration_seconds
        else:
            return JsonResponse({
                'error': 'Unsupported file type. Only audio and video files are supported.'
            }, status=400)

        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)

        # Extract duration from file
        file_extension = file.name.split('.')[-1] if file.name and '.' in file.name else None
        duration = get_media_duration(file_content, file_extension)

        if not duration:
            # Fallback to estimated duration if extraction fails
            logger.warning(f"Could not extract duration from file: {file.name}")
            # Estimate based on file size (rough approximation: 1MB = 1 minute)
            duration = max(60, min(int(file_size / 1024 / 1024 * 60), max_duration))

        # Validate duration
        if duration > max_duration:
            return JsonResponse({
                'error': f'File too long. Maximum duration: {max_duration // 60} minutes'
            }, status=400)

        # Calculate cost using pricing utility
        total_cost = calculate_transcription_cost(media_type, duration)

        # Check balance
        if wallet.balance < total_cost:
            return JsonResponse({
                'error': f'Insufficient balance. Cost: {total_cost:.2f} UZS, Your balance: {wallet.balance:.2f} UZS'
            }, status=400)

        # Transcribe file
        transcription_service = GeminiTranscriptionService(settings.ai.gemini_api_key)

        # This is a synchronous view, so we need to use sync_to_async or run in thread
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        transcription_text = loop.run_until_complete(
            transcription_service.transcribe_from_bytes(file_content, media_type, duration)
        )
        loop.close()

        if not transcription_text:
            return JsonResponse({
                'error': 'Transcription failed. Please try again.'
            }, status=500)

        # Deduct from wallet
        wallet.balance -= total_cost
        wallet.total_debited += total_cost
        wallet.last_transaction_at = timezone.now()
        wallet.save()

        # Save transcription to database
        transcription = Transcription.objects.create(
            user=request.user,
            file_telegram_id='web_upload',
            file_type=media_type,
            file_name=file.name,
            file_size=file_size,
            duration_seconds=duration,
            transcription_text=transcription_text,
            cost=total_cost,
            status='completed',
            completed_at=timezone.now()
        )

        # Update user stats
        request.user.total_transcriptions += 1
        request.user.total_spent += total_cost
        request.user.save()

        return JsonResponse({
            'success': True,
            'transcription_id': transcription.id,
            'transcription_text': transcription_text,
            'cost': float(total_cost),
            'new_balance': float(wallet.balance)
        })

    except Wallet.DoesNotExist:
        return JsonResponse({'error': 'Wallet not found'}, status=400)
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def initiate_payment(request):
    """Initiate payment with Click or Payme"""
    try:
        from apps.transactions.models import Transaction
        import uuid

        # Get payment data
        data = json.loads(request.body)
        gateway = data.get('gateway')  # 'click' or 'payme'
        amount = Decimal(str(data.get('amount', 0)))

        # Validate
        if gateway not in ['click', 'payme']:
            return JsonResponse({'error': 'Invalid payment gateway'}, status=400)

        if amount < 1000:
            return JsonResponse({'error': 'Minimum amount is 1,000 UZS'}, status=400)

        # Get user's wallet
        wallet = Wallet.objects.get(user=request.user)

        # Create transaction record
        transaction = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='credit',
            amount=amount,
            currency='UZS',
            status='pending',
            gateway=gateway,
            reference_id=str(uuid.uuid4()),
            balance_before=wallet.balance
        )

        # Generate payment URL
        if gateway == 'click':
            # Click payment URL
            from django.conf import settings as django_settings
            merchant_id = django_settings.CLICK_MERCHANT_ID
            service_id = django_settings.CLICK_SERVICE_ID

            payment_url = f"https://my.click.uz/services/pay?service_id={service_id}&merchant_id={merchant_id}&amount={amount}&transaction_param={transaction.reference_id}&return_url={request.scheme}://{request.get_host()}/payment/callback/"

        elif gateway == 'payme':
            # Payme payment URL
            from django.conf import settings as django_settings
            import base64

            merchant_id = django_settings.PAYME_MERCHANT_ID

            # Create params object
            params = {
                "m": merchant_id,
                "ac.order_id": transaction.reference_id,
                "a": int(amount * 100)  # Convert to tiyin
            }

            # Encode params
            params_str = ";".join([f"{k}={v}" for k, v in params.items()])
            params_encoded = base64.b64encode(params_str.encode()).decode()

            payment_url = f"https://checkout.paycom.uz/{params_encoded}"

        logger.info(f"Payment initiated: {gateway}, amount: {amount}, transaction: {transaction.id}")

        return JsonResponse({
            'success': True,
            'payment_url': payment_url,
            'transaction_id': transaction.id,
            'reference_id': transaction.reference_id
        })

    except Wallet.DoesNotExist:
        return JsonResponse({'error': 'Wallet not found'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Payment initiation error: {e}", exc_info=True)
        return JsonResponse({'error': 'Failed to initiate payment'}, status=500)
