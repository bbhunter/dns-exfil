#!/usr/bin/env python3

import socketserver
import argparse
from copy import deepcopy
from dnslib import DNSRecord
from dnslib.server import BaseResolver


class DNSLoggerHelper:
    @staticmethod
    def parse_suffix(suffix):
        if suffix and not suffix.startswith("."):
            suffix = f".{suffix}"
        if suffix and not suffix.endswith("."):
            suffix += "."
        return suffix

    @staticmethod
    def decode_hex(data):
        try: 
            data = bytes.fromhex(data).decode("utf-8")
        except ValueError:
            pass
        return data

    @staticmethod
    def remove_suffix(data, suffix):
        if suffix and data.endswith(suffix):
            data = data[: -len(suffix)]
        return data


class DNSLogger:
    def __init__(self, suffix="", hex_encoded=False):
        self.suffix = DNSLoggerHelper.parse_suffix(suffix)
        self.hex_encoded = hex_encoded

    def parse_question(self, question):
        if not self.hex_encoded:
            return question

        qname = str(question.get_qname())
        suffixed = DNSLoggerHelper.remove_suffix(qname, self.suffix)
        subdomains = map(DNSLoggerHelper.decode_hex, suffixed.split("."))
        question.set_qname(".".join(subdomains) + self.suffix)
        return question

    def log(self, sender, parsed_req):
        question = self.parse_question(parsed_req.get_q())
        print(f"{sender}: {question}")


class DNSHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, connection = self.request
        parsed_req = DNSRecord.parse(data)
        # (deep copying parsed_req as to not change our coming DNS response)
        self.server.logger.log(self.client_address, deepcopy(parsed_req))
        response = self.server.resolver.resolve(parsed_req, self)
        connection.sendto(response.pack(), self.client_address)


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass


def main():
    # Parse args
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-a",
        "--address",
        dest="host",
        action="store",
        metavar="HOST",
        type=str,
        default="127.0.0.1",
    )
    argparser.add_argument(
        "-p",
        "--port",
        dest="port",
        action="store",
        metavar="PORT",
        type=int,
        default=53,
    )
    argparser.add_argument(
        "-he",
        "--hex-encoded",
        dest="hex_encoded",
        action="store_true",
        help="If DNS requests will be hex encoded",
    )
    argparser.add_argument(
        "-s",
        "--suffix",
        dest="suffix",
        action="store",
        type=str,
        help="Default FQDN suffix of DNS questions (use this when DNS requests are hex encoded)",
        default="",
    )
    args = argparser.parse_args()
    # Create server
    server = ThreadedUDPServer((args.host, args.port), DNSHandler)
    server.resolver = BaseResolver()
    server.logger = DNSLogger(args.suffix, args.hex_encoded)
    server.serve_forever()


if __name__ == "__main__":
    main()
