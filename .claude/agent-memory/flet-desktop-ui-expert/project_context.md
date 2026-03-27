---
name: Contexto do Projeto Jateamento e Pintura
description: Detalhes do app industrial de medição de camada — stack, estrutura e integrações
type: project
---

App desktop de medição de camada para Jateamento e Pintura industrial.
Migrado de PySide6 + qasync para Flet (versão >=0.24.0).

**Stack:**
- UI: Flet (Python)
- BLE: bleak (BleNotifier em ble.py)
- Banco: SQLite via repo.py (Repo class)
- Export: exporter.py (export_measurement_to_excel)

**4 telas principais:**
- overview: medições pendentes (checkbox + tabela customizada)
- newedit: formulário com 46 campos de medição em grid 4 colunas + imagem de referência lateral
- batch: exportar 5 medições em lote para Excel
- history: histórico de exportações

**Why:** Migração solicitada pelo usuário para modernizar a UI, eliminar PySide6/qasync.
**How to apply:** Ao modificar UI, manter integrações com repo.py, ble.py e exporter.py inalteradas.
