from flask_socketio import SocketIO

class WsSocket:
    socketio : SocketIO = None

    def connectSocket(socketio):
        WsSocket.socketio = socketio

    def send_messages(msg, data):
        ''' Simple WS Sender'''
        WsSocket.socketio.emit(msg, {'data': data})
