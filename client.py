import json
import uuid
import os
import socket
import pickle
import random
from partialhash import partialhash
import argparse
import base64
import subprocess

def check_version_and_uuid(json_file_path):
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        return data
    else:
        RED = "\033[91m"
        RESET = "\033[0m"
        print(f"{RED}ERROR: json file not found.{RESET}")
        exit(1)

def generate_config(json_file_path):
    data = {}
    new_uuid = str(uuid.uuid4())
    data['UUID'] = new_uuid
    data['version'] = "0.0.0"
    data['server'] = "127.0.0.1"
    data['port'] = '15000'
    print(f"Generated a new config file with user UUID {new_uuid}. Please modify {json_file_path} to configure it.")
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)
    return data

def check_update(server_addr, server_port, client_data):
    host = server_addr
    port = server_port
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    try:
        data_send = []
        data_send.append(client_data['UUID'].encode("utf-8"))
        data_send.append(client_data['version'])
        serialized_data = pickle.dumps(data_send)
        data_size = len(serialized_data)
        client_socket.sendall(data_size.to_bytes(20, byteorder='big'))
        client_socket.sendall(serialized_data)
        control_msg = client_socket.recv(3).decode("utf-8")
        if control_msg == '401' :
            RED = "\033[91m"
            RESET = "\033[0m"
            print(f"{RED}ERROR: This client is not authorized.{RESET}")
            exit(1)
        if control_msg == '204':
            print("This client is up to date.")
            exit()
        if control_msg == '200':
            print("Update detected. Initiating update...")
            data_size = int.from_bytes(client_socket.recv(20), byteorder='big')
            print("Update Size:", data_size)
            print("Downloading update...")
            tmp_data = b""
            while len(tmp_data) < data_size:
                chunk = client_socket.recv(10485760)
                if not chunk:
                    break
                tmp_data += chunk
            tmp_data_size = len(tmp_data)
            print("Update downloaded, verifying integrity...")
            n = random.randint(3 + int(tmp_data_size / 10485760), 5 + int(tmp_data_size / 10485760))  # Average block size for large files: 10MB
            max_partial_size = int(tmp_data_size / n * 2)
            partial_param = partialhash.generatefinalhashquick(n, tmp_data, max_partial_size, tmp_data_size)
            final_hash = partial_param[2].decode("utf-8")
            print("Dynamic hash of downloaded data:",final_hash)
            partial_param_send = []
            partial_param_send.append(partial_param[0])
            partial_param_send.append(partial_param[1])
            partial_param_encoded = pickle.dumps(partial_param_send)
            client_socket.sendall(len(partial_param_encoded).to_bytes(20, byteorder='big'))
            client_socket.sendall(partial_param_encoded)
            final_hash_from_server = client_socket.recv(64).decode("utf-8")
            print("Dynamic hash of source data:", final_hash_from_server)
            if final_hash == final_hash_from_server:
                downloaded_data = pickle.loads(tmp_data)
                update_file_path = downloaded_data[2].decode("utf-8")
                update_filename = downloaded_data[1].decode("utf-8")
                print("Update filename:", update_file_path + update_filename)
                file_content = downloaded_data[0]
                version_info = downloaded_data[3].decode("utf-8")
                print("Update version:", version_info)
                print("Integrity verified. Applying update...")
                if os.path.exists(update_file_path + update_filename):
                    os.remove(update_file_path + update_filename)
                with open(update_file_path + update_filename, 'wb') as file:
                    file.write(file_content)
                print("Executing install script...")
                install_script = base64.b64decode(downloaded_data[4].decode("utf-8"))
                try:
                    subprocess.run(['sh', '-c', install_script], capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    RED = "\033[91m"
                    RESET = "\033[0m"
                    print(f"{RED}ERROR: Failed to execute install script.{RESET}")
                    print(f"{RED}\b", e.stderr, f"{RESET}")
                    exit(1)
                client_data['version'] = version_info
                with open(json_file_path, 'w') as file:
                    json.dump(client_data, file, indent=4)
                print("Update Completed")
            else:
                print("Integrity verification failed. The file may have been corrupted or altered and has been discarded.")
            exit()
    finally:
        client_socket.close()

parser = argparse.ArgumentParser(description='Secure Update Client with Dynamic Hash Verification')
parser.add_argument('-c','--config', metavar='CONFIG_FILE',type=str, default='config.json', help='Path to the configuration file',required=False)
parser.add_argument('-g','--generate', metavar='PATH_TO_NEW_CONFIG_FILE', type=str, help='Generate a new configuration file, for example, config.json',required=False)
args = parser.parse_args()
if args.generate is not None:
    generate_config(args.generate)
    exit(0)
json_file_path = args.config
client_data = check_version_and_uuid(json_file_path)
print("Client UUID:", client_data['UUID'])
print("Current version:", client_data['version'])
print("Checking for updates. Connecting to", client_data['server']+':'+client_data['port'])
check_update(client_data['server'], int(client_data['port']), client_data)
