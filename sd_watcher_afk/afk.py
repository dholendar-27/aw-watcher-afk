import logging
import os
import platform
from datetime import datetime, timedelta, timezone
from time import sleep

from sd_client import ActivityWatchClient
from sd_core.models import Event

from .config import load_config

# Determine the current operating system and import appropriate functions.
system = platform.system()

if system == "Windows":
    from .windows import seconds_since_last_input  # fmt: skip
elif system == "Darwin":
    from .macos import seconds_since_last_input  # fmt: skip
elif system == "Linux":
    from .unix import seconds_since_last_input  # fmt: skip
else:
    raise Exception(f"Unsupported platform: {system}")

logger = logging.getLogger(__name__)
td1ms = timedelta(milliseconds=1)


class Settings:
    def __init__(self, config_section, timeout=None, poll_time=None):
        """
        Initialize the class with values from config section.

        @param config_section: Section from which to read configuration
        @param timeout: Timeout in seconds before the user is considered AFK
        @param poll_time: Time in seconds between each activity check
        """
        self.timeout = timeout or config_section["timeout"]
        self.poll_time = poll_time or config_section["poll_time"]

        assert self.timeout >= self.poll_time, "Timeout must be greater than or equal to poll_time"


class AFKWatcher:
    def __init__(self, args, testing=False):
        """
        Initialize the object by reading settings from config and instantiating the ActivityWatchClient.

        @param args: Command-line arguments or input parameters
        @param testing: Whether or not we are testing (default: False)
        """
        # Load configuration and initialize settings
        self.settings = Settings(load_config(testing), timeout=args.timeout, poll_time=args.poll_time)

        # Initialize ActivityWatch client
        self.client = ActivityWatchClient("sd-watcher-afk", host=args.host, port=args.port, testing=testing)
        self.bucketname = f"{self.client.client_name}"

    def ping(self, afk: bool, timestamp: datetime, duration: float = 0):
        """
        Send a heartbeat to the bucket to track AFK or not-AFK status.

        @param afk: True if the user is AFK, otherwise False
        @param timestamp: Timestamp of the event
        @param duration: Duration of the event in seconds (optional)
        """
        data = {"status": "afk" if afk else "not-afk", "app": "afk", "title": "Idle time"}
        e = Event(timestamp=timestamp, duration=duration, data=data)
        pulsetime = self.settings.timeout + self.settings.poll_time
        self.client.heartbeat(self.bucketname, e, pulsetime=pulsetime, queued=True)

    def run(self):
        """
        Start the AFK checking loop in a separate thread.
        """
        logger.info("sd-watcher-afk started")

        # Initialization sleep to allow time for setup
        sleep(1)

        # Create a bucket for AFK status events
        eventtype = "afkstatus"
        self.client.create_bucket(self.bucketname, eventtype, queued=True)

        # Start the heartbeat loop
        with self.client:
            self.heartbeat_loop()

    def heartbeat_loop(self):
        """
        The main loop that checks for user AFK status and sends heartbeats accordingly.
        """
        afk = False

        while True:
            try:
                # Check if parent process is still running on Darwin and Linux (excluding PyInstaller scenarios)
                if system in ["Darwin", "Linux"] and os.getppid() == 1:
                    logger.info("afkwatcher stopped because parent process died")
                    break

                now = datetime.now(timezone.utc)
                seconds_since_input = seconds_since_last_input()
                last_input = now - timedelta(seconds=seconds_since_input)
                logger.debug(f"Seconds since last input: {seconds_since_input}")

                # Check for AFK state change
                if afk and seconds_since_input < self.settings.timeout:
                    # User is no longer AFK
                    logger.info("No longer AFK")
                    self.ping(afk=False, timestamp=last_input)
                    afk = False
                    self.ping(afk=False, timestamp=last_input + td1ms)
                elif not afk and seconds_since_input >= self.settings.timeout:
                    # User has become AFK
                    logger.info("Became AFK")
                    self.ping(afk=True, timestamp=last_input)
                    afk = True
                    self.ping(afk=True, timestamp=now)
                else:
                    # Send a regular heartbeat if no state change
                    if afk:
                        self.ping(afk=True, timestamp=now)
                    else:
                        self.ping(afk=False, timestamp=last_input)

                sleep(self.settings.poll_time)

            except KeyboardInterrupt:
                logger.info("sd-watcher-afk stopped by keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Unexpected error occurred: {e}")
                break
