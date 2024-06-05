import subprocess
import time


def get_ip_address(mac: str) -> str:
    mac = mac.lower()
    result = subprocess.run(["arp", "-a"], stdout=subprocess.PIPE)
    for line in result.stdout.decode("utf-8").split("\n"):
        print(line)
        if mac in line:
            return line.split()[1].lower().strip("()")
    return ""


def ping(ip: str) -> bool:
    result = subprocess.run(["ping", "-c", "1", ip], stdout=subprocess.PIPE)
    return result.returncode == 0


def is_device_present(mac: str, retry: int = 1) -> bool:
    ip = get_ip_address(mac)
    if ip:
        for _ in range(retry):
            if ping(ip):
                return True
            time.sleep(1)
    return False


if __name__ == "__main__":
    print(is_device_present("AA:BB:CC:DD:EE:FF"))
