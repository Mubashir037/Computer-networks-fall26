# K24-1038 Mubashir Sikandar

import socket
import struct
import random


DNS_PORT = 53


def check_domain(domain):
    # check if domain looks valid

    if not domain:
        return False

    if len(domain) > 253:
        return False

    if domain.endswith("."):
        domain = domain[:-1]

    parts = domain.split(".")

    for part in parts:

        if not part:
            return False

        if len(part) > 63:
            return False

        if part.startswith("-") or part.endswith("-"):
            return False

        for ch in part:
            if not (ch.isalnum() or ch == "-"):
                return False

    return True


def make_domain(domain):
    # change domain into dns format

    result = b""

    for part in domain.rstrip(".").split("."):
        result += struct.pack("B", len(part))
        result += part.encode()

    result += b"\x00"

    return result


def make_query(domain):
    # make dns query packet

    transaction_id = random.randint(0, 65535)

    # recursion desired
    flags = 0x0100

    # one question
    questions = 1

    answers = 0
    authority = 0
    additional = 0

    header = struct.pack(
        "!HHHHHH",
        transaction_id,
        flags,
        questions,
        answers,
        authority,
        additional
    )

    # make domain part
    question = make_domain(domain)

    # QTYPE 1 means A record
    # QCLASS 1 means internet
    question += struct.pack("!HH", 1, 1)

    return header + question, transaction_id


def read_domain(data, offset):
    # read domain name from response

    names = []
    old_offset = offset
    jumped = False
    jumps = 0

    while True:

        if offset >= len(data):
            raise ValueError("Bad domain name in response.")

        length = data[offset]

        # end of name
        if length == 0:
            offset += 1
            break

        # compressed name
        if (length & 0xC0) == 0xC0:

            if offset + 1 >= len(data):
                raise ValueError("Bad compression pointer.")

            pointer = ((length & 0x3F) << 8) | data[offset + 1]

            if pointer >= len(data):
                raise ValueError("Bad compression pointer.")

            if not jumped:
                old_offset = offset + 2

            offset = pointer
            jumped = True

            jumps += 1

            if jumps > 20:
                raise ValueError("Too many jumps in domain name.")

        else:

            if length > 63:
                raise ValueError("Bad domain label length.")

            offset += 1

            if offset + length > len(data):
                raise ValueError("Domain name goes outside response.")

            name_part = data[
                offset:offset + length
            ].decode(errors="replace")

            names.append(name_part)

            offset += length

    name = ".".join(names)

    if jumped:
        return name, old_offset

    return name, offset


