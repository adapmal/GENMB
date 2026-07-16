# GENMB SPECIFICATION v0.7

> Capítulo 7 --- Gerenciamento de Dados, Versionamento, Backup e
> Migração

# 7. Objetivo

Garantir que atualizações do GENMB nunca coloquem em risco perfis,
projetos ou configurações do usuário.

------------------------------------------------------------------------

# 7.1 Estrutura de Dados

Todos os dados do usuário ficam fora da pasta da aplicação.

``` text
Documentos/
└── GENMB/
    └── Data/
        ├── Profiles/
        ├── HeaderTemplates/
        ├── BrandThemes/
        ├── Logos/
        ├── Fonts/
        ├── Cache/
        ├── Projects/
        └── Output/
```

Cada nova versão do GENMB reutiliza essa pasta automaticamente.

------------------------------------------------------------------------

# 7.2 Gerenciamento de Dados

A aba **Configurações → Gerenciamento de Dados** exibe:

-   Perfis
-   Temas
-   Logos
-   Cache da Web
-   Capturas temporárias
-   Projetos
-   Último lote gerado
-   Total utilizado

Os valores são atualizados automaticamente.

------------------------------------------------------------------------

# 7.3 Limpeza

## Limpar cache temporário

Remove:

-   HTML baixado;
-   cache Web;
-   previews temporários;
-   arquivos intermediários;
-   logos temporários.

Preserva:

-   perfis;
-   temas;
-   projetos.

## Limpar previews

Remove apenas PNGs renderizados.

## Limpar projetos antigos

Opções:

-   30 dias
-   60 dias
-   90 dias

## Limpar tudo

Remove:

-   cache;
-   previews;
-   lotes exportados.

Nunca remove:

-   perfis;
-   HeaderTemplates;
-   BrandThemes;
-   logos oficiais.

------------------------------------------------------------------------

# 7.4 Backup

O GENMB deve permitir:

-   Exportar Perfis
-   Exportar HeaderTemplates
-   Exportar Projeto
-   Backup completo da pasta Data

Formato preferencial:

ZIP.

------------------------------------------------------------------------

# 7.5 Restauração

O usuário poderá restaurar:

-   um perfil;
-   um projeto;
-   toda a pasta Data.

Antes da restauração o sistema valida compatibilidade.

------------------------------------------------------------------------

# 7.6 Versionamento

Cada perfil possui:

-   identificador;
-   versão;
-   data de atualização;
-   histórico.

Alterações importantes geram nova versão.

------------------------------------------------------------------------

# 7.7 Migração

Ao detectar uma versão mais recente do GENMB:

1.  localizar a pasta Data;
2.  validar integridade;
3.  migrar automaticamente;
4.  registrar log da migração.

Nenhuma configuração é descartada sem confirmação.

------------------------------------------------------------------------

# 7.8 Projetos

Cada projeto contém:

-   roteiro original;
-   configurações utilizadas;
-   perfis empregados;
-   manifest;
-   renderizações.

Isso permite reabrir um projeto e renderizar novamente apenas as
notícias desejadas.

------------------------------------------------------------------------

# 7.9 Regras Imutáveis

-   Dados do usuário nunca ficam dentro da pasta da aplicação.
-   Atualizações do programa não podem apagar configurações.
-   Todo backup deve ser restaurável.
-   Toda migração deve ser reversível.
-   O usuário deve saber quanto espaço cada categoria ocupa.

------------------------------------------------------------------------

# Próximo capítulo

Capítulo 8 --- Roadmap, Convenções de Desenvolvimento e Testes.
