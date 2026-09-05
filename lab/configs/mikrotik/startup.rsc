# Configuração Inicial de Boot - MikroTik RouterOS (AS 65100)

/system identity set name=Borda-MikroTik

# Configuração de Endereçamento IP nas Interfaces de Uplink
/ip address
add address=100.64.1.2/30 interface=ether1 comment="Link-Operadora-1"
add address=100.64.2.2/30 interface=ether2 comment="Link-Operadora-2"
add address=192.168.100.1/24 interface=ether3 comment="Rede-Interna-ISP"

# Configuração da Instância BGP
/routing bgp instance
set default as=65100 router-id=100.64.1.2 redistribute-connected=yes

# Configuração dos Peers BGP com as Operadoras
/routing bgp peer
add name=PEER_OPERADORA_1 remote-address=100.64.1.1 remote-as=65001 default-originate=never comment="Upstream 1"
add name=PEER_OPERADORA_2 remote-address=100.64.2.1 remote-as=65002 default-originate=never comment="Upstream 2"

# Anúncio do Bloco do ISP (Prefixo de Teste)
/routing bgp network
add network=200.100.0.0/22 synchronize=no

# Filtros de Roteamento Padrão (Sem prepend inicial)
/routing filter
add chain=BGP_OP1_OUT action=accept
add chain=BGP_OP2_OUT action=accept
