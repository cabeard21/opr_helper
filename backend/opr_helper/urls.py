from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"data": {"status": "ok"}, "error": None})


urlpatterns = [
    path('', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/advisor/', include('advisor.urls')),
    path('api/', include('army_books.urls')),
    path('api/', include('lists.urls')),
]
