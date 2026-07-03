import os
from src.streaming.noaa_stream_producer import run_forever

if __name__ == '__main__':
    run_forever(int(os.getenv('STREAM_POLL_INTERVAL_SECONDS', '360')))
