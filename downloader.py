import logging
import os
import zipfile
from typing import List, Union
from urllib.request import urlopen

from lang import Lang


LINKS = {
    Lang.RO: {
        'models': {
            'diacritice': {
                'small': {
                    "link": "https://nextcloud.readerbench.com/index.php/s/HbNRckT5LHa4cc4/download",
                    "version": "https://nextcloud.readerbench.com/index.php/s/wtcqmsb6CmpnwdN/download"
                },
                'base': {
                    "link": "https://nextcloud.readerbench.com/index.php/s/Y56BLDLtYZ6WRRa/download",
                    "version": "https://nextcloud.readerbench.com/index.php/s/GRsJP7yFreeicaR/download"
                }
            },
        },
    },
}

def download(link: str, destination: str) -> str:
    with urlopen(link) as webpage:
        filename = webpage.info().get_filename()
        content = webpage.read()
    with open(os.path.join(destination, filename), 'wb' ) as f:
        f.write(content)
    return os.path.join(destination, filename)
    
def download_folder(link: str, destination: str):
    os.makedirs(destination, exist_ok=True)     
    filename = download(link, destination)
    logging.info('Downloaded {}'.format(filename))
    if zipfile.is_zipfile(filename):
        logging.info('Extracting files from {}'.format(filename))
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(destination)
        os.remove(filename)


def download_file(link: str, destination: str):
    os.makedirs(destination, exist_ok=True)
    filename = download(link, destination)
    logging.info('Downloaded {}'.format(filename))


def download_model(lang: Lang, name: Union[str, List[str]]) -> bool:
    if isinstance(name, str):
        name = ['models', name]
    if lang not in LINKS:
        logging.info('{} not supported.'.format(lang))
        return False
    path = "/".join(name)
    root = LINKS[lang]
    for key in name:
        if key not in root:
            logging.info('Remote path not found {} ({}).'.format(path, key))
            return False
        root = root[key]
    logging.info("Downloading model {} for {} ...".format(path, lang.value))
    link = root['link'] if isinstance(root, dict) else root
    folder = "resources/{}/{}".format(lang.value, "/".join(name[:-1]))
    download_folder(link, folder)
    return True
    
def check_version(lang: Lang, name: Union[str, List[str]]) -> bool:
    logging.info('Checking version for model {}, {}'.format(name, lang.value))
    if isinstance(name, str):
        name = ['models', name]
    path = "/".join(name)
    folder = "resources/{}/{}".format(lang.value, path)
    try:
        local_version = read_version(folder + "/version.txt")
    except FileNotFoundError:
        logging.info('Local model {} for {} not found.'.format(path, lang))
        return True

    if lang not in LINKS:
        logging.error('{} not supported.'.format(lang))
        return False
    root = LINKS[lang]
    for key in name:
        if key not in root:
            logging.error('Remote path not found {} ({}).'.format(path, key))
            return False
        root = root[key]
    if isinstance(root, dict):
        filename = download(root['version'], "resources/")
        try:
            remote_version = read_version(filename)
        except FileNotFoundError:
            logging.warning('Error reading remote version for {} ({})'.format(path, lang))
            return False
        return newer_version(remote_version, local_version)
    else:
        logging.error('Could not find version link in links json')
        return True


def read_version(filename: str) -> str:
    with open(filename, "r") as f:
        return f.readline()


def newer_version(remote_version: str, local_version: str) -> bool:
    remote_version = remote_version.split(".")
    local_version = local_version.split(".")

    for a, b in zip(remote_version, local_version):
        if int(a) > int(b):
            logging.info('Remote version {} is ahead of local version {}'.format(remote_version, local_version))
            return True
        if int(a) < int(b):
            logging.info('Remote version {} is behind of local version {}'.format(remote_version, local_version))
            return False
    logging.info('Remote version {} is the same as local version {}'.format(remote_version, local_version))
    return False
    