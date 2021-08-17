import socket
import os.path
import sys

    
def terminal_error(message, soc=None):
    print(message)
    if soc != None:
        soc.close()
    quit() 


def get_ip(ip):
    try:
        ip = socket.gethostbyname(ip)
        return ip
    except socket.error as message:
        terminal_error("Error getting IP address: {}".format(message))


def get_port(port):
    try:
        port = int(port)
        if port < 1024 or port > 64000:
            terminal_error("Please enter a valid port between 1,024 and 64,000 inclusive.")
    except ValueError:
        terminal_error("Please enter a valid port number.")
    return port
        
def get_file(file_to_send):
    if os.path.exists(file_to_send): 
        terminal_error("The indicated file already exists. Quitting to avoid over-writing existing files")
    return file_to_send
   
    
def setup():
    if len(sys.argv) == 4:
        ip = get_ip(sys.argv[1])
        port = get_port(sys.argv[2])
        file_to_send = get_file(sys.argv[3])
        return (ip, port, file_to_send)
    else:
        terminal_error("Please enter 3 parameters: ip/domain, port, and filename.")

    
def connect_socket(ip, port):
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as message:
        terminal_error("Error creating socket: {}".format(message))
        
    try:
        soc.connect((ip, port))
        return soc
    except socket.error as message:
        terminal_error("Error connecting to port: {}".format(message), soc)
    
    
    
def prepare_file_request(file_to_send):
    file_request = 0x497E << (3 * 8)
    file_request = file_request ^ (0x1 << (2 * 8))
    file_request = file_request ^ (len(file_to_send))
    
    return (file_request).to_bytes((file_request.bit_length() + 7) // 8, byteorder='big') + file_to_send
         
    
def decode_save_file(soc, filename):
    try:
        array = bytearray(soc.recv(8))
    except Exception as e:
        terminal_error("Error receiving header: {}".format(e), soc)
       
    if len(array) < 8:
        terminal_error("Could not receive full response header", soc)
    
    
    magicNo = (array[0] << 8) ^ array[1] 
    if magicNo != 0x497e:
        terminal_error("Magic no of received file is not correct", soc)
    
    _type = array[2]
    if _type != 2:
        terminal_error("Incorrect type of file response", soc)
    
    status_code = array[3]
    if status_code == 0:
        terminal_error("Status code indicates that the file does not exist in server", soc)
    
    if status_code == 1:
        data_len = (array[4] << 24) ^ (array[5] << 16) ^ (array[6] << 8) ^ array[7]
        header_bytes_received = len(array)
        f = filename
        try:
            f = open(filename, 'w')
        except Exception as e:
            terminal_error("Error opening file for writing: {}".format(e), soc)        
            
        try:
            bytes_received = 0
            array = soc.recv(4096)
            while len(array) != 0:
                for i in range(len(array)):
                    f.write(chr(array[i]))
                    bytes_received += 1
                array = soc.recv(4096)
      
            f.close()
            
            if bytes_received != data_len:
                terminal_error("Not all bytes received! {} Indicated, {} received".format(data_len, bytes_received), soc)
            print("Recieved {} bytes including header and wrote {} bytes to file".format(header_bytes_received + bytes_received, bytes_received))        
        except socket.error as message:
            f.close()
            terminal_error("Error whilst reading socket: {}".format(message), soc)    
        
            
    soc.close()
    quit()
    
def main():
    ip, port, file_to_send = setup()
    
    soc = connect_socket(ip, port)
    file_request = prepare_file_request(file_to_send.encode("utf-8"))
    soc.send(file_request)    
    soc.settimeout(1.0)
    try:
        decode_save_file(soc, file_to_send)
    except socket.timeout:
        print("Operation timed out")
        soc.close()
        
    
if __name__ == "__main__":
    main()