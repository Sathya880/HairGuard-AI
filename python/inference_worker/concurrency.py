from threading import Semaphore

MAX_CONCURRENT_INFERENCE = 2

inference_semaphore = Semaphore(MAX_CONCURRENT_INFERENCE)