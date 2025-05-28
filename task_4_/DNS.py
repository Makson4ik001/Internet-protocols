import dns.message
import dns.query
import dns.rdatatype
import socket
import threading
import time
import json
import os

CACHE_FILE = "dns_cache.json"
UPSTREAM_SERVER = "8.8.8.8"
PORT = 53
CACHE_TTL_CHECK_INTERVAL = 60  # seconds

cache = {}  # {name -> [records]}
reverse_cache = {}  # {ip -> name} for PTR

def save_cache():
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'cache': cache,
            'timestamp': time.time()
        }, f)

def load_cache():
    global cache
    if not os.path.exists(CACHE_FILE):
        return
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            cache = data.get("cache", {})
    except Exception as e:
        print(f"[!] Failed to load cache: {e}")

def is_record_valid(record):
    now = time.time()
    return record["timestamp"] + record["ttl"] > now

def get_cached_records(name):
    records = cache.get(name, [])
    valid_records = [r for r in records if is_record_valid(r)]
    return valid_records

def add_records_to_cache(name, rtype, rdata, ttl):
    timestamp = time.time()
    record = {
        "type": dns.rdatatype.to_text(rtype),
        "data": str(rdata),
        "ttl": ttl,
        "timestamp": timestamp
    }

    if name not in cache:
        cache[name] = []
    cache[name].append(record)

def parse_dns_response(response):
    for section in [response.answer, response.authority, response.additional]:
        for rrset in section:
            name = str(rrset.name)
            rtype = rrset.rdtype
            if rtype not in [dns.rdatatype.A, dns.rdatatype.AAAA, dns.rdatatype.NS, dns.rdatatype.PTR]:
                continue
            for rdata in rrset:
                ttl = rrset.ttl
                add_records_to_cache(name, rtype, rdata, ttl)

def query_upstream(request_data):
    try:
        upstream_request = dns.message.from_wire(request_data)
        response = dns.query.udp(upstream_request, UPSTREAM_SERVER, timeout=5)
        parse_dns_response(response)
        return response.to_wire()
    except Exception as e:
        print(f"[!] Upstream error: {e}")
        return None

def handle_dns(data, addr, sock):
    try:
        request = dns.message.from_wire(data)
        qname = str(request.question[0].name)
        qtype = dns.rdatatype.to_text(request.question[0].rdtype)
        print(f"[+] Получен запрос от {addr} на {qname} ({qtype})")

        cached = get_cached_records(qname)
        if cached:
            print(f"[+] Ответ найден в кэше: {qname}")
            # TODO: реализовать генерацию ответа из кэша
            return

        print(f"[ ] Запрашиваем данные у upstream для: {qname}")
        response_wire = query_upstream(data)

        # 👇 Сюда добавляем проверку длины ответа
        if response_wire and len(response_wire) > 0:
            print(f"[+] Отправляем ответ клиенту {addr}")
            sock.sendto(response_wire, addr)
        else:
            print(f"[!] Не удалось получить или отправить ответ")
    except Exception as e:
        print(f"[!] Ошибка при обработке запроса: {e}")

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))

    print(f"[*] Listening on port {PORT}...")
    while True:
        data, addr = sock.recvfrom(512)
        threading.Thread(target=handle_dns, args=(data, addr, sock)).start()

def clean_cache_periodically():
    now = time.time()
    for name in list(cache.keys()):
        cache[name] = [r for r in cache[name] if is_record_valid(r)]
        if not cache[name]:
            del cache[name]
    save_cache()
    threading.Timer(CACHE_TTL_CHECK_INTERVAL, clean_cache_periodically).start()

if __name__ == "__main__":
    load_cache()
    threading.Thread(target=clean_cache_periodically).start()
    try:
        start_server()
    except KeyboardInterrupt:
        print("[*] Shutting down...")
        save_cache()
        print("[*] Cache saved.")