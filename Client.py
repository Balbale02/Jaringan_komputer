import socket
import time

def build_get_request(host, path):
    """Buat raw HTTP GET request"""
    request  = f"GET {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"
    return request.encode()

def http_get(proxy_ip, proxy_port, path='/index.html'):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((proxy_ip, proxy_port))
    
    request = build_get_request(proxy_ip, path)
    sock.sendall(request)
    
    # Terima seluruh response
    response = b''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    sock.close()
    
    # Pisahkan header dan body
    sep = response.find(b'\r\n\r\n')
    headers = response[:sep].decode()
    body    = response[sep+4:]
    
    print("=== HEADERS ===")
    print(headers)
    print("=== BODY ===")
    print(body.decode('utf-8', errors='replace'))


def format_ping_payload(seq):
    timestamp = time.time()
    payload = f"Ping {seq} {timestamp}"
    return payload.encode()

def parse_ping_payload(data):
    """Kembalikan (seq, sent_timestamp) dari payload"""
    parts = data.decode().split(' ')
    seq       = int(parts[1])
    timestamp = float(parts[2])
    return seq, timestamp

def print_qos_stats(rtt_list, sent, received):
    lost = sent - received
    loss_pct = (lost / sent) * 100
    
    print("\n===== QoS Statistics =====")
    print(f"Packets: Sent={sent}, Received={received}, Lost={lost} ({loss_pct:.0f}% loss)")
    
    if rtt_list:
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        avg_rtt = sum(rtt_list) / len(rtt_list)
        
        # Jitter = rata-rata selisih RTT antar paket berurutan
        if len(rtt_list) >= 2:
            diffs  = [abs(rtt_list[i] - rtt_list[i-1]) for i in range(1, len(rtt_list))]
            jitter = sum(diffs) / len(diffs)
        else:
            jitter = 0.0
        
        print(f"RTT Min = {min_rtt:.3f} ms")
        print(f"RTT Avg = {avg_rtt:.3f} ms")
        print(f"RTT Max = {max_rtt:.3f} ms")
        print(f"Jitter  = {jitter:.3f} ms")
    else:
        print("Semua paket hilang — tidak ada data RTT.")