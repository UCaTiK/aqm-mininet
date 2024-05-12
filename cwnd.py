from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
import time, os


def create_network():
    # Create Mininet network with remote controller and specified switches and links
    net = Mininet(switch=OVSSwitch, link=TCLink)
    #net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    # Add switches
    switch1 = net.addSwitch('s1', failMode='standalone')
    switch2 = net.addSwitch('s2', failMode='standalone')

    net.addLink(switch1, switch2)

    # Create hosts and connect them to the first switch
    for i in range(1, 11):
        h = net.addHost(f'h{i}')
        if i <= 5:
            net.addLink(h, switch2)
        else:
            net.addLink(h, switch1)

    # Start Mininet
    net.start()

    # Configure TBF on switch interface
    print(switch1.cmd('tc qdisc add dev s1-eth1 root handle 1: tbf rate 10mbit burst 15kbit limit 25600k'))
    print(switch1.cmd('tc qdisc add dev s1-eth1 parent 1: handle 10: pfifo_fast'))

    # Configure RED on switch interface
    #switch1.cmd('tc qdisc add dev s1-eth1 parent 1:1 handle 10: red limit 1000000 avpkt 1000 burst 1000 probability 0.02')

    # Start iperf3 server
    for i in range(1, 6):
        receiver = net.get(f'h{i}')
        receiver.cmd('iperf3 -s &')

    time.sleep(1)
    start = time.time()

    # Start iperf3 clients on the sources
    for i in range(6, 11):
        h = net.get(f'h{i}')
        receiver = net.get(f'h{i-5}')
        if i == 10:
            with open("raw_cwnd.txt", "w") as f:
                f.write(h.cmd(f'iperf3 -c {receiver.IP()} -P 10 -i 0.1' + ' | sed "s/ \{1,\}/ /g"'))
        else:
            h.cmd(f'iperf3 -c {receiver.IP()} -P 10 &')

    # Start Mininet CLI for user interaction
    net.stop()

if __name__ == '__main__':
    create_network()

