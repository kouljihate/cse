"""Scan LAN for MongoDB servers on port 27017."""

import ipaddress
import socket
import struct
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

SCAN_PORT = 27017
TIMEOUT = 1.5
MAX_WORKERS = 50


def get_local_networks():
    hosts = []
    hostname = socket.gethostname()
    for info in socket.getaddrinfo(hostname, None):
        ip = info[4][0]
        if ip.count(".") == 3 and not ip.startswith("127."):
            hosts.append(ip)
    return hosts


def ip_to_int(ip):
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def int_to_ip(n):
    return socket.inet_ntoa(struct.pack("!I", n))


def guess_subnet(local_ip):
    first_octet = int(local_ip.split(".")[0])
    if first_octet < 128:
        return str(ipaddress.IPv4Network(f"{local_ip}/8", strict=False))
    elif first_octet < 192:
        return str(ipaddress.IPv4Network(f"{local_ip}/16", strict=False))
    else:
        return str(ipaddress.IPv4Network(f"{local_ip}/24", strict=False))


def probe_mongodb(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((host, port))

        import struct as s
        op_msg = 2013
        flags = 0
        sections = b"\x00" + b'{"isMaster":1}\x00'
        body = s.pack("<i", flags) + sections
        header = s.pack("<iiii", 16 + len(body), 0, 0, op_msg)
        sock.sendall(header + body)

        data = b""
        while len(data) < 36:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk

        sock.close()
        return b"ok" in data
    except Exception:
        return False


def scan_host(ip):
    try:
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
	
        result = sock.connect_ex((ip, SCAN_PORT))
        sock.close()
        if ip=="192.168.11.114":
            print(result)
        if result == 0:
            print(f"Scanning {ip}-{result}", end="\r")
            is_mongo = probe_mongodb(ip, SCAN_PORT)
            return ip, True, is_mongo
        return ip, False, False
    except Exception:
        return ip, False, False


def print_results(found):
    if not found:
        print("  No MongoDB servers found.")
        return

    print(f"  {'Host':<20} {'Status':<12} {'Port':<8}")
    print(f"  {'-'*20} {'-'*12} {'-'*8}")
    for host, is_mongo in found:
        status = "MongoDB" if is_mongo else "Port open"
        print(f"  {host:<20} {status:<12} {SCAN_PORT:<8}")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan LAN for MongoDB servers on port 27017"
    )
    parser.add_argument("--subnet", help="CIDR subnet (e.g. 192.168.1.0/24)")
    parser.add_argument("--timeout", type=float, default=TIMEOUT, help=f"Timeout per host (default {TIMEOUT}s)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help=f"Parallel workers (default {MAX_WORKERS})")
    args = parser.parse_args()

    timeout = args.timeout
    workers = args.workers

    if args.subnet:
        network = ipaddress.IPv4Network(args.subnet, strict=False)
    else:
        local_ips = get_local_networks()
        if not local_ips:
            print("Could not detect local network. Use --subnet.")
            sys.exit(1)

        local_ip = local_ips[0]
        guessed = guess_subnet(local_ip)
        print(f"Local IP: {local_ip}")
        print(f"Guessed subnet: {guessed}")
        try:
            network = ipaddress.IPv4Network(guessed, strict=False)
        except Exception:
            print("Could not determine subnet. Use --subnet.")
            sys.exit(1)

    total = network.num_addresses
    print(f"Scanning {total} hosts in {network} on port {SCAN_PORT}...")
    start = datetime.now()

    found_hosts = []
    lock = threading.Lock()
    done = 0
    done_lock = threading.Lock()

    def on_result(future):
        nonlocal done
        ip, port_open, is_mongo = future.result()
        with done_lock:
            done += 1
            if done % max(1, total // 100) == 0:
                pct = done * 100 // total
                #print(f"\r  Progress: {done}/{total} ({pct}%)", file=sys.stderr, end="")
        if port_open:
            with lock:
                found_hosts.append((ip, is_mongo))

    ips = list(network.hosts())
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(scan_host, str(ip)) for ip in ips]
        for f in as_completed(futures):
            on_result(f)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nScan finished in {elapsed:.1f}s ({done} hosts checked)")
    print_results(found_hosts)

    if found_hosts:
        print("Tip: set MONGO_HOST to one of the discovered IPs in .env or use --db-host")


if __name__ == "__main__":
    main()
