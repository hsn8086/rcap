import socket
from loguru import logger
import socks

import threading


# # 设置SOCKS5代理
# socks.set_default_proxy(
#     socks.SOCKS5, "gm.rainplay.cn", 19189, username="test", password="1145141919810"
# )
# socket.socket = socks.socksocket


def handle_client(
    client_socket: socket.socket,
    socks5_host: str,
    socks5_port: int,
    username: str,
    password: str,
):
    """
    处理客户端请求
    """
    # 接收客户端请求数据
    request_data = client_socket.recv(1024)
    # 解析请求报文
    request_lines = request_data.decode().split("\r\n")
    # 获取请求方法、URL和协议版本
    method, url, protocol = request_lines[0].split()
    logger.debug("Method: %s, URL: %s, Ver: %s" % (method, url, protocol))
    server_socket = None
    if method == "CONNECT":
        # 解析URL
        hostname, port = url.split(":")
        port = int(port)
        logger.debug("Host: %s , Port: %s" % (hostname, port))
        # 创建与目标服务器的连接
        server_socket = socks.socksocket()
        server_socket.set_proxy(
            socks.SOCKS5, socks5_host, socks5_port, username=username, password=password
        )
        server_socket.connect((hostname, port))
        # 向客户端发送连接已建立的响应
        client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        # 开始数据传输
        transfer_data(client_socket, server_socket)

    # 关闭连接
    client_socket.close()
    if server_socket is not None:
        server_socket.close()


def transfer(frm, to):
    """
    从客户端到服务器的数据传输
    """

    while True:
        # 从客户端接收数据并发送给服务器
        try:
            client_data = frm.recv(1024)
            to.sendall(client_data)
        except (socket.timeout, socket.error, BrokenPipeError):
            break
        if not client_data:
            break


def transfer_data(client_socket: socket.socket, server_socket: socket.socket):
    """
    在客户端和服务器之间传输数据
    """

    client_socket.settimeout(10)
    server_socket.settimeout(10)
    # 创建线程处理客户端到服务器的数据传输
    client_to_server_thread = threading.Thread(
        target=transfer, args=(client_socket, server_socket), daemon=True
    )
    client_to_server_thread.start()
    # 创建线程处理服务器到客户端的数据传输
    server_to_client_thread = threading.Thread(
        target=transfer, args=(server_socket, client_socket), daemon=True
    )
    server_to_client_thread.start()
    # 等待线程结束
    client_to_server_thread.join()
    server_to_client_thread.join()


def proxy_forever(
    port, socks5_host: str, socks5_port: int, username: str, password: str
):
    # 创建代理服务���套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 设置地址和端口
    server_address = ("127.0.0.1", port)
    # 绑定地址和端口
    server_socket.bind(server_address)
    # 监听连接
    server_socket.listen(5)
    logger.info("Proxy listening on: %s:%d" % server_address)
    try:
        while True:
            # 等待客户端连接
            client_socket, client_address = server_socket.accept()
            logger.debug("Client connect：%s:%d" % client_address)
            # 创建线程处理客户端请求
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, socks5_host, socks5_port, username, password),
                daemon=True,
            )
            client_thread.start()

    finally:
        # 关闭服务器套接字
        server_socket.close()
