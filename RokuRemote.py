import time
import socket
import curses
import os
import requests
import json
from tabulate import tabulate

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class RokuRemote(object):
    """
    RokuRemote is a simple tool for discovering and interacting with Roku devices on the network.    
    """
    def __init__(self):
        super(RokuRemote, self).__init__()
        self.verbose = True
        self.devices = [] #(IP, MAC, NICK)
        self.mcast_target = ('239.255.255.250', 1900)
        self.port = 8060
        self.active_device_ip = None
        self.discovery_request = f'M-SEARCH * HTTP/1.1\r\n' \
                            f'HOST:239.255.255.250:1900\r\n' \
                            f'ST:roku:ecp\r\n' \
                            f'MX:2\r\n' \
                            f'MAN:"ssdp:discover"\r\n' \
                            f'\r\n'
        self.command_key_map = { #This is used to map the strings from key detection in curses to the Roku API endpoint /keypress/. {curses_output:keypress}
            "KEY_UP": "Up",
            "KEY_DOWN": "Down",
            "KEY_LEFT": "Left",
            "KEY_RIGHT": "Right",
            "KEY_BACKSPACE": "Back",
            "KEY_HOME": "Home",
            "KEY_IC": "Select",
            "k": "VolumeUp", #When the Num Lock is on, the keypad +/- symbol report as k/m respectively using curses.
            "m": "VolumeDown",
            "+": "VolumeUp",
            "-": "VolumeDown"            
        }
        self.remote_quit_key = 'q'
        self.main_menu_options = [
            ["DISCOVER DEVICES"],
            ["IDENTIFY DEVICE"],
            ["SELECT DEVICE"],
            ["LOAD CONFIG"],
            ["SAVE CONFIG"],
            ["REMOTE"],
            ["EXIT"]
        ]
        self.saved_config = ".roku_config"
        self.devices = []
        self.active_device = {
            'mac': None,
            'ip' : None,
            'nick': None
        }
        self.logo = f"{bcolors.HEADER}   _____       _          _____                      _       \r\n" \
            f"  |  __ \     | |        |  __ \                    | |      \r\n" \
            f"  | |__) |___ | | ___   _| |__) |___ _ __ ___   ___ | |_ ___ \r\n" \
            f"  |  _  // _ \| |/ / | | |  _  // _ \ '_ ` _ \ / _ \| __/ _ \\\r\n" \
            f"  | | \ \ (_) |   <| |_| | | \ \  __/ | | | | | (_) | ||  __/\r\n" \
            f"  |_|  \_\___/|_|\_\\\__,_|_|  \_\___|_| |_| |_|\___/ \__\___|\r\n{bcolors.ENDC}"

    def clear_screen(self):
        # windows
        if os.name == 'nt': 
            os.system('cls') 
        # unix-based
        elif os.name == 'posix': 
            os.system('clear') 
        else:
            print(f"[ERROR] Failed to detect OS type with os.name() | Detected Type: {os.name}")

    def discover_devices(self, timeout=3):
        """
        Tries to discover Roku devices on the network with SSDP by using multicast request to self.mcast_target.
        https://support.pelco.com/s/article/How-a-UPnP-Search-works-1538586696122
        """
        print("[INFO] Attempting to discover devices with SSDP.")
        socket_instance = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        socket_instance.settimeout(timeout)
        socket_instance.sendto(bytes(self.discovery_request, 'utf8'), self.mcast_target)
        #Wait for response or timeout
        try:
            while True:
                raw = socket_instance.recvfrom(1024)
                device_data = raw[0]
                #Parse out the MAC and IP from the response
                ip = device_data.decode('utf-8').split('\r\n')[6].split(" ")[-1].replace("http://", "").replace("/", "").split(":")[0]
                mac = device_data.decode('utf-8').split('\r\n')[8].split(" ")[-1].split(";")[0].replace("MAC=", "")
                if ip != None:
                    if ip not in (dev['ip'] for dev in self.devices):
                        self.devices.append({"ip":ip, "mac": mac, "nick":None})
                        if self.verbose == True:
                            print(f"[INFO] Discovered Device! IP: {ip} | MAC: {mac}")
                    else:
                        print("[INFO] Discovered duplicate device, skipping...")
                
        except socket.timeout:
            pass
        socket_instance.close()

    def select_device(self):
        """
        Allows you to select a discovered device as the actively controlled device.
        """
        if not self.devices:
            print("[INFO] No Devices Have Been Discovered...")
            print("[INFO] Please run Discovery first.")
        else:
            rows =  [x.values() for x in self.devices]
            print(tabulate(rows, headers=["DEVICE ID", "IP", "MAC", "NICK"], tablefmt="presto", showindex="always"))
            print("")
            selection = int(input("Please select the Roku Device ID to control: "))
            if selection in range(len(self.devices)):
                self.active_device['ip'] = self.devices[selection]['ip']
                self.active_device['mac'] = self.devices[selection]['mac']
                if self.devices[selection]['nick']:
                    self.active_device['nick'] = self.devices[selection]['nick']
                self.url = f"http://{self.active_device['ip']}:{self.port}/keypress/"
            else:
                print(f"[ERROR] Selection falls outside of device list range. (Max = {len(self.devices)})")
                return False

    def identify_device(self, ip=None):
        """
        Simple function for anyone to visually distinguish multiple devices on a network.
        Accomplished by pressing the volume up and down key on a discovered device.
        """
        rows =  [x.values() for x in self.devices]
        print(tabulate(rows, headers=["DEVICE ID", "IP", "MAC", "NICK"], tablefmt="presto", showindex="always"))
        print("")
        selection = int(input("Please select the Roku Device ID to identify: "))
        if selection in range(len(self.devices)):
            self.url = f"http://{self.devices[selection]['ip']}:{self.port}/keypress/"
            print(f"[INFO] Attempting identification on {self.devices[selection]['ip']}")
            print("[INFO] In 3 seconds, the selected device will have the volume level increased and then decreased.")
            for n in range(1, 4):
                print(f"[INFO] {n}...")
                time.sleep(1)
            #Volume Up
            requests.post(self.url + "VolumeUp")
            time.sleep(1)
            requests.post(self.url + "VolumeDown")
            if not input(f"[INPUT] Please confirm that the device @ {self.devices[selection]['ip']} was identified. [y/N]").lower().strip()[:1] == "y":
                return False
            else:
                #Need to get IP from the MAC in the ssdp response
                if not input("[INPUT] Would you like to give the device a nickname? [y/N]").lower().strip()[:1] == "n":
                    self.devices[selection]['nick'] = input("[INPUT] Please select a nickname: ")
                    return True
                else:
                    return False
        else:
            print(f"[ERROR] Selection falls outside of device list range. (Max = {len(self.devices)})")
            return False

    def key_to_action(self, term):
        """
        Function called by curses to detect keypress via curses.wrapper()
        POSTs a supported keypress to Roku API endpoint /keypress/
        """
        term.nodelay(True)
        term.clear()
        key_list = []
        for n in self.command_key_map:
            key_list.append([n, self.command_key_map[n]])
        # term.addstr(self.logo) #curses doesnt seem to like the logo formatting        
        term.addstr("ROKU COMMAND LIST: \n")
        term.addstr(tabulate(key_list, tablefmt="fancy_grid"))
        term.addstr("\n\n Press 'q' to return to the main menu.")
        x = True
        while x == True:
            try:
                keystroke = term.getkey()
                if keystroke == self.remote_quit_key:
                    x = False
                else:
                    command = self.command_key_map[keystroke]
                    requests.post(self.url + command)
                    time.sleep(0.2)
            except Exception as e:
                #No keystroke, loop again
                pass

    def validate_config(self, cfg_json):
        try:
            json.dumps(cfg_json)
            return True
        except ValueError as error:
            print(f"[ERROR] Invalid JSON Format: {error}")
            return False

    def load_config(self):
        # read file
        try:
            with open(self.saved_config, 'r') as f:
                data = f.read()
            self.active_device = json.loads(data)
            if self.active_device not in self.devices:
                self.devices.append(self.active_device)
            time.sleep(1)
            self.active_device_ip = self.active_device['ip']
            self.url = f"http://{self.active_device['ip']}:{self.port}/keypress/"
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            time.sleep(1)
            return False

    def save_config(self):
        if self.validate_config(self.active_device):
            try:
                with open(self.saved_config, 'w') as f:
                    json.dump(self.active_device, f)
                    print(f"[INFO] Successfully saved JSON config to {self.saved_config}")
            except Exception as e:
                print(f"[ERROR] Failed to save config: {e}")

        else:
            print("[ERROR] Failed to validate JSON config file. Config was not saved. ")
            time.sleep(1)
            return False

    def main_menu(self):
        self.clear_screen()
        print(self.logo)
        if self.active_device['nick'] and self.active_device['ip'] :
            print(f"\t  {bcolors.OKBLUE} ACTIVE DEVICE: {bcolors.OKGREEN} {self.active_device['nick']} @ {self.active_device['ip']}  {bcolors.ENDC}")
        elif self.active_device['ip']:
            print(f"\t\t{bcolors.OKBLUE} ACTIVE DEVICE: {bcolors.OKGREEN} {self.active_device['ip']} {bcolors.ENDC}")    
        else:
            print(f"\t\t{bcolors.OKBLUE} ACTIVE DEVICE: {bcolors.WARNING} NONE {bcolors.ENDC}")
        print("")
        print(tabulate(self.main_menu_options,tablefmt="fancy_grid", showindex="always"))
        print("")
        try:
            option = int(input("SELECT A MENU OPTION NUMBER: "))
        except:
            print("[ERROR] Please choose a valid menu option integer.")
            time.sleep(2)
            self.main_menu()
        if option in range(len(self.main_menu_options)):
            if option == 0:
                self.clear_screen()
                print(self.logo)
                self.discover_devices()
                self.main_menu()
            elif option == 1:
                self.clear_screen()
                print(self.logo)
                self.identify_device(ip=self.active_device_ip)
                self.main_menu()
            elif option == 2:
                self.clear_screen()
                print(self.logo)
                self.select_device()
                self.main_menu()
            elif option == 3: #Load device
                self.clear_screen()
                print(self.logo)
                self.load_config()
                self.main_menu()
            elif option == 4: #Save device
                self.clear_screen()
                print(self.logo)
                self.save_config()
                self.main_menu()
            elif option == 5: #Remote
                self.clear_screen()
                curses.wrapper(self.key_to_action)
                curses.endwin()
                self.main_menu()
            elif option == 6:
                exit()
            else:
                self.main_menu()
        else:
            print("[ERROR] Please choose a valid menu option integer.")
            time.sleep(2)
            self.main_menu()

if __name__ == "__main__":
    roku = RokuRemote()
    roku.main_menu()
