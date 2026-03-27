---
name: Paleta de cores e tema — v3.0
description: Paleta de cores oficial do projeto após redesign v3.0, com todas as constantes de cor e uso
type: project
---

Paleta v3.0 definida em main.py (tema escuro profissional aprimorado):

```python
CLR_BG           = "#080b12"   # fundo principal mais profundo
CLR_SURFACE      = "#111827"   # cards / painéis
CLR_SURFACE2     = "#1c2336"   # superfície levemente elevada
CLR_SURFACE3     = "#243047"   # terceiro nível (campos focados)
CLR_BORDER       = "#2a3452"   # bordas suaves
CLR_BORDER_LIGHT = "#374166"   # borda mais visível
CLR_PRIMARY      = "#4f8ef7"   # azul principal
CLR_PRIMARY_H    = "#3b7de8"   # azul hover
CLR_PRIMARY_GLOW = "#4f8ef722" # brilho azul para sombras
CLR_SUCCESS      = "#22c55e"   # verde (conectar, salvo)
CLR_SUCCESS_H    = "#16a34a"
CLR_SUCCESS_DIM  = "#14532d"   # fundo badge verde
CLR_DANGER       = "#f05252"   # vermelho (parar, excluir)
CLR_DANGER_H     = "#dc2626"
CLR_DANGER_DIM   = "#7f1d1d"
CLR_WARNING      = "#f59e0b"   # amarelo (atenção)
CLR_WARNING_DIM  = "#451a03"
CLR_TEXT         = "#e8edf5"   # texto principal
CLR_TEXT_MUTED   = "#8a9abf"   # texto secundário
CLR_TEXT_DIM     = "#4a5578"   # texto muito suave
CLR_ACCENT       = "#818cf8"   # roxo (BLE, detalhes)
CLR_ACCENT_DIM   = "#312e81"
CLR_ROW_ALT      = "#131b2e"   # linhas alternadas tabela
CLR_SIDEBAR      = "#0c1020"   # fundo sidebar
CLR_SIDEBAR_ITEM = "#1a2240"   # item ativo sidebar
CLR_PURPLE       = "#7c3aed"   # roxo (exportar lote)
CLR_PURPLE_H     = "#6d28d9"
```

**Padrões de sombra:**
- `SHADOW` — sombra padrão de cards (blur 24, offset 4)
- `SHADOW_SM` — sombra menor (blur 10, offset 2)
- `SHADOW_GLOW` — brilho azul (usado no logo)

**How to apply:** Usar sempre essas constantes para manter consistência visual. Nunca usar cores hardcoded fora das constantes.
