# html-para-pptx (Claude Code skill)

Skill para o Claude Code que converte um deck HTML/CSS (slides em `<div class="slide">`, uma
página por `.slide`) num arquivo `.pptx` **de verdade editável** no PowerPoint: texto, tabelas e
formas nativas — nunca um screenshot dos slides colado como imagem de fundo.

Vem calibrada para o sistema de design "Disciplina Ártica" (fundo navy `#00002c`, cyan de
destaque, Montserrat + Inter), usado nos decks de planejamento e direcionamento de criativos da
Arttico, mas os helpers (`SKILL_FILES/pptx_helpers.py`) servem de referência pra adaptar a
qualquer outro sistema de cores/tipografia.

## Como instalar

1. Copie a pasta `html-para-pptx/` deste repositório para dentro de `.claude/skills/` do seu
   projeto (ou de `~/.claude/skills/` pra ficar disponível em todos os projetos):

   ```
   .claude/skills/html-para-pptx/SKILL.md
   .claude/skills/html-para-pptx/SKILL_FILES/pptx_helpers.py
   ```

2. Instale as dependências Python usadas pelo helper:

   ```
   pip install python-pptx lxml
   ```

3. No Claude Code, a skill passa a aparecer na lista de skills disponíveis e pode ser chamada com
   `/html-para-pptx` ou pedindo diretamente "converte esse deck pra pptx editável".

## Uso

Peça pro Claude converter um deck HTML existente (gerado por outra skill ou escrito à mão, desde
que siga o padrão `<div class="slide">` por página). O `SKILL.md` documenta o método completo:
como ler o HTML de origem, montar o script Python com `pptx_helpers.py`, e os pitfalls conhecidos
de python-pptx (altura de linha de tabela, cor de hyperlink sobrescrita pelo tema, opacidade de
CSS sem equivalente em pptx).

**Validação (opcional, mas recomendada pela skill):** se houver PowerPoint instalado no Windows,
o `SKILL.md` traz um trecho de automação COM via PowerShell pra exportar os slides como PNG e
conferir visualmente antes de considerar o arquivo pronto.
