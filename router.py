import subprocess
import re


MAC_RE = r"MAC Address: ((?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2}))"


def scan_network(ip: str, mask: int) -> str:
    result = subprocess.run(['nmap', '-T4', '-F', f'{ip}/{mask}'], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def get_network_devices(ip: str, mask: int) -> list:
    devices = []
    for line in scan_network(ip, mask).split('\n'):
        print(line)
        m = re.match(MAC_RE, line)
        if m:
            devices.append(m.group(1))
    return devices


if __name__ == '__main__':
    print(get_network_devices("192.168.1.0", 24))
