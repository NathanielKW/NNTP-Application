from socket import *
import os
import re
import threading
import time
from Functions import *

serverState = "Transit"
stateLock = threading.Lock()

postingClientsCount = 0
postingClientsCountLock = threading.Lock()

connectedServerCount = 0
connectedServercountLock = threading.Lock()

class IHAVEAutomation(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            retryIHAVE(serverDict)

class ThreadedClient(threading.Thread):
    def __init__(self, clientAddress, clientSocket):
        threading.Thread.__init__(self)
        self.clientSocket = clientSocket
        self.clientAddress = clientAddress
        self.serverAddress = clientSocket.getsockname()[0]
        self.postingIntent = False
        self.peerType = ""

    def run(self):
        
        global serverState
        global postingClientsCount
        global connectedServerCount

        self.peerType = self.clientSocket.recv(1024).decode()
        if self.peerType == "Server":
            connectedServercountLock.acquire()
            connectedServerCount += 1
            connectedServercountLock.release()

        stateLock.acquire()
        if serverState == "Transit":
            salutation = responseCodes['SERVER_READY_RESPONSE']
        elif serverState == "Reader":
            salutation = responseCodes["SERVER_READY_READER"]
        stateLock.release()
        
        self.clientSocket.send(salutation.encode())

        activeGroup = ""
        currentArticleNumber = ""

        # Main communication loop
        while True:        
            outMessage = None

            inMessage = None
            inMessage = self.clientSocket.recv(1024).decode()
            inMessageList = None
            inMessageList = inMessage.split()
            
            #CAPABILITIES case
            if inMessageList[0].upper() == "CAPABILITIES" and len(inMessageList) < 2:
                outMessage = responseCodes['CAPABILITIES_RESPONSE'] + "\n"
                
                stateLock.acquire()
                if serverState == "Transit" and configurationProperties['MODE_SWITCH'] == "ON":
                    for i in transitCapabilities:
                        outMessage += i + "\n"
                elif serverState == "Transit" and configurationProperties['MODE_SWITCH'] == "OFF":
                    for i in nonModeSwitchingCapabilities:
                        outMessage += i + "\n"
                elif serverState == "Reader":
                    for i in readerCapabilities:
                        outMessage += i + "\n"
                stateLock.release()
                
                outMessage += "."
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
            
            #LIST case
            elif inMessageList[0].upper() == "LIST":
                if len(inMessageList) == 2:
                    outMessage = listCommand(keyword=inMessageList[1])
                elif len(inMessageList) == 3:
                    outMessage = listCommand(inMessageList[1], inMessageList[2])
                elif len(inMessageList) > 3:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                else:
                    outMessage = listCommand()
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
            
            #GROUP case
            elif inMessageList[0].upper() == "GROUP":
                if len(inMessageList) == 2:
                    outMessage, activeGroup, currentArticleNumber = groupCommand(inMessageList[1])
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
            
            #LISTGROUP case
            elif inMessageList[0].upper() == "LISTGROUP":
                if len(inMessageList) == 2 and not re.match("^[0-9]+-{0,1}[0-9]*$", inMessageList[1]):
                    outMessage, activeGroup, currentArticleNumber = listGroupCommand(newsgroup = inMessageList[1])
                elif len(inMessageList) == 2 and re.match("^[0-9]+-{0,1}[0-9]*$", inMessageList[1]):
                    outMessage, activeGroup, currentArticleNumber = listGroupCommand(activeGroup, inMessageList[1])
                elif len(inMessageList) == 3 and re.match("^[0-9]+-{0,1}[0-9]*$", inMessageList[2]):
                    outMessage, activeGroup, currentArticleNumber = listGroupCommand(inMessageList[1], inMessageList[2])
                elif len(inMessageList) == 1:
                    if activeGroup in os.listdir(dbPath):
                        outMessage, activeGroup, currentArticleNumber = listGroupCommand(newsgroup = activeGroup)
                    else:
                        outMessage = responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE']
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
            
            #LAST case
            elif inMessageList[0].upper() == "LAST":
                if len(inMessageList) == 1:
                    outMessage, currentArticleNumber = lastCommand(activeGroup, currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())

            #Next case
            elif inMessageList[0].upper() == "NEXT":
                if len(inMessageList) == 1:
                    outMessage, currentArticleNumber = nextCommand(activeGroup, currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
            
            #ARTICLE case
            elif inMessageList[0].upper() == "ARTICLE":
                if len(inMessageList) == 2 and re.match("^<.+>$", inMessageList[1]):
                    outMessage = articleCommand(currentGroup = activeGroup, messageID = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                elif len(inMessageList) == 2 and re.match("^\d+$", inMessageList[1]):
                    outMessage, articleNumber = articleCommand(currentGroup = activeGroup, articleNum = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                elif len(inMessageList) == 1:
                    outMessage, articleNumber = articleCommand(currentGroup = activeGroup, articleNum = currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                    confirmation = self.clientSocket.recv(1024)
            
            #HEAD case
            elif inMessageList[0].upper() == "HEAD":
                if len(inMessageList) == 2 and re.match("^<.+>$", inMessageList[1]):
                    outMessage = headCommand(currentGroup = activeGroup, messageID = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                elif len(inMessageList) == 2 and re.match("^\d+$", inMessageList[1]):
                    outMessage, articleNumber = headCommand(currentGroup = activeGroup, articleNum = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                elif len(inMessageList) == 1:
                    outMessage, articleNumber = headCommand(currentGroup = activeGroup, articleNum = currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                    confirmation = self.clientSocket.recv(1024)

            #BODY case
            elif inMessageList[0].upper() == "BODY":
                if len(inMessageList) == 2 and re.match("^<.+>$", inMessageList[1]):
                    outMessage = bodyCommand(currentGroup = activeGroup, messageID = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                elif len(inMessageList) == 2 and re.match("^\d+$", inMessageList[1]):
                    outMessage, articleNumber = bodyCommand(currentGroup = activeGroup, articleNum = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                elif len(inMessageList) == 1:
                    outMessage, articleNumber = bodyCommand(currentGroup = activeGroup, articleNum = currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    for line in outMessage:
                        self.clientSocket.send(line.encode())
                        confirmation = self.clientSocket.recv(1024)
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                    confirmation = self.clientSocket.recv(1024)

            #STAT case
            elif inMessageList[0].upper() == "STAT":
                if len(inMessageList) == 2 and re.match("^<.+>$", inMessageList[1]):
                    outMessage = statCommand(currentGroup = activeGroup, messageID = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                elif len(inMessageList) == 2 and re.match("^\d+$", inMessageList[1]):
                    outMessage, articleNumber = statCommand(currentGroup = activeGroup, articleNum = inMessageList[1])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                elif len(inMessageList) == 1:
                    outMessage, articleNumber = statCommand(currentGroup = activeGroup, articleNum = currentArticleNumber)
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())
                    if articleNumber != "":
                        currentArticleNumber = articleNumber
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage[0])
                    self.clientSocket.send(outMessage.encode())

            #NEWNEWS case
            elif inMessageList[0].upper() == "NEWNEWS":
                if len(inMessageList) == 4:
                    outMessage = newnewsCommand(inMessageList[1], inMessageList[2], inMessageList[3])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                elif len(inMessageList) == 5 and inMessageList[4].upper() == "GMT":
                    outMessage = newnewsCommand(inMessageList[1], inMessageList[2], inMessageList[3], inMessageList[4])
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                else:
                    outMessage = responseCodes['BAD_SYNTAX_RESPONSE']
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())

            #POST case
            elif inMessageList[0].upper() == "POST":
                if stateLock.locked():
                    outMessage = responseCodes["POSTING_NOT_PERMITTED"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                    continue
                
                stateLock.acquire()
                if serverState == "Transit":
                    outMessage = responseCodes["POSTING_NOT_PERMITTED"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                    stateLock.release()
                    continue
                
                stateLock.release()
                
                if not self.postingIntent:
                    self.postingIntent = True
                    postingClientsCountLock.acquire()
                    postingClientsCount += 1
                    postingClientsCountLock.release()

                article = ""
                header = ""
                articleBody = ""
                newsgroup = ""
                messageID = ""
                emptyLinePassed = False
                validArticle = True
                
                outMessage = responseCodes['INITIAL_POST']
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())

                articleList = []

                # continually loop until client sends ".", indicating they're done sending an article
                while True:
                    line = self.clientSocket.recv(1024).decode()
                    if line.strip() == ".":
                        break
                    elif emptyLinePassed:
                        articleBody += line
                        articleList.append(line)
                    elif not emptyLinePassed and re.match("^newsgroup: ", line.lower()):
                        exactHeaderValue = line.split(":")[0]
                        newsgroup = line.replace(exactHeaderValue + ": ", "").strip()
                        header += line
                        articleList.append(line)
                    elif not emptyLinePassed and re.match("^date: ", line.lower()):
                        continue
                    elif not emptyLinePassed and re.match("^message-id: ", line.lower()):
                        continue
                    elif not emptyLinePassed and re.match("^[a-zA-Z]\w*:\s", line):
                        header += line
                        articleList.append(line)
                    elif not emptyLinePassed and re.match("^\s*\n$", line) and newsgroup != "":
                        emptyLinePassed = True
                        dateLine = "Date: " + time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime()) + "\n"
                        messageID = generateMessageID(newsgroup)
                        messageIDLine = "Message-ID: " + messageID + "\n"
                        
                        articleList.append(dateLine)
                        articleList.append(messageIDLine)
                        articleList.append("\n")

                        header += dateLine + messageIDLine + "\n"
                    elif not emptyLinePassed and re.match("^\s*\n$", line) and newsgroup == "":
                        emptyLinePassed = True
                        # header += "\n"
                        header += line
                        articleList.append(line)
                        validArticle = False
                    elif not emptyLinePassed and not re.match("^[a-zA-Z]\w*:\s", line):
                        validArticle = False
                articleBody += "\n"
                articleList.append("\n")

                # If article structure is valid and header and body is not empty, concat into single string and send to database
                if validArticle and header != "":
                    article = header + articleBody
                    articleName, newNewsGroup = getNewFileName(newsgroup)
                    if newNewsGroup:
                        os.mkdir(dbPath + "/" + newsgroup)
                    file = open(dbPath + "/" + newsgroup + "/" + articleName, "w")
                    file.write(article)
                    file.close()

                    outMessage = responseCodes["POST_SUCCESS"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())

                    # send IHAVE to all peer servers
                    for ip, port in serverDict.items():
                        sendIHAVE(ip, port, messageID, newsgroup, articleList)

                # else, return POST failed response message
                else:
                    outMessage = responseCodes["POST_FAILED"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())

            #MODE READER case
            elif inMessageList[0].upper() == "MODE" and inMessageList[1].upper() == "READER" and len(inMessageList) == 2:
                if stateLock.locked():
                    outMessage = responseCodes["MODE_READER_POSTING_PROHIBITED"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                else:
                    stateLock.acquire()
                    connectedServercountLock.acquire()
                    #if currently in Transit mode and server is mode_switching
                    if serverState == "Transit" and configurationProperties['MODE_SWITCH'] == "ON" and connectedServerCount == 0:
                        postingClientsCountLock.acquire()
                        postingClientsCount += 1
                        postingClientsCountLock.release()
                        self.postingIntent = True

                        serverState = "Reader"
                        outMessage = responseCodes["MODE_READER_POST_ALLOWED"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())

                    elif serverState == "Transit" and configurationProperties['MODE_SWITCH'] == "ON" and connectedServerCount > 0:
                        outMessage = responseCodes["MODE_READER_POSTING_PROHIBITED"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())

                    #if currently in Transit mode and server is not mode_switching
                    elif serverState == "Transit" and configurationProperties['MODE_SWITCH'] == "OFF":
                        outMessage = responseCodes["NO_READER_CAPABILITY"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())
                        stateLock.release()
                        break
                    
                    #if currently in reader mode
                    elif serverState == "Reader":
                        outMessage = responseCodes["BAD_COMMAND_RESPONSE"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())
                    connectedServercountLock.release()
                    stateLock.release()

            #IHAVE case
            elif inMessageList[0].upper() == "IHAVE" and len(inMessageList) == 2 and self.peerType == "Server":
                stateLock.acquire()
                # if server is in Reader mode
                if serverState == "Reader":
                    outMessage = responseCodes["IHAVE_TRY_AGAIN"]
                    writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                    self.clientSocket.send(outMessage.encode())
                    print("Blocked [" + inMessage + "] from " + self.clientAddress[0] + ". Currently in Reader state.  Try again later\n")
                # if server is in Transit mode
                elif serverState == "Transit":
                    # if message-id match found in DB
                    if findArticle(inMessageList[1]):
                        outMessage = responseCodes["IHAVE_DUPLICATE"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())
                        print("Blocked [" + inMessage + "] from " + self.clientAddress[0] + ". Duplicate found.  Don't try again\n")
                    # if no match
                    else:
                        # Send initial response
                        outMessage = responseCodes["IHAVE_SEND"]
                        writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                        self.clientSocket.send(outMessage.encode())
                        print("[" + inMessage + "] from " + self.clientAddress[0] + " initially accepted. Subsequent response to follow\n")
            
                        # Receive article
                        newsgroup = self.clientSocket.recv(1024).decode()
                        if newsgroup in getNewsgroups():
                            article = ""
                            articleList = []
                            self.clientSocket.send(".".encode())
                            while True:
                                currentLine = self.clientSocket.recv(1024).decode()
                                if currentLine == ".":
                                    break
                                else:
                                    article += currentLine
                                    articleList.append(currentLine)
                                    self.clientSocket.send(".".encode())
                            newFileName, isNewNewsgroup = getNewFileName(newsgroup)
                            file = open(dbPath + "/" + newsgroup + "/" + newFileName, "w")
                            file.write(article)
                            file.close()

                            outMessage = responseCodes["IHAVE_SUCCESS"]
                            writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                            self.clientSocket.send(outMessage.encode())
                            print("[" + inMessage + "] successfully received from " + self.clientAddress[0] + "\n")

                            for ip, port in serverDict.items():
                                sendIHAVE(ip, port, inMessageList[1], newsgroup, articleList)

                        else:
                            outMessage = responseCodes["IHAVE_FAILED_NO_RETRY"]
                            writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                            self.clientSocket.send(outMessage.encode())
                            print("[" + inMessage + "] from " + self.clientAddress[0] + " failed. Dont try again\n")
                stateLock.release()
                break


            #HELP case
            elif inMessageList[0].upper() == "HELP" and len(inMessageList) == 1:
                outMessage = responseCodes['HELP_RESPONSE'] + "\n"
                outMessage += "Valid Commands:\n"
                for i in commandList:
                    outMessage += i + "\n"
                outMessage += "."
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
            #QUIT case
            elif inMessageList[0].upper() == 'QUIT' and len(inMessageList) == 1:
                outMessage = responseCodes['QUIT_RESPONSE']
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
                break
            #BAD COMMAND case
            else:
                outMessage = responseCodes['BAD_COMMAND_RESPONSE'] + " " + inMessage.upper()
                writeLog(self.clientAddress[0], self.serverAddress, inMessage, outMessage)
                self.clientSocket.send(outMessage.encode())
        self.clientSocket.close()
        
        if self.peerType == "User" and self.postingIntent:
            postingClientsCountLock.acquire()
            postingClientsCount -= 1
            postingClientsCountLock.release()
        elif self.peerType == "Server":
            connectedServercountLock.acquire()
            connectedServerCount -= 1
            connectedServercountLock.release()

        postingClientsCountLock.acquire()
        stateLock.acquire()
        if postingClientsCount == 0:
            serverState = "Transit"
        stateLock.release()
        postingClientsCountLock.release()
    
    # End of Client Thread



configurationProperties = {}
serverDict = {}
serverPort = ""

configurationProperties, serverDict = getConf()

serverPort = configurationProperties['NNTP_PORT']

print('NNTP Server Running\n')

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', int(serverPort)))
serverAddress = serverSocket.getsockname()[0]

transitCapabilities = ["VERSION 2", "MODE READER", "IHAVE", "LIST ACTIVE NEWSGROUP"]
nonModeSwitchingCapabilities = ["VERSION 2", "IHAVE", "LIST ACTIVE NEWSGROUP"]
readerCapabilities = ["VERSION 2", "READER", "LIST ACTIVE NEWSGROUP", "POST"]
commandList = ["CAPABILITIES", "LIST", "GROUP", "LISTGROUP", "ARTICLE", "HEAD", "BODY", "STAT", "NEXT", "LAST", "NEWNEWS", "POST", "MODE READER", "HELP", "QUIT"]

# create a seperate thread that automatically sends out IHAVE commands
automatedIHAVE = IHAVEAutomation()
automatedIHAVE.start()

# Listen for clients.  When found, accept and start new thread
while True:
    
    serverSocket.listen(1)
    connectionSocket, addr = serverSocket.accept()
    thread = ThreadedClient(addr, connectionSocket)
    thread.start()


# CTRL + C to kill script