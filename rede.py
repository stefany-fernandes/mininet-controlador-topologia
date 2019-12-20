#!/usr/bin/python
#code from https://github.com/LABORA-INF-UFG/PIBIC-Katia?files=1

from mininet.cli import CLI
from mininet.log import info
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo


class SimpleScenarioTopo(Topo):

    def __init__(self):
        info("Criando uma rede personalizada")

        # Initialize topology
        Topo.__init__(self)

        info("*** Using Openflow 1.3 \n")
        protocols = "OpenFlow13"

		# inicia a criação da rede
        net = Mininet(switch=OVSSwitch)

        info("*** Creating (reference) controllers\n")
        # cria o controlador que será utilizado na rede
        c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)

        info("*** Criando os switches\n")
        s1 = net.addSwitch('s1', protocols=protocols)
        s2 = net.addSwitch('s2', protocols=protocols)

        info("*** Criando os hosts\n")
        # cria os hosts 1 e 2
        h1 = net.addHost(name='h1', ip='10.0.0.1', mac='00:00:00:00:00:01', defaultHost='')
        h2 = net.addHost(name='h2', ip='10.0.0.2', mac='00:00:00:00:00:02', defaultHost='')
     

        info("*** Creating links\n")
        # adiciona a conexao entre o host 1 e o switch 1
        net.addLink(h1, s1)
        # adiciona a conexao entre o switch 1 e o switch 2
        net.addLink(s1, s2)
        # adiciona a conexao entre o host 2 e o switch 2
        net.addLink(h2, s2)

        info("*** Criando a rede\n")
        net.build()
        # inicia o controlador da rede
        s1.start([c1])
        # incializa a rede
        net.start()
        net.staticArp()
        # inicia o CLI do Mininet
        CLI(net)
        net.stop()


topos = {'simple_scenario_topo': (lambda: SimpleScenarioTopo())}
