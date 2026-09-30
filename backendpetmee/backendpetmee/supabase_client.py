import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Carrega as variáveis do arquivo .env localizado na raiz do backend
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Inicializa o cliente Supabase se as variáveis estiverem presentes
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if SUPABASE_URL and SUPABASE_ANON_KEY
    else None
)


def get_supabase() -> Client:
    """Retorna o cliente configurado do Supabase com tratamento amigável de erro."""
    if supabase is None:
        raise RuntimeError(
            'Configure SUPABASE_URL e SUPABASE_ANON_KEY nas variáveis do ambiente (.env).'
        )
    return supabase
