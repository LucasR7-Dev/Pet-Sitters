# PetMee — Pet Sitters: Monitoramento e Cuidado Domiciliar

> Plataforma web full-stack desenvolvida para conectar tutores de animais a cuidadores de forma prática, segura e focada no bem-estar do pet no seu próprio ambiente familiar.

## Sobre o Projeto

O **PetMee** oferece uma solução prática para garantir que os animais recebam serviços essenciais durante a ausência dos tutores, garantindo a troca de água, alimentação, limpeza da gaiola e monitoramento da saúde do animal no conforto do seu próprio lar, evitando estresse com deslocamentos.

---

## Tecnologias Utilizadas

O projeto combina tecnologias modernas de desenvolvimento front-end com soluções de backend e banco de dados em nuvem:

* **HTML5 (38.2%):** Estruturação semântica e acessível das páginas e componentes globais (`header.html`, `footer.html`).
* **CSS3 (27.6%):** Estilização visual, identidade estética e total responsividade para dispositivos móveis.
* **Python / Django (27.2%):** Desenvolvimento da lógica de servidor, APIs e regras de negócio do ecossistema backend.
* **JavaScript (4.2%):** Dinamismo, manipulação de eventos e interatividade da interface do usuário.
* **PLpgSQL / Supabase (2.8%):** Lógica procedural integrada ao banco de dados relacional para automação e consistência das informações.
* **GitHub Actions:** Pipeline de Integração Contínua (`ci_pipeline.yml`) para automação de testes e checagens.

---

## Como Executar o Projeto

### Pré-requisitos

1. Tenha a versão mais recente do Python instalada no seu computador (via site oficial).
2. Tenha o editor Visual Studio Code instalado.

### Passo a Passo para Instalação e Inicialização

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com
   ```

2. **Abrir o projeto:**
   Abra a pasta do projeto clonado diretamente no seu Visual Studio Code.

3. **Liberar permissão no terminal:**
   Abra o terminal do Visual Studio Code e execute o seguinte comando para liberar a execução de scripts do PowerShell no processo atual:
   ```powershell
   Set-ExecutionPolicy Unrestricted -Scope Process
   ```

4. **Remover venv antiga (se houver):**
   Caso já exista uma pasta chamada `venv` no projeto aberto no VS Code, delete-a antes de prosseguir.

5. **Abrir um novo terminal:**
   Feche o terminal anterior e abra um novo terminal limpo no Visual Studio Code.

6. **Criar o ambiente virtual (venv):**
   ```bash
   python -m venv venv
   ```

7. **Ativar o ambiente virtual (PowerShell):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

8. **Instalar as dependências do projeto:**
   ```bash
   pip install -r requirements.txt
   ```

9. **Navegar até o diretório do backend:**
   ```bash
   cd backendpetmee
   ```

10. **Iniciar o projeto:**
    ```bash
    python manage.py runserver
    ```

Agora você pode mexer no TCC tranquilamente com o servidor rodando e as páginas funcionando de forma integrada.

---

## Interface e UX/UI

O design da plataforma foi planejado para transmitir confiança, afeto e clareza aos tutores de pets.

* **Layout Responsivo:** Perfeitamente adaptável para celulares, tablets e desktops.
* **Seção de Perfis:** Visualização clara das especialidades, preços e avaliações de cada cuidador.

---

## Desenvolvedores

Contribuintes que ajudaram a dar vida a este projeto:

* [Lucas](https://github.com/LucasR7-Dev) — Autor / Desenvolvedor Principal
* [Murilo](https://github.com/liloLNF) — Coautor / Desenvolvedor Secundário
* [Antony](https://github.com/AntonyBonefon) — Coautor / Desenvolvedor Secundário

---
Let's take care of our pets! Register your pet today!
