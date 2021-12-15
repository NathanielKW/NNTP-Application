from socket import *
import re
import os
import sys

def getConf():
    properties = {}
    confPath = os.getcwd() + "/client.conf"

    file = open(confPath, "r")
    for line in file:
        if re.match("\s*\n$", line):
            continue
        
        keyValuePair = line.split("=")
        properties[keyValuePair[0].strip()] = keyValuePair[1].strip()
    return properties

configurationProperties = {}
serverPort = ""

configurationProperties = getConf()

serverName = configurationProperties['SERVER_IP']
serverPort = int(configurationProperties['SERVER_PORT'])

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

clientSocket.send("User".encode())

salutation = clientSocket.recv(1024)
print(salutation.decode())

multiLineCommandList = ["ARTICLE", "HEAD", "BODY"]

while True:
    command = input('')
    
    # Handle empty line input
    if re.match("\n|^\s*$", command):
        continue

    clientSocket.send(command.encode())

    baseCommand = command.split()[0]
    if baseCommand.upper() in multiLineCommandList:
        responseLines = []
        while True:
            response = clientSocket.recv(1024)
            
            if re.match("^[4|5]\d\d.*", response.decode()):
                responseLines.append(response.decode().strip())
                clientSocket.send(".".encode())
                break
            elif response.decode().strip() == ".":
                responseLines.append(response.decode().strip())
                clientSocket.send(".".encode())
                break
            else:
                responseLines.append(response.decode().strip())
                clientSocket.send(".".encode())
        for line in responseLines:
            print(line)
    
    elif baseCommand.upper() == "POST":
        initialResponse = clientSocket.recv(1024).decode()
        print(initialResponse)

        if re.match("^440", initialResponse):
            continue

        while True:
            line = input('') + "\n"

            clientSocket.send(line.encode())
            if line.strip() == ".":
                break
        reply = clientSocket.recv(1024)
        print(reply.decode())

    elif command.upper() == 'QUIT':
       reply = clientSocket.recv(1024)
       print(reply.decode())
       break

    elif command.upper() == "MODE READER":
        reply = clientSocket.recv(1024)
        print(reply.decode())
        if re.match("^502", reply.decode()):
            break
    
    else:
        reply = clientSocket.recv(1024)
        print(reply.decode())

clientSocket.close()