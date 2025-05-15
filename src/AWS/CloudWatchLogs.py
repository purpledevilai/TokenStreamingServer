import logging

def get_logger(name: str = __name__, log_level: str = "INFO") -> logging.Logger:
    """
    Returns a logger with a specified name and log level.

    :param name: Logger name, typically set to __name__ (a special Python variable that
                 holds the module's name). This helps organize logs by module.
    :param log_level: Logging level as a string (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").

    Log levels (in order of verbosity): DEBUG < INFO < WARNING < ERROR < CRITICAL.
    """
    # Create a logger with the specified name
    logger = logging.getLogger(name)
    
    # Set the logging level based on the log_level parameter
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Add a console handler if no handlers exist (prevents duplicates)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)

    return logger
