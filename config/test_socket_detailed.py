import socket

host = '54.191.92.189'
port = 443
print(f"Resolving {host}:{port} with AF_INET...")
try:
    results = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
    for res in results:
        family, type, proto, canonname, sockaddr = res
        print(f"Family: {family}, Type: {type}, Proto: {proto}, Addr: {sockaddr}")
        print(f"Attempting connect to {sockaddr}...")
        s = socket.socket(family, type, proto)
        s.settimeout(2)
        try:
            s.connect(sockaddr)
            print("Success!")
        except Exception as connect_err:
            print(f"Connect error: {connect_err}")
        finally:
            s.close()
except Exception as e:
    print(f"Error: {e}")
