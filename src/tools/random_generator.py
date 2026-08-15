import string
import secrets
import random
import numpy as np


# Generate a random IPv4 address
def generate_random_ipv4():
    return f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


# Generate a random MAC address
def generate_random_mac():
    return ':'.join(f"{random.randint(0, 255):02X}" for _ in range(6))


# Generate a secure session ID
def generate_random_session_id():
    session_id = secrets.token_hex(16)  # Generate a 32-character hexadecimal string
    return session_id


# Generate random username and password
def generate_random_credentials(username_length=8, password_length=12):
    characters = string.ascii_letters + string.digits  # Including letters and digits
    random_username = ''.join(secrets.choice(characters) for _ in range(username_length))
    random_password = ''.join(secrets.choice(characters) for _ in range(password_length))
    return random_username, random_password


def generate_random_user_position(population_array, latitude_min=-70, latitude_max=70):
    if latitude_min >= latitude_max:
        raise ValueError("latitude_min must be smaller than latitude_max.")

    for _ in range(1000):
        latitude, longitude = _sample_population_position(population_array)
        if latitude_min <= latitude <= latitude_max:
            return latitude, longitude

    latitude = min(max(latitude, latitude_min), latitude_max)
    return latitude, longitude


def _sample_population_position(population_array):
    # Convert array elements to probabilities
    probabilities = population_array / population_array.sum()
    # Randomly select a block, numpy.random.choice can select according to the given probability distribution
    flat_index = np.random.choice(population_array.size, p=probabilities.flatten())
    # Convert a one-dimensional index to a two-dimensional index
    lat_index, lon_index = np.unravel_index(flat_index, population_array.shape)
    # Randomly select a more specific point within the selected 1-degree by 1-degree block.
    latitude = 90 - lat_index + np.random.uniform(0, 1)
    longitude = lon_index + np.random.uniform(0, 1) - 180
    return latitude, longitude
