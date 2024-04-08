#!/bin/python3

import socket
import struct
import time
import sys
from math import gcd
import statistics

def initiate_exchange(host, port):
    print("Sending exchange requests. Press Ctrl+C to stop.")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)  # Set a timeout for socket operations
    
    offset_A = int(0x7FFFFFFF) # Initial offset reported by client

    num_exchanges = 10
    
    adjustments = []
    rtts = []

    for i in range(num_exchanges):
        try:
            # Send a timestamp to the remote host
            send_time_A = int(time.time() * 1e6)
            packet = struct.pack('!Qi', send_time_A, offset_A)
            sock.sendto(packet, (host, port))

            # Receive the remote host's timestamp and offset
            data, _ = sock.recvfrom(1024)
            recv_time_B, offset_B = struct.unpack('!Qi', data)
            recv_time_A = int(time.time() * 1e6)
            rtt = int(recv_time_A - send_time_A)
            rtt_ms = rtt / 1000

            # Calculate local and remote offsets (this logic might need to be adjusted)
            local_offset = recv_time_B - int(time.time() * 1e6)
            remote_offset = offset_B
            offset_A = local_offset
            local_offset_ms = local_offset / 1000
            remote_offset_ms = remote_offset / 1000

            # Ensure non-zero values for remote_offset to avoid division by zero
            remote_offset = max(remote_offset, 1)

            # Use gcd to simplify the ratio
            total_offset = abs(local_offset) + abs(remote_offset)
            local_percent = abs(round((local_offset / total_offset) * 100))
            remote_percent = abs(round((remote_offset / total_offset) * 100))
            common_divisor = gcd(local_percent, remote_percent)
            simplified_local = abs(local_percent) / common_divisor
            simplified_remote = abs(remote_percent) / common_divisor
            
            
            
            skew = rtt_ms - (local_offset_ms + remote_offset_ms)
            chrony =  (remote_percent /100 ) - (local_percent / 100)
            adjustments.append(chrony)
            rtts.append(rtt)
            print(f"Exchange {i} - RTT: {rtt_ms:.2f} ms, Local Offset: {local_offset_ms:.2f} ms,  Remote Offset: {remote_offset_ms:.2f} ms,    Asymmetry Ratio: {local_percent}/{remote_percent} ({chrony:.2f}, {simplified_local:.0f}:{simplified_remote:.0f}),    Skew: {skew:.2f} ms")

        except socket.timeout:
            print(f"Exchange {i}: No response received, skipping.")
        except KeyboardInterrupt:
            print(f"Cancelled by user")
            break
    if len(adjustments) > 0:
        median_adj = statistics.median(adjustments)
        median_rtt = statistics.median(rtts) / 1000
        
        remote_percentage = 50 + (median_adj * 100) / 2
        local_percentage = 100 - remote_percentage
        
        common_divisor = gcd(local_percent, remote_percent)
        simplified_local = abs(local_percent) / common_divisor
        simplified_remote = abs(remote_percent) / common_divisor
        
        print(f"\n---- MEDIANS:\nRTT: {median_rtt:.2f}\nRatio: {local_percentage:.0f}/{remote_percentage:.0f} ({simplified_local:.0f}:{simplified_remote:.0f})")
        print(f"Chrony offset: {median_adj:.5f}")
    sock.close()


def respond_to_exchange(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))

    print("Responding to exchange requests. Press Ctrl+C to stop.")
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            recv_time_B = int(time.time() * 1e6)
            send_time_B = int(time.time() * 1e6)
            # Simplified offset calculation
            unpacked = struct.unpack('!Qi', data)
            offset_B = abs(recv_time_B - unpacked[0])
            offset_A = unpacked[1]
            packet = struct.pack('!Qi', recv_time_B, offset_B)
            if(offset_A == int(0x7FFFFFFF)):
                print(f"---- Initial request:\n   ", end='')
                skew = "N/A"
                offset_A = "N/A"
            else:
                skew = offset_A - offset_B
            sock.sendto(packet, addr)
            print(f"Received at: {recv_time_B}, Offset A: {offset_A}, Offset B: {offset_B}, Skew: {skew}")
    except KeyboardInterrupt:
        print("\nStopped responding to exchange requests.")
    finally:
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No host provided, starting in server mode...")
        respond_to_exchange(12345)
    else:
        host = sys.argv[1]
        print(f"Initiating exchange with {host}...")
        initiate_exchange(host, 12345)
