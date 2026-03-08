import time


class Timer:
    def __init__(self, name: str = ""):
        self.name = name or "process"
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        print(f"Starting {self.name}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.perf_counter()
        elapsed = end - self.start
        print(f"...{self.name}: {elapsed:.2f} s")
