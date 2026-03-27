"""
Aplicativo de Medição de Camada — Jateamento e Pintura Industrial
Migrado de PySide6 para Flet (Material Design / Fluent UI estilo Windows 11)
Redesign v3.0 — interface moderna com glassmorphism, animações e indicadores visuais
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Callable

import flet as ft

from ble import BleNotifier
from repo import Repo
from exporter import export_measurement_to_excel

# ---------------------------------------------------------------------------
# Constantes e Regex
# ---------------------------------------------------------------------------

_RX = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*(?:u[mM]|µm)\b")
RE_OPERADOR = re.compile(r"^Z\d{3}[A-Z0-9]{4}$")
RE_SERIE = re.compile(r"^\d{10}$")
RE_PROJETO = re.compile(r"^[A-Z]{3}\d{4}$")

POSTOS = [
    ("FUNDO", "Pintura - Fundo"),
    ("ACAB", "Pintura - Acabamento"),
    ("JAT", "Jateamento"),
]

BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Paleta de cores — tema escuro profissional aprimorado
# ---------------------------------------------------------------------------
CLR_BG           = "#080b12"        # fundo principal mais profundo
CLR_SURFACE      = "#111827"        # cards / painéis
CLR_SURFACE2     = "#1c2336"        # superfície levemente elevada
CLR_SURFACE3     = "#243047"        # terceiro nível — campos focados
CLR_BORDER       = "#2a3452"        # bordas suaves
CLR_BORDER_LIGHT = "#374166"        # borda mais visível
CLR_PRIMARY      = "#4f8ef7"        # azul principal
CLR_PRIMARY_H    = "#3b7de8"        # azul hover
CLR_PRIMARY_GLOW = "#4f8ef722"      # brilho azul para sombras
CLR_SUCCESS      = "#22c55e"        # verde
CLR_SUCCESS_H    = "#16a34a"
CLR_SUCCESS_DIM  = "#14532d"        # fundo badge verde
CLR_DANGER       = "#f05252"        # vermelho
CLR_DANGER_H     = "#dc2626"
CLR_DANGER_DIM   = "#7f1d1d"        # fundo badge vermelho
CLR_WARNING      = "#f59e0b"        # amarelo
CLR_WARNING_DIM  = "#451a03"
CLR_TEXT         = "#e8edf5"        # texto principal
CLR_TEXT_MUTED   = "#8a9abf"        # texto secundário
CLR_TEXT_DIM     = "#4a5578"        # texto muito suave
CLR_ACCENT       = "#818cf8"        # roxo
CLR_ACCENT_DIM   = "#312e81"
CLR_ROW_ALT      = "#131b2e"        # linhas alternadas
CLR_SIDEBAR      = "#0c1020"        # fundo da sidebar
CLR_SIDEBAR_ITEM = "#1a2240"        # item ativo na sidebar
CLR_PURPLE       = "#7c3aed"
CLR_PURPLE_H     = "#6d28d9"

# Sombras
SHADOW = [ft.BoxShadow(
    spread_radius=0, blur_radius=24,
    color="#33000000", offset=ft.Offset(0, 4)
)]
SHADOW_SM = [ft.BoxShadow(
    spread_radius=0, blur_radius=10,
    color="#22000000", offset=ft.Offset(0, 2)
)]
SHADOW_GLOW = [ft.BoxShadow(
    spread_radius=0, blur_radius=20,
    color=CLR_PRIMARY_GLOW, offset=ft.Offset(0, 0)
)]

# Grupos de medição com faixas e cores
MEASURE_GROUPS = [
    (1,  6,  "Topo",      "#4f8ef7", "#1a2d5a"),
    (7,  15, "Frente 1",  "#22c55e", "#0f3320"),
    (16, 24, "Frente 2",  "#a855f7", "#2d1459"),
    (25, 32, "Lateral 1", "#f59e0b", "#3d2a05"),
    (33, 40, "Lateral 2", "#f05252", "#3d1212"),
    (41, 46, "Fundo",     "#818cf8", "#1e1d4a"),
]


# ---------------------------------------------------------------------------
# Utilitários de UI
# ---------------------------------------------------------------------------

def _card(content: ft.Control, padding: int = 20) -> ft.Container:
    """Container com visual de card elevado."""
    return ft.Container(
        content=content,
        bgcolor=CLR_SURFACE,
        border_radius=14,
        padding=padding,
        border=ft.border.all(1, CLR_BORDER),
        shadow=SHADOW,
    )


def _glass_card(content: ft.Control, padding: int = 20) -> ft.Container:
    """Card com estilo glassmorphism sutil."""
    return ft.Container(
        content=content,
        bgcolor=CLR_SURFACE,
        border_radius=14,
        padding=padding,
        border=ft.border.all(1, CLR_BORDER_LIGHT),
        shadow=SHADOW,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[CLR_SURFACE, "#0f1525"],
        ),
    )


def _btn(
    label: str,
    on_click: Callable,
    color: str = CLR_PRIMARY,
    hover_color: str = CLR_PRIMARY_H,
    icon: str | None = None,
    disabled: bool = False,
    expand: bool = False,
    tooltip: str | None = None,
) -> ft.Container:
    """Botão estilizado com hover effect e tooltip opcional."""
    btn_ref = ft.Ref[ft.Container]()

    def _hover(e: ft.HoverEvent) -> None:
        btn_ref.current.bgcolor = hover_color if e.data == "true" else color
        btn_ref.current.update()

    row_children: list[ft.Control] = []
    if icon:
        row_children.append(ft.Icon(icon, color=CLR_TEXT, size=15))
        row_children.append(ft.Container(width=6))
    row_children.append(ft.Text(label, color=CLR_TEXT, size=13, weight=ft.FontWeight.W_600))

    return ft.Container(
        ref=btn_ref,
        content=ft.Row(row_children, alignment=ft.MainAxisAlignment.CENTER, spacing=0),
        bgcolor=color if not disabled else "#2a2f45",
        border_radius=9,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        on_click=on_click if not disabled else None,
        on_hover=_hover if not disabled else None,
        animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
        expand=expand,
        opacity=0.45 if disabled else 1.0,
        tooltip=tooltip,
    )


def _label(text: str, size: int = 13, muted: bool = False, bold: bool = False) -> ft.Text:
    return ft.Text(
        text,
        size=size,
        color=CLR_TEXT_MUTED if muted else CLR_TEXT,
        weight=ft.FontWeight.W_600 if bold else ft.FontWeight.NORMAL,
    )


def _field(
    hint: str,
    value: str = "",
    width: int | None = None,
    on_change: Callable | None = None,
    read_only: bool = False,
    multiline: bool = False,
    min_lines: int = 1,
    max_lines: int = 1,
    expand: bool = False,
) -> ft.TextField:
    return ft.TextField(
        value=value,
        hint_text=hint,
        hint_style=ft.TextStyle(color=CLR_TEXT_DIM, size=12),
        text_style=ft.TextStyle(color=CLR_TEXT, size=13),
        border_color=CLR_BORDER,
        focused_border_color=CLR_PRIMARY,
        border_radius=9,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        filled=True,
        fill_color=CLR_SURFACE2,
        cursor_color=CLR_PRIMARY,
        width=width,
        on_change=on_change,
        read_only=read_only,
        multiline=multiline,
        min_lines=min_lines,
        max_lines=max_lines,
        expand=expand,
    )


def _dropdown(
    options: list[tuple[str, str]],
    hint: str = "Selecione...",
    value: str | None = None,
    on_change: Callable | None = None,
    width: int | None = None,
    expand: bool = False,
) -> ft.Dropdown:
    return ft.Dropdown(
        options=[ft.dropdown.Option(key=k, text=v) for k, v in options],
        hint_text=hint,
        hint_style=ft.TextStyle(color=CLR_TEXT_DIM, size=12),
        text_style=ft.TextStyle(color=CLR_TEXT, size=13),
        border_color=CLR_BORDER,
        focused_border_color=CLR_PRIMARY,
        border_radius=9,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=8),
        filled=True,
        fill_color=CLR_SURFACE2,
        value=value,
        on_select=on_change,
        width=width,
        expand=expand,
    )


def _section_title(text: str) -> ft.Text:
    return ft.Text(text, size=17, weight=ft.FontWeight.W_700, color=CLR_TEXT)


def _divider() -> ft.Divider:
    return ft.Divider(height=1, color=CLR_BORDER, thickness=1)


def _snack(page: ft.Page, message: str, color: str = CLR_SUCCESS) -> None:
    """Mostra uma snack bar estilizada."""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(
                ft.Icons.CHECK_CIRCLE_OUTLINE if color == CLR_SUCCESS
                else ft.Icons.WARNING_AMBER_OUTLINED if color == CLR_WARNING
                else ft.Icons.ERROR_OUTLINE if color == CLR_DANGER
                else ft.Icons.INFO_OUTLINE,
                color=CLR_TEXT,
                size=18,
            ),
            ft.Container(width=8),
            ft.Text(message, color=CLR_TEXT, size=13),
        ]),
        bgcolor=color,
        duration=3000,
        behavior=ft.SnackBarBehavior.FLOATING,
        show_close_icon=True,
        close_icon_color=CLR_TEXT,
    )
    page.snack_bar.open = True
    page.update()


def _image_for_measure(measure_number: int) -> str:
    """Retorna o caminho da imagem para a medição dada."""
    if 1 <= measure_number <= 6:
        return str(BASE_DIR / "Images" / "Topo.png")
    if 7 <= measure_number <= 15:
        return str(BASE_DIR / "Images" / "Frente 1.png")
    if 16 <= measure_number <= 24:
        return str(BASE_DIR / "Images" / "Frente 2.png")
    if 25 <= measure_number <= 32:
        return str(BASE_DIR / "Images" / "Lateral 1.png")
    if 33 <= measure_number <= 40:
        return str(BASE_DIR / "Images" / "Lateral 2.png")
    return str(BASE_DIR / "Images" / "Fundo.png")


def _get_group_for_measure(n: int) -> tuple[str, str, str]:
    """Retorna (nome, cor_texto, cor_fundo) do grupo da medição n."""
    for lo, hi, name, clr, bg in MEASURE_GROUPS:
        if lo <= n <= hi:
            return name, clr, bg
    return "Geral", CLR_TEXT_MUTED, CLR_SURFACE2


def _stat_card(
    label: str,
    value: str,
    icon: str,
    icon_color: str,
    bg_color: str,
    width: int = 160,
) -> ft.Container:
    """Card de estatística compacto para o dashboard."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, color=icon_color, size=20),
                    bgcolor=bg_color,
                    border_radius=10,
                    padding=10,
                    width=44,
                    height=44,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(width=12),
                ft.Column(
                    [
                        ft.Text(value, size=20, weight=ft.FontWeight.W_700, color=CLR_TEXT),
                        ft.Text(label, size=11, color=CLR_TEXT_MUTED),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor=CLR_SURFACE,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.border.all(1, CLR_BORDER),
        shadow=SHADOW_SM,
        width=width,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )


def _progress_bar_section(filled: int, total: int = 46) -> ft.Container:
    """Barra de progresso das medições com label e porcentagem."""
    pct = filled / total if total > 0 else 0.0
    color = CLR_SUCCESS if filled == total else CLR_PRIMARY if filled > 0 else CLR_BORDER
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            f"Progresso das medições",
                            size=12,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"{filled} / {total}",
                            size=12,
                            color=CLR_TEXT,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Container(width=6),
                        ft.Container(
                            content=ft.Text(
                                f"{int(pct * 100)}%",
                                size=11,
                                color=color,
                                weight=ft.FontWeight.W_700,
                            ),
                            bgcolor=CLR_SURFACE2,
                            border_radius=6,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=6),
                ft.Container(
                    content=ft.Container(
                        width=None,
                        height=6,
                        bgcolor=color,
                        border_radius=3,
                        animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
                    ),
                    bgcolor=CLR_SURFACE2,
                    border_radius=3,
                    height=6,
                    expand=True,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ],
            spacing=0,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor=CLR_SURFACE,
        border_radius=ft.BorderRadius(0, 0, 12, 12),
        border=ft.border.only(
            left=ft.BorderSide(1, CLR_BORDER),
            right=ft.BorderSide(1, CLR_BORDER),
            bottom=ft.BorderSide(1, CLR_BORDER),
        ),
    )


