# https://docs.python.org/3/library/xmlrpc.html
import xmlrpc.client
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading
import difflib
import socket

'''
notes: 
    - knowing whether or not an RPC for a heartbeat is worth propagating
    - propagate to next 2 people in alphabet
    - if u receive a heartbeat older than the most recent heartbeat you received, drop it
'''

socket.setdefaulttimeout(5)

server_name = "Charlotte"
server_ip_addr = "141.165.50.133"

start_server_to_ping = "141.165.50.162"

client_list = []
num_heartbeats_sent = 0 # used for deciding when to stop pinging start server
num_heartbeats_until_switch_ping = 3

def send_heartbeat_to_ip(ip_dest, student_name, timestamp, ip_address, string_identifier): 
    try: 
        with xmlrpc.client.ServerProxy("http://" + ip_dest + ":6363") as proxy: 
            print()
            if string_identifier != "CLIENT": # if client, will say sending my own heartbeat
                print(f"{string_identifier}: Sending heartbeat with name: {student_name}, timestamp: {timestamp}, and ip address: {ip_address} to {ip_dest}")
            error = proxy.heartbeat(json.dumps({"student_name": student_name, "timestamp": int(timestamp), "ip_address": ip_address}))
            print(f"{string_identifier}: Sent heartbeat to {ip_dest}, server returned code {error}")
    except Exception as e: 
        print(f"{string_identifier}: Error - {e}")

def get_alphabetical_next_index_from_me(): 
    global client_list
    client_names = [client["student_name"] for client in client_list]
    after_me_alphabetically = [name for name in client_names if name > server_name]
    closest = difflib.get_close_matches(server_name, after_me_alphabetically, 1)
    client_index = 0
    for i, client in enumerate(client_list): 
        if client["student_name"] == closest: 
            client_index = i
            break
    return client_index
    
def purge_client_list(): 
    global client_list
    # go through client list and remove anything with a timestamp over 1 min old EXCEPT for my own client
    client_list = [client for client in client_list if abs(client["timestamp"] - time.time()) < 60]
    print(f"\nSERVER: New client list, old timestamps removed: {client_list}")

def get_next_client_index(curr_index): 
    global client_list
    return (curr_index + 1) % len(client_list)

def get_next_2_ip_addrs_to_send_to(exclude_ip, string_identifier): 
    global client_list
    if len(client_list) == 0: 
        return []
    next_index = get_alphabetical_next_index_from_me()
    orig_index = next_index # used to tell when there was a full loop (won't forward heartbeat anywhere in that case, bc no need to tell other one that they're alive)
    next_item = client_list[next_index]
    next_items = []
    original_person = next_item

    while next_item["ip_address"] == exclude_ip: # finding next available person who didn't originally send this heartbeat
        next_index = get_next_client_index(next_index)
        next_item = client_list[next_index]
        if next_index == orig_index: # went in full loop and couldn't find any ip addresses that don't match; only 1 other person in network 
            print(f"{string_identifier}: only 1 other client ip address (length {len(client_list)}), so not forwarding their own heartbeats back to them")
            print(f"-------------------------------------------------------------------------------------------------------")
            return []

    final_person = next_item
    if final_person != original_person: 
        print(f"{string_identifier}: 1st forward - skipped over {original_person['student_name']} to forward heartbeat to {final_person['student_name']}")

    next_items.append(next_item)

    next_next_index = get_next_client_index(next_index)
    next_next_item = client_list[next_next_index]
    original_next_person = next_next_item
    while next_next_item["ip_address"] == exclude_ip: # don't want to send heartbeat back to the original person who sent it, or send to the same client as the other ping
        next_next_index = get_next_client_index(next_next_index)
        next_next_item = client_list[next_next_index]

        if next_next_index == next_index: # went in full loop; means only 2 unique ip addresses in client list (3 people total, including me; in this case, stop search for next_next_index, and only send anything to next_index
            next_next_item = None
            print(f"{string_identifier}: only 2 other client ip addresses (length {len(client_list)}, so only forwarding heartbeats to one client")
            print(f"-------------------------------------------------------------------------------------------------------")
            return [next_item]

    if next_next_item is not None and next_next_item != original_next_person: 
        print(f"{string_identifier}: 2nd forward - skipped over {original_next_person['student_name']} to forward heartbeat to {next_next_item['student_name']}")
    
    next_items.append(next_next_item)
    return next_items

