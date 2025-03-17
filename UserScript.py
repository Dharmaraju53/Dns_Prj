"""
The client program is expected to pass arguments to this script directly.
Within 2 seconds, if a response is returned, the IP address of the queried
domain name will be printed; otherwise, it prints "Timeout".
"""

import argparse
import socket
from AES import AESCipher


def parse_args():
    """
    Parse arguments from the command-line string.

    Arguments:
    -d, --domain    : the domain name to be queried [required]
    -t, --type      : the type of the query         ["A" by default]
    -c, --class     : the class of the query        ["IN" by default]
    """
    parser = argparse.ArgumentParser(description="Parse DNS arguments from CLI")

    parser.add_argument(
        "-d", "--domain",
        required=True,
        help="The domain name to be queried",
        metavar="QNAME",
        dest="qname",
    )

    parser.add_argument(
        "-t", "--type",
        default="A",
        help="The type of the query (A by default)",
        metavar="QTYPE",
        dest="qtype",
    )

    parser.add_argument(
        "-c", "--class",
        default="IN",
        help="The class of the query (IN by default)",
        metavar="QCLASS",
        dest="qclass",
    )

    parser.add_argument(
        "--ip",
        required=True,
        help="IP address of the resolver",
        metavar="IP",
        dest="resolver_ip",
    )

    parser.add_argument(
        "--port",
        required=True,
        help="Port number that the resolver is listening on",
        metavar="PORT",
        dest="resolver_port",
        type=int,
    )

    parser.add_argument(
        "--protocol",
        default="udp",
        help="Protocol: tcp/udp (default is udp)",
        dest="protocol",
        type=str,
    )

    parser.add_argument(
        "--secure",
        default=1,
        help="1 for encrypted query payload, 0 for plaintext (default is encrypted)",
        dest="secure",
        type=int,
    )

    return parser.parse_args()


def make_query(args_obj) -> str:
    """
    Create a socket and send a query to resolver.
    Return the inquired IP address (if any); otherwise return an error message.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2.5)  # Ensure timeout is not too short

    # Prepare a message for transmission
    msg = f"{args_obj.qname};{args_obj.qtype};{args_obj.qclass};{args_obj.protocol}"
    resolver_address = (args_obj.resolver_ip, args_obj.resolver_port)

    # Send the message to the resolver
    if args_obj.secure != 0:
        msg = b"encrypted\n" + AESCipher().encrypt(msg)
        print("[DEBUG] Sending encrypted query")
    else:
        msg = ("non-encrypted\n" + msg).encode()
        print("[DEBUG] Sending plaintext query")

    try:
        client_socket.sendto(msg, resolver_address)
        print(f"[DEBUG] Query sent to resolver at {resolver_address}")

        # Receive the response
        response_bytes, _ = client_socket.recvfrom(1024)
        print(f"[DEBUG] Raw response received: {response_bytes}")

        # Decrypt response
        response = AESCipher().decrypt(response_bytes) if args_obj.secure != 0 else response_bytes.decode("utf-8")
        print(f"[DEBUG] Decrypted response: {response}")

        # Check if response is valid
        if not response.strip():
            print("[ERROR] Empty response received")
            response = "[ERROR] Empty response"

    except socket.timeout:
        print("[ERROR] Query timed out")
        response = "[EXCEPTION] Timeout"

    except Exception as e:
        print(f"[ERROR] Exception while receiving response: {e}")
        response = "[EXCEPTION] " + str(e)

    finally:
        client_socket.close()

    return response


if __name__ == "__main__":
    args = parse_args()

    try:
        response = make_query(args)
    except socket.timeout:
        response = "[EXCEPTION] Timeout"
    except Exception as e:
        response = "[EXCEPTION] " + str(e)
    
    print(response)
