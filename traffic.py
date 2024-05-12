from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
import time, os, sys

def create_network():
    alg_name = alg
    command = ""
    if alg == "droptail":
        alg_name = "pfifo"
        command = "pfifo limit 200"
    if alg == "red":
        command = "red limit 6400k min 1280k max 6400k avpkt 128k probability 0.02 burst 55 ecn harddrop"
    if alg == "pie":
        command = "pie limit 200 tupdate 100ms target 50ms"

    # Create Mininet network with remote controller and specified switches and links
    net = Mininet(switch=OVSSwitch, link=TCLink)

    # Add switches
    switch1 = net.addSwitch('s1', failMode='standalone')
    switch2 = net.addSwitch('s2', failMode='standalone')
    net.addLink(switch1, switch2)

    # Create hosts and connect them to the first switch
    for i in range(1, 11):
        h = net.addHost(f'h{i}')
        if i % 2 == 1:
            net.addLink(h, switch2)
        else:
            net.addLink(h, switch1)

    # Start Mininet
    net.start()

    # Configure TBF on switch interface
    print(switch1.cmd('tc qdisc add dev s1-eth1 root handle 1: tbf rate 10mbit burst 15kbit limit 25600k'))
    print(switch1.cmd(f'tc qdisc add dev s1-eth1 parent 1: handle 10: {command}'))

    # Start iperf3 server
    for i in range(1, 11, 2):
        receiver = net.get(f'h{i}')
        receiver.cmd('iperf3 -s &')

    time.sleep(1)
    start = time.time()

    if cwnd == False:
        start_alg(net)
    else:
        start_cwnd(net)

    # Start Mininet CLI for user interaction
    # CLI(net)
    net.stop()

def start_alg(net):
    # Start iperf3 clients on the sources
    for i in range(2, 11, 2):
        h = net.get(f'h{i}')
        receiver = net.get(f'h{i-1}')
        h.cmd(f'iperf3 -c {receiver.IP()} -P 10 &')

    with open("temp.txt", "w") as f:
        i = 1
        while time.time() - start < 10:
            f.write(str(time.time() - start) + " ")
            f.write(str(i) + " " + switch1.cmd('tc -s -d qdisc show dev s1-eth1 | grep -A 5 {alg_name} | grep backlog | tail -n 1 | cut -d " " -f 3,4 | tr -d p'))
            f.write(switch1.cmd(f'tc -s qdisc show dev s1-eth1 | grep -A 5 {alg_name} | grep dropped | tail -n 1 | cut -d " " -f 8 | tr -d ,'))
            i += 1
    with open("temp.txt", "r") as r:
        filename = f"{alg}_results.txt"
        with open(filename, "w") as w:
            string = ""
            for line in r:
                if string == "":
                    string = line[:-1]
                else:
                    string += " " + line
                    w.write(string)
                    string = ""

def start_cwnd(net):
    # Start iperf3 clients on the sources
    for i in range(2, 11, 2):
        h = net.get(f'h{i}')
        receiver = net.get(f'h{i-1}')
        if i == 10:
            filename = f"{alg}_raw_cwnd.txt"
            with open(filename, "w") as f:
                f.write(h.cmd(f'iperf3 -c {receiver.IP()} -P 10 -i 0.1' + ' | sed "s/ \{1,\}/ /g"'))
        else:
            h.cmd(f'iperf3 -c {receiver.IP()} -P 10 &')

if __name__ == '__main__':
    aqm_lst = ['red', 'droptail', 'pie']
    alg = "droptail"
    cwnd = False
    if len(sys.argv) >= 2 and sys.argv[1] in aqm_lst:
        alg = sys.argv[1]
    else:
        print("Default algorithm: Droptail")
    if len(sys.argv) >= 3:
        print("Start application with cwnd mode")
        cwnd = True
    create_network()

