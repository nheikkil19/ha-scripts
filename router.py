import subprocess


def scan_network() -> str:
    result = subprocess.run(['arp', '-a'], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def get_network_devices() -> list:
    devices = []
    for line in scan_network().split('\n'):
        if 'on' in line:
            parts = line.split(' ')
            devices.append(parts[3])
    return devices


if __name__ == '__main__':
    print(get_network_devices())

