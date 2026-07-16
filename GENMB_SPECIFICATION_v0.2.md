# GENMB SPECIFICATION v0.2

> Documento vivo de especificação funcional.

# 1. Princípios Imutáveis

1.  O objetivo principal é reduzir o trabalho manual do editor.
2.  A identidade visual do veículo deve ser preservada sempre que
    possível.
3.  O Preview deve representar fielmente a exportação.
4.  Toda alteração em um Perfil deve refletir imediatamente no Preview.
5.  O aplicativo nunca apaga automaticamente perfis, temas ou projetos.
6.  Deve ser possível renderizar novamente apenas a notícia selecionada.
7.  Toda decisão de arquitetura deve privilegiar economia de tempo no
    fluxo editorial.
8.  O sistema deve ser modular e extensível.

------------------------------------------------------------------------

# 2. Interface

## 2.1 Tela Principal

    +--------------------------------------------------------------+
    | GENMB                                                        |
    +--------------------------------------------------------------+
    | Notícias | Perfis | Preview | Configurações                  |
    +--------------------------------------------------------------+

    [ Área para colar múltiplas notícias ]

    [ Diagnóstico ]

    [ Gerar ]

    Status

### Fluxo

1.  Colar roteiro.
2.  Diagnóstico.
3.  Corrigir pendências.
4.  Gerar.
5.  Revisar Preview.

------------------------------------------------------------------------

## 2.2 Aba Perfis

    +---------+--------------------------+----------------------+
    | Sites   | Editor                   | Preview             |
    +---------+--------------------------+----------------------+

### Coluna esquerda

-   Lista de portais
-   Pesquisa
-   Novo
-   Duplicar
-   Excluir
-   Importar Stylus

### Editor

#### Cabeçalho

-   Capturar cabeçalho
-   Tema personalizado
-   Buscar logo no site
-   Logo escolhido
-   Escala do logo (25--300%)
-   Cor principal
-   Cor da linha inferior
-   Altura do cabeçalho

#### Título

-   Fonte do título
-   Detectar fonte original
-   Peso do título (1--9)
-   Tamanho

#### Corpo

-   Fonte do corpo
-   Detectar fonte original
-   Peso do corpo (1--9)
-   Tamanho

#### Grifos

-   Cor
-   Bordas
-   Persistência

#### Código

Exibe o CSS Stylus associado ao perfil.

### Preview

Atualização automática.

Sem botão Atualizar.

------------------------------------------------------------------------

## 2.3 Aba Preview

    +---------------------------------------------------+
    | Preview                                           |
    +---------------------------------------------------+

    [ Quadro ]

    ◀ Anterior     Próximo ▶

    Renderizar esta notícia novamente

Funções:

-   Navegação
-   Zoom
-   Re-renderizar apenas a notícia atual

------------------------------------------------------------------------

## 2.4 Configurações

### Gerenciamento de Dados

Armazenamento:

-   Perfis
-   Temas
-   Logos
-   Cache Web
-   Capturas temporárias
-   Projetos
-   Último lote
-   Total

Botões:

-   Limpar cache temporário
-   Limpar previews
-   Limpar projetos antigos
-   Limpar tudo (preservando perfis e temas)

------------------------------------------------------------------------

# 3. Próximos capítulos

-   Arquitetura
-   Site Profiles
-   Header Templates
-   Motor de Renderização
-   Diagnóstico
-   Algoritmos
-   Roadmap
