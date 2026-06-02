import socket
import time
import statistics
import csv
import os
from datetime import datetime

# BAGIAN 1: FUNGSI HTTP (TCP)
def build_get_request(host, path):
    """Buat raw HTTP GET request"""
    request  = f"GET {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"
    return request.encode()

def http_get(proxy_ip, proxy_port, path='/index.html'):
    """Mengirim HTTP GET ke Proxy dan menerima response"""
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
    if sep != -1:
        headers = response[:sep].decode()
        body    = response[sep+4:]
        
        print("=== HEADERS ===")
        print(headers)
        print("=== BODY ===")
        print(body.decode('utf-8', errors='replace'))
    else:
        print("Response tidak valid atau kosong.")
# BAGIAN 2: FUNGSI QoS (UDP)
def format_ping_payload(seq):
    """Membuat payload ping dengan sequence dan timestamp"""
    timestamp = time.time()
    payload = f"Ping {seq} {timestamp}"
    return payload.encode()

def parse_ping_payload(data):
    """Kembalikan (seq, sent_timestamp) dari payload"""
    parts = data.decode().split(' ')
    seq       = int(parts[1])
    timestamp = float(parts[2])
    return seq, timestamp

def save_log_to_csv(stats, filename="pengujian_qos.csv"):
    """Menyimpan hasil statistik QoS ke dalam file CSV tabular"""
    # Cek apakah file sudah ada untuk menentukan penulisan header
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as file:
        # Menentukan nama-nama kolom (sesuai spesifikasi)
        fieldnames = [
            'Waktu_Uji', 'Paket_Dikirim', 'Paket_Diterima', 
            'Packet_Loss(%)', 'Min_RTT(ms)', 'Avg_RTT(ms)', 
            'Max_RTT(ms)', 'Jitter(ms)'
        ]
        
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=',')
        
        # Tulis baris judul kolom jika file baru pertama kali dibuat
        if not file_exists:
            writer.writeheader()
            
        # Tulis data statistik ke baris baru
        writer.writerow(stats)
    
    print(f"[LOG] Hasil pengujian QoS berhasil disimpan ke '{filename}'")

def print_qos_stats(rtt_list, sent, received):
    """Mencetak statistik ke terminal dan memanggil fungsi simpan CSV"""
    lost = sent - received
    loss_pct = (lost / sent) * 100
    
    print("\n===== QoS Statistics =====")
    print(f"Packets: Sent={sent}, Received={received}, Lost={lost} ({loss_pct:.0f}% loss)")
    
    # Siapkan variabel default jika paket hilang semua
    min_rtt = avg_rtt = max_rtt = jitter = 0.0
    
    if rtt_list:
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        avg_rtt = sum(rtt_list) / len(rtt_list)
        
        # Jitter = rata-rata selisih RTT antar paket berurutan
        if len(rtt_list) >= 2:
            diffs  = [abs(rtt_list[i] - rtt_list[i-1]) for i in range(1, len(rtt_list))]
            jitter = sum(diffs) / len(diffs)
        
        print(f"RTT Min = {min_rtt:.3f} ms")
        print(f"RTT Avg = {avg_rtt:.3f} ms")
        print(f"RTT Max = {max_rtt:.3f} ms")
        print(f"Jitter  = {jitter:.3f} ms")
    else:
        print("Semua paket hilang — tidak ada data RTT.")
    # Bungkus hasil ke dalam dictionary agar rapi masuk ke kolom CSV
    stats_data = {
        'Waktu_Uji': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Paket_Dikirim': sent,
        'Paket_Diterima': received,
        'Packet_Loss(%)': round(loss_pct, 2),
        'Min_RTT(ms)': round(min_rtt, 3),
        'Avg_RTT(ms)': round(avg_rtt, 3),
        'Max_RTT(ms)': round(max_rtt, 3),
        'Jitter(ms)': round(jitter, 3)
    } 
    save_log_to_csv(stats_data)

    def run_qos(server_ip, server_port=9000, count=10):
    """Menjalankan pengujian ping UDP ke server"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)   # timeout per paket: 1 detik
    
    rtt_list   = []
    sent       = 0
    received   = 0
    
    print(f"Memulai pengujian QoS ping ke {server_ip}:{server_port}...\n")
    
    for seq in range(1, count + 1):
        payload = format_ping_payload(seq)
        
        sent += 1
        send_time = time.time()
        sock.sendto(payload, (server_ip, server_port))
        
        try:
            data, _ = sock.recvfrom(1024)
            recv_time = time.time()
            
            rtt = (recv_time - send_time) * 1000   # konversi ke ms
            rtt_list.append(rtt)
            received += 1
            
            print(f"Reply seq={seq}: RTT = {rtt:.3f} ms")
            
        except socket.timeout:
            print(f"Request seq={seq}: Request timed out")
            
        time.sleep(0.2)   # jeda antar paket agar tidak membanjiri jaringan terlalu cepat
        
    sock.close()
    print_qos_stats(rtt_list, sent, received)

    # BAGIAN 3: BLOK EKSEKUSI UTAMA

    if __name__ == '__main__':
    # KONFIGURASI IP DAN PORT (Ubah sesuai dengan IP saat pengujian jaringan Wi-Fi)
    # Default menggunakan localhost untuk pengujian di satu komputer
    PROXY_IP = '127.0.0.1' 
    PROXY_TCP_PORT = 8080
    
    SERVER_IP = '127.0.0.1'
    SERVER_UDP_PORT = 9000
    
    # 1. Menjalankan Mode HTTP (TCP)
    print("=== MENGUJI KONEKSI HTTP (TCP) ===")
    try:
        http_get(PROXY_IP, PROXY_TCP_PORT, '/index.html')
    except ConnectionRefusedError:
        print(f"Gagal terhubung ke Proxy di {PROXY_IP}:{PROXY_TCP_PORT}. Pastikan Proxy berjalan.")
    except Exception as e:
        print(f"Terjadi kesalahan pada HTTP GET: {e}")

    print("\n" + "="*50 + "\n")
    
    # 2. Menjalankan Mode QoS (UDP)
    print("=== MENGUJI KONEKSI QoS (UDP) ===")
    run_qos(SERVER_IP, SERVER_UDP_PORT, count=10)
    
    print("\n" + "="*50 + "\n")
    print("Pengujian selesai. Periksa file 'pengujian_qos.csv' untuk hasil QoS dalam format tabular.")