import socket

host = '8.8.8.8'
port = 53
print(f"Connecting to {host}:{port}...")
try:
    s = socket.create_connection((host, port), timeout=2)
    print("Success!")
    s.close()
except Exception as e:
    print(f"Error: {e}")
