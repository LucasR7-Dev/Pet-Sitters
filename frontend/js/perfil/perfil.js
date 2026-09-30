// 1. BANCO DE DADOS LOCAL (Os 6 perfis baseados na sua estrutura)
const pets = [
  {
    nome: "Luna 🐶",
    img: "../../pets/CA1.png", 
    tags: ["Fêmea", "Médio", "2 anos"],
    raca: "Husky Siberiano",
    localizacao: "Pinheiros, SP • ⭐ 5.0",
    status: "Disponível",
    sobre: "Muito ativa, ama correr e brincar. Ideal para quem gosta de pets cheios de energia."
  },
  {
    nome: "Bob 🐶",
    img: "../../pets/CA2.png", 
    tags: ["Macho", "Grande", "1 ano"],
    raca: "Golden Retriever",
    localizacao: "Vila Mariana, SP • ⭐ 5.0",
    status: "Disponível",
    sobre: "Super dócil, adora crianças e ama nadar. É o companheiro perfeito para a família."
  },
  {
    nome: "Senhorita Bigodes 🐱",
    img: "../../pets/GA1.png",
    tags: ["Fêmea", "Pequena", "3 anos"],
    raca: "Calico",
    localizacao: "Barueri, SP • ⭐ 5.0",
    status: "Disponível",
    sobre: "Calma, carinhosa e adora dormir no colo. Perfeita para quem mora em apartamento."
  },
  {
    nome: "Biscoito 🐹",
    img: "../../pets/HA1.png",
    tags: ["Macho", "Pequeno", "1 anos"],
    raca: "Hamster Sírio",
    localizacao: "Campinas, SP • ⭐ 4.9",
    status: "Disponível",
    sobre: "Super curioso, adora correr na rodinha e comer sementes. Muito mansinho para interagir."
  },
  {
    nome: "Amora 🐰",
    img: "../../pets/CO1.jpg",
    tags: ["Fêmea", "Pequena", "3 anos"],
    raca: "Brachylagus idahoensis",
    localizacao: "Moema, SP • ⭐ 4.5",
    status: "Disponível",
    sobre: "Companheira silenciosa, adora passeios calmos no parque e se dá bem com outros."
  },
  {
    nome: "Piquititico 🦜",
    img: "../../pets/PI1.jpg",
    tags: ["Macho", "Pequeno", "6 anos"],
    raca: "Periquito australiano",
    localizacao: "Bela Vista, SP • ⭐ 4.3",
    status: "Disponível",
    sobre: "Curioso, adora fuxicar caixas de papelão e é extremamente apegado aos donos."
  }
];

// 2. VARIÁVEL DE CONTROLE DE ÍNDICE (Descoberta dinamicamente pela URL)
const paginaAtual = window.location.pathname.split('/').pop(); // Extrai ex: "perfil3.html"
const numeroPagina = parseInt(paginaAtual.replace(/\D/g, '')); // Extrai apenas o número do arquivo (ex: 3)

// Se o número for válido na lista, define o índice correspondente (Página 1 = Índice 0, etc.)
let indiceAtual = (numeroPagina >= 1 && numeroPagina <= pets.length) ? numeroPagina - 1 : 0;

// 3. SELEÇÃO DOS ELEMENTOS DO HTML
const petImg = document.getElementById('petImg');
const petName = document.getElementById('petName');
const petBreed = document.getElementById('petBreed');
const petLocation = document.getElementById('petLocation');
const petStatus = document.getElementById('petStatus');
const petAbout = document.getElementById('petAbout');
const tagsContainer = document.querySelector('.tags');

const btnAdopt = document.getElementById('btnAdopt');
const btnNext = document.getElementById('btnNext');
const modal = document.getElementById('modal');
const closeModal = document.getElementById('closeModal');

// 4. FUNÇÃO PARA ATUALIZAR O PERFIL NA TELA
function carregarPet(indice) {
  const pet = pets[indice];

  if (!pet) return; // Evita erros caso o índice esteja fora do array

  // Atualiza os textos e imagem
  petImg.src = pet.img;
  petImg.alt = `Foto de ${pet.nome}`;
  petName.textContent = pet.nome;
  petBreed.textContent = pet.raca;
  petLocation.textContent = pet.localizacao;
  petAbout.textContent = pet.sobre;

  // VERIFICAÇÃO DE MEMÓRIA: Checa se esse pet específico já foi adotado antes
  const statusSalvo = localStorage.getItem(`pet_status_${indice}`);
  
  if (statusSalvo === "Indisponível") {
    petStatus.textContent = "Indisponível";
    petStatus.classList.add('indisponivel');
  } else {
    petStatus.textContent = pet.status;
    petStatus.classList.remove('indisponivel');
  }

  // Atualiza as tags dinamicamente
  tagsContainer.innerHTML = ''; 
  pet.tags.forEach(textoTag => {
    const span = document.createElement('span');
    span.className = 'tag';
    span.textContent = textoTag;
    tagsContainer.appendChild(span);
  });
}

// 5. EVENTOS DOS BOTÕES
// Botão "Conhecer outro pet" (Calcula o próximo arquivo físico e redireciona)
btnNext.addEventListener('click', () => {
  const proximoIndice = (indiceAtual + 1) % pets.length;
  const proximaPagina = proximoIndice + 1; // Transforma o índice 0 em página 1, índice 1 em página 2...
  
  // Redireciona o navegador para o próximo arquivo HTML na mesma pasta
  window.location.href = `perfil${proximaPagina}.html`;
});

// Botão "Quero cuidar" (Abre o modal e salva o novo status)
btnAdopt.addEventListener('click', () => {
  // Abre o modal visualmente
  modal.classList.add('active');

  // Muda o texto e aplica a classe CSS vermelha de indisponível
  petStatus.textContent = "Indisponível";
  petStatus.classList.add('indisponivel');

  // Salva no navegador que o pet desse índice atual está indisponível
  localStorage.setItem(`pet_status_${indiceAtual}`, "Indisponível");
});

// Fechar o modal
closeModal.addEventListener('click', () => {
  modal.classList.remove('active');
});

modal.addEventListener('click', (e) => {
  if (e.target === modal) modal.classList.remove('active');
});

// 6. INICIALIZAÇÃO
carregarPet(indiceAtual);
