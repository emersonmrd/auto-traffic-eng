# Guia do Laboratório Multi-Vendor com Containerlab

Este ambiente foi desenhado para testar automações de engenharia de tráfego de forma 100% isolada em container Docker Ubuntu no seu WSL2.

---

## 1. Como Iniciar o Container de Laboratório

Na raiz do repositório no PowerShell ou no terminal WSL:

```bash
# 1. Constrói e inicializa o container de lab
docker compose -f docker-compose.lab.yml run --rm lab-box
```

Você entrará diretamente no terminal interativo:
```text
[auto-traffic-lab] /workspace $
```

---

## 2. Como Subir a Topologia de Rede

Dentro do container `[auto-traffic-lab]`:

```bash
# Subir a topologia com Containerlab
clab deploy -t lab/topology.clab.yml

# Para inspecionar os nós ativos
clab inspect -t lab/topology.clab.yml

# Para destruir o laboratório após os testes
clab destroy -t lab/topology.clab.yml
```

---

## 3. Estrutura dos Nós de Rede

- **Operadora 1 (AS 65001):** Container Linux com FRRouting (FRR), IP `100.64.1.1/30`.
- **Operadora 2 (AS 65002):** Container Linux com FRRouting (FRR), IP `100.64.2.1/30`.
- **Borda do ISP (AS 65100):** Roteador sob teste (MikroTik, Cisco, Juniper ou Huawei) com interfaces ligadas a cada operadora.

---

## 4. Como Construir as Imagens dos Roteadores com vrnetlab

As imagens em `/imagens` podem ser empacotadas para o Docker usando o vrnetlab (mantido pela equipe do Containerlab):

```bash
# Dentro do container de lab:
git clone https://github.com/hellt/vrnetlab /opt/vrnetlab

# Para MikroTik RouterOS:
cp /imagens/mikrotik/chr-6.49.18.img /opt/vrnetlab/routeros/
make -C /opt/vrnetlab/routeros docker-build

# Para Huawei NE40E:
cp /imagens/NE40E-FIBERX/NE40E.img /opt/vrnetlab/ne40e/ # ou vrp
make -C /opt/vrnetlab/ne40e docker-build

# Para Juniper vMX:
cp /imagens/vmx-Juniper\ Router14.1/hda.qcow2 /opt/vrnetlab/vmx/
make -C /opt/vrnetlab/vmx docker-build
```