# client
def run_client(): 
    global num_heartbeats_sent
    global client_list
    num_to_ping = 0
    to_ping = []

    while True: 
        purge_client_list()
        to_ping = []
        if num_heartbeats_sent < num_heartbeats_until_switch_ping: 
            to_ping.append(start_server_to_ping)
        else: 
            # if 0 other people, 0 should be on the to-ping list; if 1 other person, 1 should be on the to-ping list; if 2 other people, 2 should be on the to-ping list, if 3+, then still 2 other people on the to-ping list
            num_to_ping = len(client_list)
            if num_to_ping > 2: 
                num_to_ping = 2
            
            to_ping = get_next_2_ip_addrs_to_send_to(server_ip_addr, "CLIENT")
            
        print(f"CLIENT: to_ping - {to_ping}")
        if num_to_ping > 0 and len(to_ping) > 0: 
            for person in to_ping: 
                print(f"CLIENT: Sending my own heartbeat to {person['student_name']}")
            threading.Thread(target=send_heartbeat_to_ip, args=(person['ip_address'], "Charlotte", time.time(), server_ip_addr, "CLIENT"), daemon=True).start()
            num_heartbeats_sent += 1

        time.sleep(10) # 10 second sleep before sending another heartbeat ping/checking if anyone available to send heartbeat ping to

# server
def heartbeat(json_string): 
    global client_list
    context = json.loads(json_string)
    name = context["student_name"]
    timestamp = int(context["timestamp"])
    ip_addr = context["ip_address"]
    print(f"-------------------------------------------------------------------------------------------------------")
    print(f"SERVER: Received heartbeat with name: {name}, timestamp: {timestamp}, ip_addr: {ip_addr}")
    
    if name == "Charlotte": 
        print(f"\nSERVER: Someone sent Charlotte to herself, don't propagate")
        print(f"-------------------------------------------------------------------------------------------------------")
        return 0
    
    if abs(time.time() - timestamp) < 20:
        all_ip_addrs = [client["ip_address"] for client in client_list]
        # need to include timestamps and update
        if not ip_addr in all_ip_addrs: # ip address not already in list, then add to list along with name
            client_list.append({"ip_address": ip_addr, "student_name": name, "timestamp": timestamp})
            # sort: https://stackoverflow.com/questions/72899/how-can-i-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
            client_list = sorted(client_list, key=lambda d: d["student_name"])
            print(f"SERVER: Added {ip_addr} for {name} at {timestamp} to client_list")
            print(f"SERVER: {len(client_list)} people in client list: {client_list}")
        else: 
            # update timestamp of existing entry ONLY if new timestamp more recent than old
            client_index = next((index for (index, d) in enumerate(client_list) if d["ip_address"] == ip_addr), None)
            if client_index is None: 
                print(f"SERVER: BUG - client index not found in list")
                return 1
            else: 
                if client_list[client_index]["timestamp"] < timestamp: # received more recent information; in this case, continue and forward
                    client_list[client_index]["timestamp"] = timestamp
                    print(f"SERVER: {name} exists in client list, updated client timestamp")
                else: 
                    print(f"SERVER: {name} exists in client list, but timestamp older than most recent")
                    print(f"-------------------------------------------------------------------------------------------------------")
                    return 0 # don't forward since old

                    
    else: 
        print(f"SERVER: Received invalid timestamp from {name} at {ip_addr} - {timestamp} was {abs(timestamp - time.time())} off")
        print(f"-------------------------------------------------------------------------------------------------------")
        return 1
    
    purge_client_list()

    next_items = get_next_2_ip_addrs_to_send_to(ip_addr, "SERVER")
    for person in next_items: 
        if person is not None: 
         threading.Thread(target=send_heartbeat_to_ip, args=(person["ip_address"], name, timestamp, ip_addr, "SERVER"), daemon=True).start()

    if len(next_items) == 0: 
        print(f"SERVER: no one with an ip other than {ip_addr} available to propagate to")
    
    print(f"-------------------------------------------------------------------------------------------------------")
    return 0

def run_server(): 
    with SimpleXMLRPCServer(('141.165.50.133', 6363)) as server: 
        server.register_introspection_functions()
        server.register_function(heartbeat, "heartbeat")
        server.serve_forever()

# https://www.geeksforgeeks.org/python/multithreading-python-set-1/
client_thread = threading.Thread(target=run_client)
server_thread = threading.Thread(target=run_server)

client_thread.start()
server_thread.start()

client_thread.join()
server_thread.join()
