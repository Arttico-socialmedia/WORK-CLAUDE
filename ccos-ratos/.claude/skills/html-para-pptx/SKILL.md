---
name: html-para-pptx
description: >
  Converte um deck HTML/CSS no padrão Arttico "Disciplina Ártica" (gerado pelas skills
  `plano-acao` ou `direcionamento-criativos`, ou qualquer deck no mesmo sistema visual: navy
  #00002c, cards #0a0a3d, branco como único destaque, Montserrat + Inter) num arquivo .pptx
  de verdade editável no PowerPoint. Regra de ouro: NUNCA rasterizar (print/screenshot) os
  slides do HTML para dentro do pptx — o resultado tem que ser texto, tabela e forma nativos,
  editáveis de verdade. Use quando o usuário pedir "pptx", "powerpoint", "editável",
  "consegue editar isso", ou depois de gerar um plano-acao/direcionamento-criativos quando o
  usuário quiser a versão pptx. Também dispara com /html-para-pptx.
---

# /html-para-pptx — Converter deck HTML da Arttico em PPTX editável

## Quando usar
Sempre que o usuário pedir uma versão `.pptx` de um deck que hoje só existe como HTML/PDF
(`plano-acao`, `direcionamento-criativos`, ou qualquer variação no mesmo sistema visual). Também
quando ele disser explicitamente que precisa **editar** o conteúdo depois.

## Regra de ouro
**Nunca gerar o pptx rasterizando os slides do HTML** (screenshot de cada `.slide` via Playwright
colado como imagem de fundo). Isso já foi tentado e o resultado é visualmente idêntico mas o texto
não é editável — é uma "foto" dentro de um pptx. Se o usuário pediu editável, o pptx precisa ser
**reconstruído com elementos nativos**: caixas de texto, tabelas de verdade, formas (autoshapes),
imagens só para logos/fotos reais.

---

## Método

### 1. Ler o HTML de origem
Identificar qual sistema gerou o deck (`plano-acao`, 16:9, 1280x720 — ou `direcionamento-criativos`,
vertical, 1080x1528) e extrair o conteúdo de cada slide: headline, corpo, itens de lista, linhas de
tabela, pills, ficha do avatar etc. O HTML já tem tudo isso estruturado em `<div class="slide">`.

### 2. Montar o script Python (python-pptx)
Usar `SKILL_FILES/pptx_helpers.py` como ponto de partida — é uma biblioteca de funções que já
resolve os componentes recorrentes do sistema Arttico (headline, pills, tabela de roteiro, card de
persona, briefing, footer). Escrever um script por deck que importa esses helpers e só monta o
conteúdo específico do cliente (igual a montar o HTML: uma função por tipo de slide, chamada em
sequência).

**Tamanho do slide:** converter o `@page` do CSS (px) pra EMU via polegadas:
`Emu(int(px / 96 * 914400))`. `plano-acao` = 1280x720px. `direcionamento-criativos` = 1080x1528px.

**Rodapé — depende de qual deck é a origem:**
- `plano-acao`: mantém numeração de página (`P / N`) e a barra de progresso crescente, igual ao
  HTML.
- `direcionamento-criativos`: **sem** numeração e **sem** barra de progresso — só o selo/logo no
  rodapé (ver `add_footer(..., show_progress=False)` no helper).

**Logo:** sempre a logo real como imagem (`slide.shapes.add_picture(...)`), nunca a palavra escrita
como texto. Usar o arquivo de logo branca da Arttico (o mesmo já usado nos decks HTML) ou o do
cliente, quando fizer sentido.

### 3. Pitfalls conhecidos (por que essa skill existe)

Esses três problemas já apareceram na prática e custam retrabalho se ignorados:

1. **Tabela sem altura de linha explícita quebra o layout.** Se você não setar
   `tbl.rows[i].height` pra CADA linha (inclusive o cabeçalho), o PowerPoint distribui a altura
   total igualmente entre todas as linhas. Resultado: o cabeçalho (que devia ser baixo) fica
   gigante e vazio, e o conteúdo real fica desalinhado ou estoura pra fora do slide, sobrepondo o
   próximo elemento. **Sempre** definir `tbl.rows[0].height = header_h` e
   `tbl.rows[i].height = row_h` pra cada linha de conteúdo, calculando o total a partir disso —
   nunca deixar o default.

2. **Hyperlink usa a cor de hyperlink do TEMA na renderização, não a cor do run.** Isso tem duas
   camadas:
   - No arquivo (XML), setar `run.hyperlink.address` some com a formatação se você não forçar a
     cor de novo depois: a ordem é atribuir o hyperlink primeiro, **depois**
     `run.font.color.rgb = <cor da marca>`.
   - Mesmo fazendo isso certo, o **PowerPoint ignora a cor do run ao exibir texto com
     hyperlink** e usa a cor `<a:hlink>`/`<a:folHlink>` definida no `clrScheme` do tema
     (`ppt/theme/theme1.xml`), que por padrão é azul/roxo. A única forma confiável de ter o link
     na cor da marca é **sobrescrever essas duas cores no tema**, uma vez, ao criar o deck —
     `pptx_helpers.ArtticoDeck` já faz isso automaticamente no construtor
     (`_fix_theme_hyperlink_color`, seta `hlink`/`folHlink` pra `#FFFFFF` via manipulação direta
     do XML do tema, porque o `Part` do tema não é um `XmlPart` do python-pptx e não expõe
     `._element` — precisa ler `theme_part.blob`, parsear com `lxml.etree`, editar e regravar em
     `theme_part._blob`). Se for escrever um script novo do zero sem usar o helper, replicar essa
     etapa — sem ela o link sempre sai azul, não importa o que você setar no run.

3. **Opacidade de CSS (rgba/opacity) não existe pra texto em pptx.** As variáveis do CSS Arttico
   (`--glacier` branco 92%, `--mist` branco 52%, `--faint` branco 34%) precisam virar cor sólida
   aproximada, calculada visualmente contra o fundo `#00002c`. Aproximações já validadas:
   - glacier (92%) → `#E4E4F0`
   - mist (52%) → `#9A9AB8`
   - faint (34%) → `#666688`
   - hair (linha sutil) → `#303050`

4. **Ícone/SVG do avatar não tem equivalente nativo direto.** O boneco line-art do slide de Avatar
   é um SVG customizado; não existe autoshape "pessoa" no PowerPoint. Aproximar com duas formas
   nativas sem preenchimento (`MSO_SHAPE.OVAL` pra cabeça + `MSO_SHAPE.CHORD` pra corpo, contorno
   branco). É uma simplificação aceitável e editável — avisar o usuário que, se quiser mais fiel
   ao original, pode redesenhar à mão no PowerPoint.

5. **python-pptx não tem preview.** É impossível saber se o layout ficou bom sem renderizar de
   verdade. Ver seção de validação abaixo — pular essa etapa é como gerar HTML sem nunca abrir no
   navegador.

### 4. Validar (obrigatório antes de entregar)

`python-pptx` só escreve o arquivo, não renderiza nada. É preciso exportar os slides como imagem
pra conferir visualmente antes de considerar pronto:

**Se houver PowerPoint instalado na máquina (Windows):** usar automação COM via PowerShell:
```powershell
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open("<caminho-absoluto.pptx>", $true, $false, $false)
$pres.SaveAs("<pasta-de-saida>", 18)   # 18 = ppSaveAsPNG, exporta 1 PNG por slide
$pres.Close()
$ppt.Quit()
```
Depois ler alguns PNGs representativos (capa, um slide com tabela grande, um com anexo/hyperlink,
o fechamento) e conferir: nada estourando o rodapé, nada sobrepondo, cores e fontes corretas.

**Sem PowerPoint instalado:** tentar LibreOffice headless como alternativa
(`soffice --headless --convert-to png <arquivo.pptx>`) — não validado neste ambiente, testar antes
de confiar.

Se achar overflow ou sobreposição, ajustar as alturas/posições no script Python e regerar — não dá
pra "só olhar o código" e confiar que bateu.

### 5. Salvar
Mesmo caminho e nome do deck HTML de origem, trocando a extensão para `.pptx`. Se já existir uma
versão rasterizada antiga no mesmo caminho, **substituir** (não manter as duas, pra não confundir
qual é a fonte de verdade).

### 6. Confirmar
Informar o caminho do `.pptx`, o que é nativamente editável (texto, tabelas, formas, links) e quais
simplificações foram feitas (ex. ícone do avatar, aproximação de cor). Perguntar se quer ajustar
algo antes de considerar pronto.

---

## Observações
- Fontes: usar os mesmos nomes do CSS (`Montserrat`, `Inter`, `Lora`). Se não estiverem instaladas
  na máquina de quem abrir o arquivo, o PowerPoint faz fallback automático — isso é esperado e não
  é bug.
- Não inventar rodapé/numeração além do que o deck de origem define (ver regra do passo 2).
- Esta skill não decide o conteúdo do deck — isso já vem pronto do `plano-acao` ou
  `direcionamento-criativos`. Aqui só se converte fielmente pra um formato editável.
