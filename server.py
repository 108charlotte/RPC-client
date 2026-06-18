import xmlrpc.server
import time
import xmlrpc.client
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

with SimpleXMLRPCServer(('localhost', 8000)) as server: 
    server.register_introspection_functions()

    def heartbeat(json_string): 
        context = json.load(json_string)
        name = context["student_name"]
        timestamp = context["timestamp"]
        if time.time() - timestamp < 43200: # 12 hours equivalent in epoch seconds
            return xmlrpc.client

    server.register_function(heartbeat, "heartbeat")
    server.serve_forever()
