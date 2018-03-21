import threading
import datetime
import json


class JsonWriter:
    # class to sequentially write json objects

    max_cache_len = 1000

    def __init__(self, filename, json_encoder=json.JSONEncoder):
        self._filename = filename
        self._file = open(filename, "w")
        self._cache = []
        self._write_lock = threading.Lock()
        self._cache_copy_lock = threading.Lock()
        self._index = 0
        self.json_encoder = json_encoder

    def add_to_write(self, data):
        data["datetime"] = str(datetime.datetime.now())

        with self._cache_copy_lock:
            if len(self._cache) >= JsonWriter.max_cache_len:
                cache_copy = self._cache[:]
                self._cache = []
                self.async_write(cache_copy)

        self._cache.append(data)

    def async_write(self, data):
        write_thread = threading.Thread(target=lambda: self._write(data))
        write_thread.start()

    def _write(self, data):
        with self._write_lock:
            self._unsafe_write(data)

    def _write_and_close_if_open(self, data):
        with self._write_lock:
            if self._file.closed:
                return
            self._unsafe_write(data)
            self._file.close()

    def _unsafe_write(self, data):
        for d in data:
            d["index"] = self._index
            self._index += 1
            self._file.write(json.dumps(d, cls=self.json_encoder) + "\n")
            self._file.flush()

    def close(self):
        self._write_and_close_if_open(self._cache)

    def __del__(self):
        print("JsonWriter {} __del__".format(self._filename))
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