# ---------------------------------------------------------------------------
# Componente: Sidebar modernizada
# ---------------------------------------------------------------------------

class Sidebar:
    ITEMS = [
        ("overview", ft.Icons.DASHBOARD_OUTLINED,   "Medições Pendentes"),
        ("newedit",  ft.Icons.ADD_CIRCLE_OUTLINE,    "Nova Medição"),
        ("batch",    ft.Icons.FILE_UPLOAD_OUTLINED,  "Exportar Lote"),
        ("history",  ft.Icons.HISTORY,               "Histórico"),
    ]

    def __init__(self, on_navigate: Callable[[str], None]) -> None:
        self.on_navigate = on_navigate
        self._active_route = "overview"
        self._item_containers: dict[str, ft.Container] = {}
        self._badge_text: ft.Text | None = None
        self._controls = self._build()

    def _build(self) -> ft.Container:
        # Logo premium com gradiente
        logo_icon = ft.Container(
            content=ft.Stack(
                [
                    ft.Container(
                        width=44,
                        height=44,
                        border_radius=12,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(-1, -1),
                            end=ft.Alignment(1, 1),
                            colors=["#4f8ef7", "#7c3aed"],
                        ),
                        shadow=SHADOW_GLOW,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.Icons.LAYERS_OUTLINED, color=CLR_TEXT, size=22),
                        width=44,
                        height=44,
                        alignment=ft.Alignment(0, 0),
                    ),
                ],
                width=44,
                height=44,
            ),
        )

        header = ft.Container(
            content=ft.Column(
                [
                    logo_icon,
                    ft.Container(height=10),
                    ft.Text(
                        "Jato & Pintura",
                        color=CLR_TEXT,
                        size=14,
                        weight=ft.FontWeight.W_800,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Medição de Camada",
                        color=CLR_TEXT_MUTED,
                        size=10,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Text("v3.0", size=9, color=CLR_TEXT_DIM),
                        bgcolor=CLR_SURFACE2,
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=24),
            alignment=ft.Alignment(0, 0),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=[CLR_SIDEBAR, "#10142a"],
            ),
        )

        section_label = ft.Container(
            content=ft.Text("NAVEGAÇÃO", size=9, color=CLR_TEXT_DIM, weight=ft.FontWeight.W_700, style=ft.TextStyle(letter_spacing=1.5)),
            padding=ft.padding.only(left=20, top=12, bottom=6),
        )

        items = ft.Column(
            [self._nav_item(route, icon, label) for route, icon, label in self.ITEMS],
            spacing=3,
        )

        footer = ft.Container(
            content=ft.Column(
                [
                    _divider(),
                    ft.Container(height=8),
                    ft.Row(
                        [
                            ft.Container(
                                width=8, height=8,
                                bgcolor=CLR_TEXT_DIM,
                                border_radius=4,
                            ),
                            ft.Text("Sistema offline-first", size=10, color=CLR_TEXT_DIM),
                        ],
                        spacing=6,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(height=8),
                ],
                spacing=0,
            ),
            padding=ft.padding.symmetric(horizontal=12),
        )

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    _divider(),
                    ft.Container(height=4),
                    section_label,
                    items,
                    ft.Container(expand=True),
                    footer,
                ],
                spacing=0,
                expand=True,
            ),
            bgcolor=CLR_SIDEBAR,
            width=220,
            border=ft.border.only(right=ft.BorderSide(1, CLR_BORDER)),
            expand=False,
        )

    def _nav_item(self, route: str, icon: str, label: str) -> ft.Container:
        is_active = route == self._active_route
        item_ref = ft.Ref[ft.Container]()

        # Badge de contagem — só para "overview"
        badge: ft.Control = ft.Container(width=0)
        if route == "overview":
            self._badge_text = ft.Text(
                "0",
                size=10,
                color=CLR_TEXT,
                weight=ft.FontWeight.W_700,
            )
            badge = ft.Container(
                content=self._badge_text,
                bgcolor=CLR_PRIMARY,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=6, vertical=1),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
                visible=False,
            )
            self._badge_container = badge

        def _hover(e: ft.HoverEvent) -> None:
            if route != self._active_route:
                item_ref.current.bgcolor = CLR_SURFACE2 if e.data == "true" else "transparent"
                item_ref.current.update()

        def _click(_e: ft.ControlEvent) -> None:
            self.set_active(route)
            self.on_navigate(route)

        # Indicador lateral ativo (barra esquerda estilo VS Code)
        active_bar = ft.Container(
            width=3,
            height=28,
            bgcolor=CLR_PRIMARY if is_active else "transparent",
            border_radius=ft.BorderRadius(0, 2, 2, 0),
            animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
        )

        icon_ctrl = ft.Icon(
            icon,
            color=CLR_PRIMARY if is_active else CLR_TEXT_MUTED,
            size=19,
        )
        label_ctrl = ft.Text(
            label,
            color=CLR_TEXT if is_active else CLR_TEXT_MUTED,
            size=13,
            weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL,
        )

        row_content = ft.Row(
            [
                active_bar,
                ft.Container(width=10),
                icon_ctrl,
                ft.Container(width=10),
                label_ctrl,
                ft.Container(expand=True),
                badge,
                ft.Container(width=10),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        c = ft.Container(
            ref=item_ref,
            content=row_content,
            bgcolor=CLR_SIDEBAR_ITEM if is_active else "transparent",
            border_radius=ft.BorderRadius(0, 8, 8, 0),
            padding=ft.padding.symmetric(vertical=10),
            on_click=_click,
            on_hover=_hover,
            animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
            margin=ft.margin.only(right=12),
            tooltip=label,
        )
        self._item_containers[route] = c
        return c

    def set_active(self, route: str) -> None:
        for r, c in self._item_containers.items():
            is_active = r == route
            c.bgcolor = CLR_SIDEBAR_ITEM if is_active else "transparent"
            row: ft.Row = c.content
            # active_bar está em row.controls[0]
            row.controls[0].bgcolor = CLR_PRIMARY if is_active else "transparent"
            # icon em controls[2]
            row.controls[2].color = CLR_PRIMARY if is_active else CLR_TEXT_MUTED
            # label em controls[4]
            row.controls[4].color = CLR_TEXT if is_active else CLR_TEXT_MUTED
            row.controls[4].weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL
        self._active_route = route

    def set_pending_count(self, count: int) -> None:
        """Atualiza o badge de contagem de pendentes."""
        if self._badge_text and self._badge_container:
            self._badge_text.value = str(count)
            self._badge_container.visible = count > 0
            try:
                self._badge_container.update()
            except Exception:
                pass

    @property
    def control(self) -> ft.Container:
        return self._controls


# ---------------------------------------------------------------------------
# Componente: Status Bar modernizada
# ---------------------------------------------------------------------------

class StatusBar:
    def __init__(self) -> None:
        self._ble_dot = ft.Container(
            width=8, height=8,
            bgcolor=CLR_DANGER,
            border_radius=4,
            animate=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        )
        self._ble_text = ft.Text("BLE: Desconectado", color=CLR_TEXT_MUTED, size=11)
        self._msg = ft.Text("", color=CLR_TEXT_MUTED, size=11, expand=True)
        self._pending_text = ft.Text("", color=CLR_TEXT_DIM, size=11)

        self.control = ft.Container(
            content=ft.Row(
                [
                    self._ble_dot,
                    self._ble_text,
                    ft.Container(
                        width=1, height=12,
                        bgcolor=CLR_BORDER,
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Icon(ft.Icons.PENDING_ACTIONS_OUTLINED, color=CLR_TEXT_DIM, size=13),
                    ft.Container(width=4),
                    self._pending_text,
                    ft.Container(
                        width=1, height=12,
                        bgcolor=CLR_BORDER,
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    self._msg,
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.BOLT, color=CLR_PRIMARY, size=11),
                                ft.Text("v3.0 · Flet", color=CLR_TEXT_DIM, size=10),
                            ],
                            spacing=3,
                        ),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=CLR_SIDEBAR,
            border=ft.border.only(top=ft.BorderSide(1, CLR_BORDER)),
            padding=ft.padding.symmetric(horizontal=18, vertical=7),
        )

    def set_ble(self, connected: bool, text: str = "") -> None:
        self._ble_dot.bgcolor = CLR_SUCCESS if connected else CLR_DANGER
        self._ble_text.value = f"BLE: {text or ('Conectado' if connected else 'Desconectado')}"
        self._ble_text.color = CLR_SUCCESS if connected else CLR_TEXT_MUTED
        try:
            self._ble_dot.update()
            self._ble_text.update()
        except Exception:
            pass

    def set_message(self, text: str) -> None:
        self._msg.value = text
        try:
            self._msg.update()
        except Exception:
            pass

    def set_pending(self, count: int) -> None:
        self._pending_text.value = f"{count} pendente{'s' if count != 1 else ''}"
        try:
            self._pending_text.update()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tela: Overview (Medições Pendentes)
# ---------------------------------------------------------------------------

class OverviewPage:
    def __init__(
        self,
        page: ft.Page,
        repo: Repo,
        status_bar: StatusBar,
        navigate: Callable[[str], None],
        go_batch: Callable[[list[int]], None],
        sidebar: "Sidebar | None" = None,
    ) -> None:
        self.page = page
        self.repo = repo
        self.status_bar = status_bar
        self.navigate = navigate
        self.go_batch = go_batch
        self.sidebar = sidebar

        self._checked: dict[int, bool] = {}
        self._row_ids: list[int] = []

        # Stat cards
        self._stat_total = ft.Text("0", size=22, weight=ft.FontWeight.W_700, color=CLR_TEXT)
        self._stat_fundo = ft.Text("0", size=22, weight=ft.FontWeight.W_700, color="#4f8ef7")
        self._stat_acab  = ft.Text("0", size=22, weight=ft.FontWeight.W_700, color=CLR_SUCCESS)
        self._stat_jat   = ft.Text("0", size=22, weight=ft.FontWeight.W_700, color=CLR_WARNING)

        self._table_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

        self.control = self._build()
        self.refresh()

    def _make_stat_mini(self, value_ctrl: ft.Text, label: str, icon: str, icon_bg: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, color=CLR_TEXT, size=18),
                        bgcolor=icon_bg,
                        border_radius=8,
                        padding=8,
                        width=38,
                        height=38,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(width=10),
                    ft.Column(
                        [value_ctrl, ft.Text(label, size=10, color=CLR_TEXT_MUTED)],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW_SM,
            expand=True,
        )

    def _build(self) -> ft.Column:
        # Stats bar
        stats_row = ft.Row(
            [
                self._make_stat_mini(self._stat_total, "Total pendentes", ft.Icons.INBOX_OUTLINED, "#1e3a6e"),
                ft.Container(width=8),
                self._make_stat_mini(self._stat_fundo, "Pintura Fundo",   ft.Icons.FORMAT_PAINT_OUTLINED, "#1e3a5f"),
                ft.Container(width=8),
                self._make_stat_mini(self._stat_acab,  "Pintura Acab.",   ft.Icons.BRUSH_OUTLINED,        "#14532d"),
                ft.Container(width=8),
                self._make_stat_mini(self._stat_jat,   "Jateamento",      ft.Icons.GRAIN_OUTLINED,        "#451a03"),
            ],
            expand=True,
        )

        title_row = ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.DASHBOARD_OUTLINED, color="#4f8ef7", size=20),
                    bgcolor="#1a2d5a",
                    border_radius=8,
                    padding=8,
                    width=36,
                    height=36,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(width=10),
                _section_title("Medições Pendentes"),
                ft.Container(expand=True),
                _btn(
                    "Nova Medição",
                    self._on_new,
                    icon=ft.Icons.ADD,
                    tooltip="Criar nova medição (N)",
                ),
                ft.Container(width=8),
                _btn(
                    "Atribuir / Exportar",
                    self._on_batch,
                    color=CLR_PURPLE,
                    hover_color=CLR_PURPLE_H,
                    icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                    tooltip="Selecione 5 medições para exportar em lote",
                ),
                ft.Container(width=8),
                _btn(
                    "Excluir",
                    self._on_delete,
                    color=CLR_DANGER,
                    hover_color=CLR_DANGER_H,
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Excluir medição selecionada",
                ),
                ft.Container(width=8),
                _btn(
                    "Atualizar",
                    self._on_refresh,
                    color=CLR_SURFACE2,
                    hover_color=CLR_BORDER,
                    icon=ft.Icons.REFRESH,
                    tooltip="Recarregar lista",
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            spacing=0,
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=40,
                        content=ft.Text("", size=12),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text("Data/Hora", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text("Operador", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text("Projeto", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text("Nº de Série", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=1,
                        content=ft.Text("Posto", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                ],
                spacing=8,
            ),
            bgcolor=CLR_SURFACE2,
            padding=ft.padding.symmetric(horizontal=16, vertical=9),
            border_radius=ft.BorderRadius(10, 10, 0, 0),
            border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
        )

        table_wrapper = ft.Container(
            content=ft.Column([header, self._table_col], spacing=0),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            border=ft.border.all(1, CLR_BORDER),
            expand=True,
            shadow=SHADOW,
        )

        return ft.Column(
            [
                _card(title_row, padding=14),
                ft.Container(height=12),
                stats_row,
                ft.Container(height=12),
                table_wrapper,
            ],
            expand=True,
            spacing=0,
        )

    def _make_row(self, m, alt: bool) -> ft.Container:
        row_id = m.id
        row_ref = ft.Ref[ft.Container]()
        base_color = CLR_ROW_ALT if alt else CLR_SURFACE

        chk = ft.Checkbox(
            value=self._checked.get(row_id, False),
            fill_color={
                ft.ControlState.SELECTED: CLR_PRIMARY,
                ft.ControlState.DEFAULT: "transparent",
            },
            check_color=CLR_TEXT,
            on_change=lambda e, rid=row_id: self._on_check(rid, e.control.value),
        )

        posto_styles = {
            "FUNDO": ("#4f8ef7", "#1a2d5a"),
            "ACAB":  ("#22c55e", "#0f3320"),
            "JAT":   ("#f59e0b", "#3d2a05"),
        }
        fc, bc = posto_styles.get(m.posto, (CLR_TEXT_MUTED, CLR_SURFACE2))
        posto_badge = ft.Container(
            content=ft.Text(m.posto, size=11, color=fc, weight=ft.FontWeight.W_700),
            bgcolor=bc,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border=ft.border.all(1, fc + "33"),
        )

        def _row_hover(e: ft.HoverEvent) -> None:
            row_ref.current.bgcolor = "#1e2a44" if e.data == "true" else base_color
            row_ref.current.update()

        return ft.Container(
            ref=row_ref,
            content=ft.Row(
                [
                    ft.Container(width=40, content=chk),
                    ft.Container(
                        expand=2,
                        content=ft.Text(m.created_at, size=12, color=CLR_TEXT),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(m.operador, size=12, color=CLR_TEXT),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            m.projeto or "—",
                            size=12,
                            color=CLR_TEXT_MUTED if not m.projeto else CLR_TEXT,
                        ),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            m.serie or "—",
                            size=12,
                            color=CLR_TEXT_MUTED if not m.serie else CLR_TEXT,
                        ),
                    ),
                    ft.Container(expand=1, content=posto_badge),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=base_color,
            padding=ft.padding.symmetric(horizontal=16, vertical=11),
            border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
            on_hover=_row_hover,
            animate=ft.Animation(120, ft.AnimationCurve.EASE_IN_OUT),
        )

    def refresh(self) -> None:
        items = self.repo.list_pending_all()
        self._row_ids = [m.id for m in items]
        current_ids = set(self._row_ids)
        self._checked = {k: v for k, v in self._checked.items() if k in current_ids}

        self._table_col.controls.clear()

        # Atualiza estatísticas
        count_fundo = sum(1 for m in items if m.posto == "FUNDO")
        count_acab  = sum(1 for m in items if m.posto == "ACAB")
        count_jat   = sum(1 for m in items if m.posto == "JAT")

        self._stat_total.value = str(len(items))
        self._stat_fundo.value = str(count_fundo)
        self._stat_acab.value  = str(count_acab)
        self._stat_jat.value   = str(count_jat)

        # Atualiza status bar e badge na sidebar
        self.status_bar.set_pending(len(items))
        if self.sidebar:
            self.sidebar.set_pending_count(len(items))

        if not items:
            self._table_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.INBOX_OUTLINED, color=CLR_TEXT_DIM, size=52),
                                bgcolor=CLR_SURFACE2,
                                border_radius=50,
                                padding=20,
                            ),
                            ft.Container(height=12),
                            ft.Text(
                                "Nenhuma medição pendente",
                                color=CLR_TEXT_MUTED,
                                size=15,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "Clique em 'Nova Medição' para começar",
                                color=CLR_TEXT_DIM,
                                size=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=50,
                )
            )
        else:
            for i, m in enumerate(items):
                self._table_col.controls.append(self._make_row(m, alt=i % 2 == 1))

        if self.page:
            try:
                self.page.update()
            except Exception:
                pass

    def _on_check(self, row_id: int, value: bool) -> None:
        self._checked[row_id] = value

    def _on_new(self, _e: ft.ControlEvent) -> None:
        self.navigate("newedit")

    def _on_batch(self, _e: ft.ControlEvent) -> None:
        ids = [rid for rid, v in self._checked.items() if v]
        if len(ids) != 5:
            _snack(
                self.page,
                f"Selecione exatamente 5 medições (selecionadas: {len(ids)}).",
                CLR_WARNING,
            )
            return
        self.go_batch(ids)

    def _on_delete(self, _e: ft.ControlEvent) -> None:
        ids = [rid for rid, v in self._checked.items() if v]
        if not ids:
            _snack(self.page, "Marque (checkbox) uma medição para excluir.", CLR_WARNING)
            return
        id_ = ids[0]
        _show_confirm_dialog(
            self.page,
            title="Confirmar exclusão",
            message=f"Excluir a medição ID {id_}? Esta ação não pode ser desfeita.",
            on_confirm=lambda: self._do_delete(id_),
        )

    def _do_delete(self, id_: int) -> None:
        self.repo.delete_measurement(id_)
        self._checked.pop(id_, None)
        self.refresh()
        _snack(self.page, "Medição excluída com sucesso.", CLR_SUCCESS)

    def _on_refresh(self, _e: ft.ControlEvent) -> None:
        self.refresh()
        _snack(self.page, "Lista atualizada.", CLR_PRIMARY)


# ---------------------------------------------------------------------------
# Tela: Nova Medição
# ---------------------------------------------------------------------------

class NewEditPage:
    def __init__(
        self,
        page: ft.Page,
        repo: Repo,
        status_bar: StatusBar,
        navigate: Callable[[str], None],
    ) -> None:
        self.page = page
        self.repo = repo
        self.status_bar = status_bar
        self.navigate = navigate

        self._ble: BleNotifier | None = None
        self._next_index: int = 0
        self._override_index: int | None = None
        self._warned_operator_empty: bool = False
        self._warned_posto_empty: bool = False
        self._current_img_path: str | None = None
        self._ble_running: bool = False

        self._dd_posto = _dropdown(POSTOS, hint="Selecione o posto...", on_change=self._on_posto_change)
        self._tf_projeto  = _field("Projeto (ex: SEF0500)",     on_change=self._validate_field_projeto)
        self._tf_serie    = _field("Número de Série (10 dígitos)", on_change=self._validate_field_serie)
        self._tf_operador = _field("Operador (ex: Z0052DFZ)",   on_change=self._validate_field_operador)

        self._tf_mac  = _field("MAC Address", value="24:5D:FC:00:B3:2E")
        self._tf_uuid = _field("UUID Notify", value="06d1e5e7-79ad-4a71-8faa-373789f7d93c")

        self._tf_log = _field(
            "", read_only=True, multiline=True,
            min_lines=3, max_lines=5, expand=True,
        )
        self._tf_log.bgcolor = "#060912"
        self._tf_log.text_style = ft.TextStyle(
            color="#4ade80", size=11, font_family="Consolas"
        )

        # Controles de progresso
        self._progress_filled = ft.Text(
            "0", size=22, weight=ft.FontWeight.W_800, color=CLR_TEXT
        )
        self._progress_bar_fill = ft.Container(
            width=0,
            height=6,
            bgcolor=CLR_PRIMARY,
            border_radius=3,
            animate=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
        )
        self._group_indicator = ft.Text(
            "Topo (M01-M06)",
            size=11,
            color="#4f8ef7",
            weight=ft.FontWeight.W_600,
        )

        # Indicadores de grupo (chips)
        self._group_chips: dict[str, ft.Container] = {}
        self._group_chips_row = self._build_group_chips()

        # Campos de medição
        self._measure_fields: list[ft.TextField] = []
        self._measure_containers: list[ft.Container] = []
        for i in range(46):
            _, grp_color, grp_bg = _get_group_for_measure(i + 1)

            tf = ft.TextField(
                value="",
                hint_text="—",
                hint_style=ft.TextStyle(color=CLR_TEXT_DIM, size=12),
                text_style=ft.TextStyle(
                    color=CLR_TEXT, size=12, weight=ft.FontWeight.W_700
                ),
                text_align=ft.TextAlign.CENTER,
                border_color=CLR_BORDER,
                focused_border_color=CLR_PRIMARY,
                border_radius=6,
                content_padding=ft.padding.symmetric(horizontal=4, vertical=7),
                filled=True,
                fill_color=CLR_SURFACE2,
                cursor_color=CLR_PRIMARY,
                expand=True,
                on_focus=lambda e, idx=i: self._on_field_focus(idx),
            )
            self._measure_fields.append(tf)

            lbl = ft.Text(
                f"M{i+1:02d}",
                size=9,
                color=grp_color,
                weight=ft.FontWeight.W_700,
            )
            c = ft.Container(
                content=ft.Column(
                    [lbl, tf],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=CLR_SURFACE2,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=4, vertical=5),
                border=ft.border.all(1, CLR_BORDER),
                animate=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
                expand=True,
            )
            self._measure_containers.append(c)

        self._img_ref = ft.Image(
            src=_image_for_measure(1),
            fit=ft.BoxFit.CONTAIN,
            expand=True,
        )
        self._img_label = ft.Text(
            "Topo (M01–M06)",
            size=11,
            color=CLR_TEXT_MUTED,
            text_align=ft.TextAlign.CENTER,
        )

        self._btn_start_ref = ft.Ref[ft.Container]()
        self._btn_stop_ref  = ft.Ref[ft.Container]()

        # Painel BLE e Dados colapsáveis
        self._ble_section_visible = True
        self._ble_section_ref = ft.Ref[ft.Column]()
        self._ble_toggle_icon = ft.Icon(ft.Icons.EXPAND_LESS, color=CLR_TEXT_MUTED, size=18)

        self.control = self._build()
        self._update_image(1)
        self._update_progress()

    def _build_group_chips(self) -> ft.Row:
        chips = []
        for lo, hi, name, color, bg in MEASURE_GROUPS:
            chip = ft.Container(
                content=ft.Text(name, size=10, color=color, weight=ft.FontWeight.W_600),
                bgcolor=bg,
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border=ft.border.all(1, color + "44"),
                opacity=0.4,
                animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            )
            self._group_chips[name] = chip
            chips.append(chip)
        return ft.Row(chips, spacing=6, wrap=True)

    def _update_group_chips(self, active_measure: int) -> None:
        for lo, hi, name, color, bg in MEASURE_GROUPS:
            chip = self._group_chips.get(name)
            if chip:
                chip.opacity = 1.0 if lo <= active_measure <= hi else 0.35
                try:
                    chip.update()
                except Exception:
                    pass

    def _update_progress(self) -> None:
        filled = sum(1 for f in self._measure_fields if f.value.strip())
        self._progress_filled.value = str(filled)
        # Atualiza a largura relativa via container pai
        try:
            self._progress_bar_fill.update()
        except Exception:
            pass

    def _build(self) -> ft.Column:
        topbar = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                    icon_color=CLR_TEXT_MUTED,
                    icon_size=16,
                    on_click=self._on_back,
                    tooltip="Voltar para Overview",
                ),
                ft.Container(width=6),
                ft.Container(
                    content=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color="#4f8ef7", size=18),
                    bgcolor="#1a2d5a",
                    border_radius=8,
                    padding=7,
                    width=34,
                    height=34,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(width=8),
                _section_title("Nova Medição"),
                ft.Container(expand=True),
                # Mini progresso no topbar
                ft.Container(
                    content=ft.Row(
                        [
                            self._progress_filled,
                            ft.Text(
                                " / 46 medições",
                                size=13,
                                color=CLR_TEXT_MUTED,
                                weight=ft.FontWeight.W_400,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.BASELINE,
                        spacing=0,
                    ),
                    bgcolor=CLR_SURFACE2,
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Barra de progresso expandida
        progress_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Progresso",
                                size=11,
                                color=CLR_TEXT_MUTED,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Container(expand=True),
                            self._group_indicator,
                        ],
                    ),
                    ft.Container(height=5),
                    ft.Container(
                        content=self._progress_bar_fill,
                        bgcolor=CLR_SURFACE2,
                        border_radius=3,
                        height=6,
                        expand=True,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Container(height=8),
                    self._group_chips_row,
                ],
                spacing=0,
            ),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW_SM,
        )

        header_card = _card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ASSIGNMENT_OUTLINED, color=CLR_PRIMARY, size=15),
                            ft.Text(
                                "Dados da Medição",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=CLR_TEXT,
                            ),
                        ],
                        spacing=8,
                    ),
                    _divider(),
                    ft.Container(height=6),
                    ft.ResponsiveRow(
                        [
                            ft.Column(
                                [_label("Posto"), ft.Container(height=3), self._dd_posto],
                                col={"xs": 12, "sm": 6, "md": 3},
                            ),
                            ft.Column(
                                [_label("Projeto"), ft.Container(height=3), self._tf_projeto],
                                col={"xs": 12, "sm": 6, "md": 3},
                            ),
                            ft.Column(
                                [_label("Número de Série"), ft.Container(height=3), self._tf_serie],
                                col={"xs": 12, "sm": 6, "md": 3},
                            ),
                            ft.Column(
                                [_label("Operador"), ft.Container(height=3), self._tf_operador],
                                col={"xs": 12, "sm": 6, "md": 3},
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=8,
            )
        )

        def _toggle_ble(_e: ft.ControlEvent) -> None:
            self._ble_section_visible = not self._ble_section_visible
            if self._ble_section_ref.current:
                self._ble_section_ref.current.visible = self._ble_section_visible
                self._ble_toggle_icon.name = (
                    ft.Icons.EXPAND_LESS if self._ble_section_visible
                    else ft.Icons.EXPAND_MORE
                )
                try:
                    self.page.update()
                except Exception:
                    pass

        ble_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.BLUETOOTH, color=CLR_ACCENT, size=15),
                            ft.Text(
                                "Conexão BLE",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=CLR_TEXT,
                            ),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Text(
                                            "Configurações",
                                            size=11,
                                            color=CLR_TEXT_MUTED,
                                        ),
                                        self._ble_toggle_icon,
                                    ],
                                    spacing=4,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                on_click=_toggle_ble,
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                on_hover=lambda e: None,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        ref=self._ble_section_ref,
                        controls=[
                            _divider(),
                            ft.Container(height=6),
                            ft.ResponsiveRow(
                                [
                                    ft.Column(
                                        [_label("MAC Address"), ft.Container(height=3), self._tf_mac],
                                        col={"xs": 12, "sm": 6},
                                    ),
                                    ft.Column(
                                        [_label("UUID Notify"), ft.Container(height=3), self._tf_uuid],
                                        col={"xs": 12, "sm": 6},
                                    ),
                                ],
                                spacing=12,
                            ),
                        ],
                        spacing=8,
                        visible=True,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=CLR_SURFACE,
            border_radius=14,
            padding=16,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW,
        )

        btn_start = ft.Container(
            ref=self._btn_start_ref,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINED, color=CLR_TEXT, size=15),
                    ft.Text("Conectar / Iniciar", color=CLR_TEXT, size=13, weight=ft.FontWeight.W_600),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=CLR_SUCCESS,
            border_radius=9,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            on_click=self._on_start,
            on_hover=lambda e: self._btn_hover(e, self._btn_start_ref, CLR_SUCCESS, CLR_SUCCESS_H),
            animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
            expand=True,
            tooltip="Conectar ao medidor BLE e iniciar captura",
        )
        btn_stop = ft.Container(
            ref=self._btn_stop_ref,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, color=CLR_TEXT, size=15),
                    ft.Text("Parar / Desconectar", color=CLR_TEXT, size=13, weight=ft.FontWeight.W_600),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#2a2f45",
            border_radius=9,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            on_click=None,
            on_hover=None,
            opacity=0.4,
            animate=ft.Animation(160, ft.AnimationCurve.EASE_IN_OUT),
            expand=True,
            tooltip="Parar captura e desconectar BLE",
        )

        actions_row = ft.Row(
            [
                btn_start,
                ft.Container(width=8),
                btn_stop,
                ft.Container(width=8),
                _btn(
                    "Limpar Selecionada",
                    self._on_clear_one,
                    color=CLR_SURFACE2,
                    hover_color=CLR_BORDER_LIGHT,
                    icon=ft.Icons.BACKSPACE_OUTLINED,
                    expand=True,
                    tooltip="Clique no campo de medição e depois neste botão para limpar",
                ),
                ft.Container(width=8),
                _btn(
                    "Limpar Tudo",
                    self._on_clear_all,
                    color=CLR_SURFACE2,
                    hover_color=CLR_BORDER_LIGHT,
                    icon=ft.Icons.CLEAR_ALL,
                    expand=True,
                    tooltip="Limpar todas as 46 medições",
                ),
                ft.Container(width=8),
                _btn(
                    "Salvar",
                    self._on_save,
                    color=CLR_PRIMARY,
                    hover_color=CLR_PRIMARY_H,
                    icon=ft.Icons.SAVE_OUTLINED,
                    expand=True,
                    tooltip="Salvar e voltar para lista de pendentes",
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        grid_controls = []
        for i in range(0, 46, 4):
            row_items = []
            for j in range(4):
                if i + j < 46:
                    row_items.append(
                        ft.Container(content=self._measure_containers[i + j], expand=True)
                    )
                else:
                    row_items.append(ft.Container(expand=True))
            grid_controls.append(ft.Row(row_items, spacing=6, expand=True))

        measures_grid = ft.Column(
            grid_controls,
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        image_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.IMAGE_OUTLINED, color=CLR_PRIMARY, size=13),
                            ft.Text(
                                "Referência Visual",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=CLR_TEXT,
                            ),
                        ],
                        spacing=6,
                    ),
                    _divider(),
                    ft.Container(height=4),
                    ft.Container(
                        content=self._img_ref,
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        border_radius=8,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        bgcolor=CLR_SURFACE2,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=self._img_label,
                        bgcolor=CLR_SURFACE2,
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        alignment=ft.Alignment(0, 0),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            padding=14,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW,
            width=255,
        )

        measures_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.GRID_VIEW_OUTLINED, color=CLR_PRIMARY, size=14),
                            ft.Text(
                                "Medições (M01–M46)",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=CLR_TEXT,
                            ),
                            ft.Container(expand=True),
                        ],
                        spacing=8,
                    ),
                    _divider(),
                    ft.Container(height=4),
                    measures_grid,
                ],
                spacing=6,
                expand=True,
            ),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            padding=14,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW,
            expand=True,
        )

        body_row = ft.Row(
            [
                measures_card,
                ft.Container(width=12),
                image_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        log_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TERMINAL, color=CLR_ACCENT, size=13),
                            ft.Text(
                                "Log BLE",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=CLR_TEXT,
                            ),
                            ft.Container(expand=True),
                            ft.Text("Console de depuração", size=10, color=CLR_TEXT_DIM),
                        ],
                        spacing=6,
                    ),
                    ft.Container(height=4),
                    self._tf_log,
                ],
                spacing=4,
            ),
            bgcolor="#060912",
            border_radius=12,
            padding=12,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW_SM,
        )

        return ft.Column(
            [
                _card(topbar, padding=12),
                ft.Container(height=10),
                progress_section,
                ft.Container(height=8),
                header_card,
                ft.Container(height=8),
                ble_card,
                ft.Container(height=8),
                _card(actions_row, padding=12),
                ft.Container(height=8),
                body_row,
                ft.Container(height=8),
                log_card,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )

    @staticmethod
    def _btn_hover(e: ft.HoverEvent, ref: ft.Ref, normal: str, hover: str) -> None:
        ref.current.bgcolor = hover if e.data == "true" else normal
        ref.current.update()

    def _highlight_field(self, index: int) -> None:
        for i, c in enumerate(self._measure_containers):
            if i == index:
                _, grp_color, _ = _get_group_for_measure(i + 1)
                c.bgcolor = CLR_SURFACE3
                c.border = ft.border.all(2, grp_color)
            else:
                c.bgcolor = CLR_SURFACE2
                c.border = ft.border.all(1, CLR_BORDER)
        try:
            self.page.update()
        except Exception:
            pass

    def _update_image(self, measure_number: int) -> None:
        path = _image_for_measure(measure_number)
        if path == self._current_img_path:
            return
        self._current_img_path = path
        self._img_ref.src = path

        section_labels = {
            (1, 6):   "Topo (M01–M06)",
            (7, 15):  "Frente 1 (M07–M15)",
            (16, 24): "Frente 2 (M16–M24)",
            (25, 32): "Lateral 1 (M25–M32)",
            (33, 40): "Lateral 2 (M33–M40)",
            (41, 46): "Fundo (M41–M46)",
        }
        label = ""
        for (lo, hi), lbl in section_labels.items():
            if lo <= measure_number <= hi:
                label = lbl
                break
        self._img_label.value = label

        # Atualiza indicador de grupo e chips
        group_name, group_color, _ = _get_group_for_measure(measure_number)
        self._group_indicator.value = f"{label or group_name}"
        self._group_indicator.color = group_color
        self._update_group_chips(measure_number)

        try:
            self.page.update()
        except Exception:
            pass

    def _append_log(self, text: str) -> None:
        current = self._tf_log.value or ""
        lines = current.split("\n") if current else []
        lines.append(text)
        if len(lines) > 60:
            lines = lines[-60:]
        self._tf_log.value = "\n".join(lines)
        self.status_bar.set_message(text[:80])
        try:
            self.page.update()
        except Exception:
            pass

    def _set_ble_buttons(self, running: bool) -> None:
        self._ble_running = running
        start = self._btn_start_ref.current
        stop  = self._btn_stop_ref.current
        if start and stop:
            start.bgcolor  = CLR_SUCCESS if not running else "#2a2f45"
            start.opacity  = 0.4 if running else 1.0
            start.on_click = None if running else self._on_start
            start.on_hover = (
                None if running
                else (lambda e: self._btn_hover(e, self._btn_start_ref, CLR_SUCCESS, CLR_SUCCESS_H))
            )
            stop.bgcolor   = CLR_DANGER if running else "#2a2f45"
            stop.opacity   = 1.0 if running else 0.4
            stop.on_click  = self._on_stop if running else None
            stop.on_hover  = (
                (lambda e: self._btn_hover(e, self._btn_stop_ref, CLR_DANGER, CLR_DANGER_H))
                if running else None
            )
            try:
                self.page.update()
            except Exception:
                pass

    def _on_campo_change(self, e: ft.ControlEvent, index: int) -> None:
        pass

    def _on_field_focus(self, index: int) -> None:
        self._override_index = index
        self._highlight_field(index)
        self._update_image(index + 1)

    def _on_posto_change(self, e: ft.ControlEvent) -> None:
        pass

    def _validate_field_projeto(self, e: ft.ControlEvent) -> None:
        v = e.control.value.strip()
        e.control.border_color = (
            CLR_SUCCESS if RE_PROJETO.fullmatch(v)
            else (CLR_DANGER if v else CLR_BORDER)
        )
        e.control.update()

    def _validate_field_serie(self, e: ft.ControlEvent) -> None:
        v = e.control.value.strip()
        e.control.border_color = (
            CLR_SUCCESS if RE_SERIE.fullmatch(v)
            else (CLR_DANGER if v else CLR_BORDER)
        )
        e.control.update()

    def _validate_field_operador(self, e: ft.ControlEvent) -> None:
        v = e.control.value.strip()
        e.control.border_color = (
            CLR_SUCCESS if RE_OPERADOR.fullmatch(v)
            else (CLR_DANGER if v else CLR_BORDER)
        )
        e.control.update()

    async def _on_start(self, _e: ft.ControlEvent) -> None:
        mac  = self._tf_mac.value.strip()
        uuid = self._tf_uuid.value.strip()
        if not mac or not uuid:
            _snack(self.page, "Preencha MAC e UUID antes de conectar.", CLR_WARNING)
            return

        self._set_ble_buttons(running=True)
        self._append_log("Conectando...")
        self.status_bar.set_ble(False, "Conectando...")
        try:
            self._ble = BleNotifier(mac, uuid)
            await self._ble.connect()
            await self._ble.start(self._on_notify)
            self._append_log("Conectado. Aguardando notificacoes BLE...")
            self.status_bar.set_ble(True, "Conectado")
            _snack(self.page, "BLE conectado com sucesso!", CLR_SUCCESS)
        except Exception as exc:
            self._append_log(f"Falha na conexao: {exc}")
            self._ble = None
            self._set_ble_buttons(running=False)
            self.status_bar.set_ble(False, "Erro de conexao")
            _snack(self.page, f"Falha BLE: {exc}", CLR_DANGER)

    async def _on_stop(self, _e: ft.ControlEvent) -> None:
        self._set_ble_buttons(running=False)
        try:
            if self._ble:
                await self._ble.stop()
                self._append_log("Desconectado do BLE.")
                self.status_bar.set_ble(False)
                _snack(self.page, "BLE desconectado.", CLR_WARNING)
        finally:
            self._ble = None

    def _on_notify(self, sender: int, data: bytes) -> None:
        self.page.run_task(self._handle_notify, sender, data)

    async def _handle_notify(self, sender: int, data: bytes) -> None:
        operador = self._tf_operador.value.strip()
        if not operador:
            if not self._warned_operator_empty:
                _snack(self.page, "Preencha o Operador antes de iniciar as medicoes.", CLR_WARNING)
                self._warned_operator_empty = True
            return
        else:
            self._warned_operator_empty = False

        if not self._dd_posto.value:
            if not self._warned_posto_empty:
                _snack(self.page, "Selecione o Posto antes de iniciar as medicoes.", CLR_WARNING)
                self._warned_posto_empty = True
            return
        else:
            self._warned_posto_empty = False

        value = self._extract_value_um(data)
        if value is None:
            self._append_log(f"Payload nao reconhecido: {data!r}")
            return

        was_override = self._override_index is not None

        if was_override:
            idx = self._override_index
            self._override_index = None
            for c in self._measure_containers:
                c.bgcolor = CLR_SURFACE2
                c.border = ft.border.all(1, CLR_BORDER)
        else:
            if self._next_index >= 46:
                self._append_log("Ja existem 46 medicoes. Limpe para continuar.")
                return
            idx = self._next_index
            self._next_index += 1

        self._measure_fields[idx].value = value
        # Colore o container com valor preenchido
        _, grp_color, grp_bg = _get_group_for_measure(idx + 1)
        self._measure_containers[idx].bgcolor = grp_bg
        self._measure_containers[idx].border = ft.border.all(1, grp_color + "66")

        self._append_log(f"M{idx+1:02d} = {value}")
        self._update_progress()

        if (not was_override) and idx == 45:
            await self._finish_measurement()
            return

        proxima = min(self._next_index + 1, 46)
        self._update_image(proxima)
        try:
            self.page.update()
        except Exception:
            pass

    @staticmethod
    def _extract_value_um(data: bytes) -> str | None:
        text = data.decode("utf-8", errors="ignore").strip()
        m = _RX.search(text)
        if not m:
            return None
        valor = m.group(1).replace(",", ".")
        return f"{valor} um"

    def _get_posto_code(self) -> str | None:
        return self._dd_posto.value

    def _validate_header(self) -> bool:
        projeto  = self._tf_projeto.value.strip()
        serie    = self._tf_serie.value.strip()
        operador = self._tf_operador.value.strip()

        erros = []
        if not RE_PROJETO.fullmatch(projeto):
            erros.append("Projeto: 3 letras maiusculas + 4 numeros (ex: SEF0500)")
        if not RE_SERIE.fullmatch(serie):
            erros.append("Serie: 10 digitos (ex: 1015150001)")
        if not RE_OPERADOR.fullmatch(operador):
            erros.append("Operador: Z + 3 digitos + 4 alfanumericos maiusculos (ex: Z0052DFZ)")

        if erros:
            _snack(self.page, "Campos invalidos: " + " | ".join(erros), CLR_DANGER)
            return False
        return True

    def _on_clear_one(self, _e: ft.ControlEvent) -> None:
        if self._override_index is None:
            _snack(self.page, "Clique primeiro no campo de medicao que deseja limpar.", CLR_WARNING)
            return
        idx = self._override_index
        self._measure_fields[idx].value = ""
        self._measure_containers[idx].bgcolor = CLR_SURFACE2
        self._measure_containers[idx].border = ft.border.all(1, CLR_BORDER)
        self._override_index = None
        for c in self._measure_containers:
            c.bgcolor = CLR_SURFACE2
            c.border = ft.border.all(1, CLR_BORDER)
        self._append_log(f"Medicao M{idx+1:02d} limpa.")
        self._update_progress()
        self.page.update()

    def _on_clear_all(self, _e: ft.ControlEvent) -> None:
        for f in self._measure_fields:
            f.value = ""
        for c in self._measure_containers:
            c.bgcolor = CLR_SURFACE2
            c.border = ft.border.all(1, CLR_BORDER)
        self._next_index = 0
        self._override_index = None
        self._update_image(1)
        self._update_progress()
        self._append_log("Todas as medicoes limpas.")
        self.page.update()

    def _on_save(self, _e: ft.ControlEvent) -> None:
        operador = self._tf_operador.value.strip()
        if not operador:
            _snack(self.page, "Preencha o campo Operador.", CLR_DANGER)
            return

        posto_code = self._get_posto_code()
        if not posto_code:
            _snack(self.page, "Selecione o Posto antes de salvar.", CLR_DANGER)
            return

        projeto = self._tf_projeto.value.strip() or None
        serie   = self._tf_serie.value.strip() or None
        values  = [f.value.strip() for f in self._measure_fields]

        self.repo.create_pending(
            posto=posto_code,
            operador=operador,
            values=values,
            projeto=projeto,
            serie=serie,
        )

        _snack(self.page, "Medicao salva com sucesso!", CLR_SUCCESS)
        self._on_clear_all(None)
        self._tf_serie.value = ""
        self.page.update()
        self.navigate("overview")

    def _save_silent(self) -> bool:
        operador   = self._tf_operador.value.strip()
        posto_code = self._get_posto_code()
        values     = [f.value.strip() for f in self._measure_fields]

        if not operador or not posto_code or not any(values):
            return False

        projeto = self._tf_projeto.value.strip() or None
        serie   = self._tf_serie.value.strip() or None

        self.repo.create_pending(
            posto=posto_code,
            operador=operador,
            values=values,
            projeto=projeto,
            serie=serie,
        )
        return True

    async def _finish_measurement(self) -> None:
        self._save_silent()

        def _on_yes() -> None:
            operador = self._tf_operador.value
            projeto  = self._tf_projeto.value
            self._on_clear_all(None)
            self._tf_operador.value = operador
            self._tf_projeto.value  = projeto
            self._tf_serie.value    = ""
            self.page.update()

        def _on_no() -> None:
            self.reset_form()
            self.navigate("overview")

        _show_confirm_dialog(
            self.page,
            title="46 medicoes concluidas",
            message="Medicao salva! Deseja continuar medindo (nova medicao)?",
            confirm_text="Continuar",
            cancel_text="Voltar",
            on_confirm=_on_yes,
            on_cancel=_on_no,
        )

    def _on_back(self, _e: ft.ControlEvent) -> None:
        has_any = (
            any(f.value.strip() for f in self._measure_fields)
            or self._tf_operador.value.strip()
            or self._tf_projeto.value.strip()
            or self._tf_serie.value.strip()
        )
        if has_any:
            _show_confirm_dialog(
                self.page,
                title="Sair sem salvar?",
                message="Existem dados nao salvos. Deseja sair mesmo assim?",
                confirm_text="Sair",
                on_confirm=self._do_back,
            )
        else:
            self._do_back()

    def _do_back(self) -> None:
        self.reset_form()
        self.navigate("overview")

    def reset_form(self) -> None:
        for f in self._measure_fields:
            f.value = ""
        for c in self._measure_containers:
            c.bgcolor = CLR_SURFACE2
            c.border = ft.border.all(1, CLR_BORDER)
        self._next_index = 0
        self._override_index = None
        self._tf_operador.value = ""
        self._tf_projeto.value  = ""
        self._tf_serie.value    = ""
        self._dd_posto.value    = None
        self._tf_log.value      = ""
        self._tf_operador.border_color = CLR_BORDER
        self._tf_projeto.border_color  = CLR_BORDER
        self._tf_serie.border_color    = CLR_BORDER
        self._update_image(1)
        self._update_progress()
        try:
            self.page.update()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tela: Exportar Lote
# ---------------------------------------------------------------------------

class BatchExportPage:
    def __init__(
        self,
        page: ft.Page,
        repo: Repo,
        status_bar: StatusBar,
        navigate: Callable[[str], None],
    ) -> None:
        self.page = page
        self.repo = repo
        self.status_bar = status_bar
        self.navigate = navigate

        self._ids: list[int] = []

        self._serie_fields:   list[ft.TextField] = []
        self._projeto_fields: list[ft.TextField] = []
        self._id_values:      list[int] = []

        for _ in range(5):
            self._serie_fields.append(_field("10 dígitos", width=160))
            self._projeto_fields.append(_field("ABC1234", width=120))
            self._id_values.append(0)

        self._tf_global_project = _field("Projeto global (ex: SEF0500)", expand=True)

        self.control = self._build()

    def _build(self) -> ft.Column:
        topbar = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                    icon_color=CLR_TEXT_MUTED,
                    icon_size=16,
                    on_click=lambda _: self.navigate("overview"),
                    tooltip="Voltar para lista de pendentes",
                ),
                ft.Container(width=6),
                ft.Container(
                    content=ft.Icon(ft.Icons.FILE_UPLOAD_OUTLINED, color=CLR_PURPLE, size=18),
                    bgcolor=CLR_ACCENT_DIM,
                    border_radius=8,
                    padding=7,
                    width=34,
                    height=34,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(width=8),
                _section_title("Exportar Lote"),
                ft.Container(width=8),
                ft.Container(
                    content=ft.Text(
                        "5 medições",
                        size=12,
                        color=CLR_PURPLE,
                        weight=ft.FontWeight.W_600,
                    ),
                    bgcolor=CLR_ACCENT_DIM,
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Instruções
        instructions = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=CLR_ACCENT, size=16),
                    ft.Container(width=8),
                    ft.Text(
                        "Preencha ou confirme os campos de cada medição antes de exportar. "
                        "Cada medição gerará um arquivo Excel individual.",
                        size=12,
                        color=CLR_TEXT_MUTED,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=CLR_ACCENT_DIM,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, CLR_ACCENT + "33"),
        )

        project_card = _card(
            ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_OUTLINED, color=CLR_PRIMARY, size=16),
                    ft.Text(
                        "Projeto Global",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=CLR_TEXT,
                    ),
                    ft.Container(width=12),
                    self._tf_global_project,
                    ft.Container(width=8),
                    _btn(
                        "Aplicar a todos",
                        self._on_apply_global,
                        color=CLR_PURPLE,
                        hover_color=CLR_PURPLE_H,
                        tooltip="Copiar este projeto para todas as 5 linhas",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
        )

        table_header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=44,
                        content=ft.Text("#", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=1,
                        content=ft.Text(
                            "Numero de Serie (10 digitos)",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=1,
                        content=ft.Text(
                            "Projeto (ABC1234)",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=1,
                        content=ft.Text(
                            "Operador / Posto",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                ],
                spacing=12,
            ),
            bgcolor=CLR_SURFACE2,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius(10, 10, 0, 0),
            border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
        )

        self._table_rows_col = ft.Column(spacing=0)

        table_wrapper = ft.Container(
            content=ft.Column([table_header, self._table_rows_col], spacing=0),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW,
        )

        action_row = ft.Row(
            [
                ft.Container(expand=True),
                _btn(
                    "Exportar 5 arquivos Excel",
                    self._on_export,
                    color=CLR_SUCCESS,
                    hover_color=CLR_SUCCESS_H,
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    tooltip="Gerar arquivos .xlsx e mover para histórico",
                ),
            ]
        )

        return ft.Column(
            [
                _card(topbar, padding=12),
                ft.Container(height=10),
                instructions,
                ft.Container(height=8),
                project_card,
                ft.Container(height=10),
                table_wrapper,
                ft.Container(height=14),
                action_row,
            ],
            expand=True,
            spacing=0,
        )

    def _rebuild_table_rows(self) -> None:
        self._table_rows_col.controls.clear()
        measurements = self.repo.get_by_ids(self._ids)
        for r, m in enumerate(measurements):
            self._id_values[r]         = m.id
            self._serie_fields[r].value   = m.serie or ""
            self._projeto_fields[r].value = m.projeto or ""

            info_text = f"{m.operador} · {m.posto}"
            alt = r % 2 == 1

            row_num_badge = ft.Container(
                content=ft.Text(
                    str(r + 1),
                    size=12,
                    color=CLR_TEXT,
                    weight=ft.FontWeight.W_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                bgcolor=CLR_SURFACE2,
                border_radius=6,
                width=28,
                height=28,
                alignment=ft.Alignment(0, 0),
            )

            row = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(width=44, content=row_num_badge),
                        ft.Container(expand=1, content=self._serie_fields[r]),
                        ft.Container(expand=1, content=self._projeto_fields[r]),
                        ft.Container(
                            expand=1,
                            content=ft.Text(info_text, size=12, color=CLR_TEXT_MUTED),
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=CLR_ROW_ALT if alt else CLR_SURFACE,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
            )
            self._table_rows_col.controls.append(row)
        try:
            self.page.update()
        except Exception:
            pass

    def load(self, ids: list[int]) -> None:
        self._ids = ids
        self._rebuild_table_rows()

    def _on_apply_global(self, _e: ft.ControlEvent) -> None:
        proj = self._tf_global_project.value.strip()
        if not proj:
            _snack(self.page, "Digite um projeto antes de aplicar.", CLR_WARNING)
            return
        for f in self._projeto_fields:
            f.value = proj
        self.page.update()

    def _on_export(self, _e: ft.ControlEvent) -> None:
        for r in range(5):
            serie = self._serie_fields[r].value.strip()
            proj  = self._projeto_fields[r].value.strip()
            if not RE_SERIE.fullmatch(serie):
                _snack(self.page, f"Linha {r+1}: Serie invalida (10 digitos).", CLR_DANGER)
                return
            if not RE_PROJETO.fullmatch(proj):
                _snack(self.page, f"Linha {r+1}: Projeto invalido (ex: SEF0500).", CLR_DANGER)
                return

        measurements = self.repo.get_by_ids(self._ids)
        for r, m in enumerate(measurements):
            serie = self._serie_fields[r].value.strip()
            proj  = self._projeto_fields[r].value.strip()

            self.repo.update_assignment(m.id, proj, serie)
            export_measurement_to_excel(
                serie=serie,
                projeto=proj,
                operador=m.operador,
                posto=m.posto,
                created_at=m.created_at,
                values=m.values,
            )
            self.repo.mark_exported(m.id)

        _snack(self.page, "5 arquivos exportados e enviados ao historico!", CLR_SUCCESS)
        self.navigate("history")


# ---------------------------------------------------------------------------
# Tela: Histórico
# ---------------------------------------------------------------------------

class HistoryPage:
    def __init__(
        self,
        page: ft.Page,
        repo: Repo,
        status_bar: StatusBar,
        navigate: Callable[[str], None],
    ) -> None:
        self.page = page
        self.repo = repo
        self.status_bar = status_bar
        self.navigate = navigate

        self._table_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
        self.control = self._build()
        self.refresh()

    def _build(self) -> ft.Column:
        topbar = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                    icon_color=CLR_TEXT_MUTED,
                    icon_size=16,
                    on_click=lambda _: self.navigate("overview"),
                    tooltip="Voltar para overview",
                ),
                ft.Container(width=6),
                ft.Container(
                    content=ft.Icon(ft.Icons.HISTORY, color=CLR_PRIMARY, size=18),
                    bgcolor="#1a2d5a",
                    border_radius=8,
                    padding=7,
                    width=34,
                    height=34,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(width=8),
                _section_title("Historico de Exportacoes"),
                ft.Container(expand=True),
                _btn(
                    "Atualizar",
                    self._on_refresh,
                    color=CLR_SURFACE2,
                    hover_color=CLR_BORDER_LIGHT,
                    icon=ft.Icons.REFRESH,
                    tooltip="Recarregar historico",
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=52,
                        content=ft.Text("ID", size=11, color=CLR_TEXT_MUTED, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            "Exportado em",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            "Cadastro em",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=1,
                        content=ft.Text(
                            "Posto",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            "Serie",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                    ft.Container(
                        expand=2,
                        content=ft.Text(
                            "Operador",
                            size=11,
                            color=CLR_TEXT_MUTED,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                ],
                spacing=8,
            ),
            bgcolor=CLR_SURFACE2,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=ft.BorderRadius(10, 10, 0, 0),
            border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
        )

        table_wrapper = ft.Container(
            content=ft.Column([header, self._table_col], spacing=0),
            bgcolor=CLR_SURFACE,
            border_radius=12,
            border=ft.border.all(1, CLR_BORDER),
            shadow=SHADOW,
            expand=True,
        )

        return ft.Column(
            [
                _card(topbar, padding=12),
                ft.Container(height=10),
                table_wrapper,
            ],
            expand=True,
            spacing=0,
        )

    def refresh(self) -> None:
        items = self.repo.list_history(limit=300)
        self._table_col.controls.clear()

        if not items:
            self._table_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.HISTORY_TOGGLE_OFF,
                                    color=CLR_TEXT_DIM,
                                    size=52,
                                ),
                                bgcolor=CLR_SURFACE2,
                                border_radius=50,
                                padding=20,
                            ),
                            ft.Container(height=12),
                            ft.Text(
                                "Nenhuma medicao exportada ainda.",
                                color=CLR_TEXT_MUTED,
                                size=15,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "Exporte um lote de 5 medicoes para ver o historico aqui.",
                                color=CLR_TEXT_DIM,
                                size=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=50,
                )
            )
        else:
            posto_styles = {
                "FUNDO": ("#4f8ef7", "#1a2d5a"),
                "ACAB":  ("#22c55e", "#0f3320"),
                "JAT":   ("#f59e0b", "#3d2a05"),
            }
            for i, m in enumerate(items):
                fc, bc = posto_styles.get(m.posto, (CLR_TEXT_MUTED, CLR_SURFACE2))
                posto_badge = ft.Container(
                    content=ft.Text(
                        m.posto,
                        size=11,
                        color=fc,
                        weight=ft.FontWeight.W_700,
                    ),
                    bgcolor=bc,
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    border=ft.border.all(1, fc + "33"),
                )

                # Badge de exportado
                export_badge = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=CLR_SUCCESS, size=12),
                            ft.Container(width=4),
                            ft.Text(m.exported_at or "—", size=11, color=CLR_TEXT),
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )

                row = ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=52,
                                content=ft.Text(str(m.id), size=12, color=CLR_TEXT_MUTED),
                            ),
                            ft.Container(expand=2, content=export_badge),
                            ft.Container(
                                expand=2,
                                content=ft.Text(m.created_at, size=12, color=CLR_TEXT),
                            ),
                            ft.Container(expand=1, content=posto_badge),
                            ft.Container(
                                expand=2,
                                content=ft.Text(m.serie or "—", size=12, color=CLR_TEXT),
                            ),
                            ft.Container(
                                expand=2,
                                content=ft.Text(m.operador, size=12, color=CLR_TEXT),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=CLR_ROW_ALT if i % 2 == 1 else CLR_SURFACE,
                    padding=ft.padding.symmetric(horizontal=16, vertical=11),
                    border=ft.border.only(bottom=ft.BorderSide(1, CLR_BORDER)),
                )
                self._table_col.controls.append(row)

        try:
            self.page.update()
        except Exception:
            pass

    def _on_refresh(self, _e: ft.ControlEvent) -> None:
        self.refresh()
        _snack(self.page, "Historico atualizado.", CLR_PRIMARY)


