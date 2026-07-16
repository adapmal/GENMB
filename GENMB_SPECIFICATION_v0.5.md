# GENMB SPECIFICATION v0.5

> Capítulo 5 --- Motor de Renderização, Divisão de Quadros e Algoritmo
> dos Grifos

# 5. Objetivo

O Motor de Renderização é o núcleo do GENMB. Sua função é transformar o
conteúdo da notícia em uma sequência de quadros estáticos prontos para
edição de vídeo, preservando a identidade visual do veículo e a
continuidade da leitura.

------------------------------------------------------------------------

# 5.1 Pipeline

``` text
Roteiro
   ↓
Parser
   ↓
Diagnóstico
   ↓
SiteProfile
   ↓
HeaderTemplate
   ↓
Layout Engine
   ↓
Render Engine
   ↓
Preview
   ↓
ZIP
```

------------------------------------------------------------------------

# 5.2 Ordem obrigatória

Para cada notícia:

1.  Cabeçalho + título.
2.  Foto principal (quando houver).
3.  Primeiro quadro do primeiro parágrafo.
4.  Todos os grifos referentes ao quadro atual.
5.  Novo quadro.
6.  Grifos do novo quadro.
7.  Repetir até o final do parágrafo.
8.  Próximo parágrafo.
9.  Repetir até o final da notícia.

Nunca gerar primeiro todos os quadros limpos para depois voltar
aplicando grifos.

------------------------------------------------------------------------

# 5.3 Regra de Continuidade

Todo quadro sucessor deve iniciar com a última linha visível do quadro
anterior.

Objetivos:

-   facilitar cortes secos;
-   preservar a leitura;
-   evitar perda de contexto.

A linha repetida mantém exatamente o mesmo estado de grifo do quadro
anterior.

------------------------------------------------------------------------

# 5.4 Quadros

Cada quadro contém:

-   cabeçalho (quando aplicável);
-   corpo;
-   grifos;
-   foto (quando for um quadro de imagem).

Quadros vazios nunca devem ser exportados.

------------------------------------------------------------------------

# 5.5 Grifos

Os grifos obedecem às regras:

-   não alterar o espaçamento do texto;
-   não criar "saltos" visuais;
-   preservar métricas tipográficas;
-   permanecer ativos quando reaparecem por continuidade.

Se um grifo ultrapassar o limite inferior do quadro:

1.  reposicionar o quadro antes da aplicação do grifo;
2.  manter todo o trecho destacado visível;
3.  completar o restante do quadro com linhas subsequentes, quando
    possível.

------------------------------------------------------------------------

# 5.6 Fotos

Quando houver imagem editorial:

-   gerar um quadro exclusivo;
-   preencher a área útil;
-   respeitar proporção;
-   evitar barras vazias sempre que possível.

------------------------------------------------------------------------

# 5.7 Título

Regras:

-   cabe em um único quadro;
-   maior tamanho possível;
-   deixar aproximadamente uma linha livre abaixo;
-   ignorar subtítulos, salvo configuração específica.

------------------------------------------------------------------------

# 5.8 Preview

O Preview deve utilizar exatamente o mesmo pipeline da exportação.

Qualquer alteração em:

-   perfil;
-   fontes;
-   logos;
-   grifos;
-   texto;

deve refletir imediatamente após "Renderizar esta notícia novamente".

------------------------------------------------------------------------

# 5.9 Renderização parcial

O comando "Renderizar esta notícia novamente" deve:

1.  recriar somente a notícia selecionada;
2.  preservar as demais;
3.  substituir apenas os arquivos correspondentes;
4.  atualizar imediatamente o Preview.

------------------------------------------------------------------------

# 5.10 Exportação

Estrutura:

``` text
ZIP
├── N1
├── N2
├── N3
└── ...
```

Cada pasta contém:

-   PNGs;
-   manifest.json;
-   metadados.

------------------------------------------------------------------------

# 5.11 Regras Imutáveis

-   Preview e exportação devem ser idênticos.
-   Nenhum quadro vazio é exportado.
-   Nenhuma notícia é renderizada fora da ordem.
-   Toda renderização parcial preserva o restante do lote.
-   O algoritmo de continuidade nunca deve ser desativado.

------------------------------------------------------------------------

# Próximo capítulo

Capítulo 6 --- Diagnóstico, Validação e Controle de Qualidade.
