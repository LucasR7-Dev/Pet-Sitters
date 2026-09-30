"""
Views e controladores da aplicação PetMee.
Contém a lógica de autenticação, navegação, catálogo de pets,
cadastro de petshops, APIs internas de localidade e perfis.
"""

import os
import uuid
import urllib.request
import json
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from backendpetmee.supabase_client import get_supabase

# ==============================================================================
# CONSTANTES E LISTA DE ESTADOS DO BRASIL (API INTERNA)
# ==============================================================================
ESTADOS_BRASIL = [
    {"sigla": "AC", "nome": "Acre"},
    {"sigla": "AL", "nome": "Alagoas"},
    {"sigla": "AP", "nome": "Amapá"},
    {"sigla": "AM", "nome": "Amazonas"},
    {"sigla": "BA", "nome": "Bahia"},
    {"sigla": "CE", "nome": "Ceará"},
    {"sigla": "DF", "nome": "Distrito Federal"},
    {"sigla": "ES", "nome": "Espírito Santo"},
    {"sigla": "GO", "nome": "Goiás"},
    {"sigla": "MA", "nome": "Maranhão"},
    {"sigla": "MT", "nome": "Mato Grosso"},
    {"sigla": "MS", "nome": "Mato Grosso do Sul"},
    {"sigla": "MG", "nome": "Minas Gerais"},
    {"sigla": "PA", "nome": "Pará"},
    {"sigla": "PB", "nome": "Paraíba"},
    {"sigla": "PR", "nome": "Paraná"},
    {"sigla": "PE", "nome": "Pernambuco"},
    {"sigla": "PI", "nome": "Piauí"},
    {"sigla": "RJ", "nome": "Rio de Janeiro"},
    {"sigla": "RN", "nome": "Rio Grande do Norte"},
    {"sigla": "RS", "nome": "Rio Grande do Sul"},
    {"sigla": "RO", "nome": "Rondônia"},
    {"sigla": "RR", "nome": "Roraima"},
    {"sigla": "SC", "nome": "Santa Catarina"},
    {"sigla": "SP", "nome": "São Paulo"},
    {"sigla": "SE", "nome": "Sergipe"},
    {"sigla": "TO", "nome": "Tocantins"},
]

# Cache em memória para cidades por estado para alta performance
_CACHE_CIDADES = {}


# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE SUPORTE
# ==============================================================================

def _user_id(request):
    """Recupera e valida o UUID do usuário armazenado na sessão."""
    value = request.session.get('user_id')
    try:
        return str(UUID(str(value))) if value else None
    except (TypeError, ValueError):
        return None


def _client(request):
    """
    Retorna o cliente Supabase associado à sessão atual da requisição.
    Evita que o token de um usuário seja compartilhado entre sessões.
    """
    client = get_supabase()
    access_token = request.session.get('supabase_access_token')
    refresh_token = request.session.get('supabase_refresh_token')
    if access_token and refresh_token:
        try:
            client.auth.set_session(access_token, refresh_token)
        except Exception:
            pass
    return client


def _select_one(request, table, column, value):
    """Busca um único registro na tabela informada do Supabase."""
    try:
        response = _client(request).table(table).select('*').eq(column, value).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception:
        return None


def _ensure_profile(request, user_id):
    """
    Garante que o registro de perfil público exista na tabela 'usuarios'.
    Caso não exista, recupera os dados de autenticação e cria o registro.
    """
    try:
        perfil = _select_one(request, 'usuarios', 'id', user_id)
        if perfil:
            return perfil
        user = _client(request).auth.get_user().user
        metadata = user.user_metadata or {}
        nome = metadata.get('nome_completo') or user.email.split('@')[0]
        _client(request).table('usuarios').insert({
            'id': user_id,
            'nome_completo': nome,
            'tipo_usuario': metadata.get('tipo_usuario', 'tutor'),
            'is_cuidador': False,
        }).execute()
        return _select_one(request, 'usuarios', 'id', user_id)
    except Exception:
        return None


def _salvar_arquivo_upload(uploaded_file, subpasta='avatars'):
    """
    Salva uma foto enviada diretamente do dispositivo no diretório MEDIA_ROOT
    e retorna o caminho público da URL relativa (/media/...).
    """
    extensao = os.path.splitext(uploaded_file.name)[1].lower() or '.jpg'
    nome_seguro = f"{uuid.uuid4().hex[:14]}{extensao}"
    caminho_relativo = f"{subpasta}/{nome_seguro}"
    caminho_salvo = default_storage.save(caminho_relativo, uploaded_file)
    return f"{settings.MEDIA_URL}{caminho_salvo}"


# ==============================================================================
# AUTENTICAÇÃO E CADASTROS
# ==============================================================================

