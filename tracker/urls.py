from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('callback', views.callback, name='callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update-status/<int:app_id>/', views.update_status, name='update_status'),
    path('export/', views.export_csv, name='export_csv'),
    path('logout/', views.logout, name='logout'),
]
