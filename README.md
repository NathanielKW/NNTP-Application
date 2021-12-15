
This project is a client-server NNTP application.  A client can connect to a server running NNTPServer.py to retrieve news articles contained within the server's database.  The application is multithreaded, so multiple clients can connect and retrieve articles from a single server concurrently.  Additionally, multiple servers can be set up to connect and share articles in a peer-to-peer network.  Server's are in one of two states (either in Transit state or Reader state). While a server is in Transit state, end-user clients can continue to retrieve articles, while the server can accept articles from other server peers.  While the server is in Reader state, end-user clients have the capability to post articles to their respective server.  In this Reader state, servers cannot accept articles from other server peers.  Once an article has been successfully posted while in Reader state, the server will automatically attempt to issue the "IHAVE" command and send the newly posted article to a server's peers (listed in server.conf, preficed by RSOCK_ADDR).  Upon a server start-up, the initial state of the server is Transit.  An end-user client can issue a "MODE READER" command to switch the state of the server to Reader, if MODE_SWITCH is set to "ON" in the server configuration file.  Once all end-user clients with posting intent disconnect from a server, the server will automatically revert to Transit state.

To run, simply type command:
    "Python NNTPServer.py" or "Python NNTPClient.py"

Note:  article database directory and configuration files must be present in the same directory
       as the python source code

Note:  config file lines beginning with "//" are commented out

For more information on the NNTP article, view rfc 3977 https://datatracker.ietf.org/doc/html/rfc3977
