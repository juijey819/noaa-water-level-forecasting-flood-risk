from src.streaming.noaa_stream_producer import run_once

if __name__ == '__main__':
    print(f'Sent messages: {run_once()}')
