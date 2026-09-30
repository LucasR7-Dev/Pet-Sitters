"""
Modelos da aplicação PetMee.
Mapeamento das tabelas gerenciadas no Supabase (PostgreSQL).
Todas as tabelas possuem managed = False porque sua criação e migração
são gerenciadas diretamente no Supabase via schema.sql.
"""

from django.db import models


class Usuarios(models.Model):
    """
    Tabela 'usuarios' (public.usuarios no Supabase).
    Armazena o perfil estendido dos usuários autenticados (tutores, cuidadores e petshops).
    """
    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField(blank=True, null=True)
    nome_completo = models.TextField()
    tipo_usuario = models.CharField(max_length=20, default='tutor')  # 'tutor' ou 'petshop'
    is_cuidador = models.BooleanField(default=False)
    genero = models.CharField(max_length=20, blank=True, null=True)
    cidade = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    idade = models.IntegerField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    preco_hora = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return f"{self.nome_completo} ({self.tipo_usuario})"


class Pet(models.Model):
    """
    Tabela 'pets' (public.pets no Supabase).
    Armazena os pets cadastrados pelos tutores para adoção, acolhimento ou busca por cuidador.
    """
    id = models.BigAutoField(primary_key=True)
    tutor_id = models.UUIDField()
    nome = models.TextField()
    especie = models.TextField()
    raca = models.TextField(blank=True, null=True)
    sexo = models.CharField(max_length=20, blank=True, null=True)
    porte = models.CharField(max_length=20, blank=True, null=True)
    idade = models.CharField(max_length=50, blank=True, null=True)
    localizacao = models.TextField()
    saude = models.TextField(blank=True, null=True)
    sobre = models.TextField(blank=True, null=True)
    foto_url = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pets'
        verbose_name = 'Pet'
        verbose_name_plural = 'Pets'

    def __str__(self):
        return f"{self.nome} ({self.especie})"


class Petshop(models.Model):
    """
    Tabela 'petshops' (public.petshops no Supabase).
    Armazena estabelecimentos de petshop parceiros, incluindo CNPJ, endereço,
    cidade, estado e lista de serviços/trabalhos realizados.
    """
    id = models.BigAutoField(primary_key=True)
    user_id = models.UUIDField(blank=True, null=True)
    nome = models.TextField()
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    cidade = models.TextField()
    estado = models.CharField(max_length=2)
    trabalhos = models.TextField(blank=True, null=True)  # Lista de serviços separados por vírgula ou JSON
    sobre = models.TextField(blank=True, null=True)
    foto_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'petshops'
        verbose_name = 'Petshop'
        verbose_name_plural = 'Petshops'

    def __str__(self):
        return f"{self.nome} - {self.cidade}/{self.estado}"


class Produto(models.Model):
    """
    Tabela 'produtos' (public.produtos no Supabase).
    Armazena produtos cadastrados para venda na loja da PetMee.
    """
    id = models.BigAutoField(primary_key=True)
    vendedor_id = models.UUIDField()
    nome = models.TextField()
    descricao = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=80, blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField(default=0)
    foto_url = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return self.nome


class Avaliacao(models.Model):
    """
    Tabela 'avaliacoes' (public.avaliacoes no Supabase).
    Armazena comentários e notas de 1 a 5 atribuídas aos perfis.
    """
    id = models.BigAutoField(primary_key=True)
    autor_id = models.UUIDField()
    avaliado_id = models.UUIDField()
    nota = models.SmallIntegerField()
    comentario = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'avaliacoes'
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'

    def __str__(self):
        return f"Nota {self.nota} para {self.avaliado_id}"
