import os
import hashlib
import socket
import time

CACHE_DIR = 'cache'

def build_response(status_code, status_text, content_type, body_bytes):
    headers  = f"HTTP/1.1 {status_code} {status_text}\r\n"
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body_bytes)}\r\n"
    headers += "Connection: close\r\n"
    headers += "\r\n"   # baris kosong = pemisah wajib header-body
    
    return headers.encode() + body_bytes

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

def get_cache_path(url_path):
    """Konversi URL path ke nama file cache yang aman"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Gunakan hash untuk menghindari karakter ilegal di nama file
    safe_name = url_path.strip('/').replace('/', '_') or 'root'
    # Contoh: "/index.html" → "index.html"
    #         "/folder/page" → "folder_page"
    return os.path.join(CACHE_DIR, safe_name + '.cache')

def cache_exists(url_path):
    return os.path.exists(get_cache_path(url_path))

def read_cache(url_path):
    with open(get_cache_path(url_path), 'rb') as f:
        return f.read()

def write_cache(url_path, response_bytes):
    with open(get_cache_path(url_path), 'wb') as f:
        f.write(response_bytes)

def forward_to_server(request_bytes, server_ip, server_port, timeout=5):
    """
    Kirim request ke server, kembalikan response.
    Raises: ConnectionRefusedError, socket.timeout
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        
        try:
            s.connect((server_ip, server_port))
        except (ConnectionRefusedError, OSError):
            raise ConnectionRefusedError("Server tidak terjangkau")
        
        s.sendall(request_bytes)
        
        # Kumpulkan response sampai koneksi tutup
        response = b''
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break
    
    return response

def handle_client(conn, addr, server_ip, server_port):
    start_time = time.time()
    
    # Terima request dari client
    request_data = b''
    while b'\r\n\r\n' not in request_data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        request_data += chunk
    
    # Parse URL path dari request
    method, url_path = parse_request(request_data)
    
    cache_status = 'MISS'
    
    if cache_exists(url_path):
        # Cache HIT: ambil dari file
        cache_status = 'HIT'
        response = read_cache(url_path)
    
    else:
        # Cache MISS: forward ke server
        try:
            response = forward_to_server(request_data, server_ip, server_port)
            
            # Cek apakah server mengembalikan error
            if response.startswith(b'HTTP/1.1 5'):
                response = build_response(502, 'Bad Gateway','text/html', b'<h1>502 Bad Gateway</h1>')
            else:
                write_cache(url_path, response)   # simpan ke cache
        
        except (ConnectionRefusedError, socket.timeout):
            response = build_response(504, 'Gateway Timeout','text/html', b'<h1>504 Gateway Timeout</h1>')
    
    conn.sendall(response)
    conn.close()
    
    elapsed = (time.time() - start_time) * 1000
    print(f"[PROXY] {addr[0]} | {url_path} | {cache_status} | {elapsed:.1f}ms")

def handle_client(conn, addr, server_ip, server_port):
    start_time = time.time()
    
    # Terima request dari client
    request_data = b''
    while b'\r\n\r\n' not in request_data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        request_data += chunk
    
    # Parse URL path dari request
    method, url_path = parse_request(request_data)
    
    cache_status = 'MISS'
    
    if cache_exists(url_path):
        # Cache HIT: ambil dari file
        cache_status = 'HIT'
        response = read_cache(url_path)
    
    else:
        # Cache MISS: forward ke server
        try:
            response = forward_to_server(request_data, server_ip, server_port)
            
            # Cek apakah server mengembalikan error
            if response.startswith(b'HTTP/1.1 5'):
                response = build_response(502, 'Bad Gateway','text/html', b'<h1>502 Bad Gateway</h1>')
            else:
                write_cache(url_path, response)   # simpan ke cache
        
        except (ConnectionRefusedError, socket.timeout):
            response = build_response(504, 'Gateway Timeout','text/html', b'<h1>504 Gateway Timeout</h1>')
    
    conn.sendall(response)
    conn.close()
    
    elapsed = (time.time() - start_time) * 1000
    print(f"[PROXY] {addr[0]} | {url_path} | {cache_status} | {elapsed:.1f}ms")