def read_response(data, transaction_id):
    # read dns response

    if len(data) < 12:
        raise ValueError("Response is too short.")

    # read header
    got_id, flags, qdcount, ancount, nscount, arcount = struct.unpack(
        "!HHHHHH",
        data[:12]
    )

    # check id
    if got_id != transaction_id:
        raise ValueError("Transaction ID does not match.")

    # get response code
    rcode = flags & 0x000F

    status = {
        0: "NOERROR",
        1: "FORMERR",
        2: "SERVFAIL",
        3: "NXDOMAIN",
        4: "NOTIMP",
        5: "REFUSED"
    }.get(rcode, f"Unknown ({rcode})")

    # get important flags
    qr = (flags >> 15) & 1
    aa = (flags >> 10) & 1
    tc = (flags >> 9) & 1
    rd = (flags >> 8) & 1
    ra = (flags >> 7) & 1

    print("\n----------------------------------------")
    print("DNS RESPONSE")
    print("----------------------------------------")

    print(f"Transaction ID : {got_id}")
    print(f"Flags          : 0x{flags:04X}")
    print(f"QR             : {qr}")
    print(f"AA             : {aa}")
    print(f"TC             : {tc}")
    print(f"RD             : {rd}")
    print(f"RA             : {ra}")
    print(f"Response Status: {status}")

    if qr != 1:
        raise ValueError("This is not a DNS response.")

    # read question
    if qdcount < 1:
        raise ValueError("No question found.")

    offset = 12

    question_name, offset = read_domain(
        data,
        offset
    )

    if offset + 4 > len(data):
        raise ValueError("Bad question section.")

    qtype, qclass = struct.unpack(
        "!HH",
        data[offset:offset + 4]
    )

    offset += 4

    type_name = {
        1: "A",
        2: "NS",
        5: "CNAME",
        28: "AAAA"
    }.get(qtype, str(qtype))

    print("\nQuestion:")
    print(f"Name           : {question_name}")
    print(f"Type           : {type_name}")

    print(f"\nAnswer Records : {ancount}")

    # check unsuccessful response
    if rcode != 0:

        if status == "NXDOMAIN":
            print("\nThe domain does not exist.")
        else:
            print(f"\nDNS query failed: {status}")

        return

    found_ip = False

    # read answer records
    for i in range(ancount):

        answer_name, offset = read_domain(
            data,
            offset
        )

        # type + class + ttl + data length
        if offset + 10 > len(data):
            raise ValueError("Bad answer record.")

        answer_type, answer_class, ttl, data_len = struct.unpack(
            "!HHIH",
            data[offset:offset + 10]
        )

        offset += 10

        if offset + data_len > len(data):
            raise ValueError("Bad answer data.")

        record_data = data[
            offset:offset + data_len
        ]

        offset += data_len

        # A record
        if answer_type == 1:

            if data_len != 4:
                raise ValueError("Bad A record.")

            ip = socket.inet_ntoa(record_data)

            print("\nAnswer:")
            print(f"Name           : {answer_name}")
            print("Type           : A")
            print(f"IP Address     : {ip}")
            print(f"TTL            : {ttl} seconds")

            found_ip = True

        else:

            print("\nAnswer:")
            print(f"Name           : {answer_name}")
            print(f"Type           : {answer_type}")
            print(f"TTL            : {ttl} seconds")

    if not found_ip:
        print("\nNo IPv4 A record found.")


def lookup(domain, dns_server):
    # send dns query and get response

    sock = None

    try:

        query, transaction_id = make_query(domain)

        # make udp socket
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        # wait maximum 5 seconds
        sock.settimeout(5)

        print("\nSending DNS query...")
        print(f"DNS Server     : {dns_server}")
        print(f"DNS Port       : {DNS_PORT}")

        # send query to port 53
        sock.sendto(
            query,
            (dns_server, DNS_PORT)
        )

        # get response
        response, server = sock.recvfrom(4096)

        print(
            f"Response From  : "
            f"{server[0]}:{server[1]}"
        )

        # read response
        read_response(
            response,
            transaction_id
        )

    except socket.timeout:
        print("\nError: DNS request timed out.")

    except ValueError as e:
        print(f"\nDNS Response Error: {e}")

    except OSError as e:
        print(f"\nSocket Error: {e}")

    except Exception as e:
        print(f"\nUnexpected Error: {e}")

    finally:

        if sock is not None:
            sock.close()


def main():

    print("========================================")
    print("          DNS QUERY RESOLVER")
    print("========================================")

    # get dns server from user
    dns_server = input(
        "Enter DNS Server IP: "
    ).strip()

    # check dns server ip
    try:
        socket.inet_aton(dns_server)
    except OSError:
        print("Error: Invalid DNS server IP address.")
        return

    while True:

        domain = input(
            "\nEnter Domain Name: "
        ).strip()

        # check domain
        if not check_domain(domain):
            print(
                "Error: Invalid domain name. "
                "Example: google.com"
            )
            continue

        # do lookup
        lookup(
            domain,
            dns_server
        )

        # ask for another domain
        again = input(
            "\nDo you want another lookup? (y/n): "
        ).strip().lower()

        if again != "y":
            break

    print("\nProgram terminated.")


if __name__ == "__main__":
    main()