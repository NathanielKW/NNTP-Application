from socket import *
import re
import os
import time
import random
import string
import queue

responseCodes = {"HELP_RESPONSE": "101 Help Text follows", "CAPABILITIES_RESPONSE": "101 Capability list:", "MODE_READER_POST_ALLOWED": "200 Reader mode, posting permitted", "SERVER_READY_READER": "200 NNTP Service Ready, posting allowed", "SERVER_READY_RESPONSE": "201 NNTP Service Ready, posting prohibited",
                 "MODE_READER_POSTING_PROHIBITED": "201 Posting prohibited", "QUIT_RESPONSE": "205 NNTP Service exits normally", "FULL_NEWSGROUP": "211", "EMPTY_NEWSGROUP": "211 0 0 0", "LIST_ACTIVE_RESPONSE": "215 list of newsgroups follows",
                 "LIST_NEWSGROUP_RESPONSE": "215 information follows", "ARTICLE_SUCCESS_RESPONSE": "220", "HEAD_SUCCESS_RESPONSE": "221", "BODY_SUCCESS_RESPONSE": "222",
                 "STAT_SUCCESS_RESPONSE": "223", "LAST_SUCCESS": "223", "NEWNEWS_RESPONSE": "230 list of new articles by message-id follows", "IHAVE_SUCCESS": "235 Article transferred OK", "POST_SUCCESS": "240 Article received OK", "IHAVE_SEND": "335 Send it; end with <CR-LF>.<CR-LF>", "INITIAL_POST": "340 Input article; end with <CR-LF>.<CR-LF>", 
                 "INVALID_NEWSGROUP": "411", "NO_NEWSGROUP_SELECTED_RESPONSE": "412 No newsgroup selected", "NO_ARTICLE_SELECTED_RESPONSE": "420 No article selected", 
                 "NO_NEXT_ARTICLE_RESPONSE": "421 No next article in this group", "NO_PREVIOUS_ARTICLE_RESPONSE": "422 No previous article", "ARTICLE_NOT_PRESENT_RESPONSE": "423 No article with that number", 
                 "ARTICLE_NOT_FOUND_RESPONSE": "430 No such article found","IHAVE_DUPLICATE": "435 Duplicate", "IHAVE_TRY_AGAIN": "436 Retry later", "IHAVE_FAILED_NO_RETRY": "437 Article rejected; don't send again", "POSTING_NOT_PERMITTED": "440 Posting not permitted", "POST_FAILED": "441 Posting failed", "BAD_COMMAND_RESPONSE": "500 Bad command:", "BAD_SYNTAX_RESPONSE": "501 Bad Syntax in command", 
                 "BAD_KEYWORD_RESPONSE": "501 Invalid keyword in command", "NO_READER_CAPABILITY": "502 Transit service only"}

dbPath = os.getcwd() + "/db"

messageIDQueue = queue.Queue()

def getConf():
    properties = {}
    servers = {}
    confPath = os.getcwd() + "/server.conf"

    file = open(confPath, "r")
    for line in file:
        if re.match("\s*\n$", line):
            continue
        elif re.match("^//.*", line):
            continue
        
        keyValuePair = line.split("=")
        if keyValuePair[0].strip() == "RSOCK_ADDR":
            ipAndPort = keyValuePair[1].split(":")
            servers[ipAndPort[0].strip()] = ipAndPort[1].strip()
        else:
            properties[keyValuePair[0].strip()] = keyValuePair[1].strip()
    
    return properties, servers

def matchWildmat(wildmat, string):
    patterns = wildmat.split(",")
    patterns.reverse()

    for pattern in patterns:
        if not re.match("^!{0,1}(\w+|\*|\?+)+$", pattern):
            return False
        else:
            pattern = pattern.replace("*", ".*")
            pattern = pattern.replace("?", ".")
            pattern = "^" + pattern + "$"
            
            if pattern[1] == "!" and re.match(pattern.replace("!", ""), string):
                return False
            elif re.match(pattern, string):
                return True
    return False

