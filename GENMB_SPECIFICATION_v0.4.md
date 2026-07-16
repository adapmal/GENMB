# GENMB SPECIFICATION v0.4

> Capítulo 4 --- Site Profiles e Header Templates

# 4. Objetivo

Cada portal suportado pelo GENMB é representado por um **SiteProfile**.
O SiteProfile descreve como localizar, reconstruir e renderizar uma
notícia daquele veículo.

Separadamente existe um **HeaderTemplate**, responsável exclusivamente
pela identidade visual do cabeçalho.

------------------------------------------------------------------------

# 4.1 Estrutura

``` text
SiteProfile
├── Informações gerais
├── Regras de extração
├── HeaderTemplate
├── Logos
├── Fontes
├── Stylus
├── Preview
└── Configurações
```

------------------------------------------------------------------------

# 4.2 Informações Gerais

Campos:

-   Nome do veículo
-   Domínio principal
-   Domínios alternativos
-   Idioma
-   País
-   Categoria
-   Versão do perfil
-   Última atualização

------------------------------------------------------------------------

# 4.3 Regras de Extração

Cada perfil contém:

-   seletor do título;
-   seletor da foto principal;
-   seletor do corpo;
-   seletor de legendas (futuro);
-   seletor do breadcrumb/editoria (opcional);
-   regras especiais.

Quando houver conflito entre seletores, a prioridade é:

1.  seletor específico do perfil;
2.  seletor Stylus;
3.  fallback automático.

------------------------------------------------------------------------

# 4.4 HeaderTemplate

Cada SiteProfile aponta para um HeaderTemplate.

Dois modos são suportados.

## Capturar Cabeçalho

Indicado para veículos cujo cabeçalho original já possui excelente
apresentação.

Exemplos:

-   Vatican News

Características:

-   reaproveita o cabeçalho original;
-   permite pequenos ajustes;
-   não reconstrói o layout.

## Tema Personalizado

O cabeçalho é reconstruído.

Campos editáveis:

-   logo principal;
-   sublogo (opcional);
-   cor principal;
-   cor da linha inferior;
-   altura;
-   escala do logo;
-   alinhamento;
-   margens.

------------------------------------------------------------------------

# 4.5 Logos

Cada HeaderTemplate possui:

``` text
Logos/

principal

sublogos/

favicon
```

Botões:

-   Buscar logo no site
-   Atualizar logo
-   Selecionar manualmente

O botão "Buscar logo no site" permanece em todas as versões.

------------------------------------------------------------------------

# 4.6 Fontes

Cada perfil armazena:

## Título

-   família
-   peso (1--9)
-   tamanho

## Corpo

-   família
-   peso (1--9)
-   tamanho

Botão:

**Detectar fontes do veículo**

O sistema informa:

-   fonte declarada;
-   fonte realmente utilizada;
-   fallback empregado.

------------------------------------------------------------------------

# 4.7 Preview

Todo ajuste deve atualizar automaticamente:

-   logo;
-   escala;
-   cores;
-   pesos;
-   fontes.

Não existe botão "Atualizar".

------------------------------------------------------------------------

# 4.8 Código

A aba Código exibe:

-   CSS Stylus;
-   regras de extração;
-   observações.

Nunca deve aparecer vazia quando existir um perfil.

------------------------------------------------------------------------

# 4.9 Header Assets

Todo HeaderTemplate pode utilizar:

-   PNG
-   SVG
-   WEBP
-   JPG

O sistema não tenta reconstruir marcas utilizando fontes comuns.

------------------------------------------------------------------------

# 4.10 Estrutura JSON

Exemplo simplificado:

``` json
{
  "id":"cnn",
  "headerMode":"custom",
  "logo":"cnn.png",
  "primaryColor":"#c90016",
  "lineColor":"#990010",
  "titleFont":"Arial",
  "bodyFont":"Arial"
}
```

------------------------------------------------------------------------

# 4.11 Regras Imutáveis

-   Perfis nunca são apagados automaticamente.
-   HeaderTemplates são independentes dos SiteProfiles.
-   Logos permanecem em cache.
-   Alterações refletem imediatamente no Preview.
-   Toda notícia deve poder ser renderizada novamente utilizando a
    versão atual do perfil.

------------------------------------------------------------------------

# Próximo capítulo

Capítulo 5 --- Motor de Renderização, Divisão de Quadros e Algoritmo dos
Grifos.
