import socket
from datetime import datetime
import os.path
import sys


def get_port():
    port = sys.argv[1]
    
    try:
        port = int(port)
        if port < 1024 or port > 64000:
            print("Please enter a valid port between 1,024 and 64,000 inclusive.")
            quit()
        return port
    except ValueError:
        print("Please enter a valid port number.")
        quit()    

def terminal_error(message, soc):
    print(message)
    soc.close()
    quit()  

def non_terminal_error(message, soc):
    print(message)
    soc.close()
    return False

def setup_socket(port):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        soc.bind(('', port))
    except socket.error as message:
        terminal_error("Error whilst binding socket: {}".format(message), soc)
        
    try:
        soc.listen()
        return soc
    except socket.error as message: 
        terminal_error("Error whilst listening to socket: {}".format(message), soc)      
        
def find_connection(soc):
    conn, address = soc.accept()
    print("Incoming connection at {0} from {1} port {2}".format(datetime.now(), address[0], address[1]))
    return (conn, address)  
    

def receive_decode_file(soc):
    try:
        array = bytearray(soc.recv(5))
    except Exception as e:
        return non_terminal_error("Error whilst receiving request: {}".format(e), soc)
        
    if len(array) < 5:
        return non_terminal_error("Did not receive the full request header", soc)
    
    magicNo = (array[0] << 8) ^ array[1]
    if magicNo != 0x497e:
        return non_terminal_error("Magic number of received file is not correct", soc)
    
    _type = array[2]
    if _type != 1:
        return non_terminal_error("Incorrect type of file request", soc)
    
    #int.from_bytes(array[3:], byteorder="big")
    filename_len = (array[3] << 8) ^ array[4]
    if filename_len < 1 or filename_len > 1024:
        return non_terminal_error("Filename length too long", soc)
    
    filename = ""
    filename_array = bytearray(soc.recv(filename_len))
    
    if len(filename_array) != filename_len:
        return non_terminal_error("Indicated header filename length does not match actual filename length", soc)
    
    for i in range(filename_len):
        filename += chr(filename_array[i])    
    
    return filename
    

def send_response(filename, conn):
    if os.path.exists(filename):
        filedata = None
        try:
            filedata = open(filename, 'r')
            bytes_transferred = conn.send(prepare_file_response(filedata.read().encode("utf-8")))
            filedata.close()
            conn.close()
            print("Successfully transferred {} bytes".format(bytes_transferred))
        except:
            print("Error opening and reading file")
            conn.send(prepare_file_response())
            conn.close()
    else:
        conn.send(prepare_file_response())
        conn.close()
        print("File does not exist")
    
def prepare_file_response(filedata=None):
    if filedata != None:
        file_request = 0x497E << (6 * 8)
        file_request = file_request ^ (0x2 << (5 * 8))        
        file_request = file_request ^ (0x1 << (4 * 8))
        file_request = file_request ^ (len(filedata))
        
        file_request = (file_request).to_bytes((file_request.bit_length() + 7) // 8, byteorder='big') + filedata
    else:
        file_request = 0x497E << (6 * 8)
        file_request = file_request ^ (0x2 << (5 * 8))
        file_request = (file_request).to_bytes((file_request.bit_length() + 7) // 8, byteorder='big')
    return file_request

        
def main():
    port = get_port()
    soc = setup_socket(port)
    
    while True:
        conn, address = find_connection(soc)
        conn.settimeout(1.0)
        try:
            filename = receive_decode_file(conn)
            if filename is not False:
                send_response(filename, conn)
        except socket.timeout:
            print("Socket timed out during operation")
            conn.close()
    
    
    
if __name__ == "__main__":
    main()