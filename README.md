# RokuRemote

![](https://i.imgur.com/hmChJKk.png)

RokuRemote is a simple tool for discovering and interacting with Roku devices on the network.    

## Prerequisites

Requires Python >=3.6 and corresponding pip.

Roku device must be on the same network segment to recieve the SSDP multicast.

For example, this does not work from a Qubes VM connected to your LAN.

### Installing

```
pip3 install -r requirements.txt
```

### Usage

```
python3 RokuRemote.py
```

You can save an active device configuration in the menu. It will be saved to .roku_config for later loading.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
