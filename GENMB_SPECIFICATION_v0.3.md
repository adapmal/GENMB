# GENMB SPECIFICATION v0.3

> Capítulo 3 --- Arquitetura do Sistema

# 3. Arquitetura Geral

``` text
                    +----------------------+
                    |  Interface (UI)      |
                    +----------+-----------+
                               |
         +---------------------+----------------------+
         |                                            |
   Notícias                                   Biblioteca de Perfis
         |                                            |
         +---------------------+----------------------+
                               |
                       Parser de Notícias
                               |
                 +-------------+--------------+
                 |                            |
            Diagnóstico                 SiteProfile Manager
                 |                            |
                 |                     HeaderTemplate
                 |                            |
                 +-------------+--------------+
                               |
                      Motor de Renderização
                               |
          +--------------------+---------------------+
          |                    |                     |
      Preview             Exportação ZIP      Gerenciamento
                                                 de Dados
```

# 3.1 Fluxo completo

1.  Usuário cola um roteiro contendo múltiplas notícias.
2.  O Parser identifica automaticamente os blocos.
3.  O Diagnóstico verifica:
    -   existência de perfil;
    -   conflitos;
    -   fontes;
    -   logos;
    -   links.
4.  O SiteProfile adequado é carregado.
5.  O HeaderTemplate correspondente é aplicado.
6.  O Motor de Renderização gera os quadros.
7.  O Preview mostra exatamente o resultado final.
8.  O usuário pode escolher **Renderizar esta notícia novamente**.
9.  O lote é exportado em ZIP.

# 3.2 Módulos

## Parser

Responsável por: - separar notícias; - localizar títulos; - localizar
links; - interpretar marcações de grifo.

## Diagnóstico

Executa todas as verificações antes da renderização.

Nunca altera dados do usuário.

## SiteProfile Manager

Seleciona automaticamente o perfil correto para cada domínio.

Prioridade:

1.  URL específica
2.  Prefixo
3.  Domínio
4.  Fallback

## HeaderTemplate

Responsável exclusivamente pelo cabeçalho.

Dois modos:

-   Capturar cabeçalho
-   Tema personalizado

## Render Engine

Responsável por:

-   reconstrução da página;
-   rolagem;
-   quadros;
-   grifos;
-   imagens;
-   continuidade.

## Preview Engine

Mostra exatamente os PNGs que serão exportados.

Permite renderizar novamente apenas a notícia atual.

## Data Manager

Gerencia:

-   Profiles
-   HeaderTemplates
-   BrandThemes
-   Logos
-   Fonts
-   Cache
-   Projects
-   Output

Nunca remove dados automaticamente.

# 3.3 Estrutura de Dados

``` text
GENMB Data

Profiles/
HeaderTemplates/
BrandThemes/
Logos/
Fonts/
Cache/
Projects/
Output/
```

# 3.4 Regras arquiteturais

-   Toda configuração pertence ao perfil do portal.
-   O Preview nunca deve diferir da exportação.
-   Uma notícia pode ser renderizada isoladamente.
-   Alterações de perfil refletem imediatamente no Preview.
-   O sistema deve permanecer modular, permitindo novos portais sem
    alterar o núcleo.

# Próximo capítulo

Capítulo 4 --- Site Profiles e Header Templates.
