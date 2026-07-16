# GENMB SPECIFICATION v0.8

> Capítulo 8 --- Convenções de Desenvolvimento, Testes e Critérios de
> Aceitação

# 8. Objetivo

Padronizar o desenvolvimento do GENMB para garantir evolução
consistente, minimizar regressões e definir quando uma funcionalidade
pode ser considerada concluída.

------------------------------------------------------------------------

# 8.1 Convenções Gerais

## Estrutura de módulos

Cada módulo deve possuir responsabilidade única.

Exemplos:

-   Parser
-   Diagnóstico
-   SiteProfile Manager
-   HeaderTemplate Manager
-   Render Engine
-   Preview Engine
-   Export Engine
-   Data Manager

Nenhum módulo deve depender diretamente da interface gráfica.

------------------------------------------------------------------------

# 8.2 Convenções de Arquivos

Perfis:

    cnn.profile.json

Header:

    cnn.header.json

Stylus:

    cnn.stylus.css

Logo:

    cnn.logo.svg

Projetos:

    Projeto-2026-07-15/

------------------------------------------------------------------------

# 8.3 Versionamento

Padrão:

    GENMB

    1.0.0-alpha

    1.0.0-beta

    1.0.0

    1.1.0

Toda alteração relevante atualiza o CHANGELOG.

------------------------------------------------------------------------

# 8.4 Critérios de Aceitação

Uma funcionalidade somente é considerada pronta quando:

□ atende à especificação;

□ passa pelos testes;

□ não quebra funcionalidades anteriores;

□ possui documentação;

□ foi validada no Preview;

□ foi validada na exportação.

------------------------------------------------------------------------

# 8.5 Testes Obrigatórios

Antes de cada versão:

## Parser

-   múltiplas notícias;
-   notícias sem foto;
-   notícias com foto;
-   links inválidos.

## Renderização

-   título;
-   foto;
-   continuidade;
-   grifos;
-   exportação.

## Perfis

-   busca de logo;
-   troca de fonte;
-   escala do logo;
-   preview.

## Dados

-   limpeza de cache;
-   limpeza de previews;
-   backup;
-   restauração.

------------------------------------------------------------------------

# 8.6 Checklist de Regressão

Sempre verificar:

□ última linha continua na primeira;

□ grifos não alteram espaçamento;

□ preview igual à exportação;

□ renderização parcial;

□ HeaderTemplates;

□ logos;

□ fontes;

□ fotos.

------------------------------------------------------------------------

# 8.7 Critérios de Qualidade

O software deve:

-   iniciar sem erros;
-   recuperar falhas;
-   informar mensagens claras;
-   nunca perder dados do usuário;
-   responder rapidamente às alterações do editor.

------------------------------------------------------------------------

# 8.8 Roadmap

## GENMB 1.0

-   Arquitetura
-   Perfis
-   Header Templates
-   Renderização
-   Preview
-   Diagnóstico
-   Gerenciamento de Dados

## GENMB 1.1

-   Auditoria de Perfis
-   Novos portais
-   Melhorias no editor

## GENMB 1.2

-   IA para aprender novos portais
-   Biblioteca colaborativa de perfis

------------------------------------------------------------------------

# 8.9 Documento Vivo

A SPECIFICATION é a referência oficial do projeto.

Toda alteração funcional deve ser registrada antes da implementação.

------------------------------------------------------------------------

# Conclusão

Com a conclusão do Capítulo 8, a documentação funcional do GENMB
estabelece a base arquitetural, operacional e de qualidade do projeto. A
partir deste ponto, o desenvolvimento deve evoluir por implementações
incrementais aderentes a esta especificação.
