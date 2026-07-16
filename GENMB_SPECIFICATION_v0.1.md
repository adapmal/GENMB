# GENMB --- Especificação Funcional (Rascunho Mestre)

## Objetivo

GENMB é uma plataforma de reconstrução editorial de notícias para
produção de vídeo, preservando a identidade visual dos veículos e
automatizando o fluxo de captura.

## Filosofia

-   Automatizar tarefas repetitivas.
-   Preservar identidade visual.
-   Economizar tempo do editor.
-   Não quebrar funcionalidades existentes.

## Fluxo

1.  Colar múltiplas notícias.
2.  Diagnóstico.
3.  Gerar.
4.  Revisar no Preview.
5.  Renderizar novamente apenas a notícia selecionada quando necessário.
6.  Exportar.

## Perfis

Cada portal possui: - SiteProfile - HeaderTemplate - Stylus - Logos -
Fontes

### Modos

**Capturar cabeçalho** - Usa o cabeçalho do site quando adequado.

**Tema personalizado** - Reconstrói cabeçalho usando logo, cores, fontes
e margens.

## Preview

Funções: - Navegar pelos quadros. - Zoom. - Renderizar esta notícia
novamente.

## Gerenciamento de Dados

Exibir: - Perfis - Temas - Logos - Cache Web - Capturas temporárias -
Projetos - Último lote - Total

Botões: - Limpar cache temporário - Limpar previews - Limpar projetos
antigos - Limpar tudo (preservando perfis e temas)

## Estrutura

``` text
Documentos/
  GENMB/
    Data/
      Profiles/
      HeaderTemplates/
      BrandThemes/
      Logos/
      Fonts/
      Cache/
      Projects/
      Output/
```
