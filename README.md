# Medição de Camadas — Siemens Energy

Aplicativo desktop para coleta, registro e exportação de medições de espessura de camada (pintura e jateamento) via dispositivo Bluetooth Low Energy (BLE).

---

## Visão Geral

O sistema conecta via BLE a um medidor de camada, recebe os valores automaticamente e os registra em banco de dados local. As medições ficam pendentes até serem exportadas para Excel, quando então são movidas para o histórico.

A interface guia o operador ponto a ponto com uma seta animada sobre a imagem de referência da peça, indicando exatamente onde cada medição deve ser feita.

---

## Funcionalidades

- **Conexão BLE automática** — conecta ao medidor e recebe as leituras em tempo real
- **Guia visual por seta animada** — exibe a posição exata do próximo ponto sobre a imagem da peça
- **3 postos de trabalho** — Pintura Fundo, Pintura Acabamento e Jateamento
- **Rotação semanal de pontos (Jateamento)** — de segunda a quinta, exibe apenas os 6 pontos do dia; na sexta, exibe todos os 46
- **46 pontos de medição por ciclo completo**
- **Exportação para Excel** com dados completos da medição
- **Histórico** de medições exportadas
- **Configuração BLE persistente** — MAC e UUID salvos entre sessões
- **Validação de campos** — Operador, Projeto e Número de Série com formato definido

---

## Estrutura do Projeto

```
Projeto-Jateamento-Pintura/
├── main.py                 # Interface gráfica (PySide6) e lógica principal
├── ble.py                  # Comunicação BLE (bleak + qasync)
├── repo.py                 # Acesso ao banco de dados SQLite
├── exporter.py             # Exportação para Excel (openpyxl)
├── MedicaoCamadas.spec     # Configuração do PyInstaller
├── requirements.txt        # Dependências do projeto
├── Images/
│   ├── Topo.png
│   ├── Frente 1.png
│   ├── Frente 2.png
│   ├── Lateral 1.png
│   ├── Lateral 2.png
│   ├── Fundo.png
│   ├── seta verde.png
│   └── Siemens_Energy.png
```

O banco de dados `medicoes.db` é criado automaticamente na mesma pasta do executável na primeira execução.

---

## Requisitos de Desenvolvimento

- Python 3.10+
- Dependências:

```
pip install -r requirements.txt
```

---

## Executando em Modo Desenvolvimento

```bash
python main.py
```

---

## Gerando o Executável

```bash
pyinstaller MedicaoCamadas.spec
```

O executável será gerado em `dist/MedicaoCamadas.exe`. Arquivo único, sem dependências externas — basta copiar para outro computador Windows e executar.

---

## Formato dos Campos

| Campo | Formato | Exemplo |
|---|---|---|
| Operador | `Z` + 3 dígitos + 4 alfanuméricos maiúsculos | `Z0052DFZ` |
| Projeto | 3 letras maiúsculas + 4 números | `SEF0500` |
| Número de Série | 10 dígitos | `1015150001` |

---

## Rotação de Pontos — Jateamento

Quando o posto **Jateamento** é selecionado, o sistema detecta automaticamente o dia da semana e exibe apenas os pontos correspondentes:

| Dia | Pontos |
|---|---|
| Segunda | 1, 7, 16, 25, 33, 41 |
| Terça | 3, 8, 17, 26, 34, 43 |
| Quarta | 5, 9, 18, 27, 35, 45 |
| Quinta | 2, 10, 19, 28, 36, 42 |
| Sexta / Fim de semana | Todos os 46 pontos |

---

## Configuração BLE

O MAC e UUID do medidor podem ser alterados na tela principal (Overview) e são salvos automaticamente no banco de dados. Na próxima abertura do aplicativo, os valores configurados são restaurados.

Valores padrão:
- **MAC:** `24:5D:FC:00:B3:2E`
- **UUID:** `06d1e5e7-79ad-4a71-8faa-373789f7d93c`

---

## Tecnologias

| Biblioteca | Uso |
|---|---|
| [PySide6](https://doc.qt.io/qtforpython/) | Interface gráfica |
| [bleak](https://github.com/hbldh/bleak) | Comunicação BLE |
| [qasync](https://github.com/CabbageDevelopment/qasync) | Integração asyncio + Qt |
| [openpyxl](https://openpyxl.readthedocs.io/) | Exportação para Excel |
| [PyInstaller](https://pyinstaller.org/) | Geração do executável |
| SQLite (stdlib) | Banco de dados local |
