# -*- coding: utf-8 -*-
r"""
pptx_helpers.py — biblioteca de componentes nativos do sistema Arttico
"Disciplina Ártica v2" (cyan accent) para montar decks .pptx 100% editáveis (sem rasterizar HTML).

Uso típico (um script por deck, um por cliente):

    from pptx_helpers import ArtticoDeck, MSO_SHAPE

    deck = ArtticoDeck(
        slide_w_px=1080, slide_h_px=1528,   # direcionamento-criativos (vertical)
        # slide_w_px=1280, slide_h_px=720,  # plano-acao (16:9)
        logo_path=r"C:\...\logo-arttico-branca.png",
        show_pageno=True,      # True nos dois decks agora (contador "P / N" no rodapé)
        show_progress=False,   # False = direcionamento-criativos (sem barra de progresso)
                                # True  = plano-acao (com barra de progresso cyan)
    )

    s = deck.new_slide()
    deck.add_eyebrow(s, "Grupo Arttico")
    deck.add_headline(s, deck.px(560), [("Direcionamento ", deck.FROST), ("de Criativos", deck.MIST)])
    # headline com destaque cyan (ex. slide de Avatar): [("Avatar ", deck.FROST), ("· a paciente", deck.CYAN)]
    deck.add_footer(s, pageno=1, total=18)   # pageno/total só importam se show_pageno=True
    ...
    deck.save(r"C:\...\deck.pptx")

Validado end-to-end (gerado + renderizado via automação COM do PowerPoint) no formato vertical
1080x1528 do `direcionamento-criativos`. Pra usar no formato 16:9 do `plano-acao`, ajuste os
parâmetros de margem/fonte no construtor (`margin_px`, `wrap_top_px` etc.) — os valores default
abaixo refletem o CSS do `direcionamento-criativos`; o `plano-acao` usa métricas um pouco
diferentes (ver `template-plano.html` da skill `plano-acao` pros valores exatos de referência).

PITFALLS que esta biblioteca já resolve (não desfazer ao editar):
  1. Tabelas de roteiro (`add_script_table`) setam `tbl.rows[i].height` explicitamente em CADA
     linha, cabeçalho incluso. Sem isso o PowerPoint divide a altura total igualmente entre todas
     as linhas, e o cabeçalho vira uma faixa gigante vazia enquanto o conteúdo desalinha/estoura.
  2. Molduras de referência com link (`add_ref`) aplicam `run.hyperlink.address` e SÓ DEPOIS
     forçam `run.font.color.rgb` de novo — hyperlink reseta a cor pro azul do tema do PowerPoint
     se você setar a cor antes.
  3. As cores com opacidade do CSS (--glacier/--mist/--faint, brancos a 92/52/34%) foram
     convertidas pra hex sólido aproximado, já que pptx não aplica opacidade em texto do jeito
     que CSS aplica. O mesmo vale pro cyan translúcido do ícone de avatar (--cyan-dim).
"""
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

EMU_PER_INCH = 914400

# ---------- Paleta "Disciplina Ártica v2" (aproximação sólida das cores com opacidade) ----------
NIGHT = RGBColor(0x00, 0x00, 0x2C)      # fundo --night
CARD = RGBColor(0x0A, 0x0A, 0x3D)       # --card
CARD2 = RGBColor(0x07, 0x12, 0x35)      # --card2 (banding de linha par em tabela)
FROST = RGBColor(0xFF, 0xFF, 0xFF)      # --frost (branco 100%)
CYAN = RGBColor(0xA3, 0xE3, 0xF0)       # --cyan (único destaque de cor)
CYAN_PALE = RGBColor(0xCC, 0xF9, 0xFF)  # --cyan-pale (cabeçalho de tabela)
CYAN_DIM = RGBColor(0x5C, 0x8A, 0x94)   # --cyan-dim (aproximação sólida do cyan a 60% opacidade, pro ícone de avatar)
GLACIER = RGBColor(0xE4, 0xE4, 0xF0)    # --glacier (branco ~92%)
MIST = RGBColor(0x9A, 0x9A, 0xB8)       # --mist (branco ~52%)
FAINT = RGBColor(0x66, 0x66, 0x88)      # --faint (branco ~34%)
HAIR = RGBColor(0x30, 0x30, 0x50)       # --hair (linha sutil)

