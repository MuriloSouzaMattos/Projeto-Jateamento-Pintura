---
name: Projeto Jato & Pintura — Contexto e Decisões
description: Contexto do projeto industrial de medição de camada de pintura/jateamento, arquitetura, paleta de cores e componentes-chave
type: project
---

Aplicativo desktop Flet chamado "Jato & Pintura — Medição de Camada". Versão atual: v3.0 (redesign completo).

**Por que:** Aplicação industrial para medir espessura de camada de pintura via Bluetooth BLE (46 medições por lote), com persistência SQLite e exportação Excel.

**Arquitetura:**
- `main.py` — UI principal (Flet), todas as telas e componentes visuais
- `ble.py` — BleNotifier: conexão Bluetooth Low Energy
- `repo.py` — Repo: SQLite (medicoes.db), métodos: list_pending_all, get_by_ids, create_pending, update_assignment, mark_exported, delete_measurement, list_history
- `exporter.py` — export_measurement_to_excel: gera .xlsx
- `venv/` — ambiente virtual Python na raiz do projeto

**Telas (routes):**
- `overview` — OverviewPage: lista de medições pendentes com stats cards e checkboxes
- `newedit` — NewEditPage: grid 46 campos + BLE + barra de progresso
- `batch` — BatchExportPage: exportação de 5 medições em lote
- `history` — HistoryPage: histórico de exportações

**Postos:** FUNDO (Pintura Fundo), ACAB (Pintura Acabamento), JAT (Jateamento)

**Regex de validação:**
- Operador: `^Z\d{3}[A-Z0-9]{4}$`
- Serie: `^\d{10}$`
- Projeto: `^[A-Z]{3}\d{4}$`

**Grupos de medição (MEASURE_GROUPS):**
- M01-M06: Topo (azul)
- M07-M15: Frente 1 (verde)
- M16-M24: Frente 2 (roxo)
- M25-M32: Lateral 1 (amarelo)
- M33-M40: Lateral 2 (vermelho)
- M41-M46: Fundo (lilás)

**How to apply:** Ao modificar main.py, preservar assinaturas de métodos, lógica BLE, lógica SQLite e lógica de exportação. Apenas UI pode ser alterada livremente.
