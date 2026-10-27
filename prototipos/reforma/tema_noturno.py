"""Tokens visuais da demo Noturno; não altera o sistema de temas de produção."""

import re

C = {
    "bg": "#071525",
    "side": "#091B30",
    "panel": "#10243B",
    "field": "#142C47",
    "border": "#254362",
    "text": "#EAF2FF",
    "muted": "#A5BCD5",
    "discrete": "#718DA9",
    "green": "#00B889",
    "turquoise": "#2ED9BA",
    "blue": "#3B91FF",
    "cyan": "#38BDF8",
    "yellow": "#F5B942",
    "purple": "#A477F5",
    "red": "#F05264",
    "alternate": "#172E48",
    "panel_gradient": "#0B1D31",
    "hover": "#1C3C59",
    "primary_start": "#00A98B",
    "primary_end": "#00846E",
    "query": "#0763D5",
    "query_border": "#237EE5",
    "primary_hover": "#00A585",
    "danger": "#5F2535",
    "danger_border": "#A33B50",
    "danger_hover": "#883347",
    "active_start": "#00675C",
    "active_end": "#00443F",
    "active_border": "#008C79",
    "disabled": "#102035",
    "disabled_border": "#1D324A",
    "selected": "#00564F",
    "scroll_handle": "#365878",
    "hero": "#052431",
    "card_end": "#08182B",
    "table_bg": "#09192B",
    "progress_track": "#22384B",
    "edit": "#174D80",
    "edit_border": "#2B69A8",
    "delete": "#A42C3D",
    "delete_border": "#C54A54",
}

TIPOGRAFIA = dict(
    titulo=32, painel=18, valor=30, rotulo=12, tabela=13, controle=13, auxiliar=12
)
ESPACOS = dict(margem=20, painel=16, intervalo=12, raio=12)


def estilo(modelo):
    """Resolve tokens sem tratar as chaves de QSS como formatação Python."""
    return re.sub(r"@([a-z_]+)@", lambda m: C[m[1]], modelo)


ESTILO = estilo(
    '\nQWidget { color:@text@; font-family:"FONTE"; font-size:13px; }\nQLabel, QScrollArea, QScrollArea>QWidget>QWidget { background:transparent; }\nQScrollArea { border:0; }\nQFrame[panel="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 @panel_gradient@,stop:1 @bg@); border:1px solid @border@; border-radius:12px; }\nQPushButton { background:@field@; border:1px solid @border@; border-radius:8px; padding:8px 12px; font-weight:600; }\nQPushButton:hover { background:@hover@; border-color:@blue@; }\nQPushButton:focus, QComboBox:focus, QTableWidget:focus { border:2px solid @turquoise@; }\nQPushButton[primary="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 @primary_start@,stop:1 @primary_end@); border-color:@green@; }\nQPushButton[query="true"] { background:@query@; border-color:@query_border@; }\nQPushButton[primary="true"]:hover { background:@primary_hover@; }\nQPushButton[danger="true"] { background:@danger@; border-color:@danger_border@; }\nQPushButton[danger="true"]:hover { background:@danger_hover@; }\nQPushButton[nav="true"] { text-align:left; padding:16px 15px; background:transparent; border-color:transparent; font-size:11pt; }\nQPushButton[active="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 @active_start@,stop:1 @active_end@); border-color:@active_border@; }\nQPushButton:disabled { color:@discrete@; background:@disabled@; border-color:@disabled_border@; }\nQComboBox { background:@field@; border:1px solid @border@; border-radius:6px; padding:7px 8px; min-height:18px; }\nQComboBox QAbstractItemView { background:@field@; selection-background-color:@selected@; }\nQCheckBox { spacing:6px; background:transparent; }\nQCheckBox::indicator { width:15px; height:15px; border:1px solid @discrete@; border-radius:3px; background:@field@; }\nQCheckBox::indicator:checked { background:@green@; border:2px solid @turquoise@; }\nQTableWidget { background:@table_bg@; alternate-background-color:@alternate@; border:1px solid @border@; border-radius:6px; gridline-color:@border@; selection-background-color:@selected@; }\nQTableWidget::item { padding:5px; border:0; }\nQHeaderView::section { background:@field@; color:@muted@; padding:8px 4px; border:0; font-weight:600; }\nQScrollBar:vertical { background:@side@; width:8px; margin:0; }\nQScrollBar::handle:vertical { background:@scroll_handle@; border-radius:4px; min-height:30px; }\nQScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }\nQScrollBar:horizontal { background:@side@; height:8px; }\nQScrollBar::handle:horizontal { background:@scroll_handle@; min-width:30px; }\nQScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }\nQToolTip { color:@text@; background:@field@; border:1px solid @border@; padding:9px; }\nQMessageBox, QDialog { background:@side@; }\n\nQPushButton:pressed { background:@selected@; border-color:@turquoise@; }\n\nQPushButton[nav="true"]:pressed { background:@active_start@; }\nQPushButton[day="true"] { padding:5px; min-height:18px; font-size:12px; }\nQPushButton[day="true"][active="true"] { color:@turquoise@; border-color:@green@; }\n'
)
