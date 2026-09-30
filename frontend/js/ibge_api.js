/**
 * Script de carregamento de Estados e Cidades para o formulário de busca e filtros do PetMee.
 * Utiliza prioritariamente as APIs internas do Django:
 * - /api/estados/
 * - /api/cidades/?estado=UF
 * Com fallback automático para o IBGE caso necessário.
 */

document.addEventListener('DOMContentLoaded', () => {
    const selectEstado = document.getElementById('estado');
    const selectCidade = document.getElementById('cidade');
    const selectedLocation = window.petmeeLocationFilters || {};

    if (!selectEstado || !selectCidade) return;

    /**
     * Carrega a lista de estados através da API interna do Django
     */
    async function carregarEstados() {
        try {
            // Consulta primeiro a API interna do backend
            let response = await fetch('/api/estados/');
            let estados;

            if (response.ok) {
                estados = await response.json();
            } else {
                // Fallback para o IBGE se a rota interna não responder
                response = await fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome');
                estados = await response.json();
            }

            // Limpa e popula o select de estados
            selectEstado.innerHTML = '<option value="">Todos os estados</option>';
            estados.forEach(estado => {
                const option = document.createElement('option');
                option.value = estado.sigla;
                option.textContent = `${estado.nome} (${estado.sigla})`;
                if (selectedLocation.estado && estado.sigla === selectedLocation.estado) {
                    option.selected = true;
                }
                selectEstado.appendChild(option);
            });

            // Se já houver um estado selecionado via GET, carrega as cidades dele
            if (selectEstado.value) {
                await carregarCidades(selectEstado.value);
            }
        } catch (error) {
            console.warn('Erro ao carregar estados via API:', error);
            // Mantém as opções já renderizadas pelo Django no template
        }
    }

    /**
     * Carrega a lista de cidades para a UF selecionada através da API interna do Django
     */
    async function carregarCidades(sigla) {
        if (!sigla) {
            selectCidade.disabled = true;
            selectCidade.innerHTML = '<option value="">Todas as cidades</option>';
            return;
        }

        selectCidade.disabled = true;
        selectCidade.innerHTML = '<option value="">Carregando cidades...</option>';

        try {
            // Consulta a API interna do backend que já sabe as cidades cadastradas
            let response = await fetch(`/api/cidades/?estado=${encodeURIComponent(sigla)}`);
            let cidades = [];

            if (response.ok) {
                cidades = await response.json();
            } else {
                // Fallback para o IBGE
                response = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${sigla}/municipios`);
                cidades = await response.json();
            }

            selectCidade.innerHTML = '<option value="">Todas as cidades</option>';
            cidades.forEach(item => {
                const nomeCidade = typeof item === 'string' ? item : item.nome;
                const option = document.createElement('option');
                option.value = nomeCidade;
                option.textContent = nomeCidade + (item.tem_cuidador ? ' (Cuidador ativo)' : '');
                if (selectedLocation.cidade && selectedLocation.cidade.toLowerCase() === nomeCidade.toLowerCase()) {
                    option.selected = true;
                }
                selectCidade.appendChild(option);
            });

            selectCidade.disabled = false;
        } catch (error) {
            console.warn('Erro ao carregar cidades via API:', error);
            selectCidade.innerHTML = '<option value="">Todas as cidades</option>';
            selectCidade.disabled = false;
        }
    }

    // Escuta a alteração do select de estado
    selectEstado.addEventListener('change', () => {
        carregarCidades(selectEstado.value);
    });

    // Se o select já veio com opções renderizadas pelo Django, apenas sincroniza a cidade
    if (selectEstado.value) {
        carregarCidades(selectEstado.value);
    } else if (selectEstado.options.length <= 1) {
        carregarEstados();
    }
});
