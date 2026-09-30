"""
Rotas de URL do aplicativo Core do PetMee.
Define o mapeamento de endpoints web e APIs internas.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Rota raiz (redireciona ou exibe registro/início)
    path('', views.cadastro_user, name='inicio'),

    # Autenticação e contas
    path('registro/', views.cadastro_user, name='register'),
    path('registro/petshop/', views.cadastro_petshop, name='cadastro_petshop'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # Páginas principais da plataforma
    path('home/', views.home, name='home'),
    path('sobre/', views.sobre, name='sobre'),
    path('petshops/', views.petshops, name='petshops'),
    path('loja/', views.loja, name='loja'),
    path('loja/produto/novo/', views.cadastrar_produto, name='cadastrar_produto'),

    # Cuidadores e busca avançada
    path('cuidadores/', views.search_cuidadores, name='search_cuidadores'),
    path('search/', views.search_cuidadores, name='search'),
    path('tornar-cuidador/', views.tornar_cuidador, name='tornar_cuidador'),

    # Pets
    path('pets/novo/', views.cadastrar_pet, name='cadastrar_pet'),
    path('pets/<int:pet_id>/', views.detalhes_pet, name='detalhes_pet'),

    # Perfis de usuário
    path('perfil/', views.meu_perfil, name='meu_perfil'),
    path('perfil/<uuid:user_id>/', views.perfil_usuario, name='perfil_usuario'),
    path('perfil/<uuid:user_id>/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/<uuid:user_id>/avaliacoes/', views.criar_avaliacao, name='criar_avaliacao'),

    # APIs internas para filtragem dinâmica de localidades (Estado e Cidade)
    path('api/estados/', views.api_estados, name='api_estados'),
    path('api/cidades/', views.api_cidades, name='api_cidades'),
]