F_HEAD = "Montserrat"
F_BODY = "Inter"
F_SERIF = "Lora"


class ArtticoDeck:
    NIGHT = NIGHT; CARD = CARD; CARD2 = CARD2; FROST = FROST
    CYAN = CYAN; CYAN_PALE = CYAN_PALE; CYAN_DIM = CYAN_DIM
    GLACIER = GLACIER; MIST = MIST; FAINT = FAINT; HAIR = HAIR

    def __init__(self, slide_w_px, slide_h_px, logo_path=None, show_progress=True, show_pageno=None,
                 margin_px=80, wrap_top_px=132, footer_bottom_px=64, horizon_bottom_px=116):
        self.W_PX, self.H_PX = slide_w_px, slide_h_px
        self.logo_path = logo_path
        self.show_progress = show_progress
        # show_pageno é independente da barra: direcionamento-criativos mostra "P / N" sem barra.
        # Se não informado, herda show_progress (compat com chamadas antigas).
        self.show_pageno = show_progress if show_pageno is None else show_pageno
        self.margin = margin_px
        self.wrap_top = wrap_top_px
        self.footer_bottom = footer_bottom_px
        self.horizon_bottom = horizon_bottom_px

        self.prs = Presentation()
        self.prs.slide_width = self.px(slide_w_px)
        self.prs.slide_height = self.px(slide_h_px)
        self._blank = self.prs.slide_layouts[6]
        self._fix_theme_hyperlink_color()

    def _fix_theme_hyperlink_color(self):
        """PITFALL #2 (parte 2): mesmo forçando run.font.color.rgb = FROST depois do
        hyperlink.address, o PowerPoint renderiza o texto do link usando a cor de hyperlink do
        TEMA (<a:hlink>/<a:folHlink> em theme1.xml), não a cor direta do run — isso é um
        comportamento da própria renderização do PowerPoint, não um bug do python-pptx. A única
        forma confiável de ter o link na cor da marca é sobrescrever o tema em si."""
        try:
            from lxml import etree
            master = self.prs.slide_masters[0]
            theme_part = master.part.part_related_by(
                'http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme')
            # Part generico (nao XmlPart): precisa parsear o blob manualmente e regravar em _blob.
            root = etree.fromstring(theme_part.blob)
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            changed = False
            for tag in ('hlink', 'folHlink'):
                el = root.find(f'.//a:clrScheme/a:{tag}', ns)
                if el is not None:
                    srgb = el.find('a:srgbClr', ns)
                    if srgb is not None:
                        srgb.set('val', 'FFFFFF')
                        changed = True
            if changed:
                theme_part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        except Exception:
            pass  # se o tema não seguir a estrutura esperada, ignora e mantém o hlink azul padrao

    # ---------- infra ----------
    def px(self, v):
        return Emu(int(v / 96 * EMU_PER_INCH))

    def new_slide(self):
        s = self.prs.slides.add_slide(self._blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = NIGHT
        return s

    def save(self, path):
        self.prs.save(path)
        return path

    def _letter_spacing(self, run, hundredths_pt):
        rPr = run._r.get_or_add_rPr()
        rPr.set('spc', str(hundredths_pt))

    # ---------- primitivas ----------
    def add_textbox(self, slide, l, t, w, h, text, size, color, bold=False, font=F_BODY,
                     align=PP_ALIGN.LEFT, spacing=None, italic=False, anchor=None, line_spacing=None):
        box = slide.shapes.add_textbox(l, t, w, h)
        tf = box.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        if anchor:
            tf.vertical_anchor = anchor
        p = tf.paragraphs[0]
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
        r.font.name = font; r.font.color.rgb = color
        if spacing:
            self._letter_spacing(r, spacing)
        return box

    def add_rect(self, slide, l, t, w, h, fill=None, line_color=None, dash=None, radius=False):
        shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        shp = slide.shapes.add_shape(shape_type, l, t, w, h)
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid(); shp.fill.fore_color.rgb = fill
        if line_color is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line_color; shp.line.width = Pt(1)
            if dash:
                shp.line.dash_style = dash
        shp.shadow.inherit = False
        return shp

    def add_eyebrow(self, slide, text):
        self.add_textbox(slide, self.px(self.margin), self.px(60), self.px(900), self.px(30),
                          text.upper(), 10.5, MIST, bold=True, spacing=100)

    def add_headline(self, slide, top, parts, size=42, width_px=920):
        """parts: lista de (texto, cor RGBColor)"""
        box = slide.shapes.add_textbox(self.px(self.margin), top, self.px(width_px), self.px(140))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        for (txt, color) in parts:
            r = p.add_run()
            r.text = txt; r.font.size = Pt(size); r.font.bold = True
            r.font.name = F_HEAD; r.font.color.rgb = color
        return box

    def add_uline(self, slide, top):
        self.add_rect(slide, self.px(self.margin), top, self.px(46), Emu(18000), fill=FROST)

    def add_pill(self, slide, l, t, text, filled=True, size=11):
        w = self.px(len(text) * 11 + 50)
        h = self.px(40)
        shp = self.add_rect(slide, l, t, w, h, fill=(FROST if filled else None),
                             line_color=(None if filled else FROST), radius=True)
        shp.adjustments[0] = 0.5
        tf = shp.text_frame
        tf.word_wrap = False
        tf.margin_left = self.px(6); tf.margin_right = self.px(6)
        tf.margin_top = self.px(2); tf.margin_bottom = self.px(2)
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = text.upper()
        r.font.size = Pt(size); r.font.bold = True; r.font.name = F_BODY
        r.font.color.rgb = NIGHT if filled else FROST
        self._letter_spacing(r, 80)
        return w

    # ---------- rodapé ----------
    def add_footer(self, slide, pageno=None, total=None, run_pct=None):
        """Linha + logo sempre. Barra de progresso cyan só se show_progress=True (plano-acao).
        Contador 'P / N' só se show_pageno=True (os dois decks agora) — precisa de pageno/total."""
        line_y = self.px(self.H_PX - self.horizon_bottom)
        line_w = self.px(self.W_PX)
        self.add_rect(slide, self.px(0), line_y, line_w, Emu(9525), fill=HAIR)
        if self.show_progress:
            pct = run_pct if run_pct is not None else (pageno / total if (pageno and total) else 0)
            run_w = int(self.W_PX * pct)
            if run_w > 0:
                self.add_rect(slide, self.px(0), line_y, self.px(run_w), Emu(12700), fill=CYAN)
        if self.logo_path:
            try:
                slide.shapes.add_picture(self.logo_path, self.px(self.margin),
                                          self.px(self.H_PX - self.footer_bottom - 20), height=self.px(22))
            except Exception:
                pass
        if self.show_pageno and pageno and total:
            self.add_textbox(slide, self.px(self.W_PX - 200), self.px(self.H_PX - self.footer_bottom - 26),
                              self.px(120), self.px(30), f"{pageno} / {total}", 10.5, FAINT,
                              align=PP_ALIGN.RIGHT, spacing=60)

    # ---------- persona (avatar) ----------
    def add_persona(self, slide, top, ficha_rows, width_px=920):
        """Cartão bordado com ícone-avatar (pessoa em caixa arredondada cyan) + ficha ao lado,
        no padrão v2 (substitui o antigo boneco line-art solto)."""
        card_h = self.px(220)
        self.add_rect(slide, self.px(self.margin), top, self.px(width_px), card_h,
                       fill=CARD, line_color=HAIR, radius=True)
        box_size = self.px(116)
        bx = self.px(self.margin + 32)
        by = top + (card_h - box_size) // 2
        icon_box = self.add_rect(slide, bx, by, box_size, box_size, fill=None, line_color=FAINT, radius=True)
        icon_box.adjustments[0] = 0.16
        # cabeça (círculo cyan) + ombros (arco cyan), centralizados dentro da caixa do ícone
        head_d = self.px(38)
        head_l = bx + (box_size - head_d) // 2
        head_t = by + self.px(26)
        head = self.add_rect(slide, head_l, head_t, head_d, head_d, fill=CYAN_DIM, radius=True)
        head.adjustments[0] = 0.5
        body = slide.shapes.add_shape(MSO_SHAPE.CHORD, bx + self.px(14), head_t + self.px(30),
                                       box_size - self.px(28), self.px(56))
        body.fill.solid(); body.fill.fore_color.rgb = CYAN_DIM
        body.line.fill.background(); body.shadow.inherit = False
        fx = self.px(self.margin + 32) + box_size + self.px(30)
        fy = top + self.px(24)
        row_h = card_h.emu // max(len(ficha_rows), 1)
        for i, (k, v) in enumerate(ficha_rows):
            ry = fy + Emu(row_h * i)
            self.add_textbox(slide, fx, ry, self.px(180), self.px(28), k.upper(), 9.5, MIST, bold=True, spacing=70)
            self.add_textbox(slide, fx + self.px(150), ry, self.px(600), self.px(40), v, 13, FROST, line_spacing=1.1)
        return top + card_h + self.px(30)

    def add_dores_desejos(self, slide, top, dores, desejos, width_px=920, col_gap_px=480):
        col_w = self.px((width_px - (col_gap_px - 430)) // 2) if False else self.px(430)
        add = self.add_textbox
        add(slide, self.px(self.margin), top, col_w, self.px(30), "DORES", 14, FROST, bold=True, font=F_HEAD)
        self.add_rect(slide, self.px(self.margin), top + self.px(36), col_w, Emu(9525), fill=HAIR)
        add(slide, self.px(self.margin + col_gap_px), top, col_w, self.px(30), "DESEJOS", 14, FROST, bold=True, font=F_HEAD)
        self.add_rect(slide, self.px(self.margin + col_gap_px), top + self.px(36), col_w, Emu(9525), fill=HAIR)

        def list_block(x):
            def _inner(items):
                y = top + self.px(56)
                for it in items:
                    box = slide.shapes.add_textbox(x + self.px(20), y, col_w - self.px(20), self.px(34))
                    tf = box.text_frame; tf.word_wrap = True
                    p = tf.paragraphs[0]; p.line_spacing = 1.15
                    rb = p.add_run(); rb.text = "•  "; rb.font.size = Pt(12.5); rb.font.name = F_BODY; rb.font.color.rgb = CYAN
                    rt = p.add_run(); rt.text = it; rt.font.size = Pt(12.5); rt.font.name = F_BODY; rt.font.color.rgb = GLACIER
                    y += self.px(34)
            return _inner
        list_block(self.px(self.margin))(dores)
        list_block(self.px(self.margin + col_gap_px))(desejos)

    # ---------- briefing (ficha k/v) ----------
    def add_brief_row(self, slide, y, k, v, width_px=920):
        self.add_textbox(slide, self.px(self.margin), y, self.px(300), self.px(24), k.upper(), 12, FROST,
                          bold=True, font=F_HEAD, spacing=40)
        self.add_rect(slide, self.px(self.margin), y + self.px(28), self.px(width_px), Emu(9525), fill=HAIR)
        self.add_textbox(slide, self.px(self.margin), y + self.px(36), self.px(width_px), self.px(90), v,
                          13.5, GLACIER, line_spacing=1.2)
        return y + self.px(36) + self.px(90) + self.px(10)

    # ---------- tabela de roteiro (Arte | Texto | Imagem | Observações) ----------
    def add_script_table(self, slide, top, rows, is_static=False, width_px=920):
        """rows: lista de [arte, texto, imagem, observacoes]. `texto` pode ser string OU lista de
        (texto, bold) pra múltiplos parágrafos numa célula (ex. estático: headline em bold + corpo).
        PITFALL #1 resolvido aqui: altura de linha é setada explicitamente linha a linha."""
        n_rows = len(rows) + 1
        table_w = self.px(width_px)
        col_widths = ([self.px(56), self.px(560), self.px(150), self.px(154)] if not is_static
                      else [self.px(56), self.px(600), self.px(132), self.px(132)])
        header_h = self.px(40)
        row_h = self.px(190) if is_static else self.px(105)
        table_h = Emu(int(header_h) + int(row_h) * len(rows))
        gframe = slide.shapes.add_table(n_rows, 4, self.px(self.margin), top, table_w, table_h)
        tbl = gframe.table
        tbl.rows[0].height = header_h
        for ridx in range(1, n_rows):
            tbl.rows[ridx].height = row_h
        for i, w in enumerate(col_widths):
            tbl.columns[i].width = w

        headers = ["ARTE", "TEXTO", "IMAGEM", "OBSERVAÇÕES"]
        for c, htxt in enumerate(headers):
            cell = tbl.cell(0, c)
            cell.fill.solid(); cell.fill.fore_color.rgb = CYAN_PALE
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.margin_left = self.px(10); tf.margin_top = self.px(2); tf.margin_bottom = self.px(2)
            r = tf.paragraphs[0].add_run(); r.text = htxt
            r.font.size = Pt(10.5); r.font.bold = True; r.font.name = F_BODY; r.font.color.rgb = NIGHT

        for ridx, row in enumerate(rows, start=1):
            for c, val in enumerate(row):
                cell = tbl.cell(ridx, c)
                cell.fill.solid(); cell.fill.fore_color.rgb = CARD2 if ridx % 2 == 0 else CARD
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf = cell.text_frame
                tf.word_wrap = True
                tf.margin_left = self.px(10); tf.margin_right = self.px(6)
                tf.margin_top = self.px(6); tf.margin_bottom = self.px(6)
                p = tf.paragraphs[0]; p.line_spacing = 1.2
                if c == 0:
                    r = p.add_run(); r.text = str(val)
                    r.font.size = Pt(15); r.font.bold = True; r.font.name = F_HEAD; r.font.color.rgb = CYAN
                    p.alignment = PP_ALIGN.CENTER
                elif c == 1:
                    if isinstance(val, list):
                        first = True
                        for (txt, bold) in val:
                            if not first:
                                p = tf.add_paragraph(); p.line_spacing = 1.2
                            first = False
                            r = p.add_run(); r.text = txt
                            r.font.size = Pt(12.5); r.font.bold = bold; r.font.name = F_BODY
                            r.font.color.rgb = FROST if bold else GLACIER
                    else:
                        r = p.add_run(); r.text = str(val)
                        r.font.size = Pt(12.5); r.font.name = F_BODY; r.font.color.rgb = GLACIER
                else:
                    r = p.add_run(); r.text = str(val)
                    r.font.size = Pt(10.5); r.font.name = F_BODY; r.font.color.rgb = MIST

        tblPr = tbl._tbl.find(qn('a:tblPr'))
        if tblPr is not None:
            tblPr.set('firstRow', '0'); tblPr.set('bandRow', '0')
        return top + table_h + self.px(20)

    # ---------- moldura de referência (vídeo/imagem de inspiração) ----------
    def add_ref(self, slide, top, kind="v", link=None, width_px=920):
        """Rótulo em duas linhas ("Vídeo" / "referência" em bold) + moldura tracejada 1080x1920
        (v) ou 1080x1440 (s). Com link, o rótulo vira cyan sublinhado ("Ver referência ↗")."""
        w = self.px(206)
        h = self.px(320) if kind == "v" else self.px(230)
        cx = self.px(self.margin) + (self.px(width_px) - w) // 2
        label_box = slide.shapes.add_textbox(cx - self.px(60), top, w + self.px(120), self.px(48))
        tf0 = label_box.text_frame
        tf0.word_wrap = False
        p0 = tf0.paragraphs[0]; p0.alignment = PP_ALIGN.CENTER
        r0 = p0.add_run(); r0.text = "Vídeo" if kind == "v" else "Imagem"
        r0.font.size = Pt(11); r0.font.name = F_BODY; r0.font.color.rgb = GLACIER
        p1 = tf0.add_paragraph(); p1.alignment = PP_ALIGN.CENTER
        r1 = p1.add_run(); r1.text = "referência"
        r1.font.size = Pt(14); r1.font.bold = True; r1.font.name = F_HEAD; r1.font.color.rgb = FROST
        link_box = None
        if link:
            link_box = slide.shapes.add_textbox(cx - self.px(60), top + self.px(52), w + self.px(120), self.px(20))
            tfl = link_box.text_frame; tfl.word_wrap = False
            pl = tfl.paragraphs[0]; pl.alignment = PP_ALIGN.CENTER
            rl = pl.add_run(); rl.text = "Ver referência ↗"
            # PITFALL #2: setar o hyperlink ANTES, forcar a cor da marca DEPOIS.
            rl.hyperlink.address = link
            rl.font.underline = True
            rl.font.size = Pt(10); rl.font.name = F_BODY; rl.font.color.rgb = CYAN

        frame_top = top + (self.px(76) if link else self.px(52))
        box = self.add_rect(slide, cx, frame_top, w, h, fill=None, line_color=RGBColor(0x66, 0x66, 0x88))
        box.line.dash_style = 2  # dash
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = "+"
        r.font.size = Pt(28); r.font.color.rgb = RGBColor(0x88, 0x88, 0xA8); r.font.name = F_BODY
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = "1080 x 1920" if kind == "v" else "1080 x 1440"
        r2.font.size = Pt(12); r2.font.color.rgb = FROST; r2.font.name = F_BODY
        return frame_top + h

    def add_attach(self, slide, top, label, kind="v", link=None, width_px=920):
        """Alias retrocompatível de add_ref (assinatura antiga aceitava `label` solto em vez do
        rótulo de duas linhas automático; o parâmetro é ignorado no layout novo)."""
        return self.add_ref(slide, top, kind=kind, link=link, width_px=width_px)

    # ---------- fechamento (cartão de alerta/orientação) ----------
    def add_alert_close(self, slide, top, text_parts, width_px=780):
        """Ícone circular cyan (!) + frase final. text_parts: lista de (texto, bold) —
        bold=True usa CYAN (destaque), bold=False usa FROST."""
        d = self.px(60)
        icon = self.add_rect(slide, self.px(self.margin), top, d, d, fill=None, line_color=CYAN, radius=True)
        icon.adjustments[0] = 0.5
        icon.line.width = Pt(1.6)
        tf_i = icon.text_frame
        p_i = tf_i.paragraphs[0]; p_i.alignment = PP_ALIGN.CENTER
        r_i = p_i.add_run(); r_i.text = "!"
        r_i.font.size = Pt(20); r_i.font.bold = True; r_i.font.name = F_HEAD; r_i.font.color.rgb = CYAN

        box = slide.shapes.add_textbox(self.px(self.margin), top + self.px(72), self.px(width_px), self.px(160))
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.line_spacing = 1.3
        for txt, bold in text_parts:
            r = p.add_run(); r.text = txt
            r.font.size = Pt(24); r.font.bold = bold; r.font.name = F_BODY
            r.font.color.rgb = CYAN if bold else FROST
        return top + self.px(72) + self.px(160)
