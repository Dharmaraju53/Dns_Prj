from Message import Message
from MessageHeader import MessageHeader
from MessageQuestion import MessageQuestion
from ResourceRecord import ResourceRecord
from AES import AESCipher
import dns.query
import dns.zone
import dns.resolver
import dns.exception
import threading
import socket
import os
from ParseString import parse_string_msg
from configurator import Configurator
from Database import Database


class NameServer:
    def __init__(self):
        """
        Initializes the Name Server, binds it to the correct port, and configures the database.
        """
        self.ZONE = None
        self.database = Database("DatabaseNS.db")
        Configurator.config_me(53, 53)  # Ensure this is using port 53

    def handle_query(self, query_message: Message) -> Message:
        """
        Handles incoming DNS queries, either recursively or non-recursively.
        """
        if query_message.header.qr == 0:  # If it's a query (not a response)
            header = query_message.header
            question = query_message.question
            print(f"[SERVER] Handling query for {question.qname}")
            if header.rd is True:
                return self.recursive_query(query_message)
            else:
                return self.non_recursive_query(header, question)

    def recursive_query(self, message_query: Message) -> Message:
        """
        Performs a recursive DNS query.
        """
        print(f"[DEBUG] Looking for {message_query.question.qname} in database...")
        result = self.search_record_in_database(
            message_query.question.qname,
            message_query.question.qtype,
            message_query.question.qclass,
        )

        if result is None:
            print(f"[DEBUG] Not found in database. Checking zone file...")
            result = self.search_record_in_zonefile(
                message_query.question.qname, message_query.question.qtype
            )

        if result is None:
            print(f"[DEBUG] Not found in zone file. Querying external DNS servers...")
            result = self.query_out(message_query)

        return result

    def search_record_in_database(self, qname: str, qtype: int = 1, qclass: int = 1):
        """
        Searches the DNS database for the requested record.
        """
        self.database.refresh()
        return self.database.query_from_database(qname, qtype, qclass)

    def search_record_in_zonefile(self, qname: str, qtype: str):
        """
        Searches the local DNS zone file for a record.
        If no record is found, returns None.
        """
        print(f"[DEBUG] Searching zone file for {qname} (Type: {qtype})...")
        # Placeholder: Implement proper zone file search if needed
        return None

    def query_out(self, message_query: Message):
        """
        Queries an external DNS server if the record is not found locally.
        """
        qname = message_query.question.qname
        qtype = message_query.question.qtype
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["8.8.8.8"]  # Google DNS as fallback

        try:
            resolve_query = resolver.resolve(
                qname, message_query.question.INV_QTYPE[qtype], raise_on_no_answer=False
            )
            print(f"[DEBUG] External DNS query for {qname} succeeded.")

            # Check if there are answers before processing
            if not resolve_query.response.answer:
                print(f"[WARNING] No answer received from external DNS for {qname}.")
                return None

            response_message = self.convert_response_answer_to_response_message(
                resolve_query.response, message_query
            )

            self.save_to_database(response_message)
            return response_message

        except dns.resolver.NoAnswer:
            print(f"[WARNING] No answer available for {qname}.")
            return None
        except dns.resolver.NXDOMAIN:
            print(f"[WARNING] {qname} does not exist (NXDOMAIN).")
            return None
        except dns.exception.DNSException as e:
            print(f"[ERROR] External DNS resolution failed: {e}")
            return None

    def convert_response_answer_to_response_message(self, response_answer, message_query: Message) -> Message:
        """
        Converts an external DNS response into the custom Message format.
        Handles cases where no answer is present.
        """
        message_response = Message(request=message_query)

        # Set the qr flag to 1, which indicates a response
        message_response.header.set_qr_flag()

        # Ensure response sections exist before processing
        for i, section in enumerate([response_answer.answer, response_answer.authority, response_answer.additional]):
            if section:
                for rrset in section:
                    for rr in rrset:
                        resource_record = ResourceRecord(
                            str(rrset.name), int(rr.rdtype), int(rr.rdclass), int(rrset.ttl), str(rr)
                        )
                        if i == 0:
                            message_response.add_a_new_record_to_answer_section(resource_record)
                        elif i == 1:
                            message_response.add_a_new_record_to_authority_section(resource_record)
                        elif i == 2:
                            message_response.add_a_new_record_to_additional_section(resource_record)

        return message_response

    def save_to_database(self, response: Message):
        """
        Saves the resolved DNS records into the local database for caching.
        """
        print(f"[DEBUG] Saving resolved records to database...")
        for answer in response.answers:
            self.database.add_to_database(answer)

    def start_listening_udp(self):
        """
        Starts a UDP listener for incoming DNS queries.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Prevent binding issues
        server_address = (Configurator.IP, Configurator.UDP_PORT)

        try:
            sock.bind(server_address)
            print(f"[SERVER] Listening for UDP connections at {Configurator.IP}:{Configurator.UDP_PORT}...")
        except OSError as e:
            print(f"[ERROR] Failed to bind UDP socket: {e}")
            return

        while True:
            try:
                byte_data, client_address = sock.recvfrom(Configurator.BUFFER_SIZE)
                data_receive = AESCipher().decrypt(byte_data)

                if data_receive:
                    message_query = parse_string_msg(data_receive)
                    print(f"[SERVER] Received request for {message_query.question.qname} via UDP")

                    response = self.handle_query(message_query)

                    if not isinstance(response, str):
                        response = response.to_string()

                    response_data = AESCipher().encrypt(response)
                    sock.sendto(response_data, client_address)
                    print(f"[SERVER] Sent response to {client_address}")

            except Exception as e:
                print(f"[ERROR] Exception while handling UDP connection: {e}")

    def start_listening_tcp(self):
        """
        Starts a TCP listener for incoming DNS queries.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (Configurator.IP, Configurator.TCP_PORT)

        try:
            sock.bind(server_address)
            sock.listen(5)
            print(f"[SERVER] Listening for TCP connections at {Configurator.IP}:{Configurator.TCP_PORT}...")
        except OSError as e:
            print(f"[ERROR] Failed to bind TCP socket: {e}")
            return

        while True:
            try:
                connection, client_address = sock.accept()
                byte_data = connection.recv(Configurator.BUFFER_SIZE)
                data_receive = AESCipher().decrypt(byte_data)

                if not data_receive:
                    continue

                message_query = parse_string_msg(data_receive)
                print(f"[SERVER] Received request for {message_query.question.qname} via TCP")

                response = self.handle_query(message_query)

                if not isinstance(response, str):
                    response = response.to_string()

                response_data = AESCipher().encrypt(response)
                connection.sendall(response_data)
                connection.close()
                print(f"[SERVER] Response sent to {client_address}")

            except Exception as e:
                print(f"[ERROR] Exception while handling TCP connection: {e}")

if __name__ == "__main__":
    try:
        name_server = NameServer()

        udp_thread = threading.Thread(target=name_server.start_listening_udp)
        udp_thread.start()

        tcp_thread = threading.Thread(target=name_server.start_listening_tcp)
        tcp_thread.start()

    except KeyboardInterrupt:
        print("\n[INFO] NameServer shutting down.")
