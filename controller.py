#code from https://github.com/LABORA-INF-UFG/PIBIC-Katia/


from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

# As regras abaixo funcionam para uma rede de 2 switches
# sendo que cada switch possui um host ligado a si

TOPOLOGY = {
	"00:00:00:00:00:01": {
        "00:00:00:00:00:02": {
            1: {'in_port': 1, 'out_port': 2},
            2: {'in_port': 1, 'out_port': 2},
        },
        # "00:00:00:00:00:03": {
        #     1: {'in_port': 1, 'out_port': 2},
        #     2: {'in_port': 1, 'out_port': 3},
        # }
    },
    "00:00:00:00:00:02": {
        "00:00:00:00:00:01": {
            1: {'in_port': 2, 'out_port': 1},
            2: {'in_port': 2, 'out_port': 1},
        },
    },
    # "00:00:00:00:00:03": {
    #     "00:00:00:00:00:01": {
    #         1: {'in_port': 2, 'out_port': 1},
    #         2: {'in_port': 3, 'out_port': 1},
    #     },
    # },
}


class SimpleScenario13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleScenario13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser


        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


	# adiciona o fluxo na tabela
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        # cria um "flow" (regra) a partir da topologia de rede
        dst = eth.dst # nó de destino
        src = eth.src # nó de origem
        dpid = datapath.id # identificador do switch 

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        if src in TOPOLOGY:
            if dst in TOPOLOGY[src]:
                if dpid in TOPOLOGY[src][dst]:
                    if in_port == TOPOLOGY[src][dst][dpid]['in_port']:
                        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                        out_port = TOPOLOGY[src][dst][dpid]['out_port']
                        actions = [parser.OFPActionOutput(out_port)]
                        # verifica se existe um id válido, para evitar o envio de
                        # flow_mod e packet_out
                        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                            return
                        else:
                            self.add_flow(datapath, 1, match, actions)

                        # envia o pacote agora, pelo controlador. o proximo será encaminhado normalmente pelo switch
                        # isso eh usado para evitar que o primeiro pacote seja perdido, pois não existe 
                        # uma regra criada
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