# ---------------------------------------------------------------------------
# Dialogo de confirmação
# ---------------------------------------------------------------------------

def _show_confirm_dialog(
    page: ft.Page,
    title: str,
    message: str,
    on_confirm: Callable,
    on_cancel: Callable | None = None,
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar",
) -> None:
    dlg_ref = ft.Ref[ft.AlertDialog]()

    def _confirm(_e: ft.ControlEvent) -> None:
        dlg_ref.current.open = False
        page.update()
        on_confirm()

    def _cancel(_e: ft.ControlEvent) -> None:
        dlg_ref.current.open = False
        page.update()
        if on_cancel:
            on_cancel()

    dlg = ft.AlertDialog(
        ref=dlg_ref,
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.HELP_OUTLINE_ROUNDED, color=CLR_PRIMARY, size=22),
                ft.Container(width=8),
                ft.Text(title, color=CLR_TEXT, size=16, weight=ft.FontWeight.W_700),
            ],
            spacing=0,
        ),
        content=ft.Text(message, color=CLR_TEXT_MUTED, size=13),
        bgcolor=CLR_SURFACE,
        shape=ft.RoundedRectangleBorder(radius=14),
        actions=[
            ft.TextButton(
                cancel_text,
                on_click=_cancel,
                style=ft.ButtonStyle(color=CLR_TEXT_MUTED),
            ),
            ft.Container(
                content=ft.Text(
                    confirm_text,
                    color=CLR_TEXT,
                    size=13,
                    weight=ft.FontWeight.W_600,
                ),
                bgcolor=CLR_PRIMARY,
                border_radius=9,
                padding=ft.padding.symmetric(horizontal=18, vertical=9),
                on_click=_confirm,
                animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(page: ft.Page) -> None:
    page.title = "Jato & Pintura — Medicao de Camada"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = CLR_BG
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 600
    page.padding = 0
    page.spacing = 0
    page.fonts = {}

    page.theme = ft.Theme(
        color_scheme_seed=CLR_PRIMARY,
        use_material3=True,
    )

    repo = Repo(BASE_DIR / "medicoes.db")
    status_bar = StatusBar()

    content_area = ft.Column(
        controls=[ft.Container(expand=True)],
        expand=True,
        spacing=0,
    )

    overview_page: OverviewPage | None = None
    newedit_page:  NewEditPage  | None = None
    batch_page:    BatchExportPage | None = None
    history_page:  HistoryPage  | None = None

    sidebar_ref: list[Sidebar] = []

    def navigate(route: str) -> None:
        if sidebar_ref:
            sidebar_ref[0].set_active(route)

        if route == "overview":
            overview_page.refresh()
            content_area.controls = [ft.Container(
                content=overview_page.control,
                expand=True,
                padding=ft.padding.all(20),
            )]
        elif route == "newedit":
            newedit_page.reset_form()
            content_area.controls = [ft.Container(
                content=newedit_page.control,
                expand=True,
                padding=ft.padding.all(20),
            )]
        elif route == "batch":
            content_area.controls = [ft.Container(
                content=batch_page.control,
                expand=True,
                padding=ft.padding.all(20),
            )]
        elif route == "history":
            history_page.refresh()
            content_area.controls = [ft.Container(
                content=history_page.control,
                expand=True,
                padding=ft.padding.all(20),
            )]
        page.update()

    def go_batch(ids: list[int]) -> None:
        batch_page.load(ids)
        navigate("batch")

    # Criação das páginas (sidebar é passada para overview para atualizar badge)
    sidebar = Sidebar(navigate)
    sidebar_ref.append(sidebar)

    overview_page = OverviewPage(page, repo, status_bar, navigate, go_batch, sidebar=sidebar)
    newedit_page  = NewEditPage(page, repo, status_bar, navigate)
    batch_page    = BatchExportPage(page, repo, status_bar, navigate)
    history_page  = HistoryPage(page, repo, status_bar, navigate)

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        sidebar.control,
                        ft.VerticalDivider(width=1, color=CLR_BORDER),
                        content_area,
                    ],
                    expand=True,
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                status_bar.control,
            ],
            expand=True,
            spacing=0,
        )
    )

    content_area.controls = [ft.Container(
        content=overview_page.control,
        expand=True,
        padding=ft.padding.all(20),
    )]
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
