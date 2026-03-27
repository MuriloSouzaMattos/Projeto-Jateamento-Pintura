---
name: Design System — Paleta de cores e convenções visuais
description: Paleta de cores, padrões de componentes e decisões de design do projeto
type: project
---

**Tema:** Escuro profissional inspirado em Fluent UI / Material You (Windows 11)

**Paleta de cores:**
- CLR_BG = "#0f1117"          — fundo principal
- CLR_SURFACE = "#1a1d27"     — cards / painéis
- CLR_SURFACE2 = "#22263a"    — superfície elevada
- CLR_BORDER = "#2e3250"      — bordas suaves
- CLR_PRIMARY = "#3b82f6"     — azul (ações primárias)
- CLR_PRIMARY_H = "#2563eb"   — azul hover
- CLR_SUCCESS = "#22c55e"     — verde (conectar BLE)
- CLR_DANGER = "#ef4444"      — vermelho (parar / excluir)
- CLR_WARNING = "#f59e0b"     — amarelo (avisos)
- CLR_TEXT = "#f1f5f9"        — texto principal
- CLR_TEXT_MUTED = "#94a3b8"  — texto secundário
- CLR_ACCENT = "#818cf8"      — roxo (campo selecionado nas medições)
- CLR_ROW_ALT = "#1e2235"     — linhas alternadas da tabela
- CLR_SIDEBAR = "#13162b"     — sidebar

**Padrões de componentes:**
- _card(): Container com CLR_SURFACE, border_radius=12, border 1px CLR_BORDER, shadow
- _btn(): Container com hover effect via on_hover + animate 150ms
- _field(): TextField filled, fill_color=CLR_SURFACE2, border azul no foco
- _dropdown(): Dropdown filled com mesma estética dos _field()
- Sidebar: 220px fixa, navegação com highlight ativo em CLR_SURFACE2
- StatusBar: rodapé fixo mostrando status BLE (dot colorido + texto)

**Animações:**
- AnimatedSwitcher nas trocas de tela: 200ms FADE
- Hover effects nos botões: 150ms EASE_IN_OUT
- Highlight de campo de medição: 200ms EASE_IN_OUT

**Why:** Decisões tomadas na migração PySide6 → Flet para UI mais moderna.
**How to apply:** Usar sempre essas constantes de cor ao criar novos componentes.
