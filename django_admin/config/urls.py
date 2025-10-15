from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Web interface
    path('', include('webapp.urls')),
    # API URLs
    path('api/users/', include('apps.users.urls')),
    path('api/wallet/', include('apps.wallet.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    # path('api/transcriptions/', include('apps.transcriptions.urls')),
]

# Add Debug Toolbar URLs only in DEBUG mode
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    # Also serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)