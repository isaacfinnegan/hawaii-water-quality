import socket

host = 'eha-cloud.doh.hawaii.gov'
print(f"Resolving {host}...")
try:
    results = socket.getaddrinfo(host, 443)
    for res in results:
        print(f"Family: {res[0]}, Address: {res[4]}")
except Exception as e:
    print(f"Error: {e}")
