"""
URL configuration for car_marketplace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def index_view(request):
    return JsonResponse({
        "message": "This is an information portal for collecting car advertisement data and providing price prediction based on your car details."
    })

urlpatterns = [
    path('', index_view),
    path('admin/', admin.site.urls),
    path('api/', include('cars.urls')),  # Prefix all car API routes with `/api/`
]
