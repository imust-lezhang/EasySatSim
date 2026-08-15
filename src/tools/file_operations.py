import configparser
import numpy as np
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_ini_file_to_dict(file_path):
    # Create a configuration parser object
    config = configparser.ConfigParser()
    # Read the INI file
    config.read(file_path, encoding='utf-8')
    # Create a dictionary to store configuration data
    config_dict = {}
    # Traverse all sections and add them to the dictionary
    for section in config.sections():
        config_dict[section] = {}
        for key, value in config.items(section):
            config_dict[section][key] = value
    return config_dict


def get_project_file_path(file_path):
    path = Path(file_path)
    if path.is_absolute() or path.exists():
        return path

    project_path = (PROJECT_ROOT / "src" / path).resolve()
    if project_path.exists():
        return project_path
    return path


def get_project_output_path(file_path):
    path = Path(file_path)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / "src" / path).resolve()


def load_npy_to_array(file_path):
    return np.load(get_project_file_path(file_path))


class DataWriter:
    def __init__(self, filename, title_row):
        """Try to open the file, exception handling ensures feedback on errors"""
        try:
            file_path = get_project_output_path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file = open(file_path, mode='w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file)
            self.write_data(data=title_row)
        except Exception as e:
            print(f"Failed to open the file: {e}")
            raise


    def write_data(self, data):
        """Try to write data, exception handling ensures feedback on errors"""
        try:
            self.writer.writerow(data)
            self.file.flush()
        except Exception as e:
            print(f"Failed to write data: {e}")
            raise


    def close(self):
        """Try to close the file, exception handling ensures feedback on errors"""
        try:
            self.file.close()
        except Exception as e:
            print(f"Failed to close the file: {e}")
            raise
