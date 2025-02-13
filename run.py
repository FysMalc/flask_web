from app import create_app

app = create_app()  # Define app at the top level for Gunicorn

if __name__ == '__main__':
    from waitress import serve
    import socket

    def get_ip():
        """Get the local IP address of the machine"""
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return hostname, local_ip

    hostname, local_ip = get_ip()  # Get local IP address
    port = 8000
    print(f"\nStarting server...")
    print(f"Local access:      http://localhost:{port}")
    print(f"Network access:"
          f"\n      http://{hostname}:{port}"
          f"\n      http://{local_ip}:{port} ")
    print(f"\nPress Ctrl+C to stop the server.\n")

    serve(app, host='0.0.0.0', port=port, threads=2)
