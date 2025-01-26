# Khinsider downloader

Script to download soundtracks from https://downloads.khinsider.com

Requires python 3.12+ (May work on versions down to 3.10)

## Installation
```bash
$ pip install git+https://github.com/NovaHFly/khinsider_downloader
```

## Usage
- Linux
```bash
$ python3 -m khinsider [-h] [--threads THREADS] (URLS ... | --file FILE)
```
- Windows
```cmd
> py -m khinsider [-h] [--threads THREADS] (URLS ... | --file FILE)
```

## Used libraries
- [httpx](https://www.python-httpx.org/)
- [tenacity](https://github.com/jd/tenacity)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- [lxml](https://lxml.de/)
