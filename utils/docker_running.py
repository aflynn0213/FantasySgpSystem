import os

def is_running_in_docker():
    """
    Check if the script is running inside a Docker container.
    
    Returns:
        bool: True if running in Docker, False otherwise.
    """
    return os.getenv("RUNNING_IN_DOCKER", "").lower() == "true" or os.path.exists("/.dockerenv")