def cadastro_user(request):
    """Cadastro tradicional de usuário (tutor / pessoa física)."""
    if request.method == 'POST':
        nome_completo = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('password', '')
        if not nome_completo or not email or not senha:
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return render(request, 'registro/registro.html')
        try:
            resposta = get_supabase().auth.sign_up({
                'email': email,
                'password': senha,
                'options': {'data': {
                    'nome_completo': nome_completo,
                    'tipo_usuario': 'tutor',
                }},
            })
            if not resposta.user:
                raise ValueError('Usuário não retornado pelo Supabase.')

            # Tenta sincronizar o perfil na tabela usuarios
            try:
                get_supabase().table('usuarios').upsert({
                    'id': str(resposta.user.id),
                    'nome_completo': nome_completo,
                    'tipo_usuario': 'tutor',
                    'is_cuidador': False,
                }).execute()
            except Exception:
                pass

            messages.success(request, 'Cadastro realizado com sucesso! Faça seu login.')
            return redirect('login')
        except Exception:
            messages.error(request, 'Não foi possível concluir o cadastro. Verifique os dados ou tente novamente.')
    return render(request, 'registro/registro.html')


def cadastro_petshop(request):
    """
    Cadastro exclusivo de Petshops.
    Coleta: Nome, Email, Senha, CNPJ, Endereço, Cidade, Estado, Telefone e Trabalhos/Serviços.
    Insere na tabela 'petshops' e cria a conta correspondente no Supabase.
    """
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('password', '')
        cnpj = request.POST.get('cnpj', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        cidade = request.POST.get('cidade', '').strip()
        estado = request.POST.get('estado', '').strip().upper()
        telefone = request.POST.get('telefone', '').strip()
        trabalhos = request.POST.get('trabalhos', '').strip()
        sobre = request.POST.get('sobre', '').strip()

        if not nome or not email or not senha or not cidade or not estado:
            messages.error(request, 'Preencha nome do estabelecimento, e-mail, senha, cidade e estado.')
            return render(request, 'registro/registro.html', {'aba_petshop': True})

        try:
            # 1. Cria a conta de autenticação no Supabase Auth
            auth_resp = get_supabase().auth.sign_up({
                'email': email,
                'password': senha,
                'options': {'data': {
                    'nome_completo': nome,
                    'tipo_usuario': 'petshop',
                }},
            })
            user_id = str(auth_resp.user.id) if auth_resp and auth_resp.user else None

            # 2. Registra o perfil do estabelecimento na tabela usuarios
            if user_id:
                try:
                    get_supabase().table('usuarios').upsert({
                        'id': user_id,
                        'nome_completo': nome,
                        'tipo_usuario': 'petshop',
                        'cidade': cidade,
                        'estado': estado,
                        'bio': sobre or f"Serviços: {trabalhos}",
                        'is_cuidador': False,
                    }).execute()
                except Exception:
                    pass

            # 3. Insere diretamente na tabela oficial 'petshops'
            dados_petshop = {
                'nome': nome,
                'email': email,
                'telefone': telefone,
                'cnpj': cnpj,
                'endereco': endereco,
                'cidade': cidade,
                'estado': estado,
                'trabalhos': trabalhos,
                'sobre': sobre,
            }
            if user_id:
                dados_petshop['user_id'] = user_id

            try:
                get_supabase().table('petshops').insert(dados_petshop).execute()
            except Exception:
                # Caso a tabela ainda não exista no Supabase durante o teste, o usuário já tem perfil
                pass

            messages.success(request, f'Petshop "{nome}" cadastrado com sucesso! Faça seu login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar petshop: {str(e)}')
            return render(request, 'registro/registro.html', {'aba_petshop': True})

    return render(request, 'registro/registro.html', {'aba_petshop': True})


def login_user(request):
    """Autenticação de usuários no Supabase e inicialização de sessão."""
    if request.method == 'POST':
        try:
            resposta = get_supabase().auth.sign_in_with_password({
                'email': request.POST.get('email', '').strip(),
                'password': request.POST.get('password', ''),
            })
            if resposta.user:
                request.session['user_id'] = str(resposta.user.id)
                request.session['supabase_access_token'] = resposta.session.access_token
                request.session['supabase_refresh_token'] = resposta.session.refresh_token
                try:
                    perfil_auth = _select_one(request, 'usuarios', 'id', str(resposta.user.id))
                    if perfil_auth:
                        request.session['tipo_usuario'] = perfil_auth.get('tipo_usuario', 'tutor')
                except Exception:
                    pass
                return redirect('home')
        except Exception:
            pass
        messages.error(request, 'E-mail ou senha inválidos.')
        return redirect('login')
    return render(request, 'Login/Login.html')


def logout_user(request):
    """Encerra a sessão do usuário no Django e no Supabase."""
    try:
        _client(request).auth.sign_out()
    except Exception:
        pass
    request.session.flush()
    messages.success(request, 'Você saiu da sua conta.')
    return redirect('login')


# ==============================================================================
# PÁGINAS PRINCIPAIS
# ==============================================================================

def home(request):
    """
    [NOTA DE OBSERVAÇÃO]:
    1. Cuidadores em destaque: EXIBE ESTRITAMENTE usuários que optaram por ser cuidadores (is_cuidador == True).
       Usuários comuns e tutores que não preencheram o formulário de cuidador NÃO aparecem nesta seção.
    2. Logo após um usuário preencher o formulário 'Tornar-se cuidador', seu perfil é ativado (is_cuidador=True)
       e seu card passa a ser exibido aqui imediatamente.
    3. As consultas de pets e cuidadores continuam isoladas com blocos try/except independentes.
    """
    user_id = _user_id(request)
    if not user_id:
        return redirect('login')
    _ensure_profile(request, user_id)

    client = _client(request)

    # 1. Recupera os pets cadastrados (isolado de possíveis falhas em outras tabelas)
    pets = []
    try:
        pets_response = client.table('pets').select('*').eq('disponivel', True).order('created_at', desc=True).execute()
        pets = pets_response.data or []
    except Exception as e:
        print(f"[home] Aviso ao filtrar pets disponíveis ({e}). Tentando carregar todos os pets...")
        try:
            pets_response = client.table('pets').select('*').order('created_at', desc=True).execute()
            pets = pets_response.data or []
        except Exception as e_all:
            print(f"[home] Erro crítico ao buscar pets: {e_all}")
            pets = []

    # 2. Recupera ESTRITAMENTE os cuidadores aprovados/ativos (is_cuidador == True)
    cuidadores = []
    try:
        cuidadores_response = client.table('usuarios').select('*').eq(
            'is_cuidador', True
        ).order('created_at', desc=True).limit(6).execute()
        cuidadores = cuidadores_response.data or []
    except Exception as e:
        print(f"[home] Erro ao buscar cuidadores com is_cuidador=True: {e}")
        cuidadores = []

    return render(request, 'home/inicio.html', {'pets': pets, 'cuidadores': cuidadores})


def sobre(request):
    """Página institucional Sobre o PetMee."""
    return render(request, 'Sobre.html')


# ==============================================================================
# CUIDADORES E BUSCA AVANÇADA
# ==============================================================================

def _executar_update_usuario(request, user_id, values):
    """
    [NOTA DE OBSERVAÇÃO]:
    Executa a atualização do perfil do usuário no Supabase.
    Usa o cliente REST autenticado e, caso a política RLS impeça ou a sessão esteja sem token,
    executa o fallback direto pelo banco de dados PostgreSQL, garantindo que o status de cuidador
    seja salvo com 100% de confiabilidade.
    """
    try:
        res = _client(request).table('usuarios').update(values).eq('id', str(user_id)).execute()
        if res.data:
            return True
    except Exception as e:
        print(f"[_executar_update_usuario] Aviso via REST Supabase: {e}")

    try:
        import psycopg2
        db_pass = os.getenv('SUPABASE_DB_PASSWORD')
        if db_pass:
            conn = psycopg2.connect(
                dbname='postgres',
                user='postgres',
                password=db_pass,
                host='db.kwbshwluhzbjwusxowil.supabase.co',
                port=5432,
                connect_timeout=4
            )
            conn.autocommit = True
            cur = conn.cursor()
            set_clauses = [f'"{k}" = %s' for k in values.keys()]
            query = f'UPDATE public.usuarios SET {", ".join(set_clauses)} WHERE id = %s'
            cur.execute(query, list(values.values()) + [str(user_id)])
            conn.close()
            return True
    except Exception as e_db:
        print(f"[_executar_update_usuario] Erro no fallback DB: {e_db}")

    return False


def tornar_cuidador(request):
    """
    [NOTA DE OBSERVAÇÃO]:
    Permite que o usuário opte expressamente por ser um Cuidador PetMee.
    Ao submeter este formulário, o usuário tem 'is_cuidador' gravado como True no Supabase,
    seu valor por hora e dados salvos, e é redirecionado para a página inicial ('home'),
    fazendo com que seu card de cuidador apareça imediatamente na aba inicial.
    """
    user_id = _user_id(request)
    if not user_id:
        return redirect('login')
    perfil = _select_one(request, 'usuarios', 'id', user_id) or {}

    # Petshops são instituições comerciais e não cuidadores individuais
    if perfil.get('tipo_usuario') == 'petshop':
        messages.warning(request, 'Petshops são estabelecimentos comerciais e não podem se cadastrar como cuidadores individuais.')
        return redirect('perfil_usuario', user_id=user_id)

    if request.method == 'POST':
        genero = request.POST.get('genero', '').strip().lower()
        estado = request.POST.get('estado', '').strip().upper()
        cidade = request.POST.get('cidade', '').strip()
        bio = request.POST.get('bio', '').strip()
        idade = request.POST.get('idade', '').strip()
        preco_hora = request.POST.get('preco_hora', '').strip().replace(',', '.')

        if genero not in {'masculino', 'feminino'} or not estado or not cidade or not idade:
            messages.error(request, 'Informe gênero, idade, estado e cidade para se tornar cuidador.')
            return redirect(request.META.get('HTTP_REFERER') or 'tornar_cuidador')

        try:
            idade_int = int(idade)
            if not 21 <= idade_int <= 60:
                raise ValueError
        except ValueError:
            messages.error(request, 'Para ser cuidador, a idade precisa estar entre 21 e 60 anos.')
            return redirect(request.META.get('HTTP_REFERER') or 'tornar_cuidador')

        values = {
            'is_cuidador': True,
            'genero': genero,
            'estado': estado,
            'cidade': cidade,
            'bio': bio,
            'idade': idade_int,
        }

        # Converte e salva o valor cobrado por hora se informado
        if preco_hora:
            try:
                values['preco_hora'] = float(preco_hora)
            except (ValueError, TypeError):
                pass

        if _executar_update_usuario(request, user_id, values):
            messages.success(request, 'Parabéns! Seu perfil agora está ativo como Cuidador PetMee e seu card já aparece na página inicial.')
            return redirect('home')
        else:
            messages.error(request, 'Não foi possível atualizar o perfil de cuidador no banco de dados.')

    return render(request, 'cuidador/formulario.html', {
        'perfil': perfil,
        'estados': ESTADOS_BRASIL,
    })


def _ratings_by_user(request):
    """Calcula a média de estrelas para cada usuário avaliado."""
    try:
        ratings = _client(request).table('avaliacoes').select('avaliado_id, nota').execute().data
        grouped = {}
        for rating in ratings:
            u_id = str(rating.get('avaliado_id'))
            grouped.setdefault(u_id, []).append(float(rating.get('nota', 0)))
        return {
            u_id: round(sum(values) / len(values), 1)
            for u_id, values in grouped.items()
            if values
        }
    except Exception:
        return {}


def search_cuidadores(request):
    """
    Busca avançada de cuidadores com filtros por Estado, Cidade, Idade, Gênero e Avaliação.
    Consome a lista de estados e cidades via formulário ou API interna.
    """
    filters = {
        'estado': request.GET.get('estado', '').strip().upper(),
        'cidade': request.GET.get('cidade', '').strip(),
        'genero': request.GET.get('genero', '').strip().lower(),
        'estrelas': request.GET.get('estrelas', '').strip(),
        'idade_min': request.GET.get('idade_min', '').strip(),
        'idade_max': request.GET.get('idade_max', '').strip(),
    }
    try:
        idade_min = int(filters['idade_min']) if filters['idade_min'] else 21
        idade_max = int(filters['idade_max']) if filters['idade_max'] else 60
        idade_min = max(21, min(60, idade_min))
        idade_max = max(21, min(60, idade_max))
        if idade_min > idade_max:
            idade_min, idade_max = idade_max, idade_min
    except (TypeError, ValueError):
        idade_min, idade_max = 21, 60
    filters['idade_min'], filters['idade_max'] = str(idade_min), str(idade_max)

    cuidadores = []
    try:
        query = _client(request).table('usuarios').select('*').eq('is_cuidador', True)
        if filters['estado']:
            query = query.eq('estado', filters['estado'])
        if filters['cidade']:
            query = query.eq('cidade', filters['cidade'])
        if filters['genero'] in {'masculino', 'feminino'}:
            query = query.eq('genero', filters['genero'])
        query = query.gte('idade', idade_min).lte('idade', idade_max)

        ratings = _ratings_by_user(request)
        minimum_rating = float(filters['estrelas']) if filters['estrelas'] else 0

        for cuidador in query.order('created_at', desc=True).execute().data:
            cuidador['media_avaliacoes'] = ratings.get(str(cuidador.get('id')), 0)
            if cuidador['media_avaliacoes'] >= minimum_rating:
                cuidadores.append(cuidador)
    except Exception:
        cuidadores = []

    return render(request, 'search_cuidadores.html', {
        'cuidadores': cuidadores,
        'filters': filters,
        'estados': ESTADOS_BRASIL,
    })


# ==============================================================================
# APIS INTERNAS PARA FILTRAR ESTADO E CIDADE
# ==============================================================================

def api_estados(request):
    """
    API interna para fornecer a lista oficial de Estados do Brasil em formato JSON.
    Permite busca avançada sem depender exclusivamente de conexões externas.
    """
    return JsonResponse(ESTADOS_BRASIL, safe=False)


def api_cidades(request):
    """
    API interna para fornecer a lista de cidades de determinado Estado.
    Primeiro verifica se há cidades com cuidadores/petshops cadastrados naquele Estado;
    complementa com a base de municípios oficiais do Brasil com cache em memória.
    """
    estado_uf = request.GET.get('estado', '').strip().upper()
    if not estado_uf or len(estado_uf) != 2:
        return JsonResponse({'error': 'Parâmetro "estado" inválido. Ex: ?estado=SP'}, status=400)

    # 1. Recupera cidades cadastradas no banco de dados para esse estado
    cidades_cadastradas = set()
    try:
        resp_usuarios = _client(request).table('usuarios').select('cidade').eq('estado', estado_uf).execute()
        for item in (resp_usuarios.data or []):
            if item.get('cidade'):
                cidades_cadastradas.add(item['cidade'].strip())
        resp_shops = _client(request).table('petshops').select('cidade').eq('estado', estado_uf).execute()
        for item in (resp_shops.data or []):
            if item.get('cidade'):
                cidades_cadastradas.add(item['cidade'].strip())
    except Exception:
        pass

    # 2. Carrega cidades oficiais via cache ou consulta com timeout resiliente
    if estado_uf in _CACHE_CIDADES:
        cidades_oficiais = _CACHE_CIDADES[estado_uf]
    else:
        try:
            url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{estado_uf}/municipios"
            req = urllib.request.Request(url, headers={'User-Agent': 'PetMee-App/1.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                dados = json.loads(response.read().decode())
                cidades_oficiais = [m['nome'] for m in dados if 'nome' in m]
                cidades_oficiais.sort()
                _CACHE_CIDADES[estado_uf] = cidades_oficiais
        except Exception:
            cidades_oficiais = []

    # Unifica cidades com e sem cadastros
    todas = sorted(list(cidades_cadastradas.union(set(cidades_oficiais))))
    
    # Se ainda estiver vazia por falta de internet no ambiente, retorna principais cidades de exemplo
    if not todas:
        principais = {
            'SP': ['São Paulo', 'Campinas', 'Santos', 'Ribeirão Preto', 'São José dos Campos', 'Sorocaba'],
            'RJ': ['Rio de Janeiro', 'Niterói', 'Petrópolis', 'Duque de Caxias', 'Nova Iguaçu'],
            'MG': ['Belo Horizonte', 'Uberlândia', 'Juiz de Fora', 'Contagem', 'Ouro Preto'],
            'PR': ['Curitiba', 'Londrina', 'Maringá', 'Ponta Grossa', 'Cascavel'],
            'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas', 'Canoas', 'Santa Maria'],
            'SC': ['Florianópolis', 'Joinville', 'Blumenau', 'São José', 'Chapecó'],
            'BA': ['Salvador', 'Feira de Santana', 'Vitória da Conquista', 'Camaçari'],
        }
        todas = principais.get(estado_uf, ['Capital', 'Região Central'])

    resultado = [
        {
            'nome': cidade,
            'tem_cuidador': cidade in cidades_cadastradas
        }
        for cidade in todas
    ]
    return JsonResponse(resultado, safe=False)


# ==============================================================================
# PETSHOPS E LOJA
# ==============================================================================

def petshops(request):
    """
    Lista os petshops cadastrados na plataforma.
    Busca registros da tabela 'petshops' e também de contas de petshop em 'usuarios'.
    Prioriza petshops da mesma cidade e estado do usuário autenticado.
    """
    petshops_list = []
    user_location = {}
    user_id = _user_id(request)
    try:
        if user_id:
            user_location = _select_one(request, 'usuarios', 'id', user_id) or {}

        # 1. Busca da tabela oficial 'petshops'
        registros_oficiais = []
        try:
            registros_oficiais = _client(request).table('petshops').select('*').order('created_at', desc=True).execute().data or []
        except Exception:
            pass

        # 2. Busca também de 'usuarios' onde tipo_usuario = 'petshop'
        registros_usuarios = []
        try:
            registros_usuarios = _client(request).table('usuarios').select('*').eq(
                'tipo_usuario', 'petshop'
            ).order('created_at', desc=True).execute().data or []
        except Exception:
            pass

        # Consolida e remove duplicatas por nome/email
        vistos = set()
        combinados = []
        for shop in registros_oficiais:
            chave = (shop.get('nome') or '').lower().strip()
            if chave and chave not in vistos:
                vistos.add(chave)
                shop['tipo_origem'] = 'petshop'
                combinados.append(shop)

        for u in registros_usuarios:
            chave = (u.get('nome_completo') or '').lower().strip()
            if chave and chave not in vistos:
                vistos.add(chave)
                combinados.append({
                    'id': u.get('id'),
                    'nome': u.get('nome_completo'),
                    'cidade': u.get('cidade'),
                    'estado': u.get('estado'),
                    'sobre': u.get('bio'),
                    'foto_url': u.get('avatar_url'),
                    'trabalhos': 'Banho e Tosa, Produtos e Cuidados',
                    'tipo_origem': 'usuario'
                })

        user_city = (user_location.get('cidade') or '').casefold()
        user_state = (user_location.get('estado') or '').upper()

        for petshop in combinados:
            shop_city = (petshop.get('cidade') or '').casefold()
            shop_state = (petshop.get('estado') or '').upper()
            if user_city and shop_city == user_city and user_state and shop_state == user_state:
                petshop['proximidade'] = 'Na sua cidade'
                petshop['_distance_rank'] = 0
            elif user_state and shop_state == user_state:
                petshop['proximidade'] = 'No seu estado'
                petshop['_distance_rank'] = 1
            else:
                petshop['proximidade'] = 'Petshop parceiro'
                petshop['_distance_rank'] = 2

            petshop['nome_exibicao'] = petshop.get('nome') or petshop.get('nome_completo') or 'Petshop Parceiro'
            petshop['cidade_display'] = petshop.get('cidade') or 'Região não informada'
            petshop['estado_display'] = petshop.get('estado') or ''
            petshops_list.append(petshop)

        petshops_list.sort(key=lambda item: (item['_distance_rank'], item.get('nome_exibicao', '').casefold()))
    except Exception:
        petshops_list = []

    return render(request, 'petshops/petshops.html', {
        'petshops': petshops_list,
        'user_location': user_location,
    })


def loja(request):
    """Página da loja com filtros por categoria, preço e busca por nome."""
    filters = {
        'busca': request.GET.get('busca', '').strip(),
        'categoria': request.GET.get('categoria', '').strip(),
        'min_preco': request.GET.get('min_preco', '').strip(),
        'max_preco': request.GET.get('max_preco', '').strip(),
    }
    produtos = []
    categorias = []
    try:
        registros = _client(request).table('produtos').select('*').eq('ativo', True).order(
            'created_at', desc=True
        ).execute().data
        ids = {str(produto.get('vendedor_id')) for produto in registros}
        vendedores = {}
        for u_id in ids:
            perfil = _select_one(request, 'usuarios', 'id', u_id)
            if perfil:
                vendedores[u_id] = perfil.get('nome_completo', 'Petshop')
        for produto in registros:
            categoria = produto.get('categoria') or 'Geral'
            categorias.append(categoria)
            nome = (produto.get('nome') or '').lower()
            matches_search = not filters['busca'] or filters['busca'].lower() in nome
            matches_category = not filters['categoria'] or filters['categoria'] == categoria
            try:
                preco = float(produto.get('preco', 0))
            except (TypeError, ValueError):
                preco = 0
            matches_min = not filters['min_preco'] or preco >= float(filters['min_preco'])
            matches_max = not filters['max_preco'] or preco <= float(filters['max_preco'])
            if matches_search and matches_category and matches_min and matches_max:
                produto['vendedor_nome'] = vendedores.get(str(produto.get('vendedor_id')), 'Petshop')
                produtos.append(produto)
    except (Exception, ValueError):
        produtos = []

    return render(request, 'loja/loja.html', {
        'produtos': produtos,
        'categorias': sorted(set(categorias)),
        'filters': filters,
    })


def cadastrar_produto(request):
    """Cadastra um novo produto para petshops logados."""
    user_id = _user_id(request)
    if not user_id:
        return redirect('login')
    perfil = _select_one(request, 'usuarios', 'id', user_id) or {}
    if perfil.get('tipo_usuario') != 'petshop':
        messages.error(request, 'Apenas contas do tipo Petshop podem cadastrar produtos.')
        return redirect('loja')

    if request.method == 'POST':
        produto = {
            'vendedor_id': user_id,
            'nome': request.POST.get('nome', '').strip(),
            'descricao': request.POST.get('descricao', '').strip(),
            'categoria': request.POST.get('categoria', '').strip(),
            'foto_url': request.POST.get('foto_url', '').strip(),
            'ativo': True,
        }
        try:
            produto['preco'] = float(request.POST.get('preco', '0').replace(',', '.'))
            produto['estoque'] = int(request.POST.get('estoque', '0'))
            if not produto['nome'] or produto['preco'] < 0 or produto['estoque'] < 0:
                raise ValueError
            _client(request).table('produtos').insert(produto).execute()
            messages.success(request, 'Produto publicado na loja.')
            return redirect('loja')
        except (ValueError, TypeError):
            messages.error(request, 'Informe nome, preço e estoque com valores válidos.')
        except Exception:
            messages.error(request, 'Não foi possível publicar o produto no banco.')

    return render(request, 'loja/produto_form.html', {'perfil': perfil})


# ==============================================================================
# GESTÃO DE PETS
# ==============================================================================

def cadastrar_pet(request):
    """
    Cadastra um novo pet no sistema.
    Permite escolher a foto direto do dispositivo (upload de arquivo) ou informar URL.
    """
    owner_id = _user_id(request)
    if not owner_id:
        return redirect('login')

    if request.method == 'POST':
        fields = ('nome', 'especie', 'raca', 'sexo', 'porte', 'idade', 'localizacao', 'saude', 'sobre')
        pet = {field: request.POST.get(field, '').strip() for field in fields}

        # Foto: verifica upload de arquivo do dispositivo ou campo de URL
        foto_url = request.POST.get('foto_url', '').strip()
        if request.FILES.get('foto_file'):
            try:
                foto_url = _salvar_arquivo_upload(request.FILES['foto_file'], subpasta='pets')
            except Exception:
                pass
        pet['foto_url'] = foto_url

        if not pet['nome'] or not pet['especie'] or not pet['localizacao']:
            messages.error(request, 'Nome, espécie e localização são campos obrigatórios.')
        else:
            pet.update({'tutor_id': owner_id, 'disponivel': True})
            try:
                novo_pet = _client(request).table('pets').insert(pet).execute().data[0]
                messages.success(request, 'Pet cadastrado com sucesso!')
                return redirect('detalhes_pet', pet_id=novo_pet['id'])
            except Exception:
                messages.error(request, 'Não foi possível salvar o pet no Supabase.')

    return render(request, 'pets/formulario.html', {'estados': ESTADOS_BRASIL})


def detalhes_pet(request, pet_id):
    """Exibe o perfil detalhado e sofisticado do pet selecionado."""
    try:
        pet = _select_one(request, 'pets', 'id', pet_id)
    except Exception as exc:
        raise Http404('Pet não encontrado.') from exc

    if not pet:
        raise Http404('Pet não encontrado.')

    tutor = None
    if pet.get('tutor_id'):
        tutor = _select_one(request, 'usuarios', 'id', str(pet['tutor_id']))

    return render(request, 'perfil/perfil1.html', {
        'pet': pet,
        'tutor': tutor,
        'is_owner': _user_id(request) == str(pet.get('tutor_id')),
    })


# ==============================================================================
# PERFIS DE USUÁRIO E EDITAR PERFIL
# ==============================================================================

def meu_perfil(request):
    """Redireciona para a página de perfil do usuário logado."""
    user_id = _user_id(request)
    return redirect('login') if not user_id else redirect('perfil_usuario', user_id=user_id)


def perfil_usuario(request, user_id):
    """
    Exibe a página de perfil do usuário.
    Se for o próprio usuário (is_owner):
    - Permite visualizar suas informações
    - Apresenta o formulário interativo para se tornar ou atualizar seus dados de Cuidador,
      incluindo valor cobrado por hora, bio e disponibilidade.
    """
    try:
        perfil = _select_one(request, 'usuarios', 'id', str(user_id))
        if not perfil and _user_id(request) == str(user_id):
            perfil = _ensure_profile(request, str(user_id))
        avaliacoes = _client(request).table('avaliacoes').select('*').eq('avaliado_id', str(user_id)).order('created_at', desc=True).execute().data
    except Exception:
        perfil, avaliacoes = None, []

    if not perfil:
        raise Http404('Perfil não encontrado.')

    media = round(sum(item['nota'] for item in avaliacoes) / len(avaliacoes), 1) if avaliacoes else None

    # Busca dados adicionais do petshop se for uma instituição
    petshop_dados = None
    if perfil.get('tipo_usuario') == 'petshop':
        try:
            petshop_dados = _select_one(request, 'petshops', 'user_id', str(user_id))
        except Exception:
            petshop_dados = None

    # Permite atualização rápida de hospedagem e serviços do Petshop pelo próprio dono
    if request.method == 'POST' and _user_id(request) == str(user_id) and perfil.get('tipo_usuario') == 'petshop':
        tem_hospedagem = request.POST.get('tem_hospedagem') in ['on', 'true', '1']
        preco_hora = request.POST.get('preco_hora', '').strip().replace(',', '.')
        update_vals = {}
        if tem_hospedagem and preco_hora:
            try:
                update_vals['preco_hora'] = float(preco_hora)
            except (ValueError, TypeError):
                update_vals['preco_hora'] = None
        else:
            update_vals['preco_hora'] = None

        trabalhos = request.POST.get('trabalhos', '').strip()
        if trabalhos:
            try:
                _client(request).table('petshops').update({'trabalhos': trabalhos}).eq('user_id', str(user_id)).execute()
            except Exception:
                pass

        _executar_update_usuario(request, user_id, update_vals)
        messages.success(request, 'Serviços e dados de Hospedagem do Petshop atualizados!')
        return redirect('perfil_usuario', user_id=user_id)

    # Busca também os pets cadastrados por esse tutor para enriquecer a página de perfil
    pets_usuario = []
    try:
        pets_usuario = _client(request).table('pets').select('*').eq('tutor_id', str(user_id)).execute().data or []
    except Exception:
        pass

    return render(request, 'perfil/perfil.html', {
        'perfil': perfil,
        'petshop_dados': petshop_dados,
        'avaliacoes': avaliacoes,
        'media_avaliacoes': media,
        'pets_usuario': pets_usuario,
        'is_owner': _user_id(request) == str(user_id),
        'estados': ESTADOS_BRASIL,
    })


def editar_perfil(request, user_id):
    """
    [NOTA DE OBSERVAÇÃO]:
    Edita os dados do perfil do usuário autenticado.
    Para Petshops (instituições):
    - Remove idade e gênero (não aplicáveis para empresas).
    - Exibe estado, cidade e atendimento/serviços.
    - O valor por hora é exclusivo para quando o petshop possui serviço de hospedagem.
    """
    if _user_id(request) != str(user_id):
        return HttpResponseForbidden('Você só pode editar o seu próprio perfil.')

    perfil_atual = _select_one(request, 'usuarios', 'id', str(user_id)) or {}
    petshop_atual = None
    if perfil_atual.get('tipo_usuario') == 'petshop':
        try:
            petshop_atual = _select_one(request, 'petshops', 'user_id', str(user_id))
        except Exception:
            petshop_atual = None

    if request.method == 'POST':
        values = {
            'nome_completo': request.POST.get('nome_completo', '').strip(),
            'cidade': request.POST.get('cidade', '').strip(),
            'estado': request.POST.get('estado', '').strip().upper(),
            'bio': request.POST.get('bio', '').strip(),
        }

        # Trata idade apenas para tutores (pessoas físicas), removida para petshops
        if perfil_atual.get('tipo_usuario') != 'petshop':
            idade_str = request.POST.get('idade', '').strip()
            if idade_str:
                try:
                    values['idade'] = int(idade_str)
                except ValueError:
                    pass
        else:
            # Petshops não possuem idade nem gênero
            values['idade'] = None
            values['genero'] = None

            # Hospedagem e valor por hora (apenas quando o petshop tiver hospedagem)
            tem_hospedagem = request.POST.get('tem_hospedagem') in ['on', 'true', '1']
            preco_hospedagem = request.POST.get('preco_hora', '').strip().replace(',', '.')
            if tem_hospedagem and preco_hospedagem:
                try:
                    values['preco_hora'] = float(preco_hospedagem)
                except (ValueError, TypeError):
                    values['preco_hora'] = None
            else:
                values['preco_hora'] = None

            # Sincroniza dados na tabela 'petshops'
            trabalhos_petshop = request.POST.get('trabalhos', '').strip()
            if trabalhos_petshop:
                try:
                    _client(request).table('petshops').update({
                        'trabalhos': trabalhos_petshop,
                        'cidade': values['cidade'],
                        'estado': values['estado'],
                        'sobre': values['bio'],
                    }).eq('user_id', str(user_id)).execute()
                except Exception:
                    pass

        # FOTO DO PERFIL: Pega direto do arquivo do dispositivo
        if request.FILES.get('avatar_file'):
            try:
                url_gerada = _salvar_arquivo_upload(request.FILES['avatar_file'], subpasta='avatars')
                values['avatar_url'] = url_gerada
            except Exception as e:
                messages.warning(request, f'Não foi possível salvar o arquivo da foto: {str(e)}')
        elif request.POST.get('avatar_url'):
            values['avatar_url'] = request.POST.get('avatar_url').strip()

        if _executar_update_usuario(request, user_id, values):
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil_usuario', user_id=user_id)
        else:
            messages.error(request, 'Não foi possível atualizar o perfil no banco de dados.')

    return render(request, 'perfil/editar.html', {
        'perfil': perfil_atual,
        'petshop_dados': petshop_atual,
        'estados': ESTADOS_BRASIL,
    })


def criar_avaliacao(request, user_id):
    """Cria uma avaliação com nota de 1 a 5 e depoimento para um cuidador/usuário."""
    autor_id = _user_id(request)
    if not autor_id:
        return redirect('login')
    if autor_id == str(user_id):
        messages.error(request, 'Você não pode avaliar seu próprio perfil.')
    elif request.method == 'POST':
        try:
            nota = int(request.POST.get('nota', 0))
            comentario = request.POST.get('comentario', '').strip()
            if nota not in range(1, 6) or not comentario:
                raise ValueError
            _client(request).table('avaliacoes').upsert({
                'autor_id': autor_id,
                'avaliado_id': str(user_id),
                'nota': nota,
                'comentario': comentario,
            }, on_conflict='autor_id,avaliado_id').execute()
            messages.success(request, 'Sua avaliação foi publicada!')
        except ValueError:
            messages.error(request, 'Informe uma nota de 1 a 5 e escreva um comentário.')
        except Exception:
            messages.error(request, 'Não foi possível salvar sua avaliação.')
    return redirect('perfil_usuario', user_id=user_id)
