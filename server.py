import json
import uuid
import os
from partialhash import partialhash
import socket
import pickle
import ntpath
from packaging import version
import argparse
import base64

def generate_config(json_file_path):
    data = {}
    new_uuid = str(uuid.uuid4())
    data['Allowed'] = []
    data['Allowed'].append(new_uuid)
    data['version'] = "0.0.0"
    data['listen'] = "127.0.0.1"
    data['port'] = '15000'
    data['update_file'] = '/path/to/update.bin'
    data['client_install_path'] = '/path/to/client_install_path'
    data['client_install_script'] = '/path/to/client_install_script.sh'
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Generated a new config file with user UUID {new_uuid}. Please modify {json_file_path} to configure it.")
    return data

parser = argparse.ArgumentParser(description='Secure Update Server with Dynamic Hash Verification')
parser.add_argument('-c','--config', metavar='CONFIG_FILE',type=str, default='config.json', help='Path to the configuration file',required=False)
parser.add_argument('-g','--generate', metavar='PATH_TO_NEW_CONFIG_FILE', type=str, help='Generate a new configuration file, for example, config.json',required=False)
args = parser.parse_args()
if args.generate is not None:
    generate_config(args.generate)
    exit(0)
json_file_path = args.config
if os.path.exists(json_file_path):
    with open(json_file_path, 'r') as file:
        json_config_load = json.load(file)
else:
    RED = "\033[91m"
    RESET = "\033[0m"
    print(f"{RED}ERROR: json file not found.{RESET}")
    exit(1)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = json_config_load['listen']
port = int(json_config_load['port'])
update_file_path = json_config_load['update_file']
client_install_path = json_config_load['client_install_path']
if not client_install_path.endswith('/'):
    client_install_path = client_install_path + '/'
client_install_script_path = json_config_load['client_install_script']
server_socket.bind((host, port))
server_socket.listen(1)
print("Server listening on %s:%d" % (host, port))
print("Serving File from", update_file_path)
while True:
    connection, client_address = server_socket.accept()
    try:
        size_bytes = connection.recv(20)
        if not size_bytes:
            break
        data_size = int.from_bytes(size_bytes, byteorder='big')
        tmp_data = b""
        while len(tmp_data) < data_size:
            chunk = connection.recv(10485760)
            if not chunk:
                break
            tmp_data += chunk
        received_data = pickle.loads(tmp_data)
        data = bytearray(received_data[0])
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                json_config_load = json.load(file)
        client_uuid = received_data[0].decode("utf-8")
        print("Received update request from", client_uuid, "at", client_address[0]+":"+str(client_address[1]))
        if client_uuid in  json_config_load['Allowed']:
            print("Client", client_uuid, "is authorized.")
            client_version = received_data[1]
            server_version = json_config_load['version']
            print("Client Version:", client_version)
            print("Server Version:", server_version)
            if(version.parse(server_version) <= version.parse(client_version)):
                print("Client version is up to date. No update required.")
                connection.sendall("204".encode('utf-8'))
            else:
                print("Sending update...")
                connection.sendall("200".encode('utf-8'))
                with open(update_file_path, 'rb') as file:
                    content = file.read()
                    update_filename = ntpath.basename(update_file_path)
                    data_send = []
                    data_send.append(content)
                    data_send.append(update_filename.encode("utf-8"))
                    data_send.append(client_install_path.encode("utf-8"))
                    data_send.append(str(server_version).encode("utf-8"))
                    with open(client_install_script_path, 'rb') as script_file:
                        install_script = script_file.read()
                    data_send.append(base64.b64encode(install_script))
                    serialized_data = pickle.dumps(data_send)
                    data_size = len(serialized_data)
                    print("Update Size:", data_size)
                    connection.sendall(data_size.to_bytes(20, byteorder='big'))
                    connection.sendall(serialized_data)
                    print("Update sent.")
                    partial_param_size = int.from_bytes(connection.recv(20), byteorder='big')
                    tmp_data = b""
                    while len(tmp_data) < partial_param_size:
                        chunk = connection.recv(10485760)
                        if not chunk:
                            break
                        tmp_data += chunk
                    partial_param_recv = pickle.loads(tmp_data)
                    partial_label = pickle.loads(partial_param_recv[0])
                    instruction_tag = pickle.loads(partial_param_recv[1])
                    final_hash = partialhash.generatefinalhashquickserver(serialized_data, partial_label, instruction_tag)
                    connection.sendall(final_hash.encode("utf-8"))
        else:
            YELLOW = "\033[93m"
            RESET = "\033[0m"
            print(f"{YELLOW}Client", client_uuid, f"is not authorized.{RESET}")
            connection.sendall("401".encode('utf-8'))
    except Exception as e:
        RED = "\033[91m"
        RESET = "\033[0m"
        print(f"{RED}ERROR: {e}{RESET}")
    finally:
        connection.close()