def listCommand(keyword="ACTIVE", wildmat=""):
    returnMessage = ""
    
    # If keyword not valid, return BAD_KEYWORD_RESPONSE
    if keyword not in ['ACTIVE', 'NEWSGROUP']:
        return responseCodes['BAD_KEYWORD_RESPONSE']
    
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for group in groups:
        if re.match("^[.][_].*|.DS_Store", group):
            pass
        else:
            groupsCorrected.append(group)
    groupsAndArticles = {}

    # strip out article duplicates and .txt extension at end of files.  New dictionary is groupsAndArticles
    for i in groupsCorrected:
        fileList = os.listdir(dbPath + "/" + i)
        fileListCorrected = []
        for article in fileList:
            if re.match("^[.][_].*|.info", article):
                pass
            else:
                fileListCorrected.append(article.replace(".txt", ""))
        fileListCorrected.sort(key = int)
        groupsAndArticles[i] = fileListCorrected

    # If command is "LIST ACTIVE"...
    if keyword == "ACTIVE":
        returnMessage += responseCodes['LIST_ACTIVE_RESPONSE'] + "\n"
        
        # create a dictionary with key as newsgroup and value as nested dictionary containing high watermark, low watermark, and status
        listInfo = {}
        for key, value in groupsAndArticles.items():
            try:
                listInfo[key] = {"high": groupsAndArticles[key][len(groupsAndArticles[key]) - 1], "low": groupsAndArticles[key][0], "status": "n"}
            except IndexError:
                listInfo[key] = {"high": "0", "low": "0", "status": "n"}
        
        # If no wildmat, return entire newsgroup list info
        if wildmat == "":
            for key, value in listInfo.items():
                returnMessage += key + " " + value['high'] + " " + value['low'] + " " + value['status'] + "\n"
            returnMessage += "."
            return returnMessage
        # If wildmat provided, return newsgroup list info where newsgroups listed match provided pattern
        else:
            for key, value in listInfo.items():
                if matchWildmat(wildmat, key):
                    returnMessage += key + " " + value['high'] + " " + value['low'] + " " + value['status'] + "\n"
            returnMessage += "."
            return returnMessage
    
    # If command is "LIST NEWSGROUP"...
    else:
        returnMessage += responseCodes['LIST_NEWSGROUP_RESPONSE'] + "\n"
        
        # If wildmat not provided, return list of newsgroup descriptions
        if wildmat == "":
            for group in groupsCorrected:
                groupInfo = ""
                try:
                    file = open(dbPath + "/" + group + "/.info", "r")
                    groupInfo = file.readline()
                    file.close()
                    returnMessage += group + " " + groupInfo
                except FileNotFoundError:
                    returnMessage += group + " No info on this group provided\n"
            return returnMessage + "."
        # If wildmat is provided, return list of newsgroup descriptions where newsgroups matches pattern
        else:
            for group in groupsCorrected:
                if matchWildmat(wildmat, group):
                    groupInfo = ""
                    file = open(dbPath + "/" + group + "/.info", "r")
                    groupInfo = file.readline()
                    file.close()
                    returnMessage += group + " " + groupInfo
            return returnMessage + "."

def groupCommand(newsgroup):
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for group in groups:
        if re.match("^[.][_].*|.DS_Store", group):
            pass
        else:
            groupsCorrected.append(group)

    # If invalid newsgroup, return INVALID_NEWSGROUP response
    if newsgroup not in groupsCorrected:
        return responseCodes['INVALID_NEWSGROUP'] + " " + newsgroup + " is unknown", "", ""

    # If valid newsgroup...
    else:
        # If valid newsgroup is empty, return EMPTY_RESPONSE and set active newsgroup as newsgroup argument
        if len(os.listdir(dbPath + "/" + newsgroup)) == 0 or (len(os.listdir(dbPath + "/" + newsgroup)) == 1 and os.path.exists(dbPath + "/" + newsgroup + "/.info")):
            return responseCodes['EMPTY_NEWSGROUP'] + " " + newsgroup, newsgroup, ""
        # If valid newsgroup is not empty, return appropriate success response and set active newsgroup and article num
        else:
            groupFiles = os.listdir(dbPath + "/" + newsgroup)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            groupFilesCorrected.sort(key = int)
            
            numFiles = len(groupFilesCorrected)
            lowWatermark = groupFilesCorrected[0]
            highWatermark = groupFilesCorrected[numFiles - 1]

            return responseCodes['FULL_NEWSGROUP'] + " " +  str(numFiles) + " " + lowWatermark + " " + highWatermark + " " + newsgroup, newsgroup, lowWatermark

def listGroupCommand(newsgroup="", listRange=""):
    response = ""
    
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for group in groups:
        if re.match("^[.][_].*|.DS_Store", group):
            pass
        else:
            groupsCorrected.append(group)

    # If newsgroup isn't selected
    if newsgroup == "":
        return responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE'], "", ""

    # If newsgroup invalid return INVALID_NEWSGROUP response
    elif newsgroup not in groupsCorrected:
        return responseCodes['INVALID_NEWSGROUP'] + " " + newsgroup + " is unknown", "", ""

    # If newsgroup is valid, but empty, return EMPTY_NEWSGROUP response
    elif len(os.listdir(dbPath + "/" + newsgroup)) == 0 or (len(os.listdir(dbPath + "/" + newsgroup)) == 1 and os.path.exists(dbPath + "/" + newsgroup + "/.info")):
        return responseCodes['EMPTY_NEWSGROUP'] + " " + newsgroup + " list follows\n.", newsgroup, ""

    # If newsgroup is valid and not empty...
    else:
        groupFiles = os.listdir(dbPath + "/" + newsgroup)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        groupFilesCorrected.sort(key = int)
        
        numFiles = len(groupFilesCorrected)
        lowWatermark = groupFilesCorrected[0]
        highWatermark = groupFilesCorrected[numFiles - 1]
        
        response += responseCodes['FULL_NEWSGROUP'] + " " + str(numFiles) + " " + lowWatermark + " " + highWatermark + " " + newsgroup + " list follows\n"

        # if no list range is provided
        if listRange == "":
            for article in groupFilesCorrected:
                response += article + "\n"
        # if list range is provided and in form [low]
        elif re.match("[0-9]+$", listRange):
            articleNum = int(listRange)
            if articleNum in os.listdir(dbPath + "/" + newsgroup):
                response += listRange + "\n"
        # if list range is provided and in form [low-]
        elif re.match("^[0-9]+-$", listRange):
            low = int(listRange.replace("-", ""))
            for article in groupFilesCorrected:
                if int(article) >= low:
                    response += article + "\n"
        # if list range is provided and in form [low-high]
        elif re.match("^[0-9]+-[0-9]+$", listRange):
            lowHigh = listRange.split(sep = "-")
            low = int(lowHigh[0])
            high = int(lowHigh[1])
            #ensures that range is valid. If not valid, no list provided
            if high >= low:
                for article in groupFilesCorrected:
                    if int(article) >= low and int(article) <= high:
                        response += article + "\n"
        
        response += "."
        return response, newsgroup, lowWatermark

def lastCommand(group, currentArticle):
    responseMessage = ""
    
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for i in groups:
        if re.match("^[.][_].*|.DS_Store", i):
            pass
        else:
            groupsCorrected.append(i)

    # If no newsgroup selected
    if group not in groupsCorrected:
        responseMessage = responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE']
    # If newsgroup selected, but article not selected
    elif currentArticle == "":
        responseMessage = responseCodes['NO_ARTICLE_SELECTED_RESPONSE']
    # If newsgroup and article selected...
    else:
        # remove file duplicates and strip out .txt extension.  Then sort
        groupFiles = os.listdir(dbPath + "/" + group)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        groupFilesCorrected.sort(key = int)
        
        # If current article is first article in newsgroup
        if currentArticle == groupFilesCorrected[0]:
            responseMessage = responseCodes['NO_PREVIOUS_ARTICLE_RESPONSE']
        # If current article isn't first in newsgroup
        else:
            lastArticleIndex = groupFilesCorrected.index(currentArticle) - 1
            currentArticle = groupFilesCorrected[lastArticleIndex]
            messageID = ""
            file = open(dbPath + "/" + group + "/" + currentArticle + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    messageID = line.replace("Message-ID: ", "")
                    messageID = messageID.strip()
                    break
            responseMessage = responseCodes['LAST_SUCCESS'] + " " + currentArticle + " " + messageID + " retrieved"
            file.close()
    return responseMessage, currentArticle

def nextCommand(group, currentArticle):
    responseMessage = ""
    
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for i in groups:
        if re.match("^[.][_].*|.DS_Store", i):
            pass
        else:
            groupsCorrected.append(i)

    # If no newsgroup selected
    if group not in os.listdir(dbPath):
        responseMessage = responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE']
    # If newsgroup selected, but article not selected
    elif currentArticle == "":
        responseMessage = responseCodes['NO_ARTICLE_SELECTED_RESPONSE']
    # If newsgroup and article selected...
    else:
        # remove file duplicates and strip out .txt extension.  Then sort
        groupFiles = os.listdir(dbPath + "/" + group)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        groupFilesCorrected.sort(key = int)
        
        lastArticleIndex = groupFilesCorrected.index(currentArticle) - 1
        # If current article is last article in newsgroup
        if currentArticle == groupFilesCorrected[len(groupFilesCorrected) - 1]:
            responseMessage = responseCodes['NO_NEXT_ARTICLE_RESPONSE']
        # If current article isn't last in newsgroup
        else:
            nextArticleIndex = groupFilesCorrected.index(currentArticle) + 1
            currentArticle = groupFilesCorrected[nextArticleIndex]
            messageID = ""
            file = open(dbPath + "/" + group + "/" + currentArticle + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    messageID = line.replace("Message-ID: ", "")
                    messageID = messageID.strip()
                    break
            responseMessage = responseCodes['LAST_SUCCESS'] + " " + currentArticle + " " + messageID + " retrieved"
            file.close()
    return responseMessage, currentArticle

def articleCommand(messageID="", articleNum="", currentGroup = ""):
    responseLines = []

    # First form command
    if messageID != "":
        match = False
        
        groups = os.listdir(dbPath)
        groupsCorrected = []
        for i in groups:
            if re.match("^[.][_].*|.DS_Store", i):
                pass
            else:
                groupsCorrected.append(i)

        # Loop through each newsgroup until match is found.  
        for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
            for file in groupFilesCorrected:
                currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
                for line in currentfile:
                    if re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        if mID == messageID:
                            match = True
                        else:
                            responseLines.clear()
                            break
                    responseLines.append(line)
                if match:
                    break
            if match:
                responseLines.insert(0, responseCodes['ARTICLE_SUCCESS_RESPONSE'] + " 0 " + messageID)
                responseLines.append(".")
                return responseLines
        if not match:
            responseLines.append(responseCodes['ARTICLE_NOT_FOUND_RESPONSE'])
            return responseLines
    # Second/third form command
    elif articleNum != "" and currentGroup != "":
        groupFiles = os.listdir(dbPath + "/" + currentGroup)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        if articleNum not in groupFilesCorrected:
            responseLines.append(responseCodes['ARTICLE_NOT_PRESENT_RESPONSE'])
            return responseLines, ""
        else:
            mID = ""
            file = open(dbPath + "/" + currentGroup + "/" + articleNum + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    mID = line.replace("Message-ID: ", "").strip()
                responseLines.append(line)
            responseLines.insert(0, responseCodes['ARTICLE_SUCCESS_RESPONSE'] + " " + articleNum + " " + mID)
            responseLines.append(".")
            file.close()
            return responseLines, articleNum
    # If no article selected
    elif articleNum == "" and messageID == "" and currentGroup != "":
        responseLines.append(responseCodes['NO_ARTICLE_SELECTED_RESPONSE'])
        return responseLines, ""
    # Invalid newsgroup
    else:
        responseLines.append(responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE'])
        return responseLines, ""

def headCommand(messageID="", articleNum="", currentGroup = ""):
    responseLines = []

    # First form command
    if messageID != "":
        match = False
        
        groups = os.listdir(dbPath)
        groupsCorrected = []
        for i in groups:
            if re.match("^[.][_].*|.DS_Store", i):
                pass
            else:
                groupsCorrected.append(i)

        # Loop through each newsgroup until match is found.  
        for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
            for file in groupFilesCorrected:
                currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
                for line in currentfile:
                    if re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        if mID == messageID:
                            match = True
                        else:
                            responseLines.clear()
                            break
                    elif re.match("\s*\n$", line):
                        break
                    responseLines.append(line)
                if match:
                    break
            if match:
                responseLines.insert(0, responseCodes['HEAD_SUCCESS_RESPONSE'] + " 0 " + messageID)
                responseLines.append(".")
                return responseLines
        if not match:
            responseLines.append(responseCodes['ARTICLE_NOT_FOUND_RESPONSE'])
            return responseLines
    # Second/third form command
    elif articleNum != "" and currentGroup != "":
        groupFiles = os.listdir(dbPath + "/" + currentGroup)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        if articleNum not in groupFilesCorrected:
            responseLines.append(responseCodes['ARTICLE_NOT_PRESENT_RESPONSE'])
            return responseLines, ""
        else:
            mID = ""
            file = open(dbPath + "/" + currentGroup + "/" + articleNum + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    mID = line.replace("Message-ID: ", "").strip()
                elif re.match("\s*\n$", line):
                    break
                responseLines.append(line)
            responseLines.insert(0, responseCodes['HEAD_SUCCESS_RESPONSE'] + " " + articleNum + " " + mID)
            responseLines.append(".")
            file.close()
            return responseLines, articleNum
    # If no article selected
    elif articleNum == "" and messageID == "" and currentGroup != "":
        responseLines.append(responseCodes['NO_ARTICLE_SELECTED_RESPONSE'])
        return responseLines, ""
    # Invalid newsgroup
    else:
        responseLines.append(responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE'])
        return responseLines, ""

def bodyCommand(messageID="", articleNum="", currentGroup = ""):
    responseLines = []

    # First form command
    if messageID != "":
        match = False
        
        groups = os.listdir(dbPath)
        groupsCorrected = []
        for i in groups:
            if re.match("^[.][_].*|.DS_Store", i):
                pass
            else:
                groupsCorrected.append(i)

        # Loop through each newsgroup until match is found.  
        for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
            for file in groupFilesCorrected:
                newLinePassed = False
                currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
                for line in currentfile:
                    if re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        if mID == messageID:
                            match = True
                        else:
                            responseLines.clear()
                            break
                    elif re.match("\s*\n$", line) and newLinePassed:
                        responseLines.append(line)
                    elif re.match("\s*\n$", line):
                        newLinePassed = True
                        continue
                    elif newLinePassed:
                        responseLines.append(line)
                if match:
                    break
            if match:
                responseLines.insert(0, responseCodes['BODY_SUCCESS_RESPONSE'] + " 0 " + messageID)
                responseLines.append(".")
                return responseLines
        if not match:
            responseLines.append(responseCodes['ARTICLE_NOT_FOUND_RESPONSE'])
            return responseLines
    # Second/third form command
    elif articleNum != "" and currentGroup != "":
        groupFiles = os.listdir(dbPath + "/" + currentGroup)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        if articleNum not in groupFilesCorrected:
            responseLines.append(responseCodes['ARTICLE_NOT_PRESENT_RESPONSE'])
            return responseLines, ""
        else:
            mID = ""
            newLinePassed = False
            file = open(dbPath + "/" + currentGroup + "/" + articleNum + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    mID = line.replace("Message-ID: ", "").strip()
                elif re.match("\s*\n$", line) and newLinePassed:
                    responseLines.append(line)
                elif re.match("\s*\n$", line):
                    newLinePassed = True
                    continue
                elif newLinePassed:
                    responseLines.append(line)
            responseLines.insert(0, responseCodes['BODY_SUCCESS_RESPONSE'] + " " + articleNum + " " + mID)
            responseLines.append(".")
            file.close()
            return responseLines, articleNum
    # If no article selected
    elif articleNum == "" and messageID == "" and currentGroup != "":
        responseLines.append(responseCodes['NO_ARTICLE_SELECTED_RESPONSE'])
        return responseLines, ""
    # Invalid newsgroup
    else:
        responseLines.append(responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE'])
        return responseLines, ""

def statCommand(messageID="", articleNum="", currentGroup = ""):
    response = ""

    # First form command
    if messageID != "":
        match = False
        
        groups = os.listdir(dbPath)
        groupsCorrected = []
        for i in groups:
            if re.match("^[.][_].*|.DS_Store", i):
                pass
            else:
                groupsCorrected.append(i)

        # Loop through each newsgroup until match is found.  
        for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
            for file in groupFilesCorrected:
                currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
                for line in currentfile:
                    if re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        if mID == messageID:
                            match = True
                        else:
                            break
                if match:
                    break
            if match:
                response = responseCodes['STAT_SUCCESS_RESPONSE'] + " 0 " + messageID
                return response
        if not match:
            response = responseCodes['ARTICLE_NOT_FOUND_RESPONSE']
            return response
    # Second/third form command
    elif articleNum != "" and currentGroup != "":
        groupFiles = os.listdir(dbPath + "/" + currentGroup)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        if articleNum not in groupFilesCorrected:
            response = responseCodes['ARTICLE_NOT_PRESENT_RESPONSE']
            return response, ""
        else:
            mID = ""
            file = open(dbPath + "/" + currentGroup + "/" + articleNum + ".txt", "r")
            for line in file:
                if re.match("^Message-ID:", line):
                    mID = line.replace("Message-ID: ", "").strip()
            response = responseCodes['STAT_SUCCESS_RESPONSE'] + " " + articleNum + " " + mID
            file.close()
            return response, articleNum
    # If no article selected
    elif articleNum == "" and messageID == "" and currentGroup != "":
        response = responseCodes['NO_ARTICLE_SELECTED_RESPONSE']
        return response, ""
    # Invalid newsgroup
    else:
        response = responseCodes['NO_NEWSGROUP_SELECTED_RESPONSE']
        return response, ""

def newnewsCommand(wildmat, date, time, arg=""):
    response = ""

    if len(date) != 6 and len(date) != 8:
        return responseCodes['BAD_SYNTAX_RESPONSE']
    elif not re.match("^[0-9]{6}$", time):
        return responseCodes['BAD_SYNTAX_RESPONSE']
    elif len(date) == 6 and not re.match("[0-9][0-9](0[1-9]|1[0-2])(0[1-9]|[1-2][0-9]|3[0-1])", date):
        return responseCodes['BAD_SYNTAX_RESPONSE']
    elif len(date) == 8 and not re.match("(19|[2-9][0-9])[0-9][0-9](0[1-9]|1[0-2])(0[1-9]|[1-2][0-9]|3[0-1])", date):
        return responseCodes['BAD_SYNTAX_RESPONSE']

    response += responseCodes["NEWNEWS_RESPONSE"] + "\n"

    groups = os.listdir(dbPath)
    groupsCorrected = []
    for group in groups:
        if re.match("^[.][_].*|.DS_Store", group) or not matchWildmat(wildmat, group):
            pass
        else:
            groupsCorrected.append(group)

    for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article)
            # Loop through each article in the newsgroup, return message id if date and time argument greater than article date.
            for file in groupFilesCorrected:
                mID = ""
                dateValid = False
                currentfile = open(dbPath + "/" + group + "/" + file, "r")
                for line in currentfile:
                    if re.match("^Date: ", line):
                        dateLine = line.replace("Date: ", "")
                        dateLine = dateLine.replace("\n", "")
                        # Error handling block for invalid date format in file header. Should never trigger. Here only as precaution.  Current article's message-id not returned to client
                        try:
                            dateValid = compareDates(dateLine, date, time, arg)
                        except ValueError:
                            break
                        if not dateValid:
                            break
                    elif re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        break
                currentfile.close()
                if not dateValid:
                    continue
                else:
                    response += mID + "\n"
    response += "."
    return response

def compareDates(dateLine, dateArg, timeArg, gmtArg):
    dateTime = ""

    articleDate = time.strptime(dateLine, "%a, %d %b %Y %H:%M:%S %z")

    if len(dateArg) == 6:
        dateArg = "20" + dateArg

    if gmtArg.upper() == "GMT":
        dateTime = time.strptime(dateArg+timeArg + " +0000", "%Y%m%d%H%M%S %z")
    else:
        dateTime = time.strptime(dateArg+timeArg + " " + getTimeZoneOffset(), "%Y%m%d%H%M%S %z")

    articleDateSecs = time.mktime(articleDate)
    dateTimeSecs = time.mktime(dateTime)

    if dateTimeSecs <= articleDateSecs:
        return True
    else:
        return False
    
def getTimeZoneOffset():
    negative = False

    offset = time.localtime().tm_gmtoff

    if offset < 0:
        offset = abs(offset)
        negative = True

    timeObj = time.gmtime(offset)

    offsetFormat = time.strftime("%H%M", timeObj)

    if negative:
        offsetFormat = "-" + str(offsetFormat)
    else:
        offsetFormat = "+" + str(offsetFormat)

    return offsetFormat

def writeLog(clientAddr, serverAddr, command, reply):
    log = ""
    replyDescription = ""
    if re.search("\n", reply):
        replyDescription = reply.split("\n")[0]
    else:
        replyDescription = reply
    
    log += time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " "
    log += "from-" + clientAddr + " to-" + serverAddr + " "
    log += "NNTP-[" + command + "] " + replyDescription

    file = open("srv.log", "a")
    file.write(log + "\n")
    file.close()

def generateMessageID(newsgroup):
    domainList = [".com", ".net", ".edu", ".gov"]
    randAlphaNum = ''.join(random.choices(string.ascii_letters + string.digits, k=9))
    domain = random.choice(domainList)

    messageID = "<" + randAlphaNum + "@" + newsgroup + domain + ">"
    return messageID

def getNewFileName(newsgroup):
    newNewsGroup = False
    
    if newsgroup in os.listdir(dbPath):
        newsGroupFiles = os.listdir(dbPath + "/" + newsgroup)

        groupFilesCorrected = []
        for article in newsGroupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(int(article.replace(".txt", "")))
        if len(groupFilesCorrected) == 0:
            highWaterMark = 0
            return "1.txt", newNewsGroup
        else:
            highWaterMark = max(groupFilesCorrected)
            return str(highWaterMark + 1) + ".txt", newNewsGroup

    else:
        newNewsGroup = True
        return "1.txt", newNewsGroup

def findArticle(messageID):
    match = False
        
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for i in groups:
        if re.match("^[.][_].*|.DS_Store", i):
            pass
        else:
            groupsCorrected.append(i)

    # Loop through each newsgroup until match is found.  
    for group in groupsCorrected:
        groupFiles = os.listdir(dbPath + "/" + group)
        groupFilesCorrected = []
        for article in groupFiles:
            if re.match("^[.][_].\w*|.info", article):
                pass
            else:
                groupFilesCorrected.append(article.replace(".txt", ""))
        # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
        for file in groupFilesCorrected:
            currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
            for line in currentfile:
                if re.match("^Message-ID:", line):
                    mID = line.replace("Message-ID: ", "").strip()
                    if mID == messageID:
                        match = True
                        currentfile.close()
                        return match
                elif re.match("\s*\n$", line):
                    break
            currentfile.close()
    return match

def getNewsgroups():
    groups = os.listdir(dbPath)
    groupsCorrected = []
    for i in groups:
        if re.match("^[.][_].*|.DS_Store", i):
            pass
        else:
            groupsCorrected.append(i)
    return groupsCorrected

def sendIHAVE(ip, port, messageID, newsgroup, article):
    global messageIDQueue
    
    externalServerSocket = socket(AF_INET, SOCK_STREAM)
    externalServerSocket.connect((ip, int(port)))

    #Tell server peer that I'm a server
    externalServerSocket.send("Server".encode())

    #Receive server salutation. Do nothing
    externalServerSocket.recv(1024).decode()

    command = "IHAVE " + messageID
    externalServerSocket.send(command.encode())
    response = externalServerSocket.recv(1024).decode()
    writeLog(externalServerSocket.getsockname()[0], externalServerSocket.getpeername()[0], command, response)

    # Initial Response: server is ready to receive articles
    if re.match("^335", response):
        print("Sent [" + command + "] to " + externalServerSocket.getpeername()[0] + ". Waiting on subsequent response\n")
        externalServerSocket.send(newsgroup.encode())
        response = externalServerSocket.recv(1024).decode()
        # Subsequent Response: Error with IHAVE. Don't try again
        if re.match("^437", response):
            writeLog(externalServerSocket.getsockname()[0], externalServerSocket.getpeername()[0], command, response)
            print("[" + command + "] sent to " + externalServerSocket.getpeername()[0] + " failed. Don't try again\n")
        
        # continue to send article
        elif response == ".":
            for line in article:
                externalServerSocket.send(line.encode())
                confirmation = externalServerSocket.recv(1024).decode()
            externalServerSocket.send(".".encode())
            response = externalServerSocket.recv(1024).decode()
            writeLog(externalServerSocket.getsockname()[0], externalServerSocket.getpeername()[0], command, response)
            
            if re.match("^235", response):
                print("[" + command + "] sent to " + externalServerSocket.getpeername()[0] + " successfully received\n")
            elif re.match("^436", response):
                messageIDQueue.put(messageID)
                print("[" + command + "] sent to " + externalServerSocket.getpeername()[0] + " failed. Try again later\n")
    
    # Initial Response: Server doesn't want article
    elif re.match("^435", response):
        writeLog(externalServerSocket.getsockname()[0], externalServerSocket.getpeername()[0], command, response)
        print("[" + command + "] sent to " + externalServerSocket.getpeername()[0] + " failed. Do not try again\n")
    
    # Initial Response: Server doesn't want article, retry later
    elif re.match("^436", response):
        writeLog(externalServerSocket.getsockname()[0], externalServerSocket.getpeername()[0], command, response)
        messageIDQueue.put(messageID)
        print("[" + command + "] sent to " + externalServerSocket.getpeername()[0] + " failed. Try again later\n")

    externalServerSocket.close()

def retryIHAVE(serverDict):
    global messageIDQueue
    while not messageIDQueue.empty():
       time.sleep(2)
       currentMessageID = messageIDQueue.get()
       newsgroup, article = getNewsgroupAndArticle(currentMessageID)
       if newsgroup == "" or not article:
           continue
       for ip, port in serverDict.items():
           sendIHAVE(ip, port, currentMessageID, newsgroup, article)

def getNewsgroupAndArticle(messageID):
        articleLines = []
        match = False
        groups = os.listdir(dbPath)
        groupsCorrected = []
        for i in groups:
            if re.match("^[.][_].*|.DS_Store", i):
                pass
            else:
                groupsCorrected.append(i)

        # Loop through each newsgroup until match is found.  
        for group in groupsCorrected:
            groupFiles = os.listdir(dbPath + "/" + group)
            groupFilesCorrected = []
            for article in groupFiles:
                if re.match("^[.][_].\w*|.info", article):
                    pass
                else:
                    groupFilesCorrected.append(article.replace(".txt", ""))
            # Loop through each article in the newsgroup until match is found.  If no match, go to next file.
            for file in groupFilesCorrected:
                currentfile = open(dbPath + "/" + group + "/" + file + ".txt", "r")
                for line in currentfile:
                    if re.match("^Message-ID:", line):
                        mID = line.replace("Message-ID: ", "").strip()
                        if mID == messageID:
                            match = True
                        else:
                            articleLines.clear()
                            break
                    articleLines.append(line)
                if match:
                    break
                currentfile.close()
            if match:
                return group, articleLines
        if not match:
            return "", articleLines