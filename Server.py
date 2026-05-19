import datetime
import socket
import threading

TCP_HOST = '0.0.0.0'
TCP_PORT = 8000  
UDP_PORT = 9000


def parse_request(raw_bytes):
    # HTTP request selalu diakhiri \r\n\r\n
    header_end = raw_bytes.find(b'\r\n\r\n')
    if header_end == -1:
        return None, None
    
    header_section = raw_bytes[:header_end].decode('utf-8', errors='replace')
    lines = header_section.split('\r\n')
    
    # Baris pertama: "GET /index.html HTTP/1.1"
    request_line = lines[0]
    parts = request_line.split(' ')
    
    method = parts[0]   # "GET"
    path   = parts[1]   # "/index.html"
    
    return method, path

def build_response(status_code, status_text, content_type, body_bytes):
    headers  = f"HTTP/1.1 {status_code} {status_text}\r\n"
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body_bytes)}\r\n"
    headers += "Connection: close\r\n"
    headers += "\r\n"   # baris kosong = pemisah wajib header-body
    
    return headers.encode() + body_bytes

def serve_file(path):
    # Keamanan: hilangkan leading slash, larang path traversal
    filename = path.lstrip('/')
    if filename == '':
        filename = 'index.html'
    if '..' in filename:   # cegah path traversal
        return build_response(403, 'Forbidden', 'text/plain', b'403 Forbidden')
    
    try:
        with open(filename, 'rb') as f:
            content = f.read()
        return build_response(200, 'OK', 'text/html; charset=utf-8', content)
    
    except FileNotFoundError:
        body = b'<h1>404 Not Found</h1>'
        return build_response(404, 'Not Found', 'text/html', body)
    
    except Exception as e:
        body = f'<h1>500 Internal Server Error</h1><p>{e}</p>'.encode()
        return build_response(500, 'Internal Server Error', 'text/html', body)
    
def log(client_ip, file_path, status_code):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[SERVER] {timestamp} | {client_ip} | {file_path} | {status_code}")

def run_udp_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((TCP_HOST, UDP_PORT))
    print(f"[SERVER] UDP Echo listening on port {UDP_PORT}")
    
    while True:
        data, addr = udp_sock.recvfrom(1024)
        # echo: kirim balik PERSIS payload yang diterima
        udp_sock.sendto(data, addr)

def handle_tcp_client(conn, addr):
    """Dijalankan di thread terpisah per koneksi"""
    try:
        data = b''
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\r\n\r\n' in data:   # header sudah lengkap
                break
        
        method, path = parse_request(data)
        if method == 'GET':
            response = serve_file(path)
            conn.sendall(response)
            log(addr[0], path, '200')  # sesuaikan status
    finally:
        conn.close()

def run_tcp_server():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind((TCP_HOST, TCP_PORT))
    tcp_sock.listen(10)
    print(f"[SERVER] TCP HTTP listening on port {TCP_PORT}")
    
    while True:
        conn, addr = tcp_sock.accept()
        t = threading.Thread(target=handle_tcp_client, args=(conn, addr))
        t.daemon = True
        t.start()

# Main: jalankan TCP dan UDP di thread terpisah
if __name__ == '__main__':
    udp_thread = threading.Thread(target=run_udp_server)
    udp_thread.daemon = True
    udp_thread.start()
    
    run_tcp_server()  # jalan di main thread