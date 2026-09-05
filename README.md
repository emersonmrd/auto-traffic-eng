# 🚀 Auto Traffic Engineering (Auto-Traffic-Eng)

Sistema determinístico e automatizado de **Engenharia de Tráfego BGP em Malha Fechada (Closed-Loop)** para Provedores de Internet (ISPs), controlado remotamente via **Telegram** com guardrails operacionais estritos e ambiente de emulação multi-vendor em **Containerlab**.

---

## 📌 Visão Geral

Em incidentes de rede (rompimento de fibra, degradação de latência ou perda de pacotes), analistas de telecomunicações frequentemente precisam redirecionar o tráfego de trânsito IP entre operadoras. Realizar essa operação de forma manual via CLI no calor do momento expõe a operação a erros humanos graves (duplo clique, esquecimento de rollback, flaps de BGP ou loops de roteamento).

O **Auto-Traffic-Eng** resolve esse problema implementando:
1. **Interface Rápida & Segura:** Controle via Telegram com botões interativos dinâmicos e controle de acesso estrito (RBAC/Whitelist).
2. **Máquina de Estados Finita (FSM):** Arquitetura *Hub-and-Spoke* que impede transições inválidas e exige retorno ao estado default (NORMAL_DEFAULT) antes de novas manobras.
3. **Lock Distribuído com Anti-Flap:** Bloqueio de concorrência com TTL, watchdog de liveness e rate-limiting que impede múltiplos disparos simultâneos.
4. **Motor Closed-Loop:** Validação em 4 etapas:
   \text{Pre-Check} \longrightarrow \text{Commit Confirmed / Safe Shift} \longrightarrow \text{Post-Check Telemetria} \longrightarrow \text{Confirm / Auto-Rollback}
5. **Laboratório Multi-Vendor:** Ambiente virtualizado pronto para rodar com **Containerlab** simulando BGP real com MikroTik RouterOS, Cisco IOS (FRR) e Operadoras de Trânsito.

---

## 🏛️ Arquitetura do Sistema

`mermaid
graph TD
    User([📱 Operador no Telegram]) -->|/start ou Clique Inline| Bot[🤖 Telegram Bot Service]
    Bot -->|Validação Whitelist & Fast-Ack| FSM[⚙️ State Manager / FSM]
    FSM -->|Valida Transição Permitida| Lock[🔒 Distributed Lock & Anti-Flap]
    Lock -->|Adquire Lease| Engine[🚀 Closed-Loop Executor]
    
    subgraph Orquestração Segura
        Engine -->|1. Pre-Check BGP/Rotas| Driver[🔌 Multi-Vendor Driver]
        Driver -->|2. Aplica Prepend / Filter| Router[🌐 Borda ISP - MikroTik / Cisco]
        Router -->|Anúncio BGP| Upstream1[🏢 Operadora 1 - AS 65001]
        Router -->|Anúncio BGP| Upstream2[🏢 Operadora 2 - AS 65002]
        Engine -->|3. Post-Check Telemetria| Upstream1
        Engine -->|4. Sucesso -> Confirm Commit| Router
        Engine -.->|4. Falha -> Auto-Rollback| Router
    end

    Engine -->|Atualiza Estado em Tempo Real| Bot
`

---

## 📁 Estrutura do Repositório

`	ext
├── bot/
│   └── telegram_bot.py           # Serviço do Bot (Aiogram 3, HTML seguro, Whitelist)
├── core/
│   ├── models.py                 # Data Models Pydantic e Enums
│   └── state_manager.py          # Máquina de Estados Finita (FSM Hub-and-Spoke)
├── drivers/
│   ├── base.py                   # Interface abstrata de driver
│   ├── mikrotik.py               # Driver RouterOS v6/v7 com SSH e Sanitização
│   ├── cisco.py                  # Driver Cisco IOS / FRRouting
│   ├── juniper.py                # Driver Junos
│   └── huawei.py                 # Driver Huawei VRP
├── worker/
│   ├── executor.py               # Motor de Execução Closed-Loop
│   └── lock.py                   # Redis Lock Distribuído com Watchdog e Rate Limit
├── lab/
│   ├── topology.clab.yml         # Topologia Multi-Vendor Containerlab
│   └── configs/                  # Configurações de inicialização do FRR e Roteadores
├── run_simulation.py             # Suite de testes e simulação local
├── .env.example                  # Template limpo de variáveis de ambiente
└── .gitignore                    # Regras de segurança (bloqueia tokens e imagens binárias)
`

---

## 🚀 Como Executar

### 1. Pré-requisitos
* Linux ou Windows com **WSL2** (Ubuntu 22.04 / 24.04).
* **Docker** e **Containerlab** instalados.
* Python 3.10+.

### 2. Inicializar a Topologia de Rede
`ash
clab deploy -t lab/topology.clab.yml
`

### 3. Configurar Variáveis de Ambiente
Copie o template .env.example para .env e preencha com o token do seu bot do Telegram:
`ash
cp .env.example .env
`
Edite o .env:
`env
TELEGRAM_BOT_TOKEN=seu_token_gerado_no_botfather
ALLOWED_TELEGRAM_IDS=seu_id_numerico_do_telegram
`

### 4. Iniciar o Bot do Telegram
`ash
python3 -m venv venv
source venv/bin/activate
pip install -r lab/requirements.txt  # ou pip install aiogram python-dotenv pydantic
python3 -m bot.telegram_bot
`

### 5. Executar os Testes Unitários e Simulação Local
`ash
PYTHONPATH=. python3 run_simulation.py
`

---

## 🛡️ Segurança & Boas Práticas

* **Nenhum Segredo no Git:** Tokens, chaves e credenciais ficam estritamente no arquivo local .env (ignorado pelo Git).
* **Controle de Acesso RBAC:** Somente IDs do Telegram devidamente cadastrados na variável ALLOWED_TELEGRAM_IDS têm permissão para interagir ou acionar botões.
* **Auto-Rollback (Dead Man's Switch):** Se o link de comunicação cair ou a telemetria não confirmar o desvio dentro da janela de convergência, o sistema reverte a manobra automaticamente para evitar isolamento da rede.

---

## 📄 Licença
Distribuído sob a licença MIT. Consulte LICENSE para obter mais informações.
