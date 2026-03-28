import socket

host = '54.191.92.189'
port = 443
print(f"Connecting to {host}:{port}...")
try:
    s = socket.create_connection((host, port), timeout=5)
    print("Success!")
    s.close()
except Exception as e:
    print(f"Error: {e}")
