# SecureUpdateDynamicHash
This system utilises a high-performance, security-aware dynamic hashing mechanism to facilitate the reliable distribution of updates and hotfixes to designated client endpoints.

Update payloads are partitioned at randomized offsets, with each segment individually hashed using CityHash64, XXH64, and SpookyHash64.

A final integrity check is performed by computing a SHA-256 hash over the concatenated sequence of all segment hashes.

# Server
```
usage: server.py [-h] [-c CONFIG_FILE] [-g PATH_TO_NEW_CONFIG_FILE]

Secure Update Server with Dynamic Hash Verification

options:
  -h, --help            show this help message and exit
  -c, --config CONFIG_FILE
                        Path to the configuration file
  -g, --generate PATH_TO_NEW_CONFIG_FILE
                        Generate a new configuration file, for example, config.json
```
Server Configuration :
| KEY | VALUE |
| ------------- | ------------- | 
| allowed  | List of allowed client UUIDs    |
| version  | Version of the target program/files served by the update server |
| listen  | Listening address |
| port | Listening port |
| update_file | Update file served by the update server |
| client_install_path | Path on the client where the update will be installed |
| client_install_script | Install script on the server that will be executed by the client during update installation |

# Client
```
usage: client.py [-h] [-c CONFIG_FILE] [-g PATH_TO_NEW_CONFIG_FILE]

Secure Update Client with Dynamic Hash Verification

options:
  -h, --help            show this help message and exit
  -c, --config CONFIG_FILE
                        Path to the configuration file
  -g, --generate PATH_TO_NEW_CONFIG_FILE
                        Generate a new configuration file, for example, config.json
```
Client Configuration :
| KEY | VALUE |
| ------------- | ------------- | 
| UUID  | Client UUID |
| version  | Currently installed version of the target program/files on the client |
| server | Update server address |
| port | Update server port |

# Installation
| DEPENDENCIES |
| ------------ |
| xxhash |
| cityhash |
| spookyhash |

Please install the dependencies listed above using either `pip install` or `python3 -m pip install`, depending on your environment configuration.

During installation, ensure that `server.py` and `client.py` reside in the same directory as `partialhash.py`, as it contains the partial hashing module and is a required dependency.
