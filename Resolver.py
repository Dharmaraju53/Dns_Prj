import socket
import threading
import os
import time
from Message import Message
from AES import AESCipher
from MessageHeader import MessageHeader
from ParseString import parse_string_msg
from configurator import Configurator
from ParseString import parse_string_question
from Database import Database


class Resolver:
    def __init__(self):
        """Initialize the Resolver."""
        self.database = Database("DatabaseResolver.db")
        Configurator.config_me(9292, 9393)
        Configurator.config_others(int(input("Number of name servers: ")))
        self.this_ns_idx = 0

        # Fix the "clear" error for Windows users
        os.system("cls" if os.name == "nt" else "clear")

    def _use_tcp(self, message: str) -> str:
        """
        Create a TCP connection to the NameServer, then send the message.
        If there is an error while sending and receiving the message, return an error message.
        """
        tcp_resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (
            Configurator.OTHERS[self.this_ns_idx]["ip"],
            Configurator.OTHERS[self.this_ns_idx]["tcp"],
        )
        self.this_ns_idx = (self.this_ns_idx + 1) % len(Configurator.OTHERS)

        tcp_resolver_socket.settimeout(2.0)  # Increased timeout for better stability

        try:
            print(f"[DEBUG] Connecting to NameServer at {server_address} via TCP")
            tcp_resolver_socket.connect(server_address)

            # Encrypt and send message
            bytes_to_send = AESCipher().encrypt(message)
            tcp_resolver_socket.sendall(bytes_to_send)

            # Receive response
            response_bytes = tcp_resolver_socket.recv(Configurator.BUFFER_SIZE)
            print(f"[DEBUG] Raw response received (TCP): {response_bytes}")

            response = AESCipher().decrypt(response_bytes)
            print(f"[DEBUG] Decrypted response (TCP): {response}")

        except Exception as e:
            print(f"[ERROR] TCP Connection failed: {e}")
            response = "Failed-" + str(e)

        finally:
            tcp_resolver_socket.close()
            return response

    def _use_udp(self, message: str) -> str:
        """
        Create a UDP connection to the NameServer, send the message, and retry on failure.
        """
        server_address = (
            Configurator.OTHERS[self.this_ns_idx]["ip"],
            Configurator.OTHERS[self.this_ns_idx]["udp"],
        )
        self.this_ns_idx = (self.this_ns_idx + 1) % len(Configurator.OTHERS)

        udp_resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_resolver_socket.settimeout(2.0)  # Increased timeout to avoid premature failure

        retries = 2  # Retry twice before failing
        for attempt in range(retries):
            try:
                print(f"[DEBUG] Sending query to {server_address} via UDP (Attempt {attempt + 1})")
                bytes_to_send = AESCipher().encrypt(message)
                udp_resolver_socket.sendto(bytes_to_send, server_address)

                # Receive and decrypt response
                response_bytes, _ = udp_resolver_socket.recvfrom(Configurator.BUFFER_SIZE)
                print(f"[DEBUG] Raw response received (UDP): {response_bytes}")

                response = AESCipher().decrypt(response_bytes)
                print(f"[DEBUG] Decrypted response (UDP): {response}")

                # Validate the response format before proceeding
                if not response or len(response.split("\n")) < 5:
                    print(f"[ERROR] Invalid response format: {response}")
                    continue  # Try again with the next retry

                udp_resolver_socket.close()
                return response  # Successful response, return immediately

            except Exception as e:
                print(f"[ERROR] UDP Query failed (Attempt {attempt + 1}): {e}")
                time.sleep(1)  # Wait before retrying

        udp_resolver_socket.close()
        return "Failed-UDP Timeout"

    def query(self, request: Message, tcp: bool = False) -> str:
        """
        Resolve the request.
        Before asking the NameServer, check the cache system for cached records.
        """
        print(f"[DEBUG] Searching cache for {request.question.qname}")

        self.database.refresh()
        cache_record = self.database.query_from_database(
            request.question.qname + ".",
            request.question.qtype,
            request.question.qclass,
        )

        if cache_record is not None:
            print(f"[DEBUG] Cache hit: Found {request.question.qname} -> {cache_record.to_string()}")
            return cache_record.to_string()

        print(f"[DEBUG] Cache miss: Querying NameServer for {request.question.qname}")

        response = self._use_tcp(request.to_string()) if tcp else self._use_udp(request.to_string())

        if response.startswith("Failed"):
            print(f"[ERROR] NameServer lookup failed: {response.split('-')[1]}")
            return response.split("-")[1]
        else:
            message_answer = parse_string_msg(response)
            self.save_to_database(message_answer)

        first_rr = message_answer.answers[0] if message_answer.answers else "[ERROR] No answer section found."
        return first_rr.to_string()

    def save_to_database(self, message_response: Message):
        """Save resolved records to the database."""
        for answer in message_response.answers:
            print(f"[DEBUG] Saving record: {answer}")
            self.database.add_to_database(answer)

        for authority in message_response.authorities:
            self.database.add_to_database(authority)

        for add in message_response.additional:
            self.database.add_to_database(add)

    def start_listening_udp(self):
        """
        Listen for incoming DNS requests and respond.
        """
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener_socket.bind((Configurator.IP, Configurator.UDP_PORT))
        print(f"[RESOLVER] Listening for client requests at {Configurator.IP}:{Configurator.UDP_PORT}...")

        while True:
            try:
                byte_data, client_address = listener_socket.recvfrom(Configurator.BUFFER_SIZE)
                request = byte_data.decode("utf-8").split("\n")

                encrypted = request[0] == "encrypted"
                request = AESCipher().decrypt(request[1]).split(";") if encrypted else request[1].split(";")
                protocol = request.pop()
                request = ";".join(request)

                print(f"[RESOLVER] Received request for {request} from {client_address} using {protocol.upper()}")

                response = ""
                try:
                    question = parse_string_question(request)
                except Exception as e:
                    response = "[EXCEPTION] " + str(e)

                if not response:
                    header = MessageHeader()
                    request_message = Message(header=header, question=question)
                    response = self.query(request=request_message, tcp=(protocol.lower() == "tcp"))

                try:
                    bytes_to_send = AESCipher().encrypt(response) if encrypted else response.encode("utf-8")
                    listener_socket.sendto(bytes_to_send, client_address)
                    print(f"[DEBUG] Response sent to {client_address}")

                except Exception as e:
                    print(f"[ERROR] Failed to send response: {e}")

            except Exception as e:
                print(f"[ERROR] Exception while handling UDP connection: {e}")


if __name__ == "__main__":
    try:
        resolver = Resolver()
        udp_thread = threading.Thread(target=resolver.start_listening_udp)
        udp_thread.start()
    except KeyboardInterrupt:
        print("\n[INFO] Resolver shutting down.")
