import xmlrpc.server
import time
import xmlrpc.client

# THIS DOES NOT WORK AND I'M TRYING TO FIGURE THIS OUT

with xmlrpc.server.SimpleXMLRPCServer(('localhost', 8000)) as server: 
    def heartbeat(): 
        name = xmlrpc.client.context["student_name"]
        timestamp = context["timestamp"]
        if time.time() - timestamp < 43200: # 12 hours equivalent in epoch seconds
            return xmlrpc.client
    server.register_function(heartbeat, "heartbeat